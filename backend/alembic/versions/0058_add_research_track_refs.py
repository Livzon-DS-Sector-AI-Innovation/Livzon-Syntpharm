"""add research track references to process_optimizations

Revision ID: 0058_add_research_track_refs
Revises: 0057_merge_migration_heads
Create Date: 2026-08-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0058_add_research_track_refs'
down_revision: str = '0057_merge_migration_heads'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 添加杂质研究项引用字段
    op.add_column('process_optimizations', 
        sa.Column('impurity_track_id', sa.UUID(), nullable=True),
        schema='research'
    )
    
    # 添加晶型研究项引用字段
    op.add_column('process_optimizations',
        sa.Column('crystal_track_id', sa.UUID(), nullable=True),
        schema='research'
    )
    
    # 添加外键约束
    op.create_foreign_key(
        'fk_process_opt_impurity_track',
        'process_optimizations',
        'rd_research_tracks',
        ['impurity_track_id'],
        ['id'],
        source_schema='research',
        referent_schema='research'
    )
    
    op.create_foreign_key(
        'fk_process_opt_crystal_track',
        'process_optimizations',
        'rd_research_tracks',
        ['crystal_track_id'],
        ['id'],
        source_schema='research',
        referent_schema='research'
    )
    
    # 添加注释
    op.execute("""
        COMMENT ON COLUMN research.process_optimizations.impurity_track_id IS '关联的杂质研究项ID';
        COMMENT ON COLUMN research.process_optimizations.crystal_track_id IS '关联的晶型研究项ID';
    """)


def downgrade() -> None:
    # 删除外键约束
    op.drop_constraint('fk_process_opt_crystal_track', 'process_optimizations', schema='research')
    op.drop_constraint('fk_process_opt_impurity_track', 'process_optimizations', schema='research')
    
    # 删除字段
    op.drop_column('process_optimizations', 'crystal_track_id', schema='research')
    op.drop_column('process_optimizations', 'impurity_track_id', schema='research')
