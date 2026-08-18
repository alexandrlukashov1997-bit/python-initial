from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from baseproject.core.config import settings

engine = create_async_engine(
    settings.sqlalchemy_database_url,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
