"""把妙搭偏差应用的历史记录一次性导入 quality.deviation_ledger。

用法::

    # 预演（默认，不写库）
    uv run python scripts/migration/import_deviation_ledger.py --source deviations.json

    # 落库
    uv run python scripts/migration/import_deviation_ledger.py --source deviations.json --apply

输入：妙搭导出的 JSON 数组。字段名兼容 camelCase 与 snake_case，
人员字段用**姓名**（妙搭 user_id 无法映射到平台 identity.users）。

人员解析规则：姓名在 identity.users 中唯一命中才绑定；命中 0 人或多人时，
发现人 / 上报人回落到 ``--fallback-user``（姓名或 UUID），调查人跳过并记警告。

幂等：按 ``code`` upsert，重复执行只更新不插入。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import date, datetime, UTC
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.modules.quality.qms.deviation_ledger_constants import (  # noqa: E402
    DEVIATION_LEVELS,
    INITIAL_STATUS,
    LEDGER_STATUSES,
)
from app.modules.quality.qms.deviation_ledger_models import DeviationLedger  # noqa: E402
from app.platform.identity.models import User  # noqa: E402

_NAME_SEPARATOR = "、,"


def _pick(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in raw and raw[key] not in (None, ""):
            return raw[key]
    return None


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _as_names(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value)
    for separator in _NAME_SEPARATOR[1:]:
        text = text.replace(separator, _NAME_SEPARATOR[0])
    return [part.strip() for part in text.split(_NAME_SEPARATOR[0]) if part.strip()]


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "是"}


async def _load_user_index(session: Any) -> dict[str, list[uuid.UUID]]:
    rows = await session.execute(select(User.id, User.name).where(User.is_deleted.is_(False)))  # noqa: E712
    index: dict[str, list[uuid.UUID]] = {}
    for user_id, name in rows.all():
        if name:
            index.setdefault(str(name).strip(), []).append(user_id)
    return index


def _resolve(index: dict[str, list[uuid.UUID]], name: str) -> uuid.UUID | None:
    candidates = index.get(name.strip(), [])
    return candidates[0] if len(candidates) == 1 else None


async def _run(source: Path, apply: bool, fallback_user: str | None) -> int:
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        print("输入文件必须是 JSON 数组")
        return 2

    created = updated = skipped = 0
    async with async_session_factory() as session:
        index = await _load_user_index(session)
        fallback_id: uuid.UUID | None = None
        if fallback_user:
            try:
                fallback_id = uuid.UUID(fallback_user)
            except ValueError:
                fallback_id = _resolve(index, fallback_user)
            if fallback_id is None:
                print(f"fallback-user 无法解析：{fallback_user}")
                return 2

        for raw in payload:
            if not isinstance(raw, dict):
                skipped += 1
                continue
            code = _pick(raw, "code", "Code")
            title = _pick(raw, "title", "Title")
            department = _pick(raw, "department", "Department")
            discovery_date = _as_date(_pick(raw, "discovery_date", "discoveryDate"))
            if not (code and title and department and discovery_date):
                print(f"[skip] 缺必填字段：code={code}")
                skipped += 1
                continue

            discoverer_name = _pick(raw, "discoverer_name", "discovererName", "discoverer")
            reporter_name = _pick(raw, "reporter_name", "reporterName", "reporter")
            discoverer_id = _resolve(index, str(discoverer_name)) if discoverer_name else None
            reporter_id = _resolve(index, str(reporter_name)) if reporter_name else None
            discoverer_id = discoverer_id or fallback_id
            reporter_id = reporter_id or fallback_id
            if discoverer_id is None or reporter_id is None:
                print(f"[skip] {code} 发现人/上报人无法解析，请指定 --fallback-user")
                skipped += 1
                continue

            handler_ids: list[uuid.UUID] = []
            for name in _as_names(_pick(raw, "handler_names", "handlerNames", "handler")):
                resolved = _resolve(index, name)
                if resolved is None:
                    print(f"[warn] {code} 调查人「{name}」无法唯一匹配，已跳过")
                else:
                    handler_ids.append(resolved)

            status = _pick(raw, "status") or INITIAL_STATUS
            if status not in LEDGER_STATUSES:
                print(f"[warn] {code} 状态 {status} 非法，回落 {INITIAL_STATUS}")
                status = INITIAL_STATUS
            level = _pick(raw, "deviation_level", "deviationLevel")
            if level and level not in DEVIATION_LEVELS:
                print(f"[warn] {code} 分级 {level} 非法，置空")
                level = None

            values: dict[str, Any] = {
                "final_code": _pick(raw, "final_code", "finalCode"),
                "title": str(title),
                "department": str(department),
                "discovery_date": discovery_date,
                "discovery_time": _pick(raw, "discovery_time", "discoveryTime"),
                "discovery_location": str(_pick(raw, "discovery_location", "discoveryLocation") or "-"),
                "discoverer_id": discoverer_id,
                "affected_items": str(_pick(raw, "affected_items", "affectedItems") or "-"),
                "batch_number": str(_pick(raw, "batch_number", "batchNumber") or "-"),
                "description": str(_pick(raw, "description") or "-"),
                "status": status,
                "returned_step": _pick(raw, "returned_step", "returnedStep"),
                "status_updated_at": _as_datetime(_pick(raw, "status_updated_at", "statusUpdatedAt"))
                or datetime.now(UTC),
                "deviation_level": level,
                "reason_category": _pick(raw, "reason_category", "reasonCategory"),
                "reporter_id": reporter_id,
                "handler_ids": handler_ids or None,
                "needs_cross_dept_review": _as_bool(_pick(raw, "needs_cross_dept_review", "needsCrossDeptReview")),
            }

            existing = await session.scalar(select(DeviationLedger).where(DeviationLedger.code == str(code)))
            if existing is None:
                session.add(
                    DeviationLedger(
                        code=str(code),
                        created_by=reporter_id,
                        updated_by=reporter_id,
                        **values,
                    )
                )
                created += 1
            else:
                for key, value in values.items():
                    setattr(existing, key, value)
                existing.updated_by = reporter_id
                updated += 1

        if apply:
            await session.commit()
            print(f"已导入：新增 {created} 条，更新 {updated} 条，跳过 {skipped} 条")
        else:
            await session.rollback()
            print(f"[dry-run] 待新增 {created} 条，待更新 {updated} 条，跳过 {skipped} 条（加 --apply 落库）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="导入妙搭历史偏差到 quality.deviation_ledger")
    parser.add_argument("--source", required=True, help="妙搭导出的 JSON 数组文件")
    parser.add_argument("--apply", action="store_true", help="实际写库（默认仅预演）")
    parser.add_argument("--fallback-user", default=None, help="人员无法解析时的兜底用户（姓名或 UUID）")
    args = parser.parse_args()
    return asyncio.run(_run(Path(args.source), args.apply, args.fallback_user))


if __name__ == "__main__":
    raise SystemExit(main())
