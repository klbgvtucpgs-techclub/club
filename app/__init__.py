import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add backend/app directory to __path__ so all submodules (database, models, config, etc.) resolve seamlessly
backend_app_dir = str(Path(__file__).resolve().parent.parent / "backend" / "app")
if backend_app_dir not in __path__:
    __path__.append(backend_app_dir)
