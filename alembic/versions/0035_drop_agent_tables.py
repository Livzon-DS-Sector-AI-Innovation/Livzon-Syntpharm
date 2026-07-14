"""drop_agent_tables

Revision ID: 0035_drop_agent_tables
Revises: 0034_add_reagent_quality_table
Create Date: 2026-07-14

Agent module removed — all AI chatbots deleted.
Drop all agent-related tables from core schema.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0035_drop_agent_tables"
down_revision: str | None = "0034_add_reagent_quality_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f("ix_core_agent_messages_session_id"), table_name="agent_messages", schema="core")
    op.drop_index(op.f("ix_core_agent_messages_created_at"), table_name="agent_messages", schema="core")
    op.drop_table("agent_messages", schema="core")
    op.drop_index(op.f("ix_core_agent_tool_calls_operation"), table_name="agent_tool_calls", schema="core")
    op.drop_index(op.f("ix_core_agent_tool_calls_session_id"), table_name="agent_tool_calls", schema="core")
    op.drop_table("agent_tool_calls", schema="core")
    op.drop_index(op.f("ix_core_agent_sessions_user_id"), table_name="agent_sessions", schema="core")
    op.drop_table("agent_sessions", schema="core")
    op.drop_index(op.f("ix_core_agent_workflow_runs_session_id"), table_name="agent_workflow_runs", schema="core")
    op.drop_index(op.f("ix_core_agent_workflow_runs_status"), table_name="agent_workflow_runs", schema="core")
    op.drop_index(op.f("ix_core_agent_workflow_runs_user_id"), table_name="agent_workflow_runs", schema="core")
    op.drop_index(op.f("ix_core_agent_workflow_runs_workflow_id"), table_name="agent_workflow_runs", schema="core")
    op.drop_table("agent_workflow_runs", schema="core")
    op.drop_index(op.f("ix_core_agent_confirmations_operation"), table_name="agent_confirmations", schema="core")
    op.drop_index(op.f("ix_core_agent_confirmations_session_id"), table_name="agent_confirmations", schema="core")
    op.drop_index(op.f("ix_core_agent_confirmations_user_id"), table_name="agent_confirmations", schema="core")
    op.drop_table("agent_confirmations", schema="core")
    op.drop_index(op.f("ix_core_agent_skills_name"), table_name="agent_skills", schema="core")
    op.drop_index(op.f("ix_core_agent_skills_status"), table_name="agent_skills", schema="core")
    op.drop_table("agent_skills", schema="core")
    op.drop_index(op.f("ix_core_agent_workflows_session_id"), table_name="agent_workflows", schema="core")
    op.drop_index(op.f("ix_core_agent_workflows_status"), table_name="agent_workflows", schema="core")
    op.drop_index(op.f("ix_core_agent_workflows_user_id"), table_name="agent_workflows", schema="core")
    op.drop_table("agent_workflows", schema="core")


def downgrade() -> None:
    pass