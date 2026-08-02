# mypy: ignore-errors
"""LLM configuration API endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser

from .config import LLMConfigModel
from .encryption import encrypt_api_key, mask_api_key

router = APIRouter(prefix="/llm/configs", tags=["LLM Configuration"])


class LLMConfigCreate(BaseModel):
    """Request body for creating LLM config."""

    config_name: str = Field(..., max_length=128)
    config_type: str = Field(default="text", pattern="^(text|vision)$")
    api_base_url: str = Field(..., max_length=500)
    api_key: str = Field(..., max_length=500)
    model_name: str = Field(..., max_length=128)
    temperature: float = Field(default=0.1, ge=0, le=2)
    timeout_seconds: int = Field(default=120, ge=10, le=600)
    is_active: bool = False
    notes: str | None = None


class LLMConfigUpdate(BaseModel):
    """Request body for updating LLM config."""

    config_name: str | None = Field(None, max_length=128)
    config_type: str | None = Field(None, pattern="^(text|vision)$")
    api_base_url: str | None = Field(None, max_length=500)
    api_key: str | None = Field(None, max_length=500)
    model_name: str | None = Field(None, max_length=128)
    temperature: float | None = Field(None, ge=0, le=2)
    timeout_seconds: int | None = Field(None, ge=10, le=600)
    is_active: bool | None = None
    notes: str | None = None


class LLMConfigResponse(BaseModel):
    """Response body for LLM config (never returns raw API key)."""

    id: str
    config_name: str
    config_type: str
    api_base_url: str
    api_key_masked: str
    model_name: str
    temperature: float
    timeout_seconds: int
    is_active: bool
    notes: str | None
    created_at: str
    updated_at: str


@router.get("", response_model=list[LLMConfigResponse])
async def list_configs(  # type: ignore[no-untyped-def]
    config_type: str | None = Query(None, pattern="^(text|vision)$"),
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all LLM configurations."""
    query = select(LLMConfigModel).where(~LLMConfigModel.is_deleted)

    if config_type:
        query = query.where(LLMConfigModel.config_type == config_type)

    query = query.order_by(LLMConfigModel.created_at.desc())

    result = await db.execute(query)
    configs = result.scalars().all()

    return [
        LLMConfigResponse(
            id=str(config.id),
            config_name=config.config_name,
            config_type=config.config_type,
            api_base_url=config.api_base_url,
            api_key_masked=mask_api_key(config.encrypted_api_key),
            model_name=config.model_name,
            temperature=config.temperature,
            timeout_seconds=config.timeout_seconds,
            is_active=config.is_active,
            notes=config.notes,
            created_at=config.created_at.isoformat(),
            updated_at=config.updated_at.isoformat(),
        )
        for config in configs
    ]


@router.post("", response_model=LLMConfigResponse, status_code=201)
async def post(  # type: ignore[no-untyped-def]
    data: LLMConfigCreate,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new LLM configuration (admin only)."""
    # If this config is marked as active, deactivate others of same type
    if data.is_active:
        await db.execute(
            update(LLMConfigModel)
            .where(
                LLMConfigModel.config_type == data.config_type,
                ~LLMConfigModel.is_deleted,  # type: ignore[arg-type]
            )
            .values(is_active=False)
        )

    config = LLMConfigModel(
        config_name=data.config_name,
        config_type=data.config_type,
        api_base_url=data.api_base_url,
        encrypted_api_key=encrypt_api_key(data.api_key),
        model_name=data.model_name,
        temperature=data.temperature,
        timeout_seconds=data.timeout_seconds,
        is_active=data.is_active,
        notes=data.notes,
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return LLMConfigResponse(
        id=str(config.id),
        config_name=config.config_name,
        config_type=config.config_type,
        api_base_url=config.api_base_url,
        api_key_masked=mask_api_key(config.encrypted_api_key),
        model_name=config.model_name,
        temperature=config.temperature,
        timeout_seconds=config.timeout_seconds,
        is_active=config.is_active,
        notes=config.notes,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.get("/{config_id}", response_model=LLMConfigResponse)
async def get(  # type: ignore[no-untyped-def]
    config_id: str,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific LLM configuration."""
    result = await db.execute(
        select(LLMConfigModel).where(
            LLMConfigModel.id == uuid.UUID(config_id),
            ~LLMConfigModel.is_deleted,  # type: ignore[arg-type]
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    return LLMConfigResponse(
        id=str(config.id),
        config_name=config.config_name,
        config_type=config.config_type,
        api_base_url=config.api_base_url,
        api_key_masked=mask_api_key(config.encrypted_api_key),
        model_name=config.model_name,
        temperature=config.temperature,
        timeout_seconds=config.timeout_seconds,
        is_active=config.is_active,
        notes=config.notes,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.put("/{config_id}", response_model=LLMConfigResponse)
async def put(  # type: ignore[no-untyped-def]
    config_id: str,
    data: LLMConfigUpdate,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update an LLM configuration (admin only)."""
    result = await db.execute(
        select(LLMConfigModel).where(
            LLMConfigModel.id == uuid.UUID(config_id),
            ~LLMConfigModel.is_deleted,  # type: ignore[arg-type]
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    # If activating this config, deactivate others of same type
    if data.is_active and not config.is_active:
        await db.execute(
            update(LLMConfigModel)
            .where(
                LLMConfigModel.config_type == config.config_type,
                LLMConfigModel.id != config.id,
                ~LLMConfigModel.is_deleted,  # type: ignore[arg-type]
            )
            .values(is_active=False)
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)

    # Encrypt API key if provided
    if "api_key" in update_data:
        update_data["encrypted_api_key"] = encrypt_api_key(update_data.pop("api_key"))

    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_by = current_user.id

    await db.commit()
    await db.refresh(config)

    return LLMConfigResponse(
        id=str(config.id),
        config_name=config.config_name,
        config_type=config.config_type,
        api_base_url=config.api_base_url,
        api_key_masked=mask_api_key(config.encrypted_api_key),
        model_name=config.model_name,
        temperature=config.temperature,
        timeout_seconds=config.timeout_seconds,
        is_active=config.is_active,
        notes=config.notes,
        created_at=config.created_at.isoformat(),
        updated_at=config.updated_at.isoformat(),
    )


@router.delete("/{config_id}", status_code=204)
async def delete(  # type: ignore[no-untyped-def]
    config_id: str,
    current_user: RequiredUser = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete an LLM configuration (admin only)."""
    result = await db.execute(
        select(LLMConfigModel).where(
            LLMConfigModel.id == uuid.UUID(config_id),
            ~LLMConfigModel.is_deleted,  # type: ignore[arg-type]
        )
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Config not found")

    config.is_deleted = True
    config.updated_by = current_user.id

    await db.commit()


@router.post("/test", summary="Test LLM connection")  # type: ignore[no-redef]
async def post(  # noqa: F811  # type: ignore[no-untyped-def]
    current_user: RequiredUser = None,
) -> Any:
    """Test LLM connectivity using active config."""
    from .client import llm_client

    result = await llm_client.health_check()
    return result
