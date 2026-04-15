#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from scripts.ingest_properties import (
    create_sample_properties,
    ingest_all_properties,
    create_vector_index,
)


async def seed():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text

        result = await session.execute(text("SELECT COUNT(*) FROM properties"))
        count = result.scalar()
        if count == 0:
            print("Seeding sample properties...")
            await create_sample_properties()
            await ingest_all_properties()
            await create_vector_index()
            print("Seeding complete.")
        else:
            print(f"Database already has {count} properties. Skipping seed.")


if __name__ == "__main__":
    asyncio.run(seed())
