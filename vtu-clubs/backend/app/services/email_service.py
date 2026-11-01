import logging
import smtplib
import ssl
from email.message import EmailMessage

try:
    from ..config import settings
except (ImportError, ValueError):
    try:
        from app.config import settings
    except (ImportError, ValueError):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from app.config import settings

logger = logging.getLogger("vtu.email")
OUTBOX: list = []  # used by EMAIL_BACKEND=memory (tests)


def send_email(to: str, subject: str, body: str, raise_errors: bool = False) -> None:
    backend = (settings.email_backend or "console").strip().lower()
    if backend == "memory":
        OUTBOX.append({"to": to, "subject": subject, "body": body})
        return
    if backend == "console":
        print(f"\n--- EMAIL (console mode, nothing is really sent) to {to} | {subject}\n{body}\n---", flush=True)
        return
    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    password = (settings.smtp_password or "").replace(" ", "")  # Google shows app passwords with spaces
    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=20, context=ssl.create_default_context()) as s:
                if settings.smtp_user:
                    s.login(settings.smtp_user, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
                s.ehlo()
                s.starttls(context=ssl.create_default_context())
                s.ehlo()
                if settings.smtp_user:
                    s.login(settings.smtp_user, password)
                s.send_message(msg)
        print(f"EMAIL SENT to {to}: {subject}", flush=True)
    except Exception as exc:  # never crash the request because of mail trouble
        print(f"\n!!! EMAIL FAILED to {to}: {type(exc).__name__}: {exc}\n", flush=True)
        logger.exception("Failed to send email to %s", to)
        if raise_errors:
            raise


def send_otp_email(to: str, otp: str, minutes: int) -> None:
    send_email(to, "Your VTU Clubs verification code",
               f"Your verification code is {otp}.\nIt expires in {minutes} minutes. Do not share it with anyone.\n\nIf you did not request this, ignore this email.")


def send_welcome_email(to: str, name: str, club: str, code: str, status: str) -> None:
    extra = "\nYour membership is awaiting admin approval." if status == "pending" else ""
    send_email(to, f"Welcome to the {club} Club - {code}",
               f"Hi {name},\n\nYou are now registered with the {club} Club.\nYour membership ID: {code}{extra}\n\nKeep this ID safe.\n- VTU Clubs")
