"""Create an admin from the terminal:  python -m app.scripts.create_admin USERNAME [--super]"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # lets "python app/scripts/x.py" work too

from sqlalchemy import select

try:
    from ..database import SessionLocal
    from ..models import Admin
    from ..security import hash_password
except (ImportError, ValueError):
    from app.database import SessionLocal
    from app.models import Admin
    from app.security import hash_password


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("Usage: python -m app.scripts.create_admin USERNAME [--super]")
    username, role = args[0], "superadmin" if "--super" in sys.argv else "admin"
    password = getpass.getpass("Password (min 10 characters): ")
    if len(password) < 10 or len(password.encode()) > 72:
        sys.exit("Password must be 10 to 72 bytes long.")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    with SessionLocal() as db:
        if db.scalar(select(Admin.id).where(Admin.username == username)):
            sys.exit("That username already exists.")
        db.add(Admin(username=username, password_hash=hash_password(password), role=role))
        db.commit()
    print(f"Created {role} '{username}'.")


if __name__ == "__main__":
    main()
