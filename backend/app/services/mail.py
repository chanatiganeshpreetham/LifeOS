import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from threading import Lock

from fastapi import HTTPException, status

from app.core.config import get_settings

_DEV_MAILBOX_TTL = timedelta(minutes=10)
_DEV_MAILBOX_MAX_MESSAGES = 1000
_mailbox_lock = Lock()


@dataclass(frozen=True)
class DevelopmentMail:
    email: str
    purpose: str
    code: str
    created_at: datetime


_development_mailbox: list[DevelopmentMail] = []


def send_otp_email(email: str, purpose: str, code: str) -> None:
    settings = get_settings()
    if not settings.mail_host and settings.environment == "development":
        now = datetime.now(UTC)
        with _mailbox_lock:
            _development_mailbox[:] = [
                item for item in _development_mailbox if now - item.created_at < _DEV_MAILBOX_TTL
            ]
            _development_mailbox.append(
                DevelopmentMail(email=email, purpose=purpose, code=code, created_at=now)
            )
            del _development_mailbox[:-_DEV_MAILBOX_MAX_MESSAGES]
        return

    if not settings.mail_host:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery is not configured.",
        )

    message = EmailMessage()
    message["Subject"] = (
        "Verify your LifeOS email" if purpose == "email_verify" else "Reset your LifeOS password"
    )
    message["From"] = settings.mail_from
    message["To"] = email
    message.set_content(
        f"Your LifeOS verification code is {code}. "
        "It expires in 10 minutes and can only be used once."
    )

    try:
        with smtplib.SMTP(settings.mail_host, settings.mail_port, timeout=10) as smtp:
            if settings.mail_starttls:
                smtp.starttls()
            if settings.mail_username and settings.mail_password:
                smtp.login(settings.mail_username, settings.mail_password.get_secret_value())
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email delivery failed. Please try again.",
        ) from error


def get_development_mailbox(email: str) -> list[DevelopmentMail]:
    now = datetime.now(UTC)
    with _mailbox_lock:
        _development_mailbox[:] = [
            item for item in _development_mailbox if now - item.created_at < _DEV_MAILBOX_TTL
        ]
        return [item for item in _development_mailbox if item.email == email]
