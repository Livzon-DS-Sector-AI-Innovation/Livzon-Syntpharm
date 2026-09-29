"""0060_add_deliverable_template_versions

Revision ID: 0060_add_deliverable_template_versions
Revises: 0059_add_deliverable_template_fields
Create Date: 2026-09-16 10:00:00.000000

交付物模板版本管理：
- 新表 research.rd_deliverable_template_versions：留档、查看/下载历史版本、回滚
- doc_gen_jobs 增加 deliverable_template_version_id：生成产物可追溯所用的母本版本
- 存量已有母本的模板回填一份 v1（is_current = true），保证版本链从「当前生效版本」接续
- 顺带清理假状态：无母本却被标记为启用的模板置为不启用（列出也无实际用途）

说明：is_active 的「新建默认不启用」由模型层 default=False 承担；该列 DDL 从未声明
server_default，故此处不改列默认值，避免模型与 DDL 语义不一致。

回填不依赖 gen_random_uuid()/uuid-ossp 等扩展或 PG 版本：UUID 在 Python 侧生成后逐行插入。
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '0060_add_deliverable_template_versions'
down_revision: str | Sequence[str] | None = '0059_add_deliverable_template_fields'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = 'rd_deliverable_template_versions'
_JOBS_FK = 'fk_research_doc_gen_jobs_deliverable_template_version_id'


def _base_columns() -> list[sa.Column]:
    """公共审计列（与 app/shared/base_model.py 对齐）。"""
    return [
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=True),
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    ]


def _audit_fks() -> list[sa.ForeignKeyConstraint]:
    """审计列外键。"""
    return [
        sa.ForeignKeyConstraint(['created_by'], ['identity.users.id']),
        sa.ForeignKeyConstraint(['updated_by'], ['identity.users.id']),
    ]


def _backfill_initial_versions() -> None:
    """给已有母本的模板补一条 v1，沿用模板自身的创建信息，时间线才合理。"""
    import uuid

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT t.id, t.file_object_key, t.file_name, t.file_ext, t.template_code,
                   t.template_structure, t.created_by, t.updated_by, t.created_at, t.updated_at
            FROM research.rd_deliverable_templates t
            WHERE t.file_object_key IS NOT NULL
              AND t.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1 FROM research.rd_deliverable_template_versions v
                  WHERE v.template_id = t.id
              )
            """
        )
    ).mappings().all()

    if not rows:
        return

    stmt = sa.text(
        """
        INSERT INTO research.rd_deliverable_template_versions
            (id, template_id, version_no, file_object_key, file_name, file_ext, template_code,
             template_structure, change_note, is_current, is_deleted, created_by, updated_by,
             created_at, updated_at)
        VALUES
            (:id, :template_id, :version_no, :file_object_key, :file_name, :file_ext, :template_code,
             :template_structure, :change_note, :is_current, :is_deleted, :created_by, :updated_by,
             :created_at, :updated_at)
        """
    ).bindparams(
        sa.bindparam('id', type_=sa.Uuid()),
        sa.bindparam('template_id', type_=sa.Uuid()),
        sa.bindparam('template_structure', type_=sa.JSON()),
        sa.bindparam('created_by', type_=sa.Uuid()),
        sa.bindparam('updated_by', type_=sa.Uuid()),
        sa.bindparam('created_at', type_=sa.DateTime(timezone=True)),
        sa.bindparam('updated_at', type_=sa.DateTime(timezone=True)),
    )

    for row in rows:
        bind.execute(
            stmt,
            {
                'id': uuid.uuid4(),
                'template_id': row['id'],
                'version_no': 1,
                'file_object_key': row['file_object_key'],
                'file_name': row['file_name'],
                'file_ext': row['file_ext'],
                'template_code': row['template_code'],
                'template_structure': row['template_structure'],
                'change_note': '初始版本（数据回填）',
                'is_current': True,
                'is_deleted': False,
                'created_by': row['created_by'],
                'updated_by': row['updated_by'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
            },
        )


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column('template_id', sa.Uuid(), nullable=False, comment='所属交付物模板'),
        sa.Column('version_no', sa.Integer(), nullable=False, comment='版本号，从 1 起单调递增'),
        sa.Column('file_object_key', sa.String(length=500), nullable=False, comment='该版本模板文件存储键'),
        sa.Column('file_name', sa.String(length=500), nullable=True, comment='原始文件名'),
        sa.Column('file_ext', sa.String(length=16), nullable=True, comment='扩展名（docx/dotx/doc）'),
        sa.Column('file_size', sa.BigInteger(), nullable=True, comment='文件字节数'),
        sa.Column('template_code', sa.String(length=100), nullable=True, comment='槽位定义 code 快照'),
        sa.Column('template_structure', sa.JSON(), nullable=True, comment='槽位结构定义快照'),
        sa.Column('change_note', sa.Text(), nullable=True, comment='版本说明（变更备注）'),
        sa.Column('is_current', sa.Boolean(), server_default='false', nullable=False, comment='是否当前生效版本'),
        *_base_columns(),
        sa.ForeignKeyConstraint(['template_id'], ['research.rd_deliverable_templates.id']),
        *_audit_fks(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('template_id', 'version_no', name='uq_rd_deliverable_template_versions_no'),
        schema='research',
    )
    # 同一模板最多一条当前版本；软删记录不占用该位
    op.create_index(
        'uq_rd_deliverable_template_versions_current',
        _TABLE,
        ['template_id'],
        unique=True,
        schema='research',
        postgresql_where=sa.text('is_current = true AND is_deleted = false'),
    )

    op.add_column(
        'doc_gen_jobs',
        sa.Column('deliverable_template_version_id', sa.Uuid(), nullable=True, comment='所用交付物模板版本'),
        schema='research',
    )
    op.create_foreign_key(
        _JOBS_FK,
        'doc_gen_jobs',
        _TABLE,
        ['deliverable_template_version_id'],
        ['id'],
        source_schema='research',
        referent_schema='research',
    )

    _backfill_initial_versions()

    # 无母本的模板不可能进入 AI 生成候选，却可能带着「启用」标记，先归零
    op.execute(
        """
        UPDATE research.rd_deliverable_templates
        SET is_active = false
        WHERE is_active = true
          AND file_object_key IS NULL
          AND is_deleted = false
        """
    )


def downgrade() -> None:
    op.drop_constraint(_JOBS_FK, 'doc_gen_jobs', schema='research', type_='foreignkey')
    op.drop_column('doc_gen_jobs', 'deliverable_template_version_id', schema='research')
    op.drop_index('uq_rd_deliverable_template_versions_current', table_name=_TABLE, schema='research')
    op.drop_table(_TABLE, schema='research')
