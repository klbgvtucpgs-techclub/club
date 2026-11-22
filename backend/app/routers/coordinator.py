"""Coordinator Portal API.

Coordinators are sub-admins who manage a single club (photos, announcements, reports).
They authenticate with username + password and receive a short-lived JWT Bearer token
(separate from the admin HttpOnly-cookie session so the coordinator.html SPA can store
it in sessionStorage without touching the admin cookie path).

Endpoints
---------
POST  /api/coordinator/login              -> {token, name, club, club_slug}
GET   /api/coordinator/me                 -> identity check
GET   /api/coordinator/announcements      -> list own-club announcements
POST  /api/coordinator/announcements      -> create announcement for own club
DELETE /api/coordinator/announcements/{id}
GET   /api/coordinator/photos             -> list own-club photos
POST  /api/coordinator/photos             -> upload photo to own club
DELETE /api/coordinator/photos/{id}
GET   /api/coordinator/reports            -> list own-club reports (stub – 200 [])
POST  /api/coordinator/reports            -> upload report (stub – 501)
DELETE /api/coordinator/reports/{id}      -> stub – 501
"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..dependencies import rate_limit
from ..models import Admin, Announcement, Club, Photo
from ..schemas import AnnouncementOut, MessageOut, PhotoOut
from ..security import DUMMY_HASH, create_token, decode_token, verify_password
from ..services import storage_service
from ..utils import utcnow
from .announcements import announcement_out
from .gallery import photo_out

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])

_COORDINATOR_TTL_HOURS = 10


# ---------------------------------------------------------------------------
# Bearer-token dependency
# ---------------------------------------------------------------------------

def _bearer_token(request: Request) -> dict:
    """Extract and validate the JWT Bearer token from the Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Coordinator token required")
    payload = decode_token(auth[7:])
    if not payload or payload.get("role") != "coordinator":
        raise HTTPException(401, "Invalid or expired coordinator token")
    return payload


def require_coordinator(request: Request, db: Session = Depends(get_db)) -> Admin:
    payload = _bearer_token(request)
    admin = db.get(Admin, int(payload["sub"]))
    if not admin or not admin.active or admin.role not in ("coordinator", "admin", "superadmin"):
        raise HTTPException(401, "Coordinator access required")
    return admin


def _club_of(admin: Admin, db: Session) -> Club:
    """Return the club bound to this coordinator (via club_id on the Admin row)."""
    if admin.club_id is None:
        # Default to first club for superadmin or unassigned admin
        club = db.scalars(select(Club).order_by(Club.id)).first()
        if not club:
            raise HTTPException(404, "No clubs found in database")
        return club
    club = db.get(Club, admin.club_id)
    if not club:
        raise HTTPException(404, "Assigned club not found")
    return club


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

from pydantic import BaseModel as _BM, Field


class _CoordLoginBody(_BM):
    username: str
    password: str


class _CoordAnnIn(_BM):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=5000)


@router.post("/login", dependencies=[Depends(rate_limit("coord_login", 10, 900))])
def coordinator_login(
    data: _CoordLoginBody,
    db: Session = Depends(get_db),
):
    """Accept JSON {username, password}, return a short-lived Bearer token."""
    admin = db.scalar(select(Admin).where(Admin.username == data.username.strip()))
    ok = verify_password(data.password, admin.password_hash if admin else DUMMY_HASH)
    if not admin or not ok or not admin.active:
        raise HTTPException(401, "Invalid username or password")
    if admin.role not in ("coordinator", "admin", "superadmin"):
        raise HTTPException(403, "This account does not have coordinator access")

    club = db.get(Club, admin.club_id) if admin.club_id else db.scalars(select(Club).order_by(Club.id)).first()
    ttl = timedelta(hours=_COORDINATOR_TTL_HOURS)
    token = create_token(str(admin.id), "coordinator", ttl)
    return {
        "token": token,
        "name": admin.username,
        "club": club.name if club else "All Clubs",
        "club_slug": club.slug if club else None,
    }


@router.get("/me")
def coordinator_me(admin: Admin = Depends(require_coordinator), db: Session = Depends(get_db)):
    club = db.get(Club, admin.club_id) if admin.club_id else db.scalars(select(Club).order_by(Club.id)).first()
    return {
        "name": admin.username,
        "club": club.name if club else "All Clubs",
        "club_slug": club.slug if club else None,
        "role": admin.role,
    }


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------

@router.get("/announcements", response_model=list[AnnouncementOut])
def list_coordinator_announcements(
    admin: Admin = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    club = _club_of(admin, db)
    rows = db.scalars(
        select(Announcement)
        .where(Announcement.club_id == club.id)
        .order_by(Announcement.id.desc())
        .limit(200)
    ).unique().all()
    return [announcement_out(a) for a in rows]


@router.post("/announcements", response_model=AnnouncementOut, status_code=201)
def create_coordinator_announcement(
    data: _CoordAnnIn,
    admin: Admin = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    club = _club_of(admin, db)
    a = Announcement(
        title=data.title.strip(), message=data.message.strip(),
        club_id=club.id, published=True, published_at=utcnow(), created_by=admin.id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return announcement_out(a)


@router.delete("/announcements/{ann_id}", response_model=MessageOut)
def delete_coordinator_announcement(
    ann_id: int,
    admin: Admin = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    club = _club_of(admin, db)
    a = db.get(Announcement, ann_id)
    if not a or a.club_id != club.id:
        raise HTTPException(404, "Announcement not found")
    db.delete(a)
    db.commit()
    return MessageOut(message="Announcement deleted")


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------

@router.get("/photos", response_model=list[PhotoOut])
def list_coordinator_photos(
    admin: Admin = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    club = _club_of(admin, db)
    rows = db.scalars(
        select(Photo)
        .where(Photo.club_id == club.id)
        .order_by(Photo.uploaded_at.desc())
        .limit(200)
    ).unique().all()
    return [photo_out(p) for p in rows]


@router.post("/photos", response_model=PhotoOut, status_code=201)
def upload_coordinator_photo(
    request: Request,
    title: str = Form(..., min_length=1, max_length=150),
    event: str = Form("", max_length=150),
    file: UploadFile = File(...),
    admin: Admin = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    club = _club_of(admin, db)
    data = file.file.read(settings.max_upload_bytes + 1)
    path = storage_service.save_image(club.slug, data)
    photo = Photo(
        club_id=club.id, title=title.strip(), event_name=event.strip(),
        image_path=path, uploaded_by=admin.id,
    )
    db.add(photo)
    try:
        db.commit()
    except Exception:
        db.rollback()
        storage_service.delete_image(path)
        raise
    db.refresh(photo)
    return photo_out(photo)


@router.delete("/photos/{photo_id}", response_model=MessageOut)
def delete_coordinator_photo(
    photo_id: int,
    admin: Admin = Depends(require_coordinator),
    db: Session = Depends(get_db),
):
    club = _club_of(admin, db)
    photo = db.get(Photo, photo_id)
    if not photo or photo.club_id != club.id:
        raise HTTPException(404, "Photo not found")
    path = photo.image_path
    db.delete(photo)
    db.commit()
    storage_service.delete_image(path)
    return MessageOut(message="Photo deleted")


# ---------------------------------------------------------------------------
# Reports (stub – feature-complete backend can be wired later)
# ---------------------------------------------------------------------------

@router.get("/reports")
def list_coordinator_reports(_: Admin = Depends(require_coordinator)):
    """Reports listing – returns empty list until file storage is wired up."""
    return []


@router.post("/reports", status_code=201)
def upload_coordinator_report(_: Admin = Depends(require_coordinator)):
    raise HTTPException(501, "Report uploads are not yet enabled on this server.")


@router.delete("/reports/{report_id}", response_model=MessageOut)
def delete_coordinator_report(report_id: str, _: Admin = Depends(require_coordinator)):
    raise HTTPException(501, "Report management is not yet enabled on this server.")
