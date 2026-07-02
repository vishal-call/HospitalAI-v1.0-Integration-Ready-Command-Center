import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def main():
    engine = create_async_engine('postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/hospitalai')
    async with engine.begin() as conn:
        res = await conn.execute(text('SELECT count(*) FROM beds WHERE ward_id=3'))
        print('GW BEDS:', res.scalar())
        res2 = await conn.execute(text("SELECT count(*) FROM beds WHERE status='AVAILABLE'"))
        print('AVAIL:', res2.scalar())
        res3 = await conn.execute(text("SELECT id, type, name FROM wards"))
        print('WARDS:', res3.fetchall())

asyncio.run(main())
