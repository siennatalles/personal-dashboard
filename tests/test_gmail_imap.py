"""Gmail IMAP connector: demo fallback + real-mode parsing (imaplib mocked)."""
from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from app.config import Settings
from app.connectors import gmail_imap
from app.models import Source


def test_demo_fallback_when_not_configured():
    settings = Settings(demo_mode=False, gmail_address="", gmail_app_password="")
    items, status = gmail_imap.fetch(settings)
    assert status.demo is True
    assert len(items) > 0
    assert all(i.source == Source.GMAIL for i in items)


def _raw_email(subject, sender, date_hdr, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["Date"] = date_hdr
    msg.set_content(body)
    return msg.as_bytes()


def test_real_fetch_parses_and_classifies_urgency():
    settings = Settings(demo_mode=False, gmail_address="me@gmail.com",
                         gmail_app_password="app-pw")

    unread_urgent = _raw_email(
        "URGENT: sign off needed", "boss@work.com",
        "Tue, 21 Jul 2026 10:00:00 -0000", "Please approve ASAP, this is time sensitive.",
    )
    read_newsletter = _raw_email(
        "Weekly digest", "newsletter@example.com",
        "Mon, 20 Jul 2026 08:00:00 -0000", "Here's what happened this week...",
    )

    fake_conn = MagicMock()
    fake_conn.login.return_value = ("OK", [b"success"])
    fake_conn.select.return_value = ("OK", [b"1"])
    fake_conn.search.return_value = ("OK", [b"1 2"])

    def fake_fetch(msg_id, spec):
        if msg_id == b"1":
            return "OK", [(b"1 (FLAGS () RFC822 {100}", unread_urgent)]
        return "OK", [(b"2 (FLAGS (\\Seen) RFC822 {100}", read_newsletter)]

    fake_conn.fetch.side_effect = fake_fetch

    with patch("imaplib.IMAP4_SSL", return_value=fake_conn):
        items, status = gmail_imap.fetch(settings)

    assert status.ok is True
    assert status.demo is False
    assert len(items) == 2

    urgent = next(i for i in items if i.subject.startswith("URGENT"))
    assert urgent.unread is True
    assert urgent.priority == "urgent"
    assert urgent.needs_reply is True

    newsletter = next(i for i in items if "digest" in i.subject.lower())
    assert newsletter.unread is False
    assert newsletter.priority == "low"
    assert newsletter.needs_reply is False


def test_real_fetch_surfaces_login_errors():
    settings = Settings(demo_mode=False, gmail_address="me@gmail.com",
                         gmail_app_password="wrong-pw")
    fake_conn = MagicMock()
    fake_conn.login.side_effect = Exception("Invalid credentials")

    with patch("imaplib.IMAP4_SSL", return_value=fake_conn):
        items, status = gmail_imap.fetch(settings)

    assert items == []
    assert status.ok is False
    assert "Invalid credentials" in status.error
