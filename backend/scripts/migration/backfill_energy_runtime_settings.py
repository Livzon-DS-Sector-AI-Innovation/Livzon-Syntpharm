"""Backfill ENERGY runtime settings from the loaded deployment config.

Run this **per environment before** removing the ``ENERGY_*`` keys from
``.env`` / ``core/config.py`` (audit #12). It upserts the current values into
``core.module_settings`` (module ``energy``) so behaviour does not change when
the deployment keys disappear.

Usage:
    cd backend && uv run python scripts/migration/backfill_energy_runtime_settings.py

The script reads the legacy values from the process environment (the same
values ``core/config.py`` used to expose) and exits non-zero if nothing was
written, so a skipped backfill is visible in the deploy log.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select  # noqa: E402

from app.core.config_model import ModuleSetting  # noqa: E402
from app.core.database import async_session_factory  # noqa: E402

MODULE = "energy"

# (key, env var, default, value_type)
SETTINGS: list[tuple[str, str, str, str]] = [
    ("ENERGY_AUTO_COLLECT_ENABLED", "ENERGY_AUTO_COLLECT_ENABLED", "false", "bool"),
    ("ENERGY_BITABLE_AUTO_SYNC_ENABLED", "ENERGY_BITABLE_AUTO_SYNC_ENABLED", "false", "bool"),
    ("ENERGY_BITABLE_SYNC_HOUR", "ENERGY_BITABLE_SYNC_HOUR", "17", "int"),
]


async def backfill() -> int:
    written = 0
    async with async_session_factory() as session:
        for key, env_var, default, value_type in SETTINGS:
            value = os.getenv(env_var, default)
            result = await session.execute(
                select(ModuleSetting).where(ModuleSetting.module == MODULE, ModuleSetting.key == key)
            )
            row = result.scalar_one_or_none()
            if row is None:
                session.add(ModuleSetting(module=MODULE, key=key, value=value, value_type=value_type))
            else:
                row.value = value
            written += 1
            print(f"[OK] {MODULE}.{key} = {value}")
        await session.commit()
    return written


def main() -> None:
    written = asyncio.run(backfill())
    print(f"\n[OK] Backfilled {written} energy runtime settings")
    if written == 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
