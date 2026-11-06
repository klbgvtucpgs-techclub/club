"""Check your email settings:  python -m app.scripts.test_email you@example.com
Run it from the backend folder (the one that contains .env). It prints what was loaded and the real error if sending fails."""
import smtplib
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import settings  # noqa: E402
from app.services.email_service import send_email  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Usage: python -m app.scripts.test_email recipient@example.com")
    to = sys.argv[1]
    env_file = Path(".env").resolve()
    print("Looking for .env at:", env_file, "->", "FOUND" if env_file.exists() else "NOT FOUND (run this from the backend folder)")
    print("EMAIL_BACKEND  :", settings.email_backend)
    print("SMTP_HOST/PORT :", settings.smtp_host or "(empty)", settings.smtp_port)
    print("SMTP_USER      :", settings.smtp_user or "(empty)")
    print("SMTP_PASSWORD  :", f"{len(settings.smtp_password.replace(' ', ''))} characters" if settings.smtp_password else "(empty)")
    print("EMAIL_FROM     :", settings.email_from)
    if settings.email_backend.strip().lower() != "smtp":
        sys.exit("\nProblem: EMAIL_BACKEND is '%s'. Set EMAIL_BACKEND=smtp in .env and restart." % settings.email_backend)
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        sys.exit("\nProblem: SMTP_HOST, SMTP_USER or SMTP_PASSWORD is empty in .env.")
    try:
        send_email(to, "VTU Clubs test email", "If you can read this, your email settings work.", raise_errors=True)
    except smtplib.SMTPAuthenticationError:
        sys.exit("\nGmail refused the login. Use a 16-letter App Password (needs 2-Step Verification), not your normal password. "
                 "Also check SMTP_USER is the same Gmail address the app password was created for.")
    except (socket.timeout, TimeoutError, ConnectionError, OSError) as e:
        sys.exit(f"\nCould not reach the mail server ({e}). Your network or Wi-Fi may block port 587. Try SMTP_PORT=465, or a mobile hotspot.")
    except Exception as e:
        sys.exit(f"\nFailed: {type(e).__name__}: {e}")
    print(f"\nSUCCESS: test email sent to {to}. Check the inbox and the spam folder.")


if __name__ == "__main__":
    main()
