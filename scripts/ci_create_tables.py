"""CI-only: provision a fresh test database schema from ORM models.

Bypasses the Alembic migration chain (which is known to be out of sync with
the ORM). Creates all required PostgreSQL schemas, imports every model module
so they register on Base.metadata, then runs create_all.

Usage (CI): uv run python scripts/ci_create_tables.py
"""

import asyncio
import os
import sys
from importlib import import_module

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text

from app.core.database import engine
from app.shared.base_model import Base
from app.shared.module_registry import BUSINESS_SCHEMAS

# Same import pattern as alembic/env.py so every model registers on Base.metadata.
import_module("app.platform.audit.models")
import_module("app.platform.identity.models")
for _schema in BUSINESS_SCHEMAS:
    import_module(f"app.modules.{_schema}.models")

# Schemas that must exist before create_all (create_all does NOT create schemas).
_SCHEMAS = ("identity", "audit", *BUSINESS_SCHEMAS)


async def main() -> None:
    async with engine.begin() as conn:
        for schema in _SCHEMAS:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print(f"created schemas: {', '.join(_SCHEMAS)}")
    print(f"created tables: {len(Base.metadata.tables)}")


if __name__ == "__main__":
    asyncio.run(main())
