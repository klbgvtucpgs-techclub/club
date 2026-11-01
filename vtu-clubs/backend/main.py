 # Entry-point shim so uvicorn can be started with either:
#   uvicorn main:app --reload          (from the backend/ directory)
#   uvicorn app.main:app --reload      (also works)
from app.main import app  # noqa: F401  re-exported for uvicorn

__all__ = ["app"]

