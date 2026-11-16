"""safety equipment facility evaluation grade（双轨合并 no-op 占位）

Revision ID: 0186_safety_equipment_facility_evaluation_grade
Revises: 0100_safety_equipment_facility_hazards
Create Date: 2026-11-16

本迁移与 uat 链的 0168_safety_equipment_facility_evaluation_grade 是同一逻辑变更在两个集成分支上的编号副本，upgrade 内容逐字一致。
合并后 DDL 以 uat 链版本为准；本文件转为 no-op 占位，仅保持 main 已应用链
（… → 0114_merge_safety_officer_and_deviation_heads）的 revision 引用完整性。
"""

from collections.abc import Sequence

revision: str = "0186_safety_equipment_facility_evaluation_grade"
down_revision: str = "0100_safety_equipment_facility_hazards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
