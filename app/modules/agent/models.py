import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class AgentSession(BaseModel):
    __tablename__ = "agent_sessions"
    __table_args__ = {"schema": "core", "comment": "Agent conversation sessions"}

    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="active", server_default="active"
    )
    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )


class AgentMessage(BaseModel):
    __tablename__ = "agent_messages"
    __table_args__ = {"schema": "core", "comment": "Agent conversation messages"}

    session_id: Mapped[uuid.UUID] = mapped_column(index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )


class AgentToolCall(BaseModel):
    __tablename__ = "agent_tool_calls"
    __table_args__ = {"schema": "core", "comment": "Agent tool execution audit"}

    session_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="started", server_default="started"
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AgentConfirmation(BaseModel):
    __tablename__ = "agent_confirmations"
    __table_args__ = {
        "schema": "core",
        "comment": "Agent write operation confirmations",
    }

    session_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    risk_level: Mapped[str] = mapped_column(
        String(32), default="medium", server_default="medium"
    )
    status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default="pending"
    )
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    executed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentSkill(BaseModel):
    __tablename__ = "agent_skills"
    __table_args__ = (
        UniqueConstraint("name", name="uq_core_agent_skills_name"),
        {"schema": "core", "comment": "Agent progressive disclosure skills"},
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_keywords: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="active", server_default="active", index=True
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    version: Mapped[int] = mapped_column(Integer, default=1, server_default="1")


class AgentWorkflow(BaseModel):
    __tablename__ = "agent_workflows"
    __table_args__ = {"schema": "core", "comment": "Agent user workflow definitions"}

    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="enabled", server_default="enabled", index=True
    )
    trigger_phrases: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    steps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    source_skill: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_request: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    last_run_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AgentWorkflowRun(BaseModel):
    __tablename__ = "agent_workflow_runs"
    __table_args__ = {"schema": "core", "comment": "Agent workflow run state"}

    workflow_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    session_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", server_default="pending", index=True
    )
    current_step: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    steps_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    step_results: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
