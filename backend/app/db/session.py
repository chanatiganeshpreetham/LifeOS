from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.db.engine import create_database_engine

settings = get_settings()
engine = create_database_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
