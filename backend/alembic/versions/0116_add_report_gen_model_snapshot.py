"""0116_add_report_gen_model_snapshot

Revision ID: 0116_add_report_gen_model_snapshot
Revises: 0115_add_rd_report_gen_tables
Create Date: 2026-11-08 10:00:00.000000

给 ``research.rd_report_gen_jobs`` 补模型快照列。

背景：模型档位一直是 ``core.module_settings`` 里的实时配置，任务跑完后无法回答
「这次用的是哪个模型」；运营改配置也会让历史任务的解释失去依据。这里在任务创建
时把三档原值固定下来，执行期间改配置不影响已在跑的任务。

``model_config_name`` 存的是**配置里填的原值**（LLM 配置名或模型名），执行时按它
重新解析，因此配置库改名后仍能定位；``model_name`` 存解析后的实际模型名，仅供展示。

只动 research 一张表（单模块原则），列全部可空，历史行无需回填。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0116_add_report_gen_model_snapshot"
down_revision: str | Sequence[str] | None = "0115_add_rd_report_gen_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_TABLE = "rd_report_gen_jobs"

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("model_config_name", "正文生成档位原值（LLM 配置名或模型名）"),
    ("model_name", "正文生成实际模型名"),
    ("structure_model_name", "结构识别档位原值"),
    ("fallback_model_name", "兜底档位原值"),
)


def upgrade() -> None:
    for name, comment in _COLUMNS:
        op.add_column(
            _TABLE,
            sa.Column(name, sa.String(length=128), nullable=True, comment=comment),
            schema=_SCHEMA,
        )
    op.add_column(
        _TABLE,
        sa.Column(
            "used_fallback",
            sa.Boolean(),
            nullable=False,
            server_default="false",
            comment="是否已降级到兜底模型",
        ),
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.drop_column(_TABLE, "used_fallback", schema=_SCHEMA)
    for name, _comment in reversed(_COLUMNS):
        op.drop_column(_TABLE, name, schema=_SCHEMA)
