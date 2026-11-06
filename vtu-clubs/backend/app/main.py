import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Allow running uvicorn directly from inside the app/ directory as well
import sys
if not __package__:
    _parent_dir = str(Path(__file__).resolve().parent.parent)
    if _parent_dir not in sys.path:
        sys.path.insert(0, _parent_dir)
    __package__ = "app"

from .config import settings
from .database import Base, engine
from .routers import admin, announcements, auth, clubs, gallery, memberships

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("vtu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.is_prod:
        problems = []
        if settings.secret_key.startswith("change-me") or len(settings.secret_key) < 32:
            problems.append("SECRET_KEY must be a random string of at least 32 characters")
        if settings.email_backend not in ("smtp",):
            problems.append("EMAIL_BACKEND must be 'smtp' in production")
        if not settings.cookie_secure:
            problems.append("COOKIE_SECURE must be true in production")
        if problems:
            raise RuntimeError("Unsafe production configuration: " + "; ".join(problems))
        if not settings.captcha_secret:
            log.warning("CAPTCHA_SECRET is empty: verify-otp is not protected by a captcha")

    # Ensure tables exist
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        log.warning("Could not auto-create tables: %s", e)

    # Ensure clubs and default admin exist for immediate plug-and-play delivery
    try:
        from .database import SessionLocal
        from .models import Admin
        from .scripts.seed import seed_clubs
        from .security import hash_password
        from sqlalchemy import select

        with SessionLocal() as db:
            seed_clubs(db)
            if not db.scalar(select(Admin.id)):
                db.add(Admin(username="admin", password_hash=hash_password("admin123456"), role="superadmin"))
                db.commit()
                log.info("Initialized default superadmin: username='admin', password='admin123456'")
    except Exception as e:
        log.warning("Startup data initialization error: %s", e)

    yield


app = FastAPI(
    title="VTU Clubs API", version="1.0.0", lifespan=lifespan,
    docs_url=None if settings.is_prod else "/docs", redoc_url=None,
    openapi_url=None if settings.is_prod else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware, allow_origins=settings.origins, allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Content-Type", "X-CSRF-Token"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if settings.is_prod:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


for r in (clubs.router, auth.router, memberships.router, announcements.router, gallery.router, admin.router):
    app.include_router(r)

if not settings.use_supabase_storage:  # local-disk photos for development
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/api/health", tags=["meta"])
@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# Serve the website from the same server (same origin: no CORS problems, cookies just work).
# This must stay the LAST route/mount so it never shadows /api, /docs or /uploads.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
