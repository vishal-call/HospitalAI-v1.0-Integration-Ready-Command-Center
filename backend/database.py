import os
import subprocess
import logging
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy import text

logger = logging.getLogger("HospitalAI-Database")

def get_database_url() -> str:
    # 1. If explicit DATABASE_URL is set in environment, use it
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Rewriting postgresql driver to asyncpg for SQLAlchemy async compat
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif env_url.startswith("postgresql://"):
            env_url = env_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        
        # Parse query parameters to keep only what asyncpg supports
        if "?" in env_url:
            base_url, query_str = env_url.split("?", 1)
            params = query_str.split("&")
            new_params = []
            for p in params:
                if "=" in p:
                    k, v = p.split("=", 1)
                    if k == "sslmode":
                        new_params.append(f"ssl={v}")
                    elif k in ["ssl", "host", "port", "user", "password", "database", "timeout", "command_timeout"]:
                        new_params.append(p)
            if new_params:
                env_url = base_url + "?" + "&".join(new_params)
            else:
                env_url = base_url
        return env_url
    
    # 2. Check if running inside WSL itself
    if os.path.exists("/proc/version"):
        return "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/hospitalai"
        
    # 3. Running on Windows Host, connect to the proxy on loopback 127.0.0.1:5432
    return "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/hospitalai"

DATABASE_URL = get_database_url()

# Create asynchronous engine with connection pooling to prevent socket exhaustion
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "command_timeout": 5.0,
        "timeout": 5.0
    }
)

# Async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

# Dependency to get db session in FastAPI routes with automatic transient connection retry
async def get_db():
    for attempt in range(10):
        session = None
        yielded = False
        try:
            session = AsyncSessionLocal()
            # Pessimistic pre-ping: execute a dummy query to verify connection is alive
            await session.execute(text("SELECT 1"))
            yielded = True
            yield session
            await session.commit()
            return
        except (InterfaceError, OperationalError, Exception) as e:
            # If the error happened AFTER we successfully yielded, it belongs to the route handler.
            # We must NOT retry in this case; just rollback, close, and propagate it!
            if yielded:
                if session:
                    await session.rollback()
                raise e
                
            # If the error happened BEFORE yielding, it's a transient connection failure!
            # We log and retry after a short delay.
            logger.warning(f"Transient database connection error encountered (attempt {attempt + 1}/10): {e}. Retrying in 1.0s...")
            if session:
                await session.close()
            if attempt == 9:
                raise e
            await asyncio.sleep(1.0)
        finally:
            if session and yielded:
                await session.close()
