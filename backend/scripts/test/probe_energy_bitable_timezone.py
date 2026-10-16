"""只读探针：打印能耗预警日表中「时间」列的原始毫秒值，判断它按哪个时区才是表格里显示的日期。

用法：docker exec erp-backend uv run python scripts/test/probe_energy_bitable_timezone.py
"""

import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.core.config import get_settings  # noqa: E402
from app.modules.energy.bitable_daily_import import TABLE_MAPPING, EnergyBitableDailyImport  # noqa: E402

CST = timedelta(hours=8)


async def main() -> None:
    importer = EnergyBitableDailyImport(app_token=get_settings().feishu.energy.alert_app_token)
    for table_id, (energy_type, label) in TABLE_MAPPING.items():
        records = await importer.list_records(table_id)
        stamps = sorted({r["fields"].get("时间") for r in records if isinstance(r["fields"].get("时间"), (int, float))})
        if not stamps:
            print(f"{label}: 无「时间」字段")
            continue
        for ms in stamps[-3:]:
            utc = datetime.fromtimestamp(ms / 1000, tz=UTC)
            print(
                f"{label}({energy_type}) ms={int(ms)} 余数={int(ms) % 86400000} "
                f"UTC={utc:%Y-%m-%d %H:%M} 东八区={(utc + CST):%Y-%m-%d %H:%M}"
            )
        print(f"{label}: 共 {len(records)} 条，最大 ms 见上\n")


if __name__ == "__main__":
    asyncio.run(main())
