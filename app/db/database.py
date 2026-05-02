# app/db/database.py — Async SQLAlchemy engine and session factory
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings


# Build connect_args based on database type
_connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

# Add SSL requirement for PostgreSQL (required by cloud providers like Render)
# For asyncpg (async PostgreSQL driver), ssl=True enables SSL mode
if "postgresql" in settings.DATABASE_URL.lower():
    _connect_args["ssl"] = True

# Create async engine — O(1)
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=_connect_args,
)

# Session factory — O(1)
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting async DB sessions. O(1)"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create all tables. O(n) where n = number of tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database engine. O(1)"""
    await engine.dispose()
