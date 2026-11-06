"""Create the four clubs (idempotent):  python -m app.scripts.seed"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets "python app/scripts/x.py" work too

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Club

CLUBS = [
    dict(name="Tech", slug="tech", code_prefix="TECH", head_name="Tech Club Head", contact_email="tech@vtu.example",
         description="Hackathons, coding contests, robotics and AI/ML workshops.", image_path="assets/images/club-logos/tech.webp"),
    dict(name="Sports", slug="sports", code_prefix="SPORTS", head_name="Sports Club Head", contact_email="sports@vtu.example",
         description="Inter-college tournaments, fitness drives and team training.", image_path="assets/images/club-logos/sports.webp"),
    dict(name="Culture", slug="culture", code_prefix="CULT", head_name="Culture Club Head", contact_email="culture@vtu.example",
         description="Music, dance, drama and celebrations of Indian heritage.", image_path="assets/images/club-logos/culture.webp"),
    dict(name="Multi Media", slug="multimedia", code_prefix="MM", head_name="Multi Media Head", contact_email="multimedia@vtu.example",
         description="Photography, film-making, design and event coverage.", image_path="assets/images/club-logos/multimedia.webp"),
]


def seed_clubs(db) -> int:
    added = 0
    for c in CLUBS:
        if not db.scalar(select(Club.id).where(Club.slug == c["slug"])):
            db.add(Club(**c))
            added += 1
    db.commit()
    return added


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Added {seed_clubs(session)} club(s).")
