from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import require_student
from ..models import Membership, Student
from ..schemas import MembershipOut

router = APIRouter(prefix="/api/memberships", tags=["memberships"])


@router.get("/me", response_model=list[MembershipOut])
def my_memberships(student: Student = Depends(require_student), db: Session = Depends(get_db)):
    rows = db.scalars(select(Membership).where(Membership.student_id == student.id).order_by(Membership.joined_at)).all()
    return [MembershipOut(membership_code=m.membership_code, status=m.status, joined_at=m.joined_at,
                          club_name=m.club.name, club_slug=m.club.slug) for m in rows]
