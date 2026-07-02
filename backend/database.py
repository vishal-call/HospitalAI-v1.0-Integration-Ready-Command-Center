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
        return env_url
    
    # 2. Check if WSL_IP is injected into environment
    wsl_ip = os.getenv("WSL_IP")
    if wsl_ip:
        logger.info(f"Using environment WSL_IP for PostgreSQL: {wsl_ip}")
        return f"postgresql+asyncpg://postgres:postgres@{wsl_ip}:5432/hospitalai"
        
    # 2.5. Check if a local cached wsl_ip.txt file exists to avoid subprocess hangs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    wsl_ip_path = os.path.join(base_dir, "wsl_ip.txt")
    if os.path.exists(wsl_ip_path):
        try:
            with open(wsl_ip_path, "rb") as f:
                content = f.read()
            encoding = "utf-16" if b'\x00' in content else "utf-8"
            ip_str = content.decode(encoding, errors='ignore').strip()
            parts = ip_str.split()
            if parts:
                wsl_ip = parts[0]
                logger.info(f"Using pre-resolved WSL IP from wsl_ip.txt: {wsl_ip}")
                return f"postgresql+asyncpg://postgres:postgres@{wsl_ip}:5432/hospitalai"
        except Exception as e:
            logger.warning(f"Failed to read pre-resolved wsl_ip.txt at {wsl_ip_path}: {e}")
            
    # 3. Dynamic resolution fallback if running standalone (prefer IPv4 loopback 127.0.0.1)
    host = "127.0.0.1"
    if os.name == "nt":
        try:
            # Query WSL network bridge IP with a generous timeout to prevent cold-start bottlenecks
            res = subprocess.run(["wsl", "hostname", "-I"], capture_output=True, text=True, timeout=5.0)
            if res.returncode == 0:
                ip_list = res.stdout.strip().split()
                if ip_list:
                    host = ip_list[0]
                    logger.info(f"Resolved WSL IP dynamically: {host}")
        except Exception as e:
            logger.warning(f"Failed to dynamically resolve WSL IP, falling back to 127.0.0.1: {e}")
            
    return f"postgresql+asyncpg://postgres:postgres@{host}:5432/hospitalai"

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
