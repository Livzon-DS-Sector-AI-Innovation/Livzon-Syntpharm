#!/usr/bin/env python3
"""导入历史《危险源辨识管控清单》CSV 到 safety.hazard_identifications。

用法（容器内，scripts 与 uploads 已挂载）：
    python /app/scripts/import/import_hazard_identifications.py --dry-run
    python /app/scripts/import/import_hazard_identifications.py --mode replace

说明：
    - 源文件为 GB18030 编码（先试 utf-8-sig，失败回退 gb18030）。
    - replace 模式对未删除记录做软删除（可回滚、不撞部分唯一索引），再批量插入。
    - 行映射逻辑在 app/modules/safety/service/hazard_ledger_import.py，便于单测。
"""

import argparse
import asyncio
import csv
import sys
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import func, insert, select, update

# 以脚本方式运行时 sys.path[0] 是脚本目录，需补上后端根目录才能 import app.*
BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.modules.safety.models import HazardIdentification  # noqa: E402
from app.modules.safety.service.hazard_ledger_import import CSV_COLUMNS, map_row  # noqa: E402

DEFAULT_CSV = Path(__file__).resolve().parents[2] / "uploads" / "危险源辨识_去重_12683.csv"
ENCODINGS: tuple[str, ...] = ("utf-8-sig", "gb18030")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    """按表头读取 CSV，校验列名后再返回数据行。"""
    raw = path.read_bytes()
    decoded: str | None = None
    for encoding in ENCODINGS:
        try:
            decoded = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        break
    if decoded is None:
        raise SystemExit(f"无法解码 CSV（已尝试 {', '.join(ENCODINGS)}）：{path}")

    reader = csv.reader(decoded.splitlines(keepends=True))
    rows = list(reader)
    if not rows:
        raise SystemExit("CSV 为空")

    header = [cell.strip() for cell in rows[0]]
    if header != CSV_COLUMNS:
        missing = sorted(set(CSV_COLUMNS) - set(header))
        extra = sorted(set(header) - set(CSV_COLUMNS))
        raise SystemExit(f"CSV 表头与预期不一致\n缺失列: {missing}\n多余列: {extra}\n实际表头: {header}")

    result: list[dict[str, str]] = []
    for values in rows[1:]:
        if not any(cell.strip() for cell in values):
            continue
        padded = values + [""] * (len(CSV_COLUMNS) - len(values))
        result.append(dict(zip(CSV_COLUMNS, padded, strict=True)))
    return result


def build_records(rows: list[dict[str, str]], limit: int | None) -> list[dict[str, Any]]:
    """行映射 + 生成 UUID 主键（id 无数据库默认值，必须显式给）。"""
    records: list[dict[str, Any]] = []
    for seq, row in enumerate(rows, start=1):
        if limit is not None and seq > limit:
            break
        mapped = map_row(row, seq)
        mapped["id"] = uuid.uuid4()
        records.append(mapped)
    return records


def print_stats(records: list[dict[str, Any]], elapsed: float) -> None:
    """打印导入分布，便于与源表人工核对。"""
    print(f"映射行数: {len(records)}")
    print(f"耗时: {elapsed:.2f}s")

    level_counter = Counter(str(record.get("inherent_risk_level")) for record in records)
    print("固有风险等级分布:")
    for level, count in sorted(level_counter.items()):
        print(f"  {level}: {count}")

    method_counter = Counter(str(record.get("risk_method")) for record in records)
    print(f"风险评价方法分布: {dict(method_counter)}")

    dept_counter = Counter(str(record.get("department")) for record in records)
    print("责任部门 Top5:")
    for dept, count in dept_counter.most_common(5):
        print(f"  {dept}: {count}")

    sample = records[0] if records else None
    if sample:
        print("首行抽样:")
        for key in ("hazard_id_no", "department", "risk_point_name", "inherent_risk_level", "control_level"):
            print(f"  {key}={sample.get(key)!r}")


async def write_records(records: list[dict[str, Any]], mode: str, batch_size: int) -> None:
    """单事务写入：replace 先软删历史数据，再分批插入。"""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    engine = create_async_engine(get_settings().DATABASE_URL)
    try:
        async with engine.begin() as conn:
            if mode == "replace":
                soft_delete = (
                    update(HazardIdentification)
                    .where(HazardIdentification.is_deleted.is_(False))
                    .values(is_deleted=True, updated_at=func.now())
                )
                result = await conn.execute(soft_delete)
                print(f"已软删除历史记录: {result.rowcount}")

            existing = await conn.execute(
                select(HazardIdentification.hazard_id_no).where(HazardIdentification.is_deleted.is_(False))
            )
            existing_nos = {row[0] for row in existing}
            pending = [record for record in records if record["hazard_id_no"] not in existing_nos]
            skipped = len(records) - len(pending)
            if skipped:
                print(f"跳过早已存在的编号: {skipped}")

            for start in range(0, len(pending), batch_size):
                batch = pending[start : start + batch_size]
                await conn.execute(insert(HazardIdentification), batch)
            print(f"已插入: {len(pending)}")
    finally:
        await engine.dispose()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="导入历史危险源辨识清单 CSV")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="CSV 路径（默认 backend/uploads 下的清单）")
    parser.add_argument("--mode", choices=("replace", "append"), default="replace", help="replace=软删旧数据后导入")
    parser.add_argument("--dry-run", action="store_true", help="只解析与统计，不写数据库")
    parser.add_argument("--batch-size", type=int, default=500, help="每批插入行数")
    parser.add_argument("--limit", type=int, default=None, help="仅导入前 N 行（调试用）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()

    rows = read_csv_rows(args.csv)
    print(f"CSV 数据行(非空): {len(rows)}")

    records = build_records(rows, args.limit)
    print(f"目标模式: {args.mode}{'（dry-run 不写库）' if args.dry_run else ''}")

    if not args.dry_run:
        asyncio.run(write_records(records, args.mode, args.batch_size))

    print_stats(records, time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    sys.exit(main())
