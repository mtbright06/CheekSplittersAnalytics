from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(

    settings.DATABASE_URL,

    echo=settings.DEBUG,

    future=True,

    pool_pre_ping=True,
)

SessionLocal = sessionmaker(

    bind=engine,

    autoflush=False,

    autocommit=False,

    expire_on_commit=False,
)
