import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .utils import utcnow

TZ = DateTime(timezone=True)


class Club(Base):
    __tablename__ = "clubs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    code_prefix: Mapped[str] = mapped_column(String(10), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    head_name: Mapped[str] = mapped_column(String(120), default="")
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usn: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(15))
    branch: Mapped[str] = mapped_column(String(40))
    joining_year: Mapped[int] = mapped_column(Integer)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)


class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin")  # admin | superadmin | coordinator
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # For coordinators: which club they manage (NULL = all clubs / superadmin)
    club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clubs.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("student_id", "club_id", name="uq_membership_student_club"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), index=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    membership_code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | pending | suspended
    joined_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)
    club: Mapped["Club"] = relationship(lazy="joined")


class ClubCounter(Base):
    """One row per (club, joining year); locked with SELECT ... FOR UPDATE to issue gap-free, unique numbers."""
    __tablename__ = "club_counters"
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_number: Mapped[int] = mapped_column(Integer, default=0)


class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    club_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clubs.id"), nullable=True, index=True)
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(TZ, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("admins.id"))
    created_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)
    club: Mapped[Optional["Club"]] = relationship(lazy="joined")


class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    title: Mapped[str] = mapped_column(String(150))
    event_name: Mapped[str] = mapped_column(String(150), default="")
    image_path: Mapped[str] = mapped_column(String(255))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("admins.id"))
    uploaded_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)
    club: Mapped["Club"] = relationship(lazy="joined")


class EmailOTP(Base):
    __tablename__ = "email_otps"
    __table_args__ = (Index("ix_email_otps_lookup", "email", "purpose"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255))
    purpose: Mapped[str] = mapped_column(String(20))  # register | login
    otp_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(TZ)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    consumed_at: Mapped[Optional[datetime]] = mapped_column(TZ, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)


class PendingRegistration(Base):
    """Form data parked until the email OTP is verified. Nothing becomes a student/member before that."""
    __tablename__ = "pending_registrations"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: uuid.uuid4().hex)
    usn: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str] = mapped_column(String(15))
    branch: Mapped[str] = mapped_column(String(40))
    joining_year: Mapped[int] = mapped_column(Integer)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"))
    link_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(TZ)


class RegistrationLink(Base):
    __tablename__ = "registration_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), index=True)
    public_token: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(150))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    starts_at: Mapped[Optional[datetime]] = mapped_column(TZ, nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(TZ, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("admins.id"))
    created_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)
    club: Mapped["Club"] = relationship(lazy="joined")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("admins.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    target: Mapped[str] = mapped_column(String(120), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(TZ, default=utcnow)
