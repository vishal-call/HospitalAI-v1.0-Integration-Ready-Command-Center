from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import models
import schemas
from fastapi import HTTPException, status
from datetime import datetime

async def create_integration(db: AsyncSession, integration_in: schemas.IntegrationCreate) -> models.Integration:
    new_integration = models.Integration(
        name=integration_in.name,
        type=integration_in.type,
        mode=integration_in.mode,
        status=integration_in.status,
        config_json=integration_in.config_json,
    )
    db.add(new_integration)
    await db.commit()
    await db.refresh(new_integration)
    return new_integration

async def get_integrations(db: AsyncSession) -> List[models.Integration]:
    result = await db.execute(select(models.Integration).order_by(models.Integration.id))
    return list(result.scalars().all())

async def get_integration(db: AsyncSession, integration_id: int) -> Optional[models.Integration]:
    result = await db.execute(select(models.Integration).where(models.Integration.id == integration_id))
    return result.scalars().first()

async def update_integration(db: AsyncSession, integration_id: int, integration_in: schemas.IntegrationUpdate) -> models.Integration:
    db_obj = await get_integration(db, integration_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
    
    update_data = integration_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
        
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def change_integration_status(db: AsyncSession, integration_id: int, new_status: models.IntegrationStatus) -> models.Integration:
    db_obj = await get_integration(db, integration_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Integration not found")
        
    db_obj.status = new_status
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
