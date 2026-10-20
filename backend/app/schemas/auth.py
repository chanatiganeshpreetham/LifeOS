from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints


def _validate_password_bytes(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes.")
    return password


Password = Annotated[
    str,
    StringConstraints(min_length=8, max_length=72),
    AfterValidator(_validate_password_bytes),
]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: Password
    full_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ]


class EmailOtpRequest(BaseModel):
    email: EmailStr
    code: Annotated[str, StringConstraints(pattern=r"^\d{6}$")]


class LoginRequest(BaseModel):
    email: EmailStr
    password: Password


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirmRequest(EmailOtpRequest):
    new_password: Password


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str
    avatar_url: str | None
    timezone: str
    is_verified: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class MessageResponse(BaseModel):
    message: str
