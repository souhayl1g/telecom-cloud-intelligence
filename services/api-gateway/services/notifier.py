"""SMS + email transport for NeXo actuation layer.

Provider chain (per channel):
  SMS:   Twilio (if TWILIO_* env set) → console-log
  Email: SMTP (if SMTP_* env set)     → console-log

Every send is audited to `notifications_sent` regardless of provider — the
console fallback writes a row with provider='console', status='logged' so
the defense-demo UI looks identical to a real send.
"""

from __future__ import annotations

import os
import smtplib
import uuid
from dataclasses import dataclass, asdict
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr
from typing import Optional

from psycopg2.extras import RealDictCursor

from db import _db

# ── Env-gated provider config ─────────────────────────────────────────────
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
TWILIO_FROM = os.getenv("TWILIO_FROM", "").strip()

SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
try:
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
except ValueError:
    SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", "").strip()
# Strip whitespace AND any embedded spaces (Gmail App Passwords are displayed
# as 4 groups of 4 — paste-with-spaces is the #1 cause of 535 BadCredentials).
SMTP_PASS = os.getenv("SMTP_PASS", "").strip().replace(" ", "")
SMTP_FROM_RAW = os.getenv("SMTP_FROM", "nexo-noreply@tunisietelecom.tn").strip()
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "").strip()

# Split header (display+address) from envelope (bare address).
_from_display, _from_addr = parseaddr(SMTP_FROM_RAW)
if not _from_addr:
    _from_addr = SMTP_FROM_RAW  # last-resort fallback
SMTP_FROM_ADDR = _from_addr  # envelope sender (sendmail)
SMTP_FROM_HEADER = formataddr(  # human-friendly From: header
    (SMTP_FROM_NAME or _from_display or "", _from_addr)
)


@dataclass
class NotificationResult:
    channel: str
    recipient: str
    provider: str
    status: str  # 'sent' | 'failed' | 'logged'
    provider_msg_id: Optional[str] = None
    error: Optional[str] = None

    def dict(self) -> dict:
        return asdict(self)


def _audit(
    *,
    channel: str,
    recipient: str,
    subject: Optional[str],
    body: str,
    provider: str,
    status: str,
    provider_msg_id: Optional[str],
    error: Optional[str],
    source_action_id: Optional[str],
    source_imsi_hash: Optional[str],
) -> None:
    """Insert a row into notifications_sent. Never raises (audit is best-effort)."""
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO notifications_sent
                        (channel, recipient, subject, body, provider, provider_msg_id,
                         status, error, source_action_id, source_imsi_hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        channel,
                        recipient,
                        subject,
                        body,
                        provider,
                        provider_msg_id,
                        status,
                        error,
                        source_action_id,
                        source_imsi_hash,
                    ),
                )
    except Exception as e:
        # Print to stdout — never crash the playbook on audit failure
        print(f"[notifier] audit insert failed: {e}")


def _twilio_configured() -> bool:
    return bool(TWILIO_SID and TWILIO_TOKEN and TWILIO_FROM)


def _smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def send_sms(
    recipient: str,
    body: str,
    *,
    source_action_id: Optional[str] = None,
    source_imsi_hash: Optional[str] = None,
) -> NotificationResult:
    """Send SMS via Twilio if configured, else console-log + audit."""
    if _twilio_configured():
        try:
            from twilio.rest import Client  # local import — optional dep

            client = Client(TWILIO_SID, TWILIO_TOKEN)
            msg = client.messages.create(body=body, from_=TWILIO_FROM, to=recipient)
            result = NotificationResult(
                channel="sms",
                recipient=recipient,
                provider="twilio",
                status="sent",
                provider_msg_id=msg.sid,
            )
            _audit(
                channel="sms",
                recipient=recipient,
                subject=None,
                body=body,
                provider="twilio",
                status="sent",
                provider_msg_id=msg.sid,
                error=None,
                source_action_id=source_action_id,
                source_imsi_hash=source_imsi_hash,
            )
            return result
        except Exception as e:
            err = str(e)[:300]
            _audit(
                channel="sms",
                recipient=recipient,
                subject=None,
                body=body,
                provider="twilio",
                status="failed",
                provider_msg_id=None,
                error=err,
                source_action_id=source_action_id,
                source_imsi_hash=source_imsi_hash,
            )
            return NotificationResult(
                channel="sms",
                recipient=recipient,
                provider="twilio",
                status="failed",
                error=err,
            )

    # Console fallback — defense demo path
    fake_id = f"console-{uuid.uuid4().hex[:12]}"
    print(f"[notifier:console:sms] to={recipient} body={body[:120]!r}")
    _audit(
        channel="sms",
        recipient=recipient,
        subject=None,
        body=body,
        provider="console",
        status="logged",
        provider_msg_id=fake_id,
        error=None,
        source_action_id=source_action_id,
        source_imsi_hash=source_imsi_hash,
    )
    return NotificationResult(
        channel="sms",
        recipient=recipient,
        provider="console",
        status="logged",
        provider_msg_id=fake_id,
    )


def send_email(
    recipient: str,
    subject: str,
    body: str,
    *,
    source_action_id: Optional[str] = None,
) -> NotificationResult:
    """Send email via SMTP if configured, else console-log + audit."""
    if _smtp_configured():
        try:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM_HEADER
            msg["To"] = recipient

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM_ADDR, [recipient], msg.as_string())

            msg_id = f"smtp-{uuid.uuid4().hex[:12]}"
            _audit(
                channel="email",
                recipient=recipient,
                subject=subject,
                body=body,
                provider="smtp",
                status="sent",
                provider_msg_id=msg_id,
                error=None,
                source_action_id=source_action_id,
                source_imsi_hash=None,
            )
            return NotificationResult(
                channel="email",
                recipient=recipient,
                provider="smtp",
                status="sent",
                provider_msg_id=msg_id,
            )
        except Exception as e:
            err = str(e)[:300]
            _audit(
                channel="email",
                recipient=recipient,
                subject=subject,
                body=body,
                provider="smtp",
                status="failed",
                provider_msg_id=None,
                error=err,
                source_action_id=source_action_id,
                source_imsi_hash=None,
            )
            return NotificationResult(
                channel="email",
                recipient=recipient,
                provider="smtp",
                status="failed",
                error=err,
            )

    fake_id = f"console-{uuid.uuid4().hex[:12]}"
    print(f"[notifier:console:email] to={recipient} subject={subject!r}")
    _audit(
        channel="email",
        recipient=recipient,
        subject=subject,
        body=body,
        provider="console",
        status="logged",
        provider_msg_id=fake_id,
        error=None,
        source_action_id=source_action_id,
        source_imsi_hash=None,
    )
    return NotificationResult(
        channel="email",
        recipient=recipient,
        provider="console",
        status="logged",
        provider_msg_id=fake_id,
    )


def send_email_with_attachment(
    recipient: str,
    subject: str,
    body: str,
    attachment_bytes: bytes,
    attachment_filename: str,
    *,
    attachment_mime_subtype: str = "pdf",
    source_action_id: Optional[str] = None,
) -> NotificationResult:
    """Send a multipart email with a binary attachment.

    Falls back to console-log + audit row when SMTP env vars are unset, so the
    defense-demo path still produces evidence rows in notifications_sent.
    """
    if _smtp_configured():
        try:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = SMTP_FROM_HEADER
            msg["To"] = recipient
            msg.attach(MIMEText(body, "plain", "utf-8"))

            part = MIMEApplication(attachment_bytes, _subtype=attachment_mime_subtype)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment_filename,
            )
            msg.attach(part)

            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.sendmail(SMTP_FROM_ADDR, [recipient], msg.as_string())

            msg_id = f"smtp-{uuid.uuid4().hex[:12]}"
            audit_body = f"{body}\n\n[attachment: {attachment_filename} ({len(attachment_bytes)} bytes)]"
            _audit(
                channel="email",
                recipient=recipient,
                subject=subject,
                body=audit_body,
                provider="smtp",
                status="sent",
                provider_msg_id=msg_id,
                error=None,
                source_action_id=source_action_id,
                source_imsi_hash=None,
            )
            return NotificationResult(
                channel="email",
                recipient=recipient,
                provider="smtp",
                status="sent",
                provider_msg_id=msg_id,
            )
        except Exception as e:
            err = str(e)[:300]
            _audit(
                channel="email",
                recipient=recipient,
                subject=subject,
                body=f"{body}\n\n[attachment: {attachment_filename}]",
                provider="smtp",
                status="failed",
                provider_msg_id=None,
                error=err,
                source_action_id=source_action_id,
                source_imsi_hash=None,
            )
            return NotificationResult(
                channel="email",
                recipient=recipient,
                provider="smtp",
                status="failed",
                error=err,
            )

    fake_id = f"console-{uuid.uuid4().hex[:12]}"
    print(
        f"[notifier:console:email] to={recipient} subject={subject!r} "
        f"attachment={attachment_filename} ({len(attachment_bytes)} bytes)"
    )
    _audit(
        channel="email",
        recipient=recipient,
        subject=subject,
        body=f"{body}\n\n[attachment: {attachment_filename} ({len(attachment_bytes)} bytes)]",
        provider="console",
        status="logged",
        provider_msg_id=fake_id,
        error=None,
        source_action_id=source_action_id,
        source_imsi_hash=None,
    )
    return NotificationResult(
        channel="email",
        recipient=recipient,
        provider="console",
        status="logged",
        provider_msg_id=fake_id,
    )


def list_notifications(
    *,
    recipient: Optional[str] = None,
    channel: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """Audit query — returns recent notifications."""
    where = []
    params: list = []
    if recipient:
        where.append("recipient = %s")
        params.append(recipient)
    if channel:
        where.append("channel = %s")
        params.append(channel)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)
    with _db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                f"""
                SELECT id, channel, recipient, subject, body, provider,
                       provider_msg_id, status, error, source_action_id,
                       source_imsi_hash, sent_at
                FROM notifications_sent
                {where_sql}
                ORDER BY sent_at DESC
                LIMIT %s;
                """,
                tuple(params),
            )
            return list(cur.fetchall())
