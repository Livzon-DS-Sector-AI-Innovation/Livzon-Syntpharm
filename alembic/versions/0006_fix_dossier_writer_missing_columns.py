"""fix dossier_writer missing columns

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0006'
down_revision = '0005_product_output'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 修复 asset_categories 表缺失的列
    op.add_column('asset_categories', 
        sa.Column('created_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.add_column('asset_categories', 
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.create_foreign_key(
        'asset_categories_created_by_fkey',
        'asset_categories',
        'users',
        ['created_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )
    op.create_foreign_key(
        'asset_categories_updated_by_fkey',
        'asset_categories',
        'users',
        ['updated_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )

    # 修复 field_mappings 表缺失的列
    op.add_column('field_mappings', 
        sa.Column('created_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.add_column('field_mappings', 
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.create_foreign_key(
        'field_mappings_created_by_fkey',
        'field_mappings',
        'users',
        ['created_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )
    op.create_foreign_key(
        'field_mappings_updated_by_fkey',
        'field_mappings',
        'users',
        ['updated_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )

    # 修复 field_fill_results 表缺失的列
    op.add_column('field_fill_results', 
        sa.Column('created_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.add_column('field_fill_results', 
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.create_foreign_key(
        'field_fill_results_created_by_fkey',
        'field_fill_results',
        'users',
        ['created_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )
    op.create_foreign_key(
        'field_fill_results_updated_by_fkey',
        'field_fill_results',
        'users',
        ['updated_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )

    # 修复 asset_page_splits 表缺失的列
    op.add_column('asset_page_splits', 
        sa.Column('created_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.add_column('asset_page_splits', 
        sa.Column('updated_by', sa.Uuid(), nullable=True),
        schema='dossier_writer')
    op.create_foreign_key(
        'asset_page_splits_created_by_fkey',
        'asset_page_splits',
        'users',
        ['created_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )
    op.create_foreign_key(
        'asset_page_splits_updated_by_fkey',
        'asset_page_splits',
        'users',
        ['updated_by'],
        ['id'],
        source_schema='dossier_writer',
        referent_schema='identity'
    )


def downgrade() -> None:
    # asset_page_splits
    op.drop_constraint('asset_page_splits_updated_by_fkey', 'asset_page_splits', schema='dossier_writer', type_='foreignkey')
    op.drop_constraint('asset_page_splits_created_by_fkey', 'asset_page_splits', schema='dossier_writer', type_='foreignkey')
    op.drop_column('asset_page_splits', 'updated_by', schema='dossier_writer')
    op.drop_column('asset_page_splits', 'created_by', schema='dossier_writer')

    # field_fill_results
    op.drop_constraint('field_fill_results_updated_by_fkey', 'field_fill_results', schema='dossier_writer', type_='foreignkey')
    op.drop_constraint('field_fill_results_created_by_fkey', 'field_fill_results', schema='dossier_writer', type_='foreignkey')
    op.drop_column('field_fill_results', 'updated_by', schema='dossier_writer')
    op.drop_column('field_fill_results', 'created_by', schema='dossier_writer')

    # field_mappings
    op.drop_constraint('field_mappings_updated_by_fkey', 'field_mappings', schema='dossier_writer', type_='foreignkey')
    op.drop_constraint('field_mappings_created_by_fkey', 'field_mappings', schema='dossier_writer', type_='foreignkey')
    op.drop_column('field_mappings', 'updated_by', schema='dossier_writer')
    op.drop_column('field_mappings', 'created_by', schema='dossier_writer')

    # asset_categories
    op.drop_constraint('asset_categories_updated_by_fkey', 'asset_categories', schema='dossier_writer', type_='foreignkey')
    op.drop_constraint('asset_categories_created_by_fkey', 'asset_categories', schema='dossier_writer', type_='foreignkey')
    op.drop_column('asset_categories', 'updated_by', schema='dossier_writer')
    op.drop_column('asset_categories', 'created_by', schema='dossier_writer')
