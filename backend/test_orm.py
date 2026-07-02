import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
import models

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/hospitalai')
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        gw_bed_res = await session.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 3)
            .where(models.Bed.status == models.BedStatus.AVAILABLE)
            .limit(1)
        )
        gw_bed = gw_bed_res.scalar_one_or_none()
        print("Bed:", gw_bed)
        
        # Test without BedStatus filter
        gw_bed_res_all = await session.execute(
            select(models.Bed)
            .where(models.Bed.ward_id == 3)
        )
        all_gw_beds = gw_bed_res_all.scalars().all()
        print("All GW Beds Count:", len(all_gw_beds))
        if all_gw_beds:
            print("Status of first GW bed:", repr(all_gw_beds[0].status))

asyncio.run(main())
