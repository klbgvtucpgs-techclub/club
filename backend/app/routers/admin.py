import csv
import io
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import (ADMIN_COOKIE, CSRF_COOKIE, clear_cookie, client_ip, rate_limit, require_admin,
                            require_superadmin, set_cookie)
from ..models import Admin, Announcement, AuditLog, Club, Membership, Photo, RegistrationLink, Student
from ..schemas import (AdminCreateIn, AdminLoginIn, AnnouncementCreate, AnnouncementOut, AnnouncementPatch,
                       LinkCreate, LinkPatch, MembershipPatch, MessageOut, Page, PhotoOut, PhotoPatch)
from ..security import DUMMY_HASH, create_token, hash_password, new_csrf_token, verify_password
from ..services import storage_service
from ..utils import utcnow
from .announcements import announcement_out
from .gallery import photo_out

router = APIRouter(prefix="/api/admin", tags=["admin"])
ADMIN_PATH = "/api/admin"


def audit(db: Session, admin: Optional[Admin], request: Request, action: str, target: str = "", detail: str = "") -> None:
    db.add(AuditLog(admin_id=admin.id if admin else None, action=action, target=target[:120], detail=detail[:1000],
                    ip=client_ip(request)))


def club_by_slug(db: Session, slug: str) -> Club:
    club = db.scalar(select(Club).where(Club.slug == slug))
    if not club:
        raise HTTPException(404, "Club not found")
    return club


# ------------------------------------------------------------------ session
@router.post("/login", dependencies=[Depends(rate_limit("admin_login", 10, 900))])
def admin_login(data: AdminLoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    admin = db.scalar(select(Admin).where(Admin.username == data.username.strip()))
    ok = verify_password(data.password, admin.password_hash if admin else DUMMY_HASH)
    if not admin or not ok or not admin.active:
        audit(db, None, request, "admin.login_failed", data.username.strip()[:60])
        db.commit()
        raise HTTPException(401, "Invalid username or password")
    ttl = timedelta(hours=settings.admin_session_hours)
    csrf = new_csrf_token()
    # The admin cookie is only sent to /api/admin/*; JS can't read it (HttpOnly).
    set_cookie(response, ADMIN_COOKIE, create_token(str(admin.id), "admin", ttl), int(ttl.total_seconds()), path=ADMIN_PATH)
    set_cookie(response, CSRF_COOKIE, csrf, int(ttl.total_seconds()), path=ADMIN_PATH)
    audit(db, admin, request, "admin.login", admin.username)
    db.commit()
    return {"username": admin.username, "role": admin.role, "csrf_token": csrf}


@router.post("/logout", response_model=MessageOut)
def admin_logout(response: Response):
    clear_cookie(response, ADMIN_COOKIE, ADMIN_PATH)
    clear_cookie(response, CSRF_COOKIE, ADMIN_PATH)
    return MessageOut(message="Logged out")


@router.get("/me")
def admin_me(request: Request, admin: Admin = Depends(require_admin)):
    """Also returns the CSRF token so the frontend can restore it after a page reload."""
    return {"username": admin.username, "role": admin.role, "csrf_token": request.cookies.get(CSRF_COOKIE, "")}


@router.get("/admins")
def list_admins(me: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    """List all coordinators and admins."""
    rows = db.execute(
        select(Admin.id, Admin.username, Admin.role, Admin.active, Admin.club_id, Club.name, Club.slug)
        .outerjoin(Club, Admin.club_id == Club.id)
        .order_by(Admin.id.asc())
    ).all()
    return [
        {
            "id": r[0],
            "username": r[1],
            "role": r[2],
            "active": r[3],
            "club_id": r[4],
            "club_name": r[5] or "General / Superadmin",
            "club_slug": r[6] or ""
        }
        for r in rows
    ]


@router.post("/admins", status_code=201)
def create_admin(data: AdminCreateIn, request: Request, me: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    if data.role in ("superadmin", "admin") and me.role != "superadmin":
        raise HTTPException(403, "Only superadmin can create admin/superadmin accounts")
    if db.scalar(select(Admin.id).where(Admin.username == data.username)):
        raise HTTPException(409, "Username already exists")
    club_id = None
    if data.club_slug:
        club = db.scalar(select(Club).where(Club.slug == data.club_slug))
        if club:
            club_id = club.id
    admin = Admin(username=data.username, password_hash=hash_password(data.password), role=data.role, club_id=club_id)
    db.add(admin)
    audit(db, me, request, "admin.create", data.username, f"role={data.role}")
    db.commit()
    return {"id": admin.id, "username": admin.username, "role": admin.role, "club_id": admin.club_id}


@router.delete("/admins/{admin_id}", response_model=MessageOut)
def delete_admin(admin_id: int, request: Request, me: Admin = Depends(require_superadmin), db: Session = Depends(get_db)):
    """Delete an admin or coordinator."""
    if me.id == admin_id:
        raise HTTPException(400, "Cannot delete your own account")
    target = db.get(Admin, admin_id)
    if not target:
        raise HTTPException(404, "Admin not found")
    name = target.username
    db.delete(target)
    audit(db, me, request, "admin.delete", name)
    db.commit()
    return MessageOut(message=f"Account {name} deleted successfully")


@router.get("/audit-logs")
def audit_logs(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
               _: Admin = Depends(require_superadmin), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return [{"id": r.id, "admin_id": r.admin_id, "action": r.action, "target": r.target, "detail": r.detail,
             "ip": r.ip, "created_at": r.created_at} for r in rows]


# ------------------------------------------------------------------ dashboard
@router.get("/dashboard")
def dashboard(_: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    per_club = db.execute(
        select(Club.slug, Club.name, func.count(Membership.id)).select_from(Club)
        .outerjoin(Membership, Membership.club_id == Club.id).group_by(Club.id, Club.slug, Club.name).order_by(Club.id)
    ).all()
    recent = db.execute(
        select(Membership.membership_code, Membership.status, Membership.joined_at, Student.full_name, Student.usn, Club.name)
        .join(Student, Membership.student_id == Student.id).join(Club, Membership.club_id == Club.id)
        .order_by(Membership.joined_at.desc(), Membership.id.desc()).limit(10)
    ).all()
    return {
        "total_students": db.scalar(select(func.count(Student.id))) or 0,
        "published_announcements": db.scalar(select(func.count(Announcement.id)).where(Announcement.published.is_(True))) or 0,
        "photos": db.scalar(select(func.count(Photo.id))) or 0,
        "members_per_club": [{"slug": s, "name": n, "members": c} for s, n, c in per_club],
        "recent_registrations": [{"membership_code": c, "status": st, "joined_at": j, "full_name": n, "usn": u, "club": cn}
                                 for c, st, j, n, u, cn in recent],
    }


# ------------------------------------------------------------------ photos
@router.post("/photos", response_model=PhotoOut, status_code=201)
def upload_photo(request: Request, club_slug: str = Form(..., max_length=40), title: str = Form(..., min_length=1, max_length=150),
                 event_name: str = Form("", max_length=150), file: UploadFile = File(...),
                 admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    club = club_by_slug(db, club_slug)
    data = file.file.read(settings.max_upload_bytes + 1)
    path = storage_service.save_image(club.slug, data)  # validates size, type and content
    photo = Photo(club_id=club.id, title=title.strip(), event_name=event_name.strip(), image_path=path, uploaded_by=admin.id)
    db.add(photo)
    try:
        audit(db, admin, request, "photo.upload", club.slug, title.strip())
        db.commit()
    except Exception:
        db.rollback()
        storage_service.delete_image(path)
        raise
    db.refresh(photo)
    return photo_out(photo)


@router.patch("/photos/{photo_id}", response_model=PhotoOut)
def edit_photo(photo_id: int, data: PhotoPatch, request: Request, admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    sent = data.model_fields_set
    if "title" in sent and data.title is not None:
        photo.title = data.title.strip()
    if "event_name" in sent and data.event_name is not None:
        photo.event_name = data.event_name.strip()
    if "club_slug" in sent and data.club_slug is not None:
        club = club_by_slug(db, data.club_slug)
        photo.club_id = club.id
    audit(db, admin, request, "photo.update", str(photo.id), photo.title)
    db.commit()
    db.refresh(photo)
    return photo_out(photo)


@router.delete("/photos/{photo_id}", response_model=MessageOut)
def delete_photo(photo_id: int, request: Request, admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(404, "Photo not found")
    path = photo.image_path
    audit(db, admin, request, "photo.delete", str(photo_id), photo.title)
    db.delete(photo)
    db.commit()
    storage_service.delete_image(path)
    return MessageOut(message="Photo deleted")


# ------------------------------------------------------------------ announcements
@router.get("/announcements", response_model=list[AnnouncementOut])
def all_announcements(_: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.scalars(select(Announcement).order_by(Announcement.id.desc()).limit(200)).unique().all()
    return [announcement_out(a) for a in rows]


@router.post("/announcements", response_model=AnnouncementOut, status_code=201)
def create_announcement(data: AnnouncementCreate, request: Request, admin: Admin = Depends(require_admin),
                        db: Session = Depends(get_db)):
    club = club_by_slug(db, data.club_slug) if data.club_slug else None
    a = Announcement(title=data.title.strip(), message=data.message.strip(), club_id=club.id if club else None,
                     published=data.published, published_at=utcnow() if data.published else None, created_by=admin.id)
    db.add(a)
    db.flush()
    audit(db, admin, request, "announcement.create", str(a.id), a.title)
    db.commit()
    db.refresh(a)
    return announcement_out(a)


@router.patch("/announcements/{ann_id}", response_model=AnnouncementOut)
def edit_announcement(ann_id: int, data: AnnouncementPatch, request: Request, admin: Admin = Depends(require_admin),
                      db: Session = Depends(get_db)):
    a = db.get(Announcement, ann_id)
    if not a:
        raise HTTPException(404, "Announcement not found")
    sent = data.model_fields_set
    if "title" in sent and data.title is not None:
        a.title = data.title.strip()
    if "message" in sent and data.message is not None:
        a.message = data.message.strip()
    if "club_slug" in sent:  # explicit null makes it global
        a.club_id = club_by_slug(db, data.club_slug).id if data.club_slug else None
    if "published" in sent and data.published is not None:
        if data.published and not a.published:
            a.published_at = utcnow()
        a.published = data.published
    audit(db, admin, request, "announcement.update", str(a.id), f"published={a.published}")
    db.commit()
    db.refresh(a)
    return announcement_out(a)


@router.delete("/announcements/{ann_id}", response_model=MessageOut)
def delete_announcement(ann_id: int, request: Request, admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    a = db.get(Announcement, ann_id)
    if not a:
        raise HTTPException(404, "Announcement not found")
    audit(db, admin, request, "announcement.delete", str(ann_id), a.title)
    db.delete(a)
    db.commit()
    return MessageOut(message="Announcement deleted")


# ------------------------------------------------------------------ registration links
def _link_out(l: RegistrationLink) -> dict:
    return {"id": l.id, "club_slug": l.club.slug, "club_name": l.club.name, "title": l.title, "active": l.active,
            "public_token": l.public_token, "starts_at": l.starts_at, "ends_at": l.ends_at,
            "url": f"{settings.frontend_base_url.rstrip('/')}/#register?link={l.public_token}"}


@router.get("/registration-links")
def list_links(_: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    return [_link_out(l) for l in db.scalars(select(RegistrationLink).order_by(RegistrationLink.id.desc())).unique().all()]


@router.post("/registration-links", status_code=201)
def create_link(data: LinkCreate, request: Request, admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    club = club_by_slug(db, data.club_slug)
    link = RegistrationLink(club_id=club.id, public_token=secrets.token_urlsafe(12), title=data.title.strip(),
                            starts_at=data.starts_at, ends_at=data.ends_at, created_by=admin.id)
    db.add(link)
    db.flush()
    audit(db, admin, request, "link.create", str(link.id), club.slug)
    db.commit()
    db.refresh(link)
    return _link_out(link)


@router.patch("/registration-links/{link_id}")
def edit_link(link_id: int, data: LinkPatch, request: Request, admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    link = db.get(RegistrationLink, link_id)
    if not link:
        raise HTTPException(404, "Link not found")
    sent = data.model_fields_set
    if "active" in sent and data.active is not None:
        link.active = data.active
    if "title" in sent and data.title is not None:
        link.title = data.title.strip()
    if "ends_at" in sent:
        link.ends_at = data.ends_at
    audit(db, admin, request, "link.update", str(link.id), f"active={link.active}")
    db.commit()
    db.refresh(link)
    return _link_out(link)


@router.delete("/registration-links/{link_id}", response_model=MessageOut)
def delete_link(link_id: int, request: Request, admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    link = db.get(RegistrationLink, link_id)
    if not link:
        raise HTTPException(404, "Link not found")
    audit(db, admin, request, "link.delete", str(link.id), link.title)
    db.delete(link)
    db.commit()
    return MessageOut(message="Registration link deleted")


# ------------------------------------------------------------------ students / memberships
def _like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _member_query(q: Optional[str], club: Optional[str]):
    stmt = (select(Membership.id, Membership.membership_code, Membership.status, Membership.joined_at, Student.usn,
                   Student.full_name, Student.email, Student.phone, Student.branch, Student.joining_year, Club.name, Club.slug)
            .join(Student, Membership.student_id == Student.id).join(Club, Membership.club_id == Club.id))
    if q:
        pat = _like(q.strip())
        stmt = stmt.where(or_(Student.usn.ilike(pat, escape="\\"), Student.full_name.ilike(pat, escape="\\"),
                              Student.branch.ilike(pat, escape="\\"), Membership.membership_code.ilike(pat, escape="\\")))
    if club:
        stmt = stmt.where(Club.slug == club)
    return stmt.order_by(Membership.id.desc())


_FIELDS = ("membership_id", "membership_code", "status", "joined_at", "usn", "full_name", "email", "phone", "branch",
           "joining_year", "club_name", "club_slug")


@router.get("/students", response_model=Page)
def list_students(q: Optional[str] = Query(None, max_length=80), club: Optional[str] = Query(None, max_length=40),
                  page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100),
                  _: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    stmt = _member_query(q, club)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.execute(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return Page(items=[dict(zip(_FIELDS, r)) for r in rows], total=total, page=page, page_size=page_size)


def _csv_safe(v) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s[:1] in ("=", "+", "-", "@", "\t", "\r") else s  # blocks spreadsheet formula injection


@router.get("/students/export")
def export_students(request: Request, q: Optional[str] = Query(None, max_length=80), club: Optional[str] = Query(None, max_length=40),
                    admin: Admin = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.execute(_member_query(q, club)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_FIELDS[1:])
    for r in rows:
        w.writerow([_csv_safe(v) for v in r[1:]])
    audit(db, admin, request, "students.export", club or "all", f"rows={len(rows)}")
    db.commit()
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": 'attachment; filename="members.csv"'})


@router.patch("/memberships/{membership_id}", response_model=MessageOut)
def update_membership(membership_id: int, data: MembershipPatch, request: Request, admin: Admin = Depends(require_admin),
                      db: Session = Depends(get_db)):
    m = db.get(Membership, membership_id)
    if not m:
        raise HTTPException(404, "Membership not found")
    m.status = data.status
    audit(db, admin, request, "membership.update", m.membership_code, f"status={data.status}")
    db.commit()
    return MessageOut(message=f"Membership set to {data.status}")


@router.delete("/memberships/{membership_id}", response_model=MessageOut)
def delete_membership(membership_id: int, request: Request, admin: Admin = Depends(require_admin),
                      db: Session = Depends(get_db)):
    m = db.get(Membership, membership_id)
    if not m:
        raise HTTPException(404, "Membership not found")
    student = db.get(Student, m.student_id)
    code = m.membership_code
    audit(db, admin, request, "membership.delete", code, f"student={student.usn if student else m.student_id}")
    db.delete(m)
    if student:
        remaining = db.scalar(select(Membership.id).where(Membership.student_id == student.id, Membership.id != membership_id))
        if not remaining:
            db.delete(student)
    db.commit()
    return MessageOut(message=f"Membership {code} deleted")
