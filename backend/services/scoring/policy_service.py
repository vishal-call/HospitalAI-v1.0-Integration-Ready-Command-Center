from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import ScoringPolicy

async def get_active_policy(db: AsyncSession) -> ScoringPolicy:
    """
    Fetches the single active scoring policy from the database.
    If no active policy exists, raises an exception to fail-safe the clinical pipeline.
    """
    query = select(ScoringPolicy).where(ScoringPolicy.is_active == True)
    result = await db.execute(query)
    policy = result.scalars().first()
    
    if not policy:
        raise ValueError("CRITICAL: No active ScoringPolicy found in the database. Clinical engine halted.")
        
    return policy
