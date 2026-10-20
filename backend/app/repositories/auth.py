from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models import OtpCode, RefreshToken, User


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email, User.deleted_at.is_(None)))


def get_user_by_email_including_deleted(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email))


def get_user_by_auth0_subject(session: Session, subject: str) -> User | None:
    return session.scalar(
        select(User).where(User.auth0_subject == subject, User.deleted_at.is_(None))
    )


def get_user_by_id(session: Session, user_id: UUID) -> User | None:
    return session.scalar(
        select(User).where(
            User.id == user_id,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
    )


def create_user(session: Session, user: User) -> None:
    session.add(user)


def add_otp(session: Session, otp: OtpCode) -> None:
    session.add(otp)


def get_active_otp(session: Session, user_id: UUID, purpose: str, now: datetime) -> OtpCode | None:
    return session.scalar(
        select(OtpCode)
        .where(
            OtpCode.user_id == user_id,
            OtpCode.purpose == purpose,
            OtpCode.is_used.is_(False),
            OtpCode.expires_at > now,
        )
        .order_by(OtpCode.created_at.desc())
        .limit(1)
        .with_for_update()
    )


def mark_active_otps_used(session: Session, user_id: UUID, purpose: str) -> None:
    session.execute(
        update(OtpCode)
        .where(
            OtpCode.user_id == user_id,
            OtpCode.purpose == purpose,
            OtpCode.is_used.is_(False),
        )
        .values(is_used=True)
    )


def add_refresh_token(session: Session, token: RefreshToken) -> None:
    session.add(token)


def get_refresh_token(session: Session, token_hash: str, now: datetime) -> RefreshToken | None:
    return session.scalar(
        select(RefreshToken)
        .where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > now,
        )
        .with_for_update()
    )


def revoke_refresh_token(session: Session, token_hash: str) -> None:
    session.execute(
        update(RefreshToken).where(RefreshToken.token_hash == token_hash).values(is_revoked=True)
    )


def revoke_all_user_refresh_tokens(session: Session, user_id: UUID) -> None:
    session.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked.is_(False))
        .values(is_revoked=True)
    )
