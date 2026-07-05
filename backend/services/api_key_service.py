import secrets
import hashlib
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import IntegrationApiKey

def hash_api_key(raw_key: str) -> str:
    """Hash the raw key using SHA-256 for secure database storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()

async def generate_api_key(db: AsyncSession, name: str, scopes: list[str]) -> tuple[str, str]:
    """Generates a secure API key, saves the hash, and returns (raw_key, prefix)."""
    raw_key = secrets.token_urlsafe(32)
    key_prefix = raw_key[:8]
    hashed_key = hash_api_key(raw_key)

    new_key = IntegrationApiKey(
        name=name,
        api_key_hash=hashed_key,
        key_prefix=key_prefix,
        scopes=scopes,
        is_active=True,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    return raw_key, key_prefix

async def verify_api_key(db: AsyncSession, raw_key: str, required_scope: str = None) -> IntegrationApiKey:
    """Verifies the raw key against the db hash. Checks scope and active status."""
    hashed_key = hash_api_key(raw_key)
    result = await db.execute(
        select(IntegrationApiKey).where(IntegrationApiKey.api_key_hash == hashed_key)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        return None

    if not api_key.is_active:
        return None

    if required_scope and (not api_key.scopes or required_scope not in api_key.scopes):
        return None

    # Update last used
    api_key.last_used_at = datetime.utcnow()
    db.add(api_key)
    await db.commit()

    return api_key

async def get_all_api_keys(db: AsyncSession):
    result = await db.execute(select(IntegrationApiKey).order_by(IntegrationApiKey.created_at.desc()))
    return result.scalars().all()

async def revoke_api_key(db: AsyncSession, key_id: int):
    result = await db.execute(select(IntegrationApiKey).where(IntegrationApiKey.id == key_id))
    api_key = result.scalar_one_or_none()
    if api_key:
        api_key.is_active = False
        db.add(api_key)
        await db.commit()
    return api_key
