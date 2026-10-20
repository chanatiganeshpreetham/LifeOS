import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.services import auth0

_ISSUER = "https://auth0.example.com/"
_DOMAIN = "auth0.example.com"
_AUDIENCE = "https://lifeos-api"


class _SigningKey:
    def __init__(self, key: rsa.RSAPrivateKey) -> None:
        self.key = key.public_key()


class _JwksClient:
    def __init__(self, key: rsa.RSAPrivateKey) -> None:
        self.signing_key = _SigningKey(key)

    def get_signing_key_from_jwt(self, token: str) -> _SigningKey:
        return self.signing_key


def _make_token(key: rsa.RSAPrivateKey, issued_at: int) -> str:
    return jwt.encode(
        {
            "sub": "test-user",
            "aud": _AUDIENCE,
            "iss": _ISSUER,
            "iat": issued_at,
            "exp": issued_at + 300,
        },
        key,
        algorithm="RS256",
    )


def test_decode_token_allows_small_clock_skew(monkeypatch: pytest.MonkeyPatch) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(auth0, "_jwks_client", lambda domain: _JwksClient(key))
    token = _make_token(key, int(time.time()) + 30)

    claims = auth0._decode_token(token, _AUDIENCE, _ISSUER, _DOMAIN)

    assert claims["sub"] == "test-user"


def test_decode_token_rejects_large_future_clock_skew(monkeypatch: pytest.MonkeyPatch) -> None:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(auth0, "_jwks_client", lambda domain: _JwksClient(key))
    token = _make_token(key, int(time.time()) + 120)

    with pytest.raises(HTTPException) as error:
        auth0._decode_token(token, _AUDIENCE, _ISSUER, _DOMAIN)

    assert error.value.status_code == 401
