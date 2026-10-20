import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import bcrypt
import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import OtpCode, RefreshToken, User
from app.repositories import auth as auth_repository
from app.services.mail import send_otp_email

ACCESS_TOKEN_SECONDS = 15 * 60
REFRESH_TOKEN_DAYS = 7
OTP_MINUTES = 10
_JWT_ALGORITHM = "HS256"


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("ascii")


def _verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("ascii"))
    except (ValueError, TypeError):
        return False


def _hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_otp(session: Session, user_id: UUID, purpose: str) -> str:
    auth_repository.mark_active_otps_used(session, user_id, purpose)
    code = f"{secrets.randbelow(1_000_000):06d}"
    auth_repository.add_otp(
        session,
        OtpCode(
            user_id=user_id,
            code_hash=_hash_password(code),
            purpose=purpose,
            expires_at=_now() + timedelta(minutes=OTP_MINUTES),
        ),
    )
    return code


def _check_otp(session: Session, user_id: UUID, purpose: str, code: str) -> OtpCode:
    otp = auth_repository.get_active_otp(session, user_id, purpose, _now())
    if otp is None or not _verify_password(code, otp.code_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The code is invalid or expired.",
        )
    otp.is_used = True
    return otp


def register_user(session: Session, email: str, password: str, full_name: str) -> None:
    normalized_email = email.strip().lower()
    user = auth_repository.get_user_by_email(session, normalized_email)
    if user and user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if user is None:
        user = User(
            email=normalized_email,
            hashed_password=_hash_password(password),
            full_name=full_name.strip(),
        )
        auth_repository.create_user(session, user)
        session.flush()
    else:
        user.full_name = full_name.strip()
        user.hashed_password = _hash_password(password)

    code = _new_otp(session, user.id, "email_verify")
    session.commit()
    send_otp_email(normalized_email, "email_verify", code)


def verify_email(session: Session, email: str, code: str) -> None:
    user = auth_repository.get_user_by_email(session, email.strip().lower())
    if user is None or user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The code is invalid or expired.",
        )
    _check_otp(session, user.id, "email_verify", code)
    user.is_verified = True
    session.commit()


def _create_session(session: Session, user: User, user_agent: str | None) -> tuple[str, str, int]:
    now = _now()
    settings = get_settings()
    access_token = jwt.encode(
        {
            "sub": str(user.id),
            "iat": now,
            "exp": now + timedelta(seconds=ACCESS_TOKEN_SECONDS),
            "type": "access",
        },
        settings.secret_key.get_secret_value(),
        algorithm=_JWT_ALGORITHM,
    )
    refresh_token = secrets.token_urlsafe(48)
    auth_repository.add_refresh_token(
        session,
        RefreshToken(
            user_id=user.id,
            token_hash=_hash_opaque_token(refresh_token),
            expires_at=now + timedelta(days=REFRESH_TOKEN_DAYS),
            device_hint=(user_agent or "")[:100] or None,
        ),
    )
    return access_token, refresh_token, REFRESH_TOKEN_DAYS * 24 * 60 * 60


def login(
    session: Session, email: str, password: str, user_agent: str | None
) -> tuple[str, str, int, User]:
    user = auth_repository.get_user_by_email(session, email.strip().lower())
    if user is None or not _verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email before signing in.",
        )
    access_token, refresh_token, refresh_max_age = _create_session(session, user, user_agent)
    session.commit()
    return access_token, refresh_token, refresh_max_age, user


def refresh_session(
    session: Session, refresh_cookie: str, user_agent: str | None
) -> tuple[str, str, int, User]:
    now = _now()
    old_token = auth_repository.get_refresh_token(session, _hash_opaque_token(refresh_cookie), now)
    if old_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        )
    user = auth_repository.get_user_by_id(session, old_token.user_id)
    if user is None:
        old_token.is_revoked = True
        session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is no longer available. Please sign in again.",
        )

    old_token.is_revoked = True
    access_token, new_refresh_token, refresh_max_age = _create_session(session, user, user_agent)
    session.commit()
    return access_token, new_refresh_token, refresh_max_age, user


def logout(session: Session, refresh_cookie: str | None) -> None:
    if refresh_cookie:
        auth_repository.revoke_refresh_token(session, _hash_opaque_token(refresh_cookie))
        session.commit()


def request_password_reset(session: Session, email: str) -> None:
    normalized_email = email.strip().lower()
    user = auth_repository.get_user_by_email(session, normalized_email)
    if user is None or not user.is_active:
        return
    code = _new_otp(session, user.id, "password_reset")
    session.commit()
    send_otp_email(normalized_email, "password_reset", code)


def confirm_password_reset(session: Session, email: str, code: str, new_password: str) -> None:
    user = auth_repository.get_user_by_email(session, email.strip().lower())
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The code is invalid or expired.",
        )
    _check_otp(session, user.id, "password_reset", code)
    user.hashed_password = _hash_password(new_password)
    auth_repository.revoke_all_user_refresh_tokens(session, user.id)
    session.commit()


def decode_access_token(access_token: str) -> UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            access_token,
            settings.secret_key.get_secret_value(),
            algorithms=[_JWT_ALGORITHM],
            options={"require": ["exp", "sub", "type"]},
        )
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
