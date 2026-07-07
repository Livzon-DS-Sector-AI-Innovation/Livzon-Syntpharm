import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.core.response import success_response
from app.platform.identity.deps import RequiredUser

from .llm_proxy import forward_chat_completion, list_active_text_models
from .schemas import (
    AgentChatRequest,
    AgentConfirmationExecuteResponse,
    AgentSkillCreate,
    AgentSkillResolveRequest,
    AgentSkillUpdate,
    AgentToolExecuteRequest,
)
from .service import AgentService
from .tool_registration import ensure_agent_tools_registered
from .tools import tool_registry

router = APIRouter()


def _bearer_token(authorization: str | None) -> str | None:
    if authorization and authorization.startswith("Bearer "):
        return authorization.removeprefix("Bearer ").strip()
    return None


def require_service_token(expected: str, authorization: str | None) -> None:
    token = _bearer_token(authorization)
    if not expected or token != expected:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Agent service token")


@router.post("/chat")
async def chat(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    result = await AgentService(settings).chat(
        db, request=payload, current_user=current_user
    )
    return success_response(data=result.model_dump(mode="json"))


@router.post("/chat/stream")
async def chat_stream(
    payload: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    return StreamingResponse(
        AgentService(settings).stream_chat(
            db,
            request=payload,
            current_user=current_user,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/tools/execute")
async def execute_tool(
    payload: AgentToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    require_service_token(settings.AGENT_TOOL_TOKEN, authorization)
    result = await AgentService(settings).execute_tool(db, request=payload)
    return success_response(data=result.model_dump(mode="json"))


@router.get("/tools")
async def list_tools(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    require_service_token(settings.AGENT_TOOL_TOKEN, authorization)
    ensure_agent_tools_registered()
    return success_response(data=[tool.public_dict() for tool in tool_registry.list()])


@router.post("/skills/resolve")
async def resolve_skills(
    payload: AgentSkillResolveRequest,
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    require_service_token(settings.AGENT_TOOL_TOKEN, authorization)
    result = await AgentService(settings).resolve_skills(db, request=payload)
    return success_response(data=result.model_dump(mode="json"))


@router.get("/skills")
async def list_skills(
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    result = await AgentService(settings).list_skills(db)
    return success_response(data=[item.model_dump(mode="json") for item in result])


@router.post("/skills")
async def create_skill(
    payload: AgentSkillCreate,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    result = await AgentService(settings).create_skill(
        db, request=payload, current_user=current_user
    )
    return success_response(data=result.model_dump(mode="json"))


@router.get("/skills/{skill_id}")
async def get_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    result = await AgentService(settings).get_skill(db, skill_id=skill_id)
    return success_response(data=result.model_dump(mode="json"))


@router.put("/skills/{skill_id}")
async def update_skill(
    skill_id: uuid.UUID,
    payload: AgentSkillUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    result = await AgentService(settings).update_skill(
        db, skill_id=skill_id, request=payload, current_user=current_user
    )
    return success_response(data=result.model_dump(mode="json"))


@router.post("/skills/{skill_id}/enable")
async def enable_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    result = await AgentService(settings).set_skill_status(
        db, skill_id=skill_id, status_value="active", current_user=current_user
    )
    return success_response(data=result.model_dump(mode="json"))


@router.post("/skills/{skill_id}/disable")
async def disable_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    result = await AgentService(settings).set_skill_status(
        db, skill_id=skill_id, status_value="disabled", current_user=current_user
    )
    return success_response(data=result.model_dump(mode="json"))


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    if current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin required")
    await AgentService(settings).delete_skill(
        db, skill_id=skill_id, current_user=current_user
    )
    return success_response(data={"ok": True})


@router.post("/confirmations/{confirmation_id}/execute")
async def execute_confirmation(
    confirmation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    confirmation, result = await AgentService(settings).execute_confirmation(
        db,
        confirmation_id=confirmation_id,
        current_user=current_user,
    )
    response = AgentConfirmationExecuteResponse(
        confirmation=AgentService(settings)._confirmation_out(confirmation),
        result=result,
    )
    return success_response(data=response.model_dump(mode="json"))


@router.post("/confirmations/{confirmation_id}/cancel")
async def cancel_confirmation(
    confirmation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: RequiredUser = None,
    settings: Settings = Depends(get_settings),
):
    confirmation = await AgentService(settings).cancel_confirmation(
        db,
        confirmation_id=confirmation_id,
        current_user=current_user,
    )
    return success_response(
        data=AgentService(settings)
        ._confirmation_out(confirmation)
        .model_dump(mode="json")
    )


@router.get("/llm/models")
async def agent_llm_models(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    require_service_token(settings.AGENT_LLM_PROXY_TOKEN, authorization)
    return await list_active_text_models()


@router.post("/llm/chat/completions")
async def agent_llm_chat_completions(
    request: Request,
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
):
    require_service_token(settings.AGENT_LLM_PROXY_TOKEN, authorization)
    payload: dict[str, Any] = await request.json()
    return await forward_chat_completion(payload)
