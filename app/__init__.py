import sys
from pathlib import Path

# Ensure backend directory is in sys.path so backend modules resolve seamlessly
backend_dir = str(Path(__file__).resolve().parent.parent / "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
