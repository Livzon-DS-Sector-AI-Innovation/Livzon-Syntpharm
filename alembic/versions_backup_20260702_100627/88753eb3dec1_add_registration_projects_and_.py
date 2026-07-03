"""add registration_projects and registration_certificates

Revision ID: 88753eb3dec1
Revises: a3f7c2e19b45
Create Date: 2026-06-24 13:57:37.256085
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "88753eb3dec1"
down_revision: str | None = "7ef205f0db8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "registration_certificates",
        sa.Column(
            "product_name", sa.String(length=255), nullable=False, comment="品种名称"
        ),
        sa.Column("market", sa.String(length=128), nullable=False, comment="国家/市场"),
        sa.Column(
            "certificate_type",
            sa.String(length=32),
            nullable=False,
            comment="证书类型：domestic_approval/overseas_registration/wc/copp/gmp/other",
        ),
        sa.Column(
            "certificate_no", sa.String(length=128), nullable=True, comment="证书编号"
        ),
        sa.Column("approved_at", sa.Date(), nullable=True, comment="获批日期"),
        sa.Column("valid_until", sa.Date(), nullable=True, comment="有效期至"),
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="valid",
            nullable=False,
            comment="证书状态：valid/expiring/expired/pending",
        ),
        sa.Column(
            "file_path", sa.String(length=512), nullable=True, comment="证书文件路径"
        ),
        sa.Column(
            "related_project_id", sa.Uuid(), nullable=True, comment="关联注册项目ID"
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint(
            "certificate_type IN ('domestic_approval', 'overseas_registration', 'wc', 'copp', 'gmp', 'other')",
            name="ck_registration_certificates_type",
        ),
        sa.CheckConstraint(
            "status IN ('valid', 'expiring', 'expired', 'pending')",
            name="ck_registration_certificates_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["identity.users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["identity.users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="registration",
    )
    op.create_table(
        "registration_projects",
        sa.Column(
            "product_name", sa.String(length=255), nullable=False, comment="品种名称"
        ),
        sa.Column(
            "market", sa.String(length=128), nullable=False, comment="注册市场/国家"
        ),
        sa.Column(
            "registration_type",
            sa.String(length=64),
            nullable=True,
            comment="注册类型（新注册/再注册/变更等）",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="draft",
            nullable=False,
            comment="状态：draft/preparing/submitted/accepted/under_review/supplementary/approved/withdrawn/terminated",
        ),
        sa.Column("submitted_at", sa.Date(), nullable=True, comment="申报日期"),
        sa.Column("accepted_at", sa.Date(), nullable=True, comment="受理日期"),
        sa.Column("approved_at", sa.Date(), nullable=True, comment="获批日期"),
        sa.Column(
            "expected_completion_at", sa.Date(), nullable=True, comment="预计完成时间"
        ),
        sa.Column("owner", sa.String(length=128), nullable=True, comment="负责人"),
        sa.Column("latest_progress", sa.Text(), nullable=True, comment="最新进展"),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'preparing', 'submitted', 'accepted', 'under_review', 'supplementary', 'approved', 'withdrawn', 'terminated')",
            name="ck_registration_projects_status",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["identity.users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["identity.users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        schema="registration",
    )


def downgrade() -> None:
    op.drop_table("registration_projects", schema="registration")
    op.drop_table("registration_certificates", schema="registration")
