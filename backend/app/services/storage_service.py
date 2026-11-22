"""Photo storage: local disk uploads/ by default, with optional Supabase Storage support and seamless fallback."""
import io
import logging
import uuid
from pathlib import Path

import httpx
from fastapi import HTTPException
from PIL import Image

from ..config import settings

logger = logging.getLogger("vtu.storage")
Image.MAX_IMAGE_PIXELS = 40_000_000
FORMATS = {"JPEG": ("jpg", "image/jpeg"), "PNG": ("png", "image/png"), "WEBP": ("webp", "image/webp"), "GIF": ("gif", "image/gif")}


def get_upload_dir() -> Path:
    """Return the absolute path to the backend uploads directory."""
    d = Path(__file__).resolve().parents[2] / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def validate_image(data: bytes) -> tuple[str, str]:
    """Return (extension, content_type) after confirming the bytes really are an allowed image."""
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"Image must be under {settings.max_upload_mb} MB")
    try:
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format
            im.verify()
    except Exception:
        raise HTTPException(400, "File is not a valid image")
    if fmt not in FORMATS:
        raise HTTPException(400, "Only JPEG, PNG, WebP and GIF images are allowed")
    return FORMATS[fmt]


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.supabase_service_key}", "apikey": settings.supabase_service_key}


def _object_url(path: str) -> str:
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/{settings.supabase_bucket}/{path}"


def save_image(club_slug: str, data: bytes) -> str:
    ext, content_type = validate_image(data)
    path = f"{club_slug}/{uuid.uuid4().hex}.{ext}"

    # Try Supabase Storage if configured with valid non-dummy credentials
    if settings.use_supabase_storage:
        try:
            r = httpx.post(_object_url(path), content=data, timeout=10,
                           headers={**_headers(), "Content-Type": content_type, "x-upsert": "false"})
            if r.status_code < 400:
                logger.info("Uploaded photo %s to Supabase storage.", path)
                return path
            logger.warning("Supabase storage error (%s: %s). Falling back to local disk storage.", r.status_code, r.text[:200])
        except Exception as exc:
            logger.warning("Supabase storage unreachable (%s). Storing photo on local server disk.", exc)

    # Local disk storage
    target = get_upload_dir() / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    logger.info("Saved photo to local storage at %s", target)
    return path


def delete_image(path: str) -> None:
    try:
        if settings.use_supabase_storage:
            httpx.delete(_object_url(path), headers=_headers(), timeout=10)
    except Exception:
        pass
    try:
        (get_upload_dir() / path).unlink(missing_ok=True)
    except Exception as exc:
        logger.warning("Could not delete local image %s: %s", path, exc)


def public_url(path: str) -> str:
    """Return the browser-accessible URL for an image.
    
    If stored on local disk or Supabase is unconfigured, returns '/uploads/{path}'.
    """
    local_file = get_upload_dir() / path
    if local_file.is_file() or not settings.use_supabase_storage:
        return f"/uploads/{path}"
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_bucket}/{path}"
