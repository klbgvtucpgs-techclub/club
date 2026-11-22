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

    try:
        pg_engine = create_engine(
            url, pool_pre_ping=True, pool_size=5, max_overflow=5, pool_recycle=1800, connect_args=args
        )
        # Verify connection on startup
        with pg_engine.connect():
            pass
        logger.info("Connected to primary Postgres database successfully.")
        return pg_engine
    except Exception as exc:
        logger.warning(
            "Could not connect to Postgres (%s). Falling back to local SQLite database (%s) for reliable execution.",
            exc,
            _default_sqlite_url(),
        )
        return create_engine(_default_sqlite_url(), connect_args={"check_same_thread": False})


engine = _init_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
