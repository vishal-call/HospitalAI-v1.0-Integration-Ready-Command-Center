import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@172.21.128.63:5432/hospitalai')
        print("Connected to 172.21.128.63!")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
