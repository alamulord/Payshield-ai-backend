# app/db/database.py — Async SQLAlchemy engine and session factory
import sys
import ssl
import os

# Debug logging to file
_debug_log = []
def log(msg):
    _debug_log.append(msg)
    with open('/tmp/db_debug.log', 'a') as f:
        f.write(msg + '\n')

log("=== DATABASE MODULE LOADING ===")

# Get DATABASE_URL - check all possible env var names
_DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL_INTERNAL")
log(f"Raw DATABASE_URL: {_DATABASE_URL}")

# If not in env, check settings (for local development)
if not _DATABASE_URL:
    log("DATABASE_URL not in env, using settings")
    from app.core.config import settings
    _DATABASE_URL = settings.DATABASE_URL
    log(f"From settings: {_DATABASE_URL}")

# CRITICAL: Force conversion to postgresql+asyncpg
if _DATABASE_URL:
    # Handle postgres:// (Render's format)
    if _DATABASE_URL.startswith("postgres://"):
        _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        log("Converted postgres:// to postgresql+asyncpg://")
    # Handle postgresql:// without +asyncpg
    elif _DATABASE_URL.startswith("postgresql://"):
        _DATABASE_URL = _DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        log("Added +asyncpg driver")

log(f"FINAL DATABASE_URL: {_DATABASE_URL}")

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Build connect_args based on database type
_connect_args = {"check_same_thread": False} if "sqlite" in _DATABASE_URL else {}

# Add SSL for PostgreSQL (Render requires SSL)
if "postgresql" in _DATABASE_URL.lower():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    _connect_args["ssl"] = ssl_context
    log("SSL enabled")

log(f"Creating engine with URL starting with: {_DATABASE_URL[:30]}")

engine = create_async_engine(
    _DATABASE_URL,
    echo=os.environ.get("DEBUG", "false").lower() == "true",
    connect_args=_connect_args,
)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

log("Engine created successfully")

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

# Also print at end of module load
print(f"\n\n[DB_INIT] DATABASE_URL used: {_DATABASE_URL[:50]}...")
print(f"[DB_INIT] Engine created successfully\n\n")
