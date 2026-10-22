import ssl

import pytest
from sqlalchemy.engine import make_url

from app.db.engine import _database_url_and_connect_args, normalize_database_url


def test_normalizes_prisma_postgres_url_and_requires_verified_tls() -> None:
    url, connect_args = _database_url_and_connect_args(
        "postgres://user:secret@pooled.db.prisma.io:5432/postgres?sslmode=require"
    )

    assert url.drivername == "postgresql+pg8000"
    assert url.host == "pooled.db.prisma.io"
    assert "sslmode" not in url.query
    assert isinstance(connect_args["ssl_context"], ssl.SSLContext)
    assert connect_args["ssl_context"].verify_mode == ssl.CERT_REQUIRED
    assert connect_args["ssl_context"].check_hostname


def test_preserves_other_query_options_when_normalizing_url() -> None:
    url = normalize_database_url(
        "postgresql://user:secret@db.example.com/lifeos?sslmode=require&application_name=lifeos"
    )

    assert url.drivername == "postgresql+pg8000"
    assert url.query == {"application_name": "lifeos"}


def test_maps_verify_ca_ssl_mode_without_disabling_certificate_verification() -> None:
    _, connect_args = _database_url_and_connect_args(
        "postgresql+pg8000://user:secret@db.example.com/lifeos?sslmode=verify-ca"
    )

    context = connect_args["ssl_context"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert not context.check_hostname


def test_rejects_unsupported_ssl_mode() -> None:
    with pytest.raises(ValueError, match="Unsupported PostgreSQL sslmode"):
        _database_url_and_connect_args("postgres://user:secret@db.example.com/lifeos?sslmode=allow")


def test_normalizes_explicit_psycopg_driver_urls() -> None:
    url, connect_args = _database_url_and_connect_args(
        make_url("postgresql+psycopg://user:secret@db.example.com/lifeos?sslmode=require")
    )

    assert url.drivername == "postgresql+pg8000"
    assert url.query == {}
    assert isinstance(connect_args["ssl_context"], ssl.SSLContext)


def test_parses_percent_encoded_password_with_special_characters() -> None:
    url = normalize_database_url("postgresql+psycopg://user:p%40%40ss@db.example.com/lifeos")

    assert url.password == "p@@ss"
    assert "p%40%40ss@" in url.render_as_string(hide_password=False)
