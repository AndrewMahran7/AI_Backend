import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "postgresql+asyncpg://postgres:PostgreSQL%231@localhost:5432/ai_backend"

async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        print("SQLAlchemy connection: OK", result.fetchone())
    await engine.dispose()

asyncio.run(main())
