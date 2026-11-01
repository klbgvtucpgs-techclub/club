"""Photo storage: Supabase Storage (REST API) when configured, otherwise the local uploads/ folder."""
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
    if settings.use_supabase_storage:
        try:
            r = httpx.post(_object_url(path), content=data, timeout=30,
                           headers={**_headers(), "Content-Type": content_type, "x-upsert": "false"})
        except httpx.HTTPError:
            logger.exception("Supabase upload failed")
            raise HTTPException(502, "Image storage is unavailable")
        if r.status_code >= 400:
            logger.error("Supabase upload error %s: %s", r.status_code, r.text[:300])
            raise HTTPException(502, "Image storage rejected the upload")
    else:
        target = Path(settings.upload_dir) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return path


def delete_image(path: str) -> None:
    try:
        if settings.use_supabase_storage:
            httpx.delete(_object_url(path), headers=_headers(), timeout=15)
        else:
            (Path(settings.upload_dir) / path).unlink(missing_ok=True)
    except Exception:
        logger.exception("Could not delete stored image %s", path)


def public_url(path: str) -> str:
    if settings.use_supabase_storage:
        return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_bucket}/{path}"
    return f"/uploads/{path}"
