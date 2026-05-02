# app/db/database.py — Async SQLAlchemy engine and session factory
import sys
import ssl
import os

# IMMEDIATE print to stderr (should show in Render logs)
print("[DB_START] Loading database module", flush=True)
sys.stderr.write("[DB_START] Loading database module\n")
sys.stderr.flush()

# Get DATABASE_URL from environment (Render sets this)
_DATABASE_URL = os.environ.get("DATABASE_URL", "")

print(f"[DB_URL] Raw URL: {_DATABASE_URL[:60]}...", flush=True)
sys.stderr.write(f"[DB_URL] Raw URL: {_DATABASE_URL[:60]}...\n")
sys.stderr.flush()

# Convert postgres:// to postgresql+asyncpg://
if _DATABASE_URL.startswith("postgres://"):
    _DATABASE_URL = _DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
    print("[DB_URL] Converted postgres:// to postgresql+asyncpg://", flush=True)
elif _DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in _DATABASE_URL:
    _DATABASE_URL = _DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    print("[DB_URL] Added +asyncpg driver", flush=True)

print(f"[DB_URL] Final URL prefix: {_DATABASE_URL[:35]}...", flush=True)

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# Build connect_args
_connect_args = {"check_same_thread": False} if "sqlite" in _DATABASE_URL else {}

# Add SSL for PostgreSQL
if "postgresql" in _DATABASE_URL.lower():
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    _connect_args["ssl"] = ssl_context
    print("[DB_SSL] SSL enabled for PostgreSQL", flush=True)

# Create engine
print("[DB_ENGINE] Creating async engine...", flush=True)
engine = create_async_engine(
    _DATABASE_URL,
    echo=False,
    connect_args=_connect_args,
)
print("[DB_ENGINE] Engine created successfully", flush=True)

# Session factory
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting async DB sessions"""
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
    """Create all tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database engine"""
    await engine.dispose()
