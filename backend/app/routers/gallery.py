from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Club, Photo
from ..schemas import Page, PhotoOut
from ..services import storage_service

router = APIRouter(prefix="/api/gallery", tags=["gallery"])


def photo_out(p: Photo) -> PhotoOut:
    return PhotoOut(id=p.id, title=p.title, event_name=p.event_name, club_slug=p.club.slug, club_name=p.club.name,
                    image_url=storage_service.public_url(p.image_path), uploaded_at=p.uploaded_at)


@router.get("", response_model=Page)
def gallery(club: Optional[str] = Query(None, max_length=40), event: Optional[str] = Query(None, max_length=150),
            page: int = Query(1, ge=1), page_size: int = Query(12, ge=1, le=60), db: Session = Depends(get_db)):
    stmt = select(Photo)
    if club:
        c = db.scalar(select(Club).where(Club.slug == club))
        if not c:
            raise HTTPException(404, "Club not found")
        stmt = stmt.where(Photo.club_id == c.id)
    if event:
        stmt = stmt.where(Photo.event_name == event)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Photo.uploaded_at.desc(), Photo.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).unique().all()
    return Page(items=[photo_out(p) for p in rows], total=total, page=page, page_size=page_size)


@router.get("/albums")
def albums(club: Optional[str] = Query(None, max_length=40), db: Session = Depends(get_db)):
    """Event-specific albums: one entry per (club, event name)."""
    stmt = (select(Club.slug, Club.name, Photo.event_name, func.count(Photo.id))
            .select_from(Photo).join(Club, Photo.club_id == Club.id)
            .where(Photo.event_name != "").group_by(Club.slug, Club.name, Photo.event_name))
    if club:
        stmt = stmt.where(Club.slug == club)
    return [{"club_slug": s, "club_name": n, "event_name": e, "photo_count": c} for s, n, e, c in db.execute(stmt).all()]
