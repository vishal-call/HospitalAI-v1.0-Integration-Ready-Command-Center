from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import ResponseSLAPolicy, RiskBand

async def get_active_sla_policy(db: AsyncSession, risk_band: str) -> ResponseSLAPolicy:
    """Fetch the active Response SLA Policy for a specific risk band."""
    result = await db.execute(
        select(ResponseSLAPolicy).filter(
            ResponseSLAPolicy.risk_band == risk_band,
            ResponseSLAPolicy.is_active == True
        )
    )
    return result.scalars().first()

async def seed_default_sla_policies(db: AsyncSession):
    """Seed default SLA policies if none exist."""
    result = await db.execute(select(ResponseSLAPolicy))
    existing = result.scalars().all()
    if not existing:
        policies = [
            ResponseSLAPolicy(
                hospital_id=1,
                risk_band=RiskBand.HIGH.value,
                acknowledge_within_minutes=2,
                resolve_within_minutes=10,
                escalate_to_role="DOCTOR",
                is_active=True
            ),
            ResponseSLAPolicy(
                hospital_id=1,
                risk_band=RiskBand.MEDIUM.value,
                acknowledge_within_minutes=10,
                resolve_within_minutes=30,
                escalate_to_role="COORDINATOR",
                is_active=True
            ),
            ResponseSLAPolicy(
                hospital_id=1,
                risk_band=RiskBand.LOW.value,
                acknowledge_within_minutes=30,
                resolve_within_minutes=120,
                escalate_to_role="NURSE",
                is_active=True
            )
        ]
        db.add_all(policies)
        await db.commit()
