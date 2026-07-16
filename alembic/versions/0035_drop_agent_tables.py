"""drop_agent_tables

Revision ID: 0035_drop_agent_tables
Revises: 0034_add_reagent_quality_table
Create Date: 2026-07-14

Agent module removed — drop agent-related tables from core schema.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0035_drop_agent_tables"
down_revision: str | None = "0034_add_reagent_quality_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_messages_created_at")
    op.execute("DROP TABLE IF EXISTS core.agent_messages CASCADE")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_tool_calls_operation")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_tool_calls_session_id")
    op.execute("DROP TABLE IF EXISTS core.agent_tool_calls CASCADE")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_sessions_user_id")
    op.execute("DROP TABLE IF EXISTS core.agent_sessions CASCADE")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflow_runs_session_id")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflow_runs_status")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflow_runs_user_id")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflow_runs_workflow_id")
    op.execute("DROP TABLE IF EXISTS core.agent_workflow_runs CASCADE")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_confirmations_operation")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_confirmations_session_id")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_confirmations_user_id")
    op.execute("DROP TABLE IF EXISTS core.agent_confirmations CASCADE")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_skills_name")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_skills_status")
    op.execute("DROP TABLE IF EXISTS core.agent_skills CASCADE")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflows_session_id")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflows_status")
    op.execute("DROP INDEX IF EXISTS core.ix_core_agent_workflows_user_id")
    op.execute("DROP TABLE IF EXISTS core.agent_workflows CASCADE")


def downgrade() -> None:
    pass