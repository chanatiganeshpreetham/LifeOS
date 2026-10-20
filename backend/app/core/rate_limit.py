from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()
storage_uri = settings.redis_url if settings.environment == "production" else "memory://"
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    headers_enabled=True,
)
