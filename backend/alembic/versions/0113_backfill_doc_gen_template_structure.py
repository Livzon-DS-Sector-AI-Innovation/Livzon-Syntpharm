"""0113_backfill_doc_gen_template_structure

Revision ID: 0113_backfill_doc_gen_template_structure
Revises: 0112_merge_0108_0111_heads
Create Date: 2026-11-06 21:55:00.000000

把代码内置的槽位定义（``doc_gen/templates/tech_research_report.py``，37 个槽位，
含 ``manual_only`` / ``from_meta`` / ``compute`` / 动态章节等手工语义）一次性落库到
``research.rd_deliverable_templates.template_structure`` 与
``research.rd_deliverable_template_versions.template_structure``。

背景：槽位定义此前有两条来源——代码注册表（内置）与母本自动识别（落库）。双轨导致
「同一份母本可能走不同轨道」「改内置必须发版」「界面需要解释哪套配置生效」。本次统一为
「落库结构是唯一真相」，代码注册表随后删除。为了让删除后行为完全不变，存量里只写了
``template_code``、``template_structure`` 为空的模板必须先把内置值搬进库里。

数据来源：``alembic/data/doc_gen/tech_research_report_spec.json``（由内置 SPEC 一次性
dump 的快照）。刻意不在迁移里 import 业务模块——注册表删除后，从零重建库仍要能跑通本迁移。

幂等：仅在 ``template_structure IS NULL`` 时写入；已有结构（含人工编辑过的）一律不覆盖。
回滚：只把与本迁移写入值完全一致的行清空，不会误删回填后的人工编辑。
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op

revision: str = "0113_backfill_doc_gen_template_structure"
down_revision: str | Sequence[str] | None = "0112_merge_0108_0111_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SPEC_PATH = Path(__file__).resolve().parent.parent / "data" / "doc_gen" / "tech_research_report_spec.json"
_TEMPLATE_TABLE = "research.rd_deliverable_templates"
_VERSION_TABLE = "research.rd_deliverable_template_versions"


def _load_spec() -> tuple[str, str]:
    """读取内置规格快照，返回 (code, 紧凑 JSON 文本)。"""
    if not _SPEC_PATH.exists():
        raise RuntimeError(f"缺少内置规格快照文件，无法回填槽位定义: {_SPEC_PATH}")
    spec = json.loads(_SPEC_PATH.read_text(encoding="utf-8"))
    code = str(spec.get("code") or "")
    if not code or not spec.get("slots"):
        raise RuntimeError(f"内置规格快照不合法（缺 code 或 slots）: {_SPEC_PATH}")
    return code, json.dumps(spec, ensure_ascii=False)


def _backfill(table: str, code: str, payload: str) -> None:
    """给该表里「只写了 code、没有结构」的行补上结构。"""
    op.get_bind().execute(
        sa.text(
            f"UPDATE {table} "  # noqa: S608 - 表名为本模块常量，非外部输入
            "SET template_structure = CAST(:payload AS json) "
            "WHERE template_code = :code AND template_structure IS NULL"
        ),
        {"code": code, "payload": payload},
    )


def upgrade() -> None:
    code, payload = _load_spec()
    _backfill(_TEMPLATE_TABLE, code, payload)
    _backfill(_VERSION_TABLE, code, payload)


def downgrade() -> None:
    code, payload = _load_spec()
    # json 类型没有等号运算符，比较走 jsonb；只清掉与本迁移写入值一致的行
    for table in (_VERSION_TABLE, _TEMPLATE_TABLE):
        op.get_bind().execute(
            sa.text(
                f"UPDATE {table} "  # noqa: S608 - 表名为本模块常量，非外部输入
                "SET template_structure = NULL "
                "WHERE template_code = :code AND template_structure::jsonb = CAST(:payload AS jsonb)"
            ),
            {"code": code, "payload": payload},
        )
