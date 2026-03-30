import asyncio
import asyncpg

async def main():
    # Connect to the default postgres database first
    conn = await asyncpg.connect(
        user="postgres",
        password="PostgreSQL#1",
        host="localhost",
        port=5432,
        database="postgres",
    )
    rows = await conn.fetch("SELECT datname FROM pg_database WHERE datname='ai_backend'")
    if rows:
        print("ai_backend database exists: YES")
    else:
        print("ai_backend database does not exist — creating...")
        await conn.execute("CREATE DATABASE ai_backend")
        print("Database created.")

    # Also check pgvector extension
    conn2 = await asyncpg.connect(
        user="postgres",
        password="PostgreSQL#1",
        host="localhost",
        port=5432,
        database=rows[0]["datname"] if rows else "ai_backend",
    )
    ext = await conn2.fetch("SELECT extname FROM pg_extension WHERE extname='vector'")
    if ext:
        print("pgvector extension: installed")
    else:
        print("pgvector extension: NOT installed — attempting install...")
        try:
            await conn2.execute("CREATE EXTENSION IF NOT EXISTS vector")
            print("pgvector installed.")
        except Exception as e:
            print(f"Could not install pgvector: {e}")

    await conn.close()
    await conn2.close()
    print("Done.")

asyncio.run(main())
