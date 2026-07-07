import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

AgentRole = Literal["system", "user", "assistant", "tool"]


class AgentChatRequest(BaseModel):
    session_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=8000)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentMessageOut(BaseModel):
    id: uuid.UUID | None = None
    role: AgentRole
    content: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentConfirmationOut(BaseModel):
    id: uuid.UUID
    operation: str
    summary: str
    risk_level: str
    status: str
    expires_at: datetime
    request_payload: dict[str, Any] = Field(default_factory=dict)


class AgentChatResponse(BaseModel):
    session_id: uuid.UUID
    message: AgentMessageOut
    pending_confirmations: list[AgentConfirmationOut] = Field(default_factory=list)
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)


class AgentToolExecuteRequest(BaseModel):
    operation: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    context: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=500)


class AgentToolExecuteResponse(BaseModel):
    ok: bool
    operation: str
    data: Any = None
    meta: dict[str, Any] = Field(default_factory=dict)
    requires_confirmation: bool = False
    confirmation: AgentConfirmationOut | None = None


class AgentConfirmationExecuteResponse(BaseModel):
    confirmation: AgentConfirmationOut
    result: AgentToolExecuteResponse


class AgentSkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=4000)
    trigger_keywords: list[str] = Field(default_factory=list)
    content: str = Field(min_length=1)
    status: Literal["active", "disabled"] = "active"
    is_builtin: bool = False


class AgentSkillUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    trigger_keywords: list[str] | None = None
    content: str | None = Field(default=None, min_length=1)
    status: Literal["active", "disabled"] | None = None


class AgentSkillOut(BaseModel):
    id: uuid.UUID
    name: str
    title: str
    description: str
    trigger_keywords: list[str] = Field(default_factory=list)
    content: str
    status: str
    is_builtin: bool
    version: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentSkillResolveRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    enabled_toolsets: list[str] = Field(default_factory=list)
    business_scope: list[str] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    limit: int = Field(default=3, ge=1, le=10)


class AgentSkillResolvedOut(BaseModel):
    name: str
    title: str
    description: str
    trigger_keywords: list[str] = Field(default_factory=list)
    content: str
    score: int


class AgentSkillResolveResponse(BaseModel):
    skills: list[AgentSkillResolvedOut] = Field(default_factory=list)


class AgentWorkflowStep(BaseModel):
    order: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    operation: str = Field(min_length=1, max_length=120)
    params: dict[str, Any] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1000)


class AgentWorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    trigger_phrases: list[str] = Field(default_factory=list)
    steps: list[AgentWorkflowStep] = Field(min_length=1)
    source_skill: str | None = Field(default=None, max_length=120)
    source_request: str | None = Field(default=None, max_length=8000)


class AgentWorkflowOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    status: str
    trigger_phrases: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    source_skill: str | None = None
    source_request: str | None = None
    last_run_id: uuid.UUID | None = None
    last_run_status: str | None = None
    last_run_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AgentWorkflowRunOut(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    user_id: uuid.UUID | None = None
    session_id: uuid.UUID | None = None
    status: str
    current_step: int
    steps_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    step_results: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
