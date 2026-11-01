import hmac

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Club, ClubCounter, EmailOTP, Membership, PendingRegistration, RegistrationLink, Student
from ..security import hash_otp
from ..utils import aware, utcnow


def get_valid_link(db: Session, token: str, club_id: int) -> RegistrationLink:
    link = db.scalar(select(RegistrationLink).where(RegistrationLink.public_token == token))
    now = utcnow()
    if (
        not link or link.club_id != club_id or not link.active
        or (link.starts_at and aware(link.starts_at) > now)
        or (link.ends_at and aware(link.ends_at) < now)
    ):
        raise HTTPException(403, "This registration link is invalid, disabled or expired")
    return link


def check_otp(db: Session, email: str, purpose: str, code: str) -> None:
    """Validates expiry, attempt limit and the code itself. Failed attempts are committed before raising."""
    rec = db.scalar(
        select(EmailOTP)
        .where(EmailOTP.email == email, EmailOTP.purpose == purpose, EmailOTP.consumed_at.is_(None))
        .order_by(EmailOTP.created_at.desc(), EmailOTP.id.desc())
        .limit(1)
    )
    if rec is None or aware(rec.expires_at) < utcnow():
        raise HTTPException(400, "Code expired or not found. Request a new one.")
    if rec.attempts >= settings.otp_max_attempts:
        raise HTTPException(429, "Too many wrong attempts. Request a new code.")
    rec.attempts += 1
    if not hmac.compare_digest(rec.otp_hash, hash_otp(email, purpose, code)):
        left = settings.otp_max_attempts - rec.attempts
        db.commit()
        raise HTTPException(400, f"Incorrect code. {left} attempt(s) left." if left > 0 else "Incorrect code. Request a new code.")
    rec.consumed_at = utcnow()


def next_number(db: Session, club_id: int, year: int) -> int:
    """Concurrency-safe counter: create the row if needed, then lock it (FOR UPDATE) and increment."""
    try:
        with db.begin_nested():
            db.add(ClubCounter(club_id=club_id, year=year, last_number=0))
    except IntegrityError:
        pass  # another request created it first
    counter = db.execute(
        select(ClubCounter).where(ClubCounter.club_id == club_id, ClubCounter.year == year).with_for_update()
    ).scalar_one()
    counter.last_number += 1
    db.flush()
    return counter.last_number


def complete_registration(db: Session, pending: PendingRegistration):
    club = db.get(Club, pending.club_id)
    student = db.scalar(select(Student).where(Student.usn == pending.usn))
    if student is None:
        student = Student(
            usn=pending.usn, full_name=pending.full_name, email=pending.email, phone=pending.phone,
            branch=pending.branch, joining_year=pending.joining_year, email_verified=True,
        )
        db.add(student)
        db.flush()
    else:
        student.email_verified = True
    if db.scalar(select(Membership.id).where(Membership.student_id == student.id, Membership.club_id == club.id)):
        raise HTTPException(409, "You are already a member of this club")
    year = pending.joining_year
    code = f"{club.code_prefix}-{year}-{next_number(db, club.id, year):04d}"
    membership = Membership(
        student_id=student.id, club_id=club.id, membership_code=code,
        status="pending" if settings.require_admin_approval else "active",
    )
    db.add(membership)
    db.delete(pending)
    db.flush()
    return student, membership, club
