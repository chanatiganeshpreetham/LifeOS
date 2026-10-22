import ssl
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, make_url


def _database_url_and_connect_args(database_url: str | URL) -> tuple[URL, dict[str, Any]]:
    url = make_url(database_url)
    if url.drivername in {
        "postgres",
        "postgresql",
        "postgresql+psycopg",
        "postgresql+psycopg2",
    }:
        url = url.set(drivername="postgresql+pg8000")

    connect_args: dict[str, Any] = {}
    if url.drivername != "postgresql+pg8000":
        return url, connect_args

    query = dict(url.query)
    sslmode = query.pop("sslmode", None)
    if isinstance(sslmode, tuple):
        if len(sslmode) != 1:
            raise ValueError("DATABASE_URL must specify sslmode at most once")
        sslmode = sslmode[0]
    url = url.set(query=query)

    if sslmode is None:
        return url, connect_args

    normalized_sslmode = sslmode.lower()
    if normalized_sslmode == "disable":
        connect_args["ssl_context"] = False
    elif normalized_sslmode in {"require", "verify-full"}:
        connect_args["ssl_context"] = ssl.create_default_context()
    elif normalized_sslmode == "verify-ca":
        context = ssl.create_default_context()
        context.check_hostname = False
        connect_args["ssl_context"] = context
    elif normalized_sslmode == "prefer":
        connect_args["ssl_context"] = None
    else:
        raise ValueError(f"Unsupported PostgreSQL sslmode for pg8000: {sslmode}")

    return url, connect_args


def normalize_database_url(database_url: str | URL) -> URL:
    return _database_url_and_connect_args(database_url)[0]


def create_database_engine(database_url: str | URL, **kwargs: Any) -> Engine:
    url, ssl_connect_args = _database_url_and_connect_args(database_url)
    connect_args = {**kwargs.pop("connect_args", {}), **ssl_connect_args}
    return create_engine(url, connect_args=connect_args, **kwargs)
