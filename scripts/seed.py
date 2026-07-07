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

DEPARTMENTS_JSON = PROJECT_ROOT / "departments.json"
TEAMS_JSON = PROJECT_ROOT / "teams.json"


async def seed_departments(conn: asyncpg.Connection) -> dict[str, uuid.UUID]:
    """Insert departments and return name -> id mapping."""
    if not DEPARTMENTS_JSON.exists():
        print(f"[SKIP] {DEPARTMENTS_JSON} not found")
        return {}

    with open(DEPARTMENTS_JSON, "r", encoding="utf-8") as f:
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


async def seed_teams(conn: asyncpg.Connection, name_to_id: dict[str, uuid.UUID]) -> None:
    """Insert teams linked to departments."""
    if not TEAMS_JSON.exists():
        print(f"[SKIP] {TEAMS_JSON} not found")
        return

    with open(TEAMS_JSON, "r", encoding="utf-8") as f:
        teams = json.load(f)

    inserted = 0
    skipped = 0

    for team in teams:
        dept_name = team["department"]
        dept_id = name_to_id.get(dept_name)

        if dept_id is None:
            # Try to query DB in case departments were already inserted
            row = await conn.fetchrow(
                "SELECT id FROM hr.departments WHERE name = $1", dept_name
            )
            if row is None:
                print(f"[WARN] Department '{dept_name}' not found, skipping team '{team['team']}'")
                skipped += 1
                continue
            dept_id = row["id"]

        # Generate a deterministic code from team name
        team_code = team["team"].strip().replace(" ", "_").lower()[:32] or str(uuid.uuid4())[:8]

        # Check if team already exists for this department
        existing = await conn.fetchrow(
            "SELECT id FROM hr.teams WHERE name = $1 AND department_id = $2",
            team["team"],
            dept_id,
        )
        if existing:
            skipped += 1
            continue

        await conn.execute(
            """
            INSERT INTO hr.teams (id, name, code, description, department_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
            """,
            uuid.uuid4(),
            team["team"],
            team_code,
            None,
            dept_id,
        )
        inserted += 1

    print(f"[OK] Seeded {inserted} teams ({skipped} skipped)")


async def main() -> None:
    print(f"Connecting to database...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Seeding departments...")
        name_to_id = await seed_departments(conn)

        print("Seeding teams...")
        await seed_teams(conn, name_to_id)

        print("\n[OK] Seed completed!")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
