"""email_service.send_email SMTP path.

The client used to require the server to offer STARTTLS on any port other than
465 and silently failed on servers that do not. Sending must work on servers
with and without STARTTLS.
"""
from app.config import settings
from app.services import email_service


class FakeSMTP:
    """Stands in for smtplib.SMTP; records the commands the client would send."""

    advertise_starttls = False
    created = []

    def __init__(self, host, port, timeout=None):
        self.calls = []
        FakeSMTP.created.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def ehlo(self):
        self.calls.append("ehlo")

    def has_extn(self, ext):
        return ext.lower() == "starttls" and self.advertise_starttls

    def starttls(self, context=None):
        self.calls.append("starttls")

    def login(self, user, password):
        self.calls.append("login")

    def send_message(self, msg):
        self.calls.append(("send_message", msg["Subject"]))


def _use_smtp_backend(monkeypatch, advertise_starttls):
    FakeSMTP.advertise_starttls = advertise_starttls
    FakeSMTP.created = []
    monkeypatch.setattr(email_service.smtplib, "SMTP",
                        lambda host, port, timeout=None: FakeSMTP(host, port, timeout))
    monkeypatch.setattr(settings, "email_backend", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_port", 2525)
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "pass")
    email_service.send_email("receiver@example.com", "Subject", "Body")
    return FakeSMTP.created[-1]


def test_starttls_is_used_when_the_server_offers_it(monkeypatch):
    fake = _use_smtp_backend(monkeypatch, advertise_starttls=True)
    assert "starttls" in fake.calls
    assert any(c[0] == "send_message" for c in fake.calls)


def test_sends_when_the_server_does_not_offer_starttls(monkeypatch):
    fake = _use_smtp_backend(monkeypatch, advertise_starttls=False)
    assert "starttls" not in fake.calls
    assert any(c[0] == "send_message" for c in fake.calls)
