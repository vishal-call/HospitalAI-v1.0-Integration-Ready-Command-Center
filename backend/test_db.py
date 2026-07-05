import asyncio
import asyncpg

async def main():
    try:
        conn = await asyncpg.connect('postgresql://postgres:postgres@127.0.0.1:5432/hospitalai')
        print("Connected to 127.0.0.1!")
        await conn.close()
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
