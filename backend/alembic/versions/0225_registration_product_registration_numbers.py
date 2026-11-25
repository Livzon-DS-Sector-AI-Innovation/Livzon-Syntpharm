"""registration product registration numbers mapping table

Revision ID: 0225_registration_product_registration_numbers
Revises: 0224_deprecate_registration_removed_permissions
Create Date: 2026-11-24

把原先硬编码在 service/authorization.py 的「品种→登记号」对照表迁入数据库，
支持后续手动录入新品种自动入库（仅新增、不覆盖）。
只动 registration schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0225_registration_product_registration_numbers"
down_revision: str | None = "0224_deprecate_registration_removed_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "registration"
_TABLE = "product_registration_numbers"

# 品种名 -> 登记号（原硬编码字典 39 条）
_SEED: list[tuple[str, str]] = [
    ("阿魏酸钠", "Y20190001800"),
    ("艾普拉唑", "Y20190009784"),
    ("艾普拉唑钠", "Y20170001429"),
    ("奥美拉唑钠", "Y20190006673"),
    ("丙氨酰谷氨酰胺", "Y20190002584"),
    ("布南色林", "Y20210001289"),
    ("丹曲林钠", "Y20170001099"),
    ("丁苯酞", "Y20170001569"),
    ("厄贝沙坦", "Y20190001962"),
    ("更昔洛韦", "Y20190008005"),
    ("枸酸铋钾 (干品)", "Y20200001089"),
    ("枸橼酸铋钾 (湿品)", "Y20190003316"),
    ("枸橼酸铋雷尼替丁 (1:1)", "Y20190005110"),
    ("枸橼酸铋雷尼替丁 (1:1.1)", "Y20190001948"),
    ("桂利嗪", "Y20190007743"),
    ("酒石酸托特罗定", "Y20190001881"),
    ("卡维地洛", "Y20190001959"),
    ("磷酸川芎嗪", "Y20190007731"),
    ("硫酸钾", "Y20230000325"),
    ("硫酸头孢匹罗", "Y20190002699"),
    ("氯雷他定", "Y20190008122"),
    ("马来酸氟伏沙明", "Y20170001958"),
    ("马来酸茚达特罗", "Y20220000555"),
    ("舒巴坦钠", "Y20190001952"),
    ("他唑巴坦", "Y20190003875"),
    ("头孢地嗪钠", "Y20190001846"),
    ("头孢呋辛钠", "Y20190009596"),
    ("头孢曲松钠", "Y20190009444"),
    ("头孢他啶/碳酸钠", "Y20190006854"),
    ("头孢他啶", "Y20190007742"),
    ("无水碳酸钠", "Y20190006967"),
    ("盐酸哌罗匹隆 (新工艺)", "Y20220000720"),
    ("盐酸哌罗匹隆", "Y20190006883"),
    ("盐酸头孢吡肟", "Y20190001951"),
    ("盐酸伊托必利", "Y20190001876"),
    ("阿立哌唑", "Y20230000505"),
    ("盐酸鲁拉西酮", "Y20230001106"),
    ("棕榈酸帕利哌酮", "Y20240000016"),
]


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("product_name", sa.String(255), nullable=False, comment="品种名称"),
        sa.Column("registration_number", sa.String(32), nullable=False, comment="登记号"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        schema=_SCHEMA,
    )
    op.create_unique_constraint(
        "uq_product_registration_numbers_name", _TABLE, ["product_name", "is_deleted"], schema=_SCHEMA
    )

    # 种子：把原硬编码字典入库（仅未软删记录，is_deleted=false）
    if _SEED:
        values_sql = ", ".join(
            f"('{name.replace(chr(39), chr(39) * 2)}', '{number}')" for name, number in _SEED
        )
        op.execute(
            f"""
            INSERT INTO {_SCHEMA}.{_TABLE}
                (id, product_name, registration_number, created_at, updated_at, is_deleted)
            SELECT gen_random_uuid(), v.name, v.number, now(), now(), false
            FROM (VALUES {values_sql}) AS v(name, number)
            """
        )


def downgrade() -> None:
    op.drop_constraint("uq_product_registration_numbers_name", _TABLE, type_="unique", schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
