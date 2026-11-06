from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import STUDENT_COOKIE, clear_cookie, client_ip, rate_limit, require_student, set_cookie
from ..models import Club, EmailOTP, Membership, PendingRegistration, Student
from ..schemas import (MembershipOut, MessageOut, PendingOut, RegisterIn, RegistrationResult, SendOtpIn,
                       StudentLoginIn, StudentOut, VerifyOtpIn)
from ..security import create_token, generate_otp, hash_otp
from ..services import email_service
from ..services.captcha_service import verify_captcha
from ..services.membership_service import check_otp, complete_registration, get_valid_link
from ..utils import aware, utcnow

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _membership_out(m: Membership) -> MembershipOut:
    return MembershipOut(membership_code=m.membership_code, status=m.status, joined_at=m.joined_at,
                         club_name=m.club.name, club_slug=m.club.slug)


def _start_student_session(response: Response, student: Student) -> None:
    ttl = timedelta(days=settings.student_session_days)
    set_cookie(response, STUDENT_COOKIE, create_token(str(student.id), "student", ttl), int(ttl.total_seconds()))


@router.post("/register", response_model=PendingOut, dependencies=[Depends(rate_limit("register", 10, 3600))])
def register(data: RegisterIn, db: Session = Depends(get_db)):
    """Step 1: validate the form and park it. No student or membership exists until the OTP is verified."""
    club = db.scalar(select(Club).where(Club.slug == data.club_slug))
    if not club:
        raise HTTPException(404, "Club not found")
    domains = settings.email_domains
    if domains and data.email.rsplit("@", 1)[-1] not in domains:
        raise HTTPException(422, "Please use your college email address")
    link = None
    if data.link_token:
        link = get_valid_link(db, data.link_token, club.id)
    elif settings.require_registration_link:
        raise HTTPException(403, "A registration link from the club admin is required")

    existing = db.scalar(select(Student).where((Student.usn == data.usn) | (Student.email == data.email)))
    if existing:
        if existing.usn != data.usn or existing.email != data.email:
            raise HTTPException(409, "This USN or email is already registered with different details")
        if db.scalar(select(Membership.id).where(Membership.student_id == existing.id, Membership.club_id == club.id)):
            raise HTTPException(409, "You are already a member of this club")

    db.execute(delete(PendingRegistration).where(PendingRegistration.email == data.email))
    pending = PendingRegistration(
        usn=data.usn, full_name=data.full_name, email=data.email, phone=data.phone, branch=data.branch,
        joining_year=data.joining_year, club_id=club.id, link_id=link.id if link else None,
        expires_at=utcnow() + timedelta(minutes=settings.pending_ttl_minutes),
    )
    db.add(pending)
    db.commit()
    return PendingOut(pending_id=pending.id)


@router.post("/send-otp", response_model=MessageOut, dependencies=[Depends(rate_limit("send_otp", 6, 600))])
def send_otp(data: SendOtpIn, background: BackgroundTasks, db: Session = Depends(get_db)):
    generic = MessageOut(message="If the details are valid, a verification code has been emailed.")
    if data.purpose == "register":
        if not data.pending_id:
            raise HTTPException(422, "pending_id is required")
        pending = db.get(PendingRegistration, data.pending_id)
        if not pending or aware(pending.expires_at) < utcnow():
            raise HTTPException(404, "Registration session expired. Please register again.")
        email = pending.email
    else:
        if not data.email:
            raise HTTPException(422, "email is required")
        email = data.email.lower()
        if not db.scalar(select(Student.id).where(Student.email == email, Student.email_verified.is_(True))):
            return generic  # do not reveal whether the email is registered

    last = db.scalar(select(EmailOTP).where(EmailOTP.email == email, EmailOTP.purpose == data.purpose,
                                         EmailOTP.consumed_at.is_(None))
                     .order_by(EmailOTP.created_at.desc(), EmailOTP.id.desc()).limit(1))
    if last and (utcnow() - aware(last.created_at)).total_seconds() < settings.otp_resend_cooldown_seconds:
        raise HTTPException(429, f"Please wait {settings.otp_resend_cooldown_seconds} seconds before requesting another code")

    otp = generate_otp()
    db.add(EmailOTP(email=email, purpose=data.purpose, otp_hash=hash_otp(email, data.purpose, otp),
                    expires_at=utcnow() + timedelta(seconds=settings.otp_ttl_seconds)))
    db.commit()
    background.add_task(email_service.send_otp_email, email, otp, max(1, settings.otp_ttl_seconds // 60))
    return MessageOut(message="If the details are valid, a verification code has been emailed.")


@router.post("/verify-otp", response_model=RegistrationResult, dependencies=[Depends(rate_limit("verify_otp", 20, 600))])
def verify_otp(data: VerifyOtpIn, request: Request, response: Response, background: BackgroundTasks,
               db: Session = Depends(get_db)):
    """Step 3: captcha + OTP check, then create the verified student and the unique club ID."""
    verify_captcha(data.captcha_token, client_ip(request))
    pending = db.get(PendingRegistration, data.pending_id)
    if not pending or aware(pending.expires_at) < utcnow():
        raise HTTPException(404, "Registration session expired. Please register again.")
    check_otp(db, pending.email, "register", data.otp)
    try:
        student, membership, club = complete_registration(db, pending)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "This USN, email or membership already exists")
    background.add_task(email_service.send_welcome_email, student.email, student.full_name, club.name,
                        membership.membership_code, membership.status)
    _start_student_session(response, student)
    return RegistrationResult(membership=_membership_out(membership), student=StudentOut.model_validate(student))


@router.post("/login", response_model=StudentOut, dependencies=[Depends(rate_limit("student_login", 15, 600))])
def student_login(data: StudentLoginIn, response: Response, db: Session = Depends(get_db)):
    """Passwordless student login: request a code with /send-otp (purpose=login), then post it here."""
    email = data.email.lower()
    check_otp(db, email, "login", data.otp)
    student = db.scalar(select(Student).where(Student.email == email, Student.email_verified.is_(True)))
    if not student:
        raise HTTPException(400, "Invalid code")
    db.commit()
    _start_student_session(response, student)
    return student


@router.post("/logout", response_model=MessageOut)
def student_logout(response: Response):
    clear_cookie(response, STUDENT_COOKIE)
    return MessageOut(message="Logged out")


@router.get("/me", response_model=StudentOut)
def me(student: Student = Depends(require_student)):
    return student
