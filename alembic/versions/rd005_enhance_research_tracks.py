"""enhance research tracks: add conclusion version history + finding fields

Revision ID: rd005
Revises: id001
Create Date: 2026-06-29
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "rd005"
down_revision = "id001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create conclusion version history table
    op.create_table(
        "rd_track_conclusion_versions",
        sa.Column("track_id", sa.UUID(), nullable=False, comment="研究项ID"),
        sa.Column("version", sa.Integer(), nullable=False, comment="版本号"),
        sa.Column("conclusion", sa.Text(), nullable=True, comment="结论文本"),
        sa.Column(
            "confidence", sa.String(50), server_default="preliminary", comment="置信度"
        ),
        sa.Column("change_summary", sa.Text(), nullable=True, comment="变更说明"),
        sa.Column(
            "evidence_refs",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="支撑证据引用",
        ),
        sa.Column("author_id", sa.UUID(), nullable=True, comment="作者"),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=True
        ),
        sa.ForeignKeyConstraint(["track_id"], ["research.rd_research_tracks.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="research",
    )

    # 2. Add enhanced fields to rd_research_findings
    op.add_column(
        "rd_research_findings",
        sa.Column("experiment_date", sa.Date(), nullable=True, comment="实验日期"),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column("operator", sa.String(100), nullable=True, comment="操作人"),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column(
            "experiment_conditions",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="实验条件",
        ),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column(
            "materials_used",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="使用物料",
        ),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column(
            "equipment_used",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="使用设备",
        ),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column(
            "spectra_refs",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="图谱引用",
        ),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column(
            "analytical_results",
            postgresql.JSON(astext_type=sa.Text()),
            nullable=True,
            comment="检测结果",
        ),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column("observations", sa.Text(), nullable=True, comment="实验现象/观察"),
        schema="research",
    )
    op.add_column(
        "rd_research_findings",
        sa.Column("notes", sa.Text(), nullable=True, comment="备注"),
        schema="research",
    )


def downgrade() -> None:
    op.drop_table("rd_track_conclusion_versions", schema="research")
    for col in [
        "notes",
        "observations",
        "analytical_results",
        "spectra_refs",
        "equipment_used",
        "materials_used",
        "experiment_conditions",
        "operator",
        "experiment_date",
    ]:
        op.drop_column("rd_research_findings", col, schema="research")
