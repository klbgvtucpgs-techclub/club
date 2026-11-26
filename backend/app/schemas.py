import re
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from .config import settings
from .utils import utcnow


class MessageOut(BaseModel):
    message: str


class ClubOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    description: str
    head_name: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    image_path: Optional[str] = None


class RegisterIn(BaseModel):
    usn: str
    full_name: str = Field(min_length=3, max_length=120)
    email: EmailStr
    phone: str
    branch: str = Field(min_length=2, max_length=40)
    joining_year: int
    club_slug: str = Field(max_length=40)
    link_token: Optional[str] = Field(default=None, max_length=40)
    captcha_token: Optional[str] = Field(default=None, max_length=4096)
    captcha_code: Optional[str] = Field(default=None, max_length=32)

    @field_validator("usn")
    @classmethod
    def check_usn(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.fullmatch(settings.usn_pattern, v):
            raise ValueError("Invalid USN format")
        return v

    @field_validator("email")
    @classmethod
    def lower_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        v = re.sub(r"[\s-]", "", v)
        if v.startswith("+91"):
            v = v[3:]
        if not re.fullmatch(r"[6-9]\d{9}", v):
            raise ValueError("Enter a valid 10-digit Indian mobile number")
        return v

    @field_validator("full_name", "branch")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return " ".join(v.split())

    @field_validator("joining_year")
    @classmethod
    def check_year(cls, v: int) -> int:
        if not 2000 <= v <= utcnow().year:
            raise ValueError("Year of joining is out of range")
        return v


class CaptchaOut(BaseModel):
    token: str
    code: str


class PendingOut(BaseModel):
    pending_id: str
    message: str = "Registration saved. Request the email OTP to continue."


class SendOtpIn(BaseModel):
    purpose: Literal["register", "login"]
    pending_id: Optional[str] = Field(default=None, max_length=32)
    email: Optional[EmailStr] = None


class VerifyOtpIn(BaseModel):
    pending_id: str = Field(max_length=32)
    otp: str = Field(max_length=16)
    captcha_token: Optional[str] = Field(default=None, max_length=4096)

    @field_validator("otp")
    @classmethod
    def clean_otp(cls, v: str) -> str:
        v = re.sub(r"[\s-]", "", v.strip())
        if not re.fullmatch(r"^\d{6}$", v):
            raise ValueError("OTP verification code must be exactly 6 digits")
        return v


class StudentLoginIn(BaseModel):
    email: EmailStr
    otp: str = Field(max_length=16)

    @field_validator("otp")
    @classmethod
    def clean_otp(cls, v: str) -> str:
        v = re.sub(r"[\s-]", "", v.strip())
        if not re.fullmatch(r"^\d{6}$", v):
            raise ValueError("OTP verification code must be exactly 6 digits")
        return v


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    usn: str
    full_name: str
    email: str
    phone: str
    branch: str
    joining_year: int


class MembershipOut(BaseModel):
    membership_code: str
    status: str
    joined_at: datetime
    club_name: str
    club_slug: str


class RegistrationResult(BaseModel):
    membership: MembershipOut
    student: StudentOut


class AnnouncementOut(BaseModel):
    id: int
    title: str
    message: str
    club_slug: Optional[str] = None
    club_name: Optional[str] = None
    published: bool
    published_at: Optional[datetime] = None


class PhotoOut(BaseModel):
    id: int
    title: str
    event_name: str
    club_slug: str
    club_name: str
    image_url: str
    uploaded_at: datetime


class PhotoPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    event_name: Optional[str] = Field(default=None, max_length=150)
    club_slug: Optional[str] = Field(default=None, max_length=40)


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int


# ---------- admin ----------
class AdminLoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=72)


class AdminCreateIn(BaseModel):
    username: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=72)
    role: Literal["admin", "superadmin"] = "admin"


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    club_slug: Optional[str] = Field(default=None, max_length=40)  # null = all clubs
    published: bool = False


class AnnouncementPatch(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    message: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    club_slug: Optional[str] = Field(default=None, max_length=40)
    published: Optional[bool] = None


class LinkCreate(BaseModel):
    club_slug: str = Field(max_length=40)
    title: str = Field(min_length=3, max_length=150)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None

    @model_validator(mode="after")
    def order(self):
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class LinkPatch(BaseModel):
    active: Optional[bool] = None
    title: Optional[str] = Field(default=None, min_length=3, max_length=150)
    ends_at: Optional[datetime] = None


class MembershipPatch(BaseModel):
    status: Literal["active", "pending", "suspended"]
