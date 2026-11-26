import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

logger = logging.getLogger("vtu.database")


class Base(DeclarativeBase):
    pass


def _default_sqlite_url() -> str:
    db_file = Path(__file__).resolve().parent.parent / "dev.db"
    return f"sqlite:///{db_file.as_posix()}"


def _build_url(raw: str) -> str:
    url = raw.strip()
    if url in ("sqlite:///./dev.db", "sqlite:///dev.db", "sqlite://dev.db"):
        return _default_sqlite_url()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    if "://" in url and "@" in url:
        scheme, rest = url.split("://", 1)
        userinfo, sep, hostpart = rest.rpartition("@")
        if sep and ":" in userinfo:
            user, password = userinfo.split(":", 1)
            for ch, enc in (("@", "%40"), ("#", "%23"), ("?", "%3F"), ("/", "%2F")):
                password = password.replace(ch, enc)
            url = f"{scheme}://{user}:{password}@{hostpart}"
    return url


def _init_engine():
    raw_url = settings.database_url or _default_sqlite_url()
    url = _build_url(raw_url)

    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})

    # Postgres configuration
    args: dict = {"prepare_threshold": None}
    if "sslmode=" not in url and not any(h in url for h in ("localhost", "127.0.0.1")):
        args["sslmode"] = "require"

    # Create engine. pool_pre_ping=True tests each connection before use
    # so transient Supabase hiccups recover automatically.
    # We do NOT test at import time — that would crash the server on startup
    # if Supabase is momentarily unreachable.
    pg_engine = create_engine(
        url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=1800, connect_args=args
    )
    logger.info("Postgres engine created for: %s", url.split("@")[-1])
    return pg_engine


engine = _init_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
