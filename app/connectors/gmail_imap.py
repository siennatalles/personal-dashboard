"""Gmail via IMAP + app password (personal Gmail accounts only — Google
Workspace accounts disabled IMAP basic auth in 2025; those need OAuth/Graph-
style access instead, which is out of scope here since this is a personal
tool).

Auth: enable 2-Step Verification, then generate an app password at
https://myaccount.google.com/apppasswords for "Mail".
"""
from __future__ import annotations

import email
import imaplib
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Tuple

from ..config import Settings
from ..demo_data import demo_gmail_emails
from ..models import EmailItem, Source, SourceStatus
from .common import simulate_latency, status_error, status_ok, timed

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
MAX_MESSAGES = 20

URGENT_KEYWORDS = ("urgent", "asap", "action required", "deadline", "important")
LOW_PRIORITY_SENDERS = ("no-reply", "noreply", "notifications@", "newsletter", "orders@")


def fetch(settings: Settings) -> Tuple[List[EmailItem], SourceStatus]:
    if settings.demo_mode or not settings.gmail_configured:
        with timed() as t:
            simulate_latency()
            items = demo_gmail_emails()
        return items, status_ok(Source.GMAIL, len(items), t["ms"],
                                 demo=True, configured=settings.gmail_configured)

    with timed() as t:
        try:
            items = _fetch_real(settings)
        except Exception as exc:  # noqa: BLE001
            return [], status_error(Source.GMAIL, t["ms"], True, str(exc))
    return items, status_ok(Source.GMAIL, len(items), t["ms"], demo=False, configured=True)


def _decode(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            out.append(text.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _snippet(msg: email.message.Message, max_len: int = 160) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and not part.get_filename():
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    continue
                break
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8", errors="replace")
        except Exception:
            body = ""
    body = " ".join(body.split())
    return body[:max_len]


def _classify(subject: str, sender: str, unread: bool) -> tuple[bool, str]:
    subject_l = subject.lower()
    sender_l = sender.lower()
    if any(s in sender_l for s in LOW_PRIORITY_SENDERS):
        return False, "low"
    if any(k in subject_l for k in URGENT_KEYWORDS):
        return True, "urgent"
    if unread:
        return True, "normal"
    return False, "normal"


def _fetch_real(settings: Settings) -> List[EmailItem]:
    conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    try:
        conn.login(settings.gmail_address, settings.gmail_app_password)
        conn.select("INBOX", readonly=True)
        status, data = conn.search(None, "ALL")
        if status != "OK":
            raise RuntimeError(f"IMAP search failed: {status}")
        ids = data[0].split()[-MAX_MESSAGES:]  # most recent N
        items: List[EmailItem] = []
        for msg_id in reversed(ids):
            status, msg_data = conn.fetch(msg_id, "(RFC822 FLAGS)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            flags_blob = str(msg_data[0][0])
            unread = "\\Seen" not in flags_blob

            subject = _decode(msg.get("Subject", "(no subject)"))
            sender = _decode(msg.get("From", "unknown sender"))
            date_hdr = msg.get("Date")
            try:
                received_at = parsedate_to_datetime(date_hdr) if date_hdr else None
            except Exception:
                received_at = None
            needs_reply, priority = _classify(subject, sender, unread)

            items.append(EmailItem(
                id=msg_id.decode(),
                source=Source.GMAIL,
                subject=subject,
                sender=sender,
                received_at=received_at or _now_fallback(),
                snippet=_snippet(msg),
                unread=unread,
                needs_reply=needs_reply,
                priority=priority,
            ))
        return items
    finally:
        try:
            conn.logout()
        except Exception:
            pass


def _now_fallback():
    from datetime import datetime
    return datetime.utcnow()
