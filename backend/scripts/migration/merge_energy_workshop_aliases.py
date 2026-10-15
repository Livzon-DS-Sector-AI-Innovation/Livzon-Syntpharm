"""一次性数据迁移：合并能源车间别名、统一规范名称。

同一部门在月度多维表格的 水/电/汽 三个 section 里写法不同，交叉表导入器按字面建了
两个车间，导致月度记录的车间筛选选中一个只能看到单一能源类型。本脚本把别名实体挂回
规范实体并软删除，同时把规范名统一成业务确认的写法。

用法：
    python scripts/migration/merge_energy_workshop_aliases.py            # dry-run（默认，不写库）
    python scripts/migration/merge_energy_workshop_aliases.py --apply    # 实际执行
    python scripts/migration/merge_energy_workshop_aliases.py --apply --audit-path /tmp/audit.json

别名来源与判定依据见 backend/docs/energy-bitable-field-mapping.md。
脚本可重复执行：第二次运行应为 0 动作。
"""

import argparse
import asyncio
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402

# 别名实体 -> 规范实体。命中时：规范实体已存在则合并，不存在则原地改名。
#
# 顺序有意义：多条规则指向同一个规范实体时，先跑的那条负责把它「改名」建出来，
# 后面的才能走「合并」。反过来先跑「废水站」会先把废水站改名成环保中心，
# 让存活的 workshop_id 落到水侧实体上——结果同样正确，但与本地已执行过的环境不一致。
WORKSHOP_UNIFICATION: dict[str, str] = {
    "QC": "质量控制部",
    "炊事班": "饭堂",
    "生活办公": "办公楼",
    "环保中心(含RTO)": "环保中心",
    "废水站": "环保中心",
    "303车间": "303、106车间",
}

# 带 workshop_id 外键、需要跟着改挂的业务表
REPOINT_TABLES: tuple[tuple[str, str], ...] = (
    ("energy_monthly_records", "uq_energy_monthly_record (workshop_id, energy_type, record_date)"),
    ("energy_unit_consumption_targets", "uk_workshop_month (workshop_id, target_month)"),
)

# 唯一约束的判重列（不含 is_deleted，软删除行同样占位）
CONFLICT_COLUMNS: dict[str, tuple[str, ...]] = {
    "energy_monthly_records": ("energy_type", "record_date"),
    "energy_unit_consumption_targets": ("target_month",),
}

# 用名称字符串引用车间的表，改名后要一起跟上
NAME_STRING_TABLES: tuple[tuple[str, str], ...] = (("energy_device_configs", "workshop"),)


async def _find_active(db, name: str):
    row = (
        await db.execute(
            text(
                "select id, name, code from energy.energy_workshops "
                "where is_deleted = false and (name = :name or code = :name) order by id"
            ),
            {"name": name},
        )
    ).fetchall()
    return row[0] if row else None


async def _find_conflicts(db, table: str, src_id: str, tgt_id: str) -> list[Any]:
    cols = CONFLICT_COLUMNS[table]
    on_clause = " and ".join(f"t.{c} = m.{c}" for c in cols)
    sql = (
        f"select {', '.join('m.' + c for c in cols)} from energy.{table} m "  # noqa: S608
        f"join energy.{table} t on t.workshop_id = cast(:tgt as uuid) and {on_clause} "
        "where m.workshop_id = cast(:src as uuid)"
    )
    return (await db.execute(text(sql), {"src": str(src_id), "tgt": str(tgt_id)})).fetchall()


async def _repoint(db, table: str, src_id: str, tgt_id: str, apply: bool) -> int:
    row = (
        await db.execute(
            text(f"select count(*) from energy.{table} where workshop_id = cast(:src as uuid)"),  # noqa: S608
            {"src": str(src_id)},
        )
    ).one()
    count = int(row[0])
    if count and apply:
        await db.execute(
            text(
                f"update energy.{table} set workshop_id = cast(:tgt as uuid), updated_at = now() "  # noqa: S608
                "where workshop_id = cast(:src as uuid)"
            ),
            {"src": str(src_id), "tgt": str(tgt_id)},
        )
    return count


async def _totals(db) -> dict[str, tuple[int, str]]:
    rows = (
        await db.execute(
            text(
                "select energy_type, count(*), coalesce(sum(value), 0) from energy.energy_monthly_records "
                "where is_deleted = false group by energy_type order by energy_type"
            )
        )
    ).fetchall()
    return {r[0]: (int(r[1]), str(r[2])) for r in rows}


async def run(apply: bool, audit_path: str | None) -> int:
    actions: list[dict[str, Any]] = []
    blocked: list[dict[str, str]] = []

    async with async_session_factory() as db:
        before = await _totals(db)
        print("迁移前月度记录合计（按能源类型）:")
        for etype, (n, total) in before.items():
            print(f"  {etype}: count={n} sum={total}")

        for alias, canonical in WORKSHOP_UNIFICATION.items():
            src = await _find_active(db, alias)
            tgt = await _find_active(db, canonical)

            if src is None:
                print(f"\n[跳过] {alias} -> {canonical}：别名实体不存在（已合并过）")
                continue

            if tgt is None:
                # 规范实体还没出现：原地改名，记录不动
                code_taken = (
                    await db.execute(
                        text(
                            "select count(*) from energy.energy_workshops "
                            "where code = :code and id <> cast(:id as uuid) and is_deleted = false"
                        ),
                        {"code": canonical, "id": str(src.id)},
                    )
                ).scalar()
                if code_taken:
                    blocked.append({"alias": alias, "reason": f"编码 {canonical} 已被其他车间占用"})
                    print(f"\n[阻止] {alias} -> {canonical}：编码已被占用")
                    continue
                print(f"\n[改名] {alias} -> {canonical}（车间 {src.id}）")
                if apply:
                    await db.execute(
                        text(
                            "update energy.energy_workshops set name = :name, code = :code, updated_at = now() "
                            "where id = cast(:id as uuid)"
                        ),
                        {"name": canonical, "code": canonical, "id": str(src.id)},
                    )
                    for table, column in NAME_STRING_TABLES:
                        await db.execute(
                            text(
                                f"update energy.{table} set {column} = :name "  # noqa: S608
                                f"where {column} = :old"
                            ),
                            {"name": canonical, "old": alias},
                        )
                actions.append({"type": "rename", "from": alias, "to": canonical, "workshop_id": str(src.id)})
                continue

            # 两个实体都在：先做唯一约束重叠守卫，再改挂
            conflicts: list[str] = []
            for table, constraint in REPOINT_TABLES:
                rows = await _find_conflicts(db, table, src.id, tgt.id)
                if rows:
                    conflicts.append(f"{table}({constraint}) 重叠 {len(rows)} 行")
            if conflicts:
                blocked.append({"alias": alias, "reason": "；".join(conflicts)})
                print(f"\n[阻止] {alias} -> {canonical}：{'；'.join(conflicts)}")
                continue

            moved = {}
            for table, _ in REPOINT_TABLES:
                n = await _repoint(db, table, src.id, tgt.id, apply)
                if n:
                    moved[table] = n
            print(f"\n[合并] {alias} -> {canonical}：改挂 {moved}，软删除车间 {src.id}")
            if apply:
                # 一并让出 code：uq_energy_workshop_code 不含 is_deleted，
                # 软删除行继续占着编码会让日后重建同名车间直接撞唯一约束
                await db.execute(
                    text(
                        "update energy.energy_workshops set is_deleted = true, updated_at = now(), "
                        "code = left(code || '#merged#' || substring(cast(id as text), 1, 8), 50) "
                        "where id = cast(:id as uuid)"
                    ),
                    {"id": str(src.id)},
                )
            actions.append(
                {
                    "type": "merge",
                    "from": alias,
                    "to": canonical,
                    "workshop_id": str(src.id),
                    "target_workshop_id": str(tgt.id),
                    "moved": moved,
                }
            )

        if apply:
            await db.commit()
            after = await _totals(db)
            print("\n迁移后月度记录合计（按能源类型）:")
            for etype, (n, total) in after.items():
                print(f"  {etype}: count={n} sum={total}")
            if after != before:
                print("\n[错误] 记录合计发生变化，迁移不应改变任何数值！")
                return 1
        else:
            print("\n(dry-run，未写入。加 --apply 执行)")

        print(f"\n动作 {len(actions)} 个，阻止 {len(blocked)} 个")
        for b in blocked:
            print(f"  阻止: {b['alias']} — {b['reason']}")

        audit = {"apply": apply, "actions": actions, "blocked": blocked}
        if audit_path:
            with open(audit_path, "w", encoding="utf-8") as f:
                json.dump(audit, f, ensure_ascii=False, indent=2)
            print(f"审计文件已写入 {audit_path}")

        return 1 if blocked else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="合并能源车间别名实体")
    parser.add_argument("--apply", action="store_true", help="实际写库，默认只做 dry-run")
    parser.add_argument("--audit-path", default=None, help="把动作清单写成 JSON，供反向恢复参考")
    args = parser.parse_args()
    return asyncio.run(run(apply=args.apply, audit_path=args.audit_path))


if __name__ == "__main__":
    raise SystemExit(main())
