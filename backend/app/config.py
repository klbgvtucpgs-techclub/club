from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            Path(__file__).resolve().parents[2] / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            Path(__file__).resolve().parent / ".env",
            Path(__file__).resolve().parent.parent / ".env.example",
            Path(__file__).resolve().parents[2] / ".env.example",
            ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite:///./dev.db"
    frontend_origins: str = "http://127.0.0.1:5500,http://localhost:5500"
    frontend_base_url: str = "http://127.0.0.1:8000"

    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "club-photos"
    upload_dir: str = "uploads"
    max_upload_mb: int = 5

    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    admin_session_hours: int = 8
    student_session_days: int = 7

    email_backend: str = "smtp"  # smtp | console | memory (tests)
    email_from: str = "VTU Clubs <klbgvtucpgs@gmail.com>"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str = "klbgvtucpgs@gmail.com"
    smtp_password: str = "bbym qhij kjrq gfno"

    captcha_provider: str = "turnstile"
    captcha_secret: str = ""

    usn_pattern: str = r"^[1-4][A-Z]{2}\d{2}[A-Z]{2,3}\d{3}$"
    allowed_email_domains: str = ""
    require_registration_link: bool = False
    require_admin_approval: bool = False
    otp_ttl_seconds: int = 300
    otp_max_attempts: int = 3
    otp_resend_cooldown_seconds: int = 60
    pending_ttl_minutes: int = 30
    rate_limit_enabled: bool = True
    trust_proxy: bool = False

    @property
    def is_prod(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_origins.split(",") if o.strip()]

    @property
    def email_domains(self) -> list[str]:
        return [d.strip().lower() for d in self.allowed_email_domains.split(",") if d.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024

    @property
    def use_supabase_storage(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


settings = Settings()
