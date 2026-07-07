import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AgentConfirmation,
    AgentMessage,
    AgentSession,
    AgentSkill,
    AgentToolCall,
    AgentWorkflow,
    AgentWorkflowRun,
)


class AgentRepository:
    async def get_session(
        self,
        db: AsyncSession,
        session_id: uuid.UUID,
    ) -> AgentSession | None:
        result = await db.execute(
            select(AgentSession).where(
                AgentSession.id == session_id,
                AgentSession.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def create_session(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None,
        context: dict[str, Any],
        title: str | None,
    ) -> AgentSession:
        session = AgentSession(user_id=user_id, title=title, context=context)
        session.created_by = user_id
        session.updated_by = user_id
        db.add(session)
        await db.flush()
        return session

    async def add_message(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        role: str,
        content: str,
        metadata: dict[str, Any] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> AgentMessage:
        message = AgentMessage(
            session_id=session_id,
            role=role,
            content=content,
            message_metadata=metadata or {},
        )
        message.created_by = user_id
        message.updated_by = user_id
        db.add(message)
        await db.flush()
        return message

    async def list_messages(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        limit: int = 20,
    ) -> list[AgentMessage]:
        result = await db.execute(
            select(AgentMessage)
            .where(
                AgentMessage.session_id == session_id,
                AgentMessage.is_deleted.is_(False),
            )
            .order_by(AgentMessage.created_at.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def create_tool_call(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID | None,
        operation: str,
        request_payload: dict[str, Any],
    ) -> AgentToolCall:
        call = AgentToolCall(
            session_id=session_id,
            operation=operation,
            request_payload=request_payload,
        )
        db.add(call)
        await db.flush()
        return call

    async def finish_tool_call(
        self,
        db: AsyncSession,
        call: AgentToolCall,
        *,
        status: str,
        response_payload: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> AgentToolCall:
        call.status = status
        call.response_payload = response_payload
        call.error_message = error_message
        await db.flush()
        return call

    async def create_confirmation(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        operation: str,
        summary: str,
        risk_level: str,
        request_payload: dict[str, Any],
        expires_at: datetime,
    ) -> AgentConfirmation:
        confirmation = AgentConfirmation(
            session_id=session_id,
            user_id=user_id,
            operation=operation,
            summary=summary,
            risk_level=risk_level,
            request_payload=request_payload,
            expires_at=expires_at,
        )
        confirmation.created_by = user_id
        confirmation.updated_by = user_id
        db.add(confirmation)
        await db.flush()
        return confirmation

    async def get_confirmation(
        self,
        db: AsyncSession,
        confirmation_id: uuid.UUID,
    ) -> AgentConfirmation | None:
        result = await db.execute(
            select(AgentConfirmation).where(
                AgentConfirmation.id == confirmation_id,
                AgentConfirmation.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def execute_confirmation(
        self,
        db: AsyncSession,
        confirmation: AgentConfirmation,
        *,
        result_payload: dict[str, Any],
        user_id: uuid.UUID | None,
    ) -> AgentConfirmation:
        confirmation.status = "executed"
        confirmation.executed_at = datetime.now(UTC)
        confirmation.result_payload = result_payload
        confirmation.updated_by = user_id
        await db.flush()
        return confirmation

    async def cancel_confirmation(
        self,
        db: AsyncSession,
        confirmation: AgentConfirmation,
        *,
        user_id: uuid.UUID | None,
    ) -> AgentConfirmation:
        confirmation.status = "cancelled"
        confirmation.updated_by = user_id
        await db.flush()
        return confirmation

    async def list_skills(self, db: AsyncSession) -> list[AgentSkill]:
        result = await db.execute(
            select(AgentSkill)
            .where(AgentSkill.is_deleted.is_(False))
            .order_by(AgentSkill.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_active_skills(self, db: AsyncSession) -> list[AgentSkill]:
        result = await db.execute(
            select(AgentSkill)
            .where(
                AgentSkill.is_deleted.is_(False),
                AgentSkill.status == "active",
            )
            .order_by(AgentSkill.name.asc())
        )
        return list(result.scalars().all())

    async def get_skill(
        self, db: AsyncSession, skill_id: uuid.UUID
    ) -> AgentSkill | None:
        result = await db.execute(
            select(AgentSkill).where(
                AgentSkill.id == skill_id,
                AgentSkill.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_skill_by_name(self, db: AsyncSession, name: str) -> AgentSkill | None:
        result = await db.execute(
            select(AgentSkill).where(
                AgentSkill.name == name,
                AgentSkill.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def create_workflow(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None,
        session_id: uuid.UUID | None,
        name: str,
        description: str | None,
        trigger_phrases: list[str],
        steps: list[dict[str, Any]],
        source_skill: str | None,
        source_request: str | None,
    ) -> AgentWorkflow:
        workflow = AgentWorkflow(
            user_id=user_id,
            session_id=session_id,
            name=name,
            description=description,
            trigger_phrases=trigger_phrases,
            steps=steps,
            source_skill=source_skill,
            source_request=source_request,
        )
        workflow.created_by = user_id
        workflow.updated_by = user_id
        db.add(workflow)
        await db.flush()
        return workflow

    async def list_workflows(
        self,
        db: AsyncSession,
        *,
        user_id: uuid.UUID | None,
    ) -> list[AgentWorkflow]:
        query = select(AgentWorkflow).where(AgentWorkflow.is_deleted.is_(False))
        if user_id is not None:
            query = query.where(AgentWorkflow.user_id == user_id)
        else:
            query = query.where(AgentWorkflow.user_id.is_(None))
        result = await db.execute(query.order_by(AgentWorkflow.created_at.desc()))
        return list(result.scalars().all())

    async def get_workflow(
        self,
        db: AsyncSession,
        workflow_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
    ) -> AgentWorkflow | None:
        query = select(AgentWorkflow).where(
            AgentWorkflow.id == workflow_id,
            AgentWorkflow.is_deleted.is_(False),
        )
        if user_id is not None:
            query = query.where(AgentWorkflow.user_id == user_id)
        else:
            query = query.where(AgentWorkflow.user_id.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_workflow_run(
        self,
        db: AsyncSession,
        *,
        workflow: AgentWorkflow,
        user_id: uuid.UUID | None,
        session_id: uuid.UUID | None,
    ) -> AgentWorkflowRun:
        run = AgentWorkflowRun(
            workflow_id=workflow.id,
            user_id=user_id,
            session_id=session_id,
            status="running",
            current_step=0,
            steps_snapshot=workflow.steps,
            step_results=[],
            started_at=datetime.now(UTC),
        )
        run.created_by = user_id
        run.updated_by = user_id
        db.add(run)
        await db.flush()
        return run

    async def get_workflow_run(
        self,
        db: AsyncSession,
        run_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None,
    ) -> AgentWorkflowRun | None:
        query = select(AgentWorkflowRun).where(
            AgentWorkflowRun.id == run_id,
            AgentWorkflowRun.is_deleted.is_(False),
        )
        if user_id is not None:
            query = query.where(AgentWorkflowRun.user_id == user_id)
        else:
            query = query.where(AgentWorkflowRun.user_id.is_(None))
        result = await db.execute(query)
        return result.scalar_one_or_none()
