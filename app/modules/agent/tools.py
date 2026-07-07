import inspect
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.audit.models import AuditLog
from app.platform.identity.models import User

from .models import AgentConfirmation
from .repository import AgentRepository
from .schemas import AgentToolExecuteRequest, AgentToolExecuteResponse

RiskLevel = Literal["low", "medium", "high"]
ToolHandler = Callable[["ToolContext", BaseModel], Awaitable[Any] | Any]


@dataclass(frozen=True)
class ToolContext:
    db: AsyncSession
    session_id: uuid.UUID | None
    user_id: uuid.UUID | None
    user: User | None
    reason: str | None
    raw_request: AgentToolExecuteRequest
    agent_service: Any = None
    confirmation_id: uuid.UUID | None = None


@dataclass(frozen=True)
class AgentToolSpec:
    name: str
    summary: str
    input_model: type[BaseModel]
    handler: ToolHandler
    write: bool = False
    risk_level: RiskLevel = "medium"
    required_roles: tuple[str, ...] = ()
    workflow_allowed: bool = True
    human_decision_required: bool = False
    method: str = "TOOL"
    path: str = ""
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_hint: str = ""

    def public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "summary": self.summary,
            "input_schema": self.input_schema or self.input_model.model_json_schema(),
            "risk_level": self.risk_level,
            "write": self.write,
            "method": self.method,
            "path": self.path,
            "required_roles": list(self.required_roles),
            "workflow_allowed": self.workflow_allowed,
            "human_decision_required": self.human_decision_required,
            "output_hint": self.output_hint,
        }


class EmptyToolInput(BaseModel):
    pass


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentToolSpec] = {}

    def register(self, spec: AgentToolSpec) -> AgentToolSpec:
        if spec.name in self._tools:
            raise ValueError(f"Agent tool already registered: {spec.name}")
        self._tools[spec.name] = spec
        return spec

    def get(self, name: str) -> AgentToolSpec | None:
        return self._tools.get(name)

    def require(self, name: str) -> AgentToolSpec:
        spec = self.get(name)
        if spec is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Operation is not in Agent tool registry",
            )
        return spec

    def list(self) -> list[AgentToolSpec]:
        return [self._tools[name] for name in sorted(self._tools)]

    def clear(self) -> None:
        self._tools.clear()


tool_registry = ToolRegistry()


def agent_tool(
    *,
    name: str,
    summary: str,
    input_model: type[BaseModel] = EmptyToolInput,
    write: bool = False,
    risk_level: RiskLevel = "medium",
    required_roles: tuple[str, ...] | list[str] = (),
    workflow_allowed: bool | None = None,
    human_decision_required: bool = False,
    method: str = "TOOL",
    path: str = "",
    input_schema: dict[str, Any] | None = None,
    output_hint: str = "",
    registry: ToolRegistry = tool_registry,
) -> Callable[[ToolHandler], ToolHandler]:
    def decorator(func: ToolHandler) -> ToolHandler:
        spec = AgentToolSpec(
            name=name,
            summary=summary,
            input_model=input_model,
            handler=func,
            write=write,
            risk_level=risk_level,
            required_roles=tuple(required_roles),
            workflow_allowed=(
                not human_decision_required
                if workflow_allowed is None
                else workflow_allowed
            ),
            human_decision_required=human_decision_required,
            method=method,
            path=path,
            input_schema=input_schema or input_model.model_json_schema(),
            output_hint=output_hint,
        )
        registry.register(spec)
        return func

    return decorator


class ToolExecutor:
    def __init__(
        self,
        *,
        registry: ToolRegistry = tool_registry,
        repo: AgentRepository | None = None,
        confirmation_ttl_seconds: int = 300,
    ) -> None:
        self.registry = registry
        self.repo = repo or AgentRepository()
        self.confirmation_ttl_seconds = confirmation_ttl_seconds

    async def execute(
        self,
        db: AsyncSession,
        *,
        request: AgentToolExecuteRequest,
        agent_service: Any = None,
    ) -> AgentToolExecuteResponse:
        spec = self.registry.require(request.operation)
        session_id, user_id, user = await self._resolve_identity(db, request)
        call = await self.repo.create_tool_call(
            db,
            session_id=session_id,
            operation=request.operation,
            request_payload=request.model_dump(mode="json"),
        )

        try:
            if spec.human_decision_required:
                result = self._policy_refusal(request.operation)
                await self.repo.finish_tool_call(
                    db,
                    call,
                    status="rejected_by_policy",
                    response_payload=result.model_dump(mode="json"),
                )
                await self._write_audit(
                    db,
                    action="agent_tool_reject",
                    spec=spec,
                    request=request,
                    session_id=session_id,
                    user_id=user_id,
                    status_value="rejected_by_policy",
                    response_payload=result.model_dump(mode="json"),
                )
                return result
            try:
                validated = self._validate_input(spec, request)
            except HTTPException as exc:
                result = AgentToolExecuteResponse(
                    ok=False,
                    operation=request.operation,
                    data={"message": str(exc.detail)},
                    meta={"validation": "failed"},
                )
                await self.repo.finish_tool_call(
                    db,
                    call,
                    status="invalid_request",
                    response_payload=result.model_dump(mode="json"),
                )
                await self._write_audit(
                    db,
                    action="agent_tool_execute",
                    spec=spec,
                    request=request,
                    session_id=session_id,
                    user_id=user_id,
                    status_value="invalid_request",
                    response_payload=result.model_dump(mode="json"),
                )
                return result
            self._check_permission(spec, user)

            if spec.write:
                confirmation = await self._create_confirmation(
                    db,
                    spec=spec,
                    request=request,
                    session_id=session_id,
                    user_id=user_id,
                )
                result = AgentToolExecuteResponse(
                    ok=True,
                    operation=request.operation,
                    data=None,
                    requires_confirmation=True,
                    confirmation=agent_service._confirmation_out(confirmation)
                    if agent_service is not None
                    else None,
                )
                await self.repo.finish_tool_call(
                    db,
                    call,
                    status="confirmation_required",
                    response_payload=result.model_dump(mode="json"),
                )
                await self._write_audit(
                    db,
                    action="agent_tool_execute",
                    spec=spec,
                    request=request,
                    session_id=session_id,
                    user_id=user_id,
                    confirmation_id=confirmation.id,
                    status_value="confirmation_required",
                    response_payload=result.model_dump(mode="json"),
                )
                return result

            result = await self._invoke_tool(
                db,
                spec=spec,
                request=request,
                validated=validated,
                session_id=session_id,
                user_id=user_id,
                user=user,
                agent_service=agent_service,
            )
            await self.repo.finish_tool_call(
                db,
                call,
                status="succeeded",
                response_payload=result.model_dump(mode="json"),
            )
            await self._write_audit(
                db,
                action="agent_tool_execute",
                spec=spec,
                request=request,
                session_id=session_id,
                user_id=user_id,
                status_value="succeeded",
                response_payload=result.model_dump(mode="json"),
            )
            return result
        except HTTPException as exc:
            await self.repo.finish_tool_call(
                db,
                call,
                status="invalid_request"
                if exc.status_code == status.HTTP_400_BAD_REQUEST
                else "failed",
                error_message=str(exc.detail),
            )
            await self._write_audit(
                db,
                action="agent_tool_execute",
                spec=spec,
                request=request,
                session_id=session_id,
                user_id=user_id,
                status_value="failed",
                error_message=str(exc.detail),
            )
            raise
        except Exception as exc:
            await self.repo.finish_tool_call(
                db,
                call,
                status="failed",
                error_message=str(exc),
            )
            await self._write_audit(
                db,
                action="agent_tool_execute",
                spec=spec,
                request=request,
                session_id=session_id,
                user_id=user_id,
                status_value="failed",
                error_message=str(exc),
            )
            raise

    async def execute_confirmed(
        self,
        db: AsyncSession,
        *,
        request: AgentToolExecuteRequest,
        current_user: User,
        confirmation: AgentConfirmation,
        agent_service: Any = None,
    ) -> AgentToolExecuteResponse:
        spec = self.registry.require(request.operation)
        if not spec.write:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Confirmation operation is invalid",
            )
        if spec.human_decision_required:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                HUMAN_DECISION_REQUIRED_MESSAGE,
            )
        validated = self._validate_input(spec, request)
        self._check_permission(spec, current_user)
        result = await self._invoke_tool(
            db,
            spec=spec,
            request=request,
            validated=validated,
            session_id=confirmation.session_id,
            user_id=current_user.id,
            user=current_user,
            agent_service=agent_service,
            confirmation_id=confirmation.id,
        )
        await self._write_audit(
            db,
            action="agent_tool_confirm",
            spec=spec,
            request=request,
            session_id=confirmation.session_id,
            user_id=current_user.id,
            confirmation_id=confirmation.id,
            status_value="succeeded",
            response_payload=result.model_dump(mode="json"),
        )
        return result

    def _validate_input(
        self,
        spec: AgentToolSpec,
        request: AgentToolExecuteRequest,
    ) -> BaseModel:
        payload = {**request.params, **(request.body or {})}
        try:
            return spec.input_model.model_validate(payload)
        except ValidationError as exc:
            first = exc.errors()[0] if exc.errors() else {}
            loc = ".".join(str(part) for part in first.get("loc", ()))
            message = first.get("msg") or str(exc)
            detail = f"{loc}: {message}" if loc else message
            raise HTTPException(status.HTTP_400_BAD_REQUEST, detail) from exc

    def _check_permission(self, spec: AgentToolSpec, user: User | None) -> None:
        if not spec.required_roles:
            return
        if user is None or user.role not in spec.required_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Agent tool permission denied",
            )

    async def _invoke_tool(
        self,
        db: AsyncSession,
        *,
        spec: AgentToolSpec,
        request: AgentToolExecuteRequest,
        validated: BaseModel,
        session_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        user: User | None,
        agent_service: Any,
        confirmation_id: uuid.UUID | None = None,
    ) -> AgentToolExecuteResponse:
        context = ToolContext(
            db=db,
            session_id=session_id,
            user_id=user_id,
            user=user,
            reason=request.reason,
            raw_request=request,
            agent_service=agent_service,
            confirmation_id=confirmation_id,
        )
        data = spec.handler(context, validated)
        if inspect.isawaitable(data):
            data = await data
        return AgentToolExecuteResponse(ok=True, operation=request.operation, data=data)

    async def _create_confirmation(
        self,
        db: AsyncSession,
        *,
        spec: AgentToolSpec,
        request: AgentToolExecuteRequest,
        session_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
    ) -> AgentConfirmation:
        return await self.repo.create_confirmation(
            db,
            session_id=session_id,
            user_id=user_id,
            operation=request.operation,
            summary=request.reason or spec.summary or request.operation,
            risk_level=spec.risk_level,
            request_payload=request.model_dump(mode="json"),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.confirmation_ttl_seconds),
        )

    async def _resolve_identity(
        self,
        db: AsyncSession,
        request: AgentToolExecuteRequest,
    ) -> tuple[uuid.UUID | None, uuid.UUID | None, User | None]:
        session_id = self._uuid_or_none(request.context.get("session_id"))
        user_id = self._uuid_or_none(request.context.get("user_id"))
        if user_id is None and session_id is not None:
            session = await self.repo.get_session(db, session_id)
            if session:
                user_id = session.user_id
        user = None
        if user_id is not None and hasattr(db, "get"):
            user = await db.get(User, user_id)
            if user and getattr(user, "is_deleted", False):
                user = None
        return session_id, user_id, user

    async def _write_audit(
        self,
        db: AsyncSession,
        *,
        action: str,
        spec: AgentToolSpec,
        request: AgentToolExecuteRequest,
        session_id: uuid.UUID | None,
        user_id: uuid.UUID | None,
        status_value: str,
        confirmation_id: uuid.UUID | None = None,
        response_payload: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> None:
        if not hasattr(db, "add"):
            return
        audit = AuditLog(
            request_id=str(session_id) if session_id else None,
            user_id=user_id,
            method="AGENT",
            path=f"agent://tools/{spec.name}",
            status_code=(
                200 if status_value in {"succeeded", "confirmation_required"} else 400
            ),
            resource_type="agent_tool",
            action=action,
            new_value=self._truncate_payload(response_payload),
            extra={
                "operation": spec.name,
                "risk_level": spec.risk_level,
                "write": spec.write,
                "session_id": str(session_id) if session_id else None,
                "confirmation_id": str(confirmation_id) if confirmation_id else None,
                "status": status_value,
                "request": self._sanitize_request(request),
                "error_message": error_message,
            },
        )
        db.add(audit)

    @staticmethod
    def _sanitize_request(request: AgentToolExecuteRequest) -> dict[str, Any]:
        data = request.model_dump(mode="json")
        for section in ("params", "body", "context"):
            value = data.get(section)
            if isinstance(value, dict):
                data[section] = ToolExecutor._mask_secret_fields(value)
        return data

    @staticmethod
    def _mask_secret_fields(value: dict[str, Any]) -> dict[str, Any]:
        masked: dict[str, Any] = {}
        for key, item in value.items():
            key_lower = str(key).lower()
            if any(
                token in key_lower
                for token in ("secret", "token", "password", "key")
            ):
                masked[key] = "***"
            elif isinstance(item, dict):
                masked[key] = ToolExecutor._mask_secret_fields(item)
            else:
                masked[key] = item
        return masked

    @staticmethod
    def _truncate_payload(value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is None:
            return None
        text = str(value)
        if len(text) <= 4000:
            return value
        return {"truncated": True, "preview": text[:4000]}

    @staticmethod
    def _policy_refusal(operation: str) -> AgentToolExecuteResponse:
        return AgentToolExecuteResponse(
            ok=False,
            operation=operation,
            data={"message": HUMAN_DECISION_REQUIRED_MESSAGE},
            meta={"policy": "human_decision_required"},
        )

    @staticmethod
    def _uuid_or_none(value: Any) -> uuid.UUID | None:
        if not value:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except ValueError:
            return None


HUMAN_DECISION_REQUIRED_MESSAGE = (
    "抱歉，我不能代你完成审批、驳回、批准、重启等需要责任判断的高风险操作。"
    "请你在对应业务页面自行查看资料、评估风险并手动操作；我可以帮助你查询待处理事项、"
    "整理背景信息或生成意见草稿供你参考。"
)
