from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from slowapi import Limiter
from sqlalchemy.orm import Session

from app.core.dependencies import get_auth0_access_claims, get_current_user, get_db
from app.core.rate_limit import limiter
from app.models import User
from app.repositories import auth as auth_repository
from app.schemas.auth import UserResponse
from app.services.auth0 import provision_user, verify_id_token

router = APIRouter(prefix="/auth", tags=["authentication"])
_limiter: Limiter = limiter


@router.post("/session", response_model=UserResponse)
@_limiter.limit("60/minute")
def initialize_session(
    request: Request,
    response: Response,
    access_claims: dict[str, Any] = Depends(get_auth0_access_claims),
    session: Session = Depends(get_db),
) -> UserResponse:
    subject = access_claims["sub"]
    user = auth_repository.get_user_by_auth0_subject(session, subject)
    if user is None:
        id_token = request.headers.get("X-LifeOS-ID-Token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="An Auth0 identity token is required to initialize your LifeOS profile.",
            )
        identity_claims = verify_id_token(id_token)
        if identity_claims.get("sub") != subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The Auth0 identity token does not match the access token.",
            )
        user = provision_user(session, identity_claims)
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is inactive.",
        )
    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
@_limiter.limit("60/minute")
def get_profile(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
) -> UserResponse:
    return UserResponse.model_validate(user)
