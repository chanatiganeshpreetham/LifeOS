import logging
from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError, PyJWTError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import User
from app.repositories import auth as auth_repository

logger = logging.getLogger(__name__)
_JWT_CLOCK_SKEW_LEEWAY_SECONDS = 60


@lru_cache(maxsize=4)
def _jwks_client(domain: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(f"https://{domain}/.well-known/jwks.json", cache_keys=True)


def _issuer_and_domain() -> tuple[str, str, str]:
    settings = get_settings()
    domain = (settings.auth0_domain or "").strip().removeprefix("https://").rstrip("/")
    audience = (settings.auth0_audience or "").strip()
    if not domain or not audience:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth0 is not configured for the LifeOS API.",
        )
    if "/" in domain or "://" in domain:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AUTH0_DOMAIN must be the Auth0 tenant hostname.",
        )
    return f"https://{domain}/", domain, audience


def _decode_token(token: str, audience: str, issuer: str, domain: str) -> dict[str, Any]:
    try:
        signing_key = _jwks_client(domain).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=issuer,
            leeway=_JWT_CLOCK_SKEW_LEEWAY_SECONDS,
            options={"require": ["exp", "iat", "sub", "aud", "iss"]},
        )
    except PyJWKClientConnectionError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not reach Auth0 to validate the token.",
        ) from error
    except (PyJWKClientError, PyJWTError, ValueError) as error:
        logger.warning(
            "Auth0 token validation failed (%s): %s",
            type(error).__name__,
            error,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Auth0 token is invalid or expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def verify_access_token(access_token: str) -> dict[str, Any]:
    issuer, domain, audience = _issuer_and_domain()
    claims = _decode_token(access_token, audience, issuer, domain)
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The access token does not identify a user.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return claims


def verify_id_token(id_token: str) -> dict[str, Any]:
    issuer, domain, _ = _issuer_and_domain()
    client_id = get_settings().auth0_client_id
    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth0 is not configured for the LifeOS API.",
        )
    return _decode_token(id_token, client_id, issuer, domain)


def provision_user(session: Session, claims: dict[str, Any]) -> User:
    subject = claims.get("sub")
    email = claims.get("email")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The Auth0 identity does not identify a user.",
        )
    if not isinstance(email, str) or not email.strip() or claims.get("email_verified") is not True:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verify your email with Auth0 before using LifeOS.",
        )
    normalized_email = email.strip().lower()
    user = auth_repository.get_user_by_auth0_subject(session, subject)
    if user is not None:
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This account is inactive.",
            )
        return user
    if auth_repository.get_user_by_email_including_deleted(session, normalized_email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already associated with a LifeOS account.",
        )

    name = claims.get("name")
    full_name = (
        name.strip() if isinstance(name, str) and name.strip() else normalized_email.split("@")[0]
    )
    picture = claims.get("picture")
    user = User(
        auth0_subject=subject,
        email=normalized_email,
        hashed_password=None,
        full_name=full_name[:100],
        avatar_url=picture if isinstance(picture, str) else None,
        is_verified=True,
    )
    try:
        with session.begin_nested():
            session.add(user)
            session.flush()
    except IntegrityError:
        user = auth_repository.get_user_by_auth0_subject(session, subject)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A LifeOS account could not be created for this identity.",
            ) from None
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    session.commit()
    return user
