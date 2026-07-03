"""hr_missing_tables_20260702

Create missing hr tables that were created outside of migrations.

Revision ID: 004_hr
Revises: 003_equipment
Create Date: 2026-07-02 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_hr'
down_revision: Union[str, None] = '003_equipment'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS hr')
    
    # Create sop_catalog table if not exists
    op.execute('''
        CREATE TABLE IF NOT EXISTS hr.sop_catalog (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            file_name VARCHAR(256) NOT NULL,
            sop_number VARCHAR(64),
            category VARCHAR(128),
            department VARCHAR(128),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            created_by UUID,
            updated_by UUID,
            is_deleted BOOLEAN DEFAULT false NOT NULL
        )
    ''')
    
    # Create trainers table if not exists
    op.execute('''
        CREATE TABLE IF NOT EXISTS hr.trainers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(64) NOT NULL,
            department VARCHAR(64),
            trainable_departments TEXT,
            qualification_scope TEXT,
            certification_date DATE,
            confirmation_date DATE,
            confirmation_reminder DATE,
            remarks TEXT,
            is_primary_trainer BOOLEAN DEFAULT false NOT NULL,
            admin VARCHAR(64),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
            created_by UUID,
            updated_by UUID,
            is_deleted BOOLEAN DEFAULT false NOT NULL
        )
    ''')
    
    # Create indexes
    op.execute('CREATE INDEX IF NOT EXISTS ix_sop_catalog_category ON hr.sop_catalog (category)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_sop_catalog_department ON hr.sop_catalog (department)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_trainers_department ON hr.trainers (department)')
    op.execute('CREATE INDEX IF NOT EXISTS ix_trainers_name ON hr.trainers (name)')


def downgrade() -> None:
    op.drop_table('trainers', schema='hr')
    op.drop_table('sop_catalog', schema='hr')
