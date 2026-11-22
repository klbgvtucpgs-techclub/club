import html
import logging
import smtplib
import socket
import ssl
from email.message import EmailMessage
from typing import Optional

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


def _build_otp_text(otp: str, minutes: int, name: Optional[str] = None, club_name: Optional[str] = None) -> str:
    greeting = f"Hello {name}," if name else "Hello Student,"
    club_phrase = f"your registration for the {club_name} Club" if club_name else "VTU Clubs registration"
    return f"""==================================================
      VISVESVARAYA TECHNOLOGICAL UNIVERSITY
                VTU CLUBS HOUSE
==================================================

{greeting}

Thank you for your interest in {club_phrase}.
Your email verification code is:

     >>>  {otp}  <<<

This code is valid for {minutes} minutes (single use only).

SECURITY ADVISORY:
- Never share this code with anyone.
- VTU coordinators and staff will never ask for your verification code.
- If you did not request this verification, please disregard this email.

Warm regards,
VTU Clubs Central Committee
Visvesvaraya Technological University, Karnataka
=================================================="""


def _build_otp_html(otp: str, minutes: int, name: Optional[str] = None, club_name: Optional[str] = None) -> str:
    safe_name = html.escape(name) if name else "Student"
    club_text = f"your registration for the <strong>{html.escape(club_name)} Club</strong>" if club_name else "<strong>VTU Clubs</strong>"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VTU Clubs Email Verification</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c1017; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased;">
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0c1017; padding: 36px 12px;">
    <tr>
      <td align="center">
        <!-- Main Card Container -->
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 580px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 12px 36px rgba(0,0,0,0.45); border: 1px solid rgba(212,175,55,0.25);">
          
          <!-- University Header Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #0e141d 0%, #172132 100%); padding: 32px 28px; text-align: center; border-bottom: 3px solid #d4af37;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td align="center">
                    <div style="color: #d4af37; font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 8px;">
                      Visvesvaraya Technological University
                    </div>
                    <div style="color: #ffffff; font-size: 23px; font-weight: 800; letter-spacing: 0.5px; margin: 0;">
                      VTU STUDENT CLUBS
                    </div>
                    <div style="color: #94a3b8; font-size: 13px; margin-top: 6px; letter-spacing: 0.3px;">
                      Official Verification Service
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Main Body Content -->
          <tr>
            <td style="padding: 36px 32px 28px;">
              <h2 style="color: #0f172a; font-size: 21px; font-weight: 700; margin-top: 0; margin-bottom: 16px; letter-spacing: -0.3px;">
                Email Verification Code
              </h2>
              <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 14px;">
                Hello <strong>{safe_name}</strong>,
              </p>
              <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
                Thank you for your interest in joining {club_text}. To complete your email verification, please enter the One-Time Password (OTP) below:
              </p>

              <!-- OTP Code Display Card -->
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fdfbf7; border: 2px dashed #d4af37; border-radius: 12px; margin: 24px 0;">
                <tr>
                  <td align="center" style="padding: 26px 16px;">
                    <div style="color: #92400e; font-size: 11px; font-weight: 700; letter-spacing: 2.5px; text-transform: uppercase; margin-bottom: 10px;">
                      Your One-Time Password (OTP)
                    </div>
                    <div style="font-family: 'Courier New', Courier, monospace; font-size: 40px; font-weight: 800; letter-spacing: 12px; color: #0f172a; line-height: 1.2; padding-left: 12px;">
                      {otp}
                    </div>
                    <div style="display: inline-block; background-color: #fef3c7; color: #92400e; font-size: 12px; font-weight: 600; padding: 5px 14px; border-radius: 20px; margin-top: 14px; border: 1px solid #fde68a;">
                      &#x23F1; Valid for {minutes} minutes &bull; Single-use only
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Security Guidelines -->
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; border-left: 4px solid #2563eb; border-radius: 0 8px 8px 0; margin: 24px 0 20px;">
                <tr>
                  <td style="padding: 16px 18px;">
                    <div style="color: #1e3a8a; font-size: 13px; font-weight: 700; margin-bottom: 6px;">
                      &#x1F512; Important Security Notice
                    </div>
                    <ul style="color: #475569; font-size: 13px; line-height: 1.5; margin: 0; padding-left: 18px;">
                      <li style="margin-bottom: 4px;">Never disclose this code to anyone. VTU coordinators will never ask for it.</li>
                      <li>If you did not request this code, no action is needed; your details remain safe.</li>
                    </ul>
                  </td>
                </tr>
              </table>

              <p style="color: #64748b; font-size: 14px; line-height: 1.5; margin-top: 26px; margin-bottom: 0;">
                Warm regards,<br>
                <strong style="color: #0f172a;">VTU Clubs Central Committee</strong><br>
                <span style="font-size: 13px; color: #64748b;">Visvesvaraya Technological University</span>
              </p>
            </td>
          </tr>

          <!-- Official University Footer -->
          <tr>
            <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 22px 28px; text-align: center;">
              <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin: 0 0 6px;">
                <strong>Visvesvaraya Technological University (VTU)</strong><br>
                Jnana Sangama, Machhe, Belagavi / Kalaburagi, Karnataka, India
              </p>
              <p style="color: #94a3b8; font-size: 11px; margin: 0;">
                This is an automated system email. Please do not reply directly to this email.<br>
                &copy; 2026 VTU Clubs House. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_welcome_text(name: str, club: str, code: str, status: str) -> str:
    status_msg = "Your membership is awaiting admin approval." if status == "pending" else "Your membership is active and verified."
    return f"""==================================================
      VISVESVARAYA TECHNOLOGICAL UNIVERSITY
                VTU CLUBS HOUSE
==================================================

Welcome to the {club} Club!

Dear {name},

Congratulations! You are officially registered with the {club} Club.

Your Club Membership ID: {code}
Membership Status: {status.upper()} ({status_msg})

NEXT STEPS:
- Keep this Membership ID safe for event check-ins and hackathons.
- Check the VTU Clubs portal regularly for club announcements.
- Connect with your club coordinators and participate actively.

Welcome aboard!

Warm regards,
The {club} Club & VTU Clubs Central Committee
Visvesvaraya Technological University
=================================================="""


def _build_welcome_html(name: str, club: str, code: str, status: str) -> str:
    safe_name = html.escape(name)
    safe_club = html.escape(club)
    safe_code = html.escape(code)
    is_pending = status.lower() == "pending"
    status_label = "Pending Admin Approval" if is_pending else "Active Member"
    status_bg = "#fef3c7" if is_pending else "#dcfce7"
    status_color = "#92400e" if is_pending else "#166534"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Welcome to {safe_club} Club - VTU Clubs</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0c1017; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; -webkit-font-smoothing: antialiased;">
  <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #0c1017; padding: 36px 12px;">
    <tr>
      <td align="center">
        <!-- Main Card Container -->
        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 580px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 12px 36px rgba(0,0,0,0.45); border: 1px solid rgba(212,175,55,0.25);">
          
          <!-- University Header Banner -->
          <tr>
            <td style="background: linear-gradient(135deg, #0e141d 0%, #172132 100%); padding: 32px 28px; text-align: center; border-bottom: 3px solid #d4af37;">
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td align="center">
                    <div style="color: #d4af37; font-size: 11px; font-weight: 700; letter-spacing: 3px; text-transform: uppercase; margin-bottom: 8px;">
                      Visvesvaraya Technological University
                    </div>
                    <div style="color: #ffffff; font-size: 23px; font-weight: 800; letter-spacing: 0.5px; margin: 0;">
                      WELCOME TO VTU CLUBS
                    </div>
                    <div style="color: #94a3b8; font-size: 13px; margin-top: 6px;">
                      Official Membership Confirmation
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Main Body Content -->
          <tr>
            <td style="padding: 36px 32px 28px;">
              <h2 style="color: #0f172a; font-size: 21px; font-weight: 700; margin-top: 0; margin-bottom: 14px;">
                Registration Confirmed! &#x1F389;
              </h2>
              <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 14px;">
                Dear <strong>{safe_name}</strong>,
              </p>
              <p style="color: #334155; font-size: 15px; line-height: 1.6; margin: 0 0 24px;">
                Congratulations! You are officially registered with the <strong>{safe_club} Club</strong>. Your official membership details are provided below:
              </p>

              <!-- Membership Badge Card -->
              <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border: 2px solid #d4af37; border-radius: 14px; margin: 24px 0; color: #ffffff;">
                <tr>
                  <td style="padding: 26px 24px;">
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                      <tr>
                        <td>
                          <div style="color: #d4af37; font-size: 11px; font-weight: 700; letter-spacing: 2px; text-transform: uppercase;">
                            Club Membership ID
                          </div>
                          <div style="font-family: 'Courier New', Courier, monospace; font-size: 30px; font-weight: 800; color: #facc15; letter-spacing: 2px; margin: 10px 0;">
                            {safe_code}
                          </div>
                        </td>
                      </tr>
                    </table>
                    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-top: 1px solid rgba(255,255,255,0.15); padding-top: 14px; margin-top: 8px;">
                      <tr>
                        <td style="color: #94a3b8; font-size: 13px;">
                          Club: <strong style="color: #ffffff;">{safe_club}</strong>
                        </td>
                        <td align="right">
                          <span style="background-color: {status_bg}; color: {status_color}; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 12px; display: inline-block;">
                            {status_label}
                          </span>
                        </td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>

              <!-- What to do next -->
              <h3 style="color: #0f172a; font-size: 16px; font-weight: 700; margin: 24px 0 10px;">Next Steps</h3>
              <ul style="color: #475569; font-size: 14px; line-height: 1.6; margin: 0 0 24px; padding-left: 20px;">
                <li style="margin-bottom: 6px;">Keep this Membership ID handy for event access, workshops, and competitions.</li>
                <li style="margin-bottom: 6px;">Check the Announcements board on the VTU Clubs portal for club meetings.</li>
                <li>Reach out to your club leads and collaborate on upcoming university projects!</li>
              </ul>

              <p style="color: #64748b; font-size: 14px; line-height: 1.5; margin-top: 26px; margin-bottom: 0;">
                Warm regards,<br>
                <strong style="color: #0f172a;">The {safe_club} Club & VTU Clubs Central Committee</strong>
              </p>
            </td>
          </tr>

          <!-- Official University Footer -->
          <tr>
            <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 22px 28px; text-align: center;">
              <p style="color: #64748b; font-size: 12px; line-height: 1.5; margin: 0 0 6px;">
                <strong>Visvesvaraya Technological University (VTU)</strong><br>
                Jnana Sangama, Machhe, Belagavi / Kalaburagi, Karnataka, India
              </p>
              <p style="color: #94a3b8; font-size: 11px; margin: 0;">
                &copy; 2026 VTU Clubs House. All rights reserved.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_email(to: str, subject: str, body: str, html_body: Optional[str] = None, raise_errors: bool = False) -> None:
    """Send an email with plain-text body and optional rich HTML alternative.
    
    Supports 'memory' (tests), 'console' (local debugging), and 'smtp' with automatic
    STARTTLS/port 587 and SSL/port 465 fallback.
    """
    backend = (settings.email_backend or "console").strip().lower()
    if backend == "memory":
        OUTBOX.append({"to": to, "subject": subject, "body": body, "html": html_body})
        return
    if backend == "smtp" and not settings.smtp_host:
        logger.warning(
            "EMAIL_BACKEND is 'smtp' but SMTP_HOST is empty: mail cannot be sent over network. "
            "Set SMTP_HOST, SMTP_USER and SMTP_PASSWORD in .env, or set EMAIL_BACKEND=console."
        )
        backend = "console"
    if backend == "console":
        logger.info("Email (console mode) to %s: %s", to, subject)
        print(f"EMAIL (console mode) to {to}: {subject}", flush=True)
        return

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    if html_body:
        msg.add_alternative(html_body, subtype="html")

    password = (settings.smtp_password or "").replace(" ", "")  # Google app passwords can have spaces

    try:
        if settings.smtp_port == 465:
            with smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=20, context=ssl.create_default_context()) as s:
                if settings.smtp_user and password:
                    s.login(settings.smtp_user, password)
                s.send_message(msg)
        else:
            # Default to Port 587 (with STARTTLS if offered), with graceful SSL fallback on port 465
            try:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
                    s.ehlo()
                    if s.has_extn("starttls"):
                        s.starttls(context=ssl.create_default_context())
                        s.ehlo()
                    if settings.smtp_user and password:
                        s.login(settings.smtp_user, password)
                    s.send_message(msg)
            except (socket.timeout, TimeoutError, ConnectionError, OSError, smtplib.SMTPConnectError) as conn_err:
                # Some networks/ISPs block port 587 outbound; retry on SSL port 465
                logger.warning("SMTP connect failed on port %s (%s). Retrying with SSL on port 465...", settings.smtp_port, conn_err)
                with smtplib.SMTP_SSL(settings.smtp_host, 465, timeout=20, context=ssl.create_default_context()) as s:
                    if settings.smtp_user and password:
                        s.login(settings.smtp_user, password)
                    s.send_message(msg)

        print(f"EMAIL SENT to {to}: {subject}", flush=True)
        logger.info("Email sent successfully to %s: %s", to, subject)
    except Exception as exc:
        print(f"\n!!! EMAIL FAILED to {to}: {type(exc).__name__}: {exc}\n", flush=True)
        logger.exception("Failed to send email to %s", to)
        if raise_errors:
            raise


def send_otp_email(to: str, otp: str, minutes: int, name: Optional[str] = None, club_name: Optional[str] = None) -> None:
    subject = "Your VTU Clubs Verification Code"
    text_body = _build_otp_text(otp, minutes, name=name, club_name=club_name)
    html_body = _build_otp_html(otp, minutes, name=name, club_name=club_name)
    send_email(to, subject, text_body, html_body=html_body)


def send_welcome_email(to: str, name: str, club: str, code: str, status: str) -> None:
    subject = f"Welcome to the {club} Club - {code}"
    text_body = _build_welcome_text(name, club, code, status)
    html_body = _build_welcome_html(name, club, code, status)
    send_email(to, subject, text_body, html_body=html_body)
