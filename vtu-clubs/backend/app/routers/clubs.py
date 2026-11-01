from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Club, RegistrationLink
from ..schemas import ClubOut
from ..services.membership_service import get_valid_link

router = APIRouter(prefix="/api", tags=["clubs"])


@router.get("/clubs", response_model=list[ClubOut])
def list_clubs(db: Session = Depends(get_db)):
    return db.scalars(select(Club).order_by(Club.id)).all()


@router.get("/clubs/{slug}", response_model=ClubOut)
def get_club(slug: str, db: Session = Depends(get_db)):
    club = db.scalar(select(Club).where(Club.slug == slug))
    if not club:
        raise HTTPException(404, "Club not found")
    return club


@router.get("/registration-links/{token}")
def check_registration_link(token: str, db: Session = Depends(get_db)):
    """Lets register.html confirm a shared link is still valid and which club it belongs to."""
    link = db.scalar(select(RegistrationLink).where(RegistrationLink.public_token == token))
    if not link:
        raise HTTPException(404, "Registration link not found")
    get_valid_link(db, token, link.club_id)
    return {"title": link.title, "club_slug": link.club.slug, "club_name": link.club.name, "ends_at": link.ends_at}
