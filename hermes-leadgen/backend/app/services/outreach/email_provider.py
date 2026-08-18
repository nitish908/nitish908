"""Email-sending provider interface. Implemented so the plumbing exists,
but nothing in this codebase calls `send()` unless OUTREACH_LIVE_SEND_ENABLED
is explicitly set AND a matching, human-approved ApprovalRecord exists for
the exact recipient/channel/content/time being sent (see
app/api/routers/outreach.py). This keeps "live sending" a deliberate,
auditable opt-in rather than something that can happen by default.
"""
from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings


@dataclass
class SendResult:
    ok: bool
    detail: str = ""


class EmailProvider:
    def send(self, *, to_address: str, subject: str, body: str) -> SendResult:
        raise NotImplementedError


class SMTPEmailProvider(EmailProvider):
    def send(self, *, to_address: str, subject: str, body: str) -> SendResult:
        settings = get_settings()
        if not (settings.smtp_host and settings.smtp_from_address):
            return SendResult(False, "SMTP is not configured (SMTP_HOST/SMTP_FROM_ADDRESS missing)")

        message = EmailMessage()
        message["From"] = settings.smtp_from_address
        message["To"] = to_address
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(message)
            return SendResult(True)
        except (smtplib.SMTPException, OSError) as exc:
            return SendResult(False, str(exc))


def get_email_provider() -> EmailProvider:
    return SMTPEmailProvider()
