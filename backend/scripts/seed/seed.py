"""Seed initial data into PostgreSQL database.

Usage:
    uv run python scripts/seed.py

Requires DATABASE_URL environment variable or .env file.
"""

import asyncio
import json
import os
import uuid
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

load_dotenv()

_raw_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/dazah")
DATABASE_URL = _raw_url.replace("postgresql+asyncpg://", "postgresql://")

SCRIPTS_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPTS_DIR.parent

DEPARTMENTS_JSON = PROJECT_ROOT / "seed" / "departments.json"


async def seed_departments(conn: asyncpg.Connection) -> dict[str, uuid.UUID]:
    """Insert departments and return name -> id mapping."""
    if not DEPARTMENTS_JSON.exists():
        print(f"[SKIP] {DEPARTMENTS_JSON} not found")
        return {}

    with open(DEPARTMENTS_JSON, encoding="utf-8") as f:
        departments = json.load(f)

    name_to_id: dict[str, uuid.UUID] = {}

    for dept in departments:
        dept_id = uuid.UUID(dept["id"])
        name_to_id[dept["name"]] = dept_id

        # Upsert: insert or do nothing on conflict
        await conn.execute(
            """
            INSERT INTO hr.departments (id, name, code, description, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            ON CONFLICT (code) DO NOTHING
            """,
            dept_id,
            dept["name"],
            dept["code"],
            dept.get("description"),
        )

    print(f"[OK] Seeded {len(departments)} departments")
    return name_to_id


async def main() -> None:
    print("Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("\n[OK] Seed completed!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
