from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Announcement, Club
from ..schemas import AnnouncementOut

router = APIRouter(prefix="/api/announcements", tags=["announcements"])


def announcement_out(a: Announcement) -> AnnouncementOut:
    return AnnouncementOut(id=a.id, title=a.title, message=a.message, published=a.published, published_at=a.published_at,
                           club_slug=a.club.slug if a.club else None, club_name=a.club.name if a.club else None)


@router.get("", response_model=list[AnnouncementOut])
def list_published(club: Optional[str] = Query(None, max_length=40), db: Session = Depends(get_db)):
    """Published announcements. With ?club=slug you also get the global ones."""
    stmt = select(Announcement).where(Announcement.published.is_(True))
    if club:
        c = db.scalar(select(Club).where(Club.slug == club))
        if not c:
            raise HTTPException(404, "Club not found")
        stmt = stmt.where(or_(Announcement.club_id.is_(None), Announcement.club_id == c.id))
    rows = db.scalars(stmt.order_by(Announcement.published_at.desc()).limit(100)).unique().all()
    return [announcement_out(a) for a in rows]
