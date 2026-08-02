"""Module settings API — CRUD for runtime configuration."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import ApiResponse

router = APIRouter(prefix="/module-settings", tags=["Module Settings"])


# ── Pydantic schemas ──────────────────────────────────────────


class ModuleSettingResponse(BaseModel):
    """Response schema for a module setting."""

    id: str
    module: str
    key: str
    value: str
    value_type: str
    description: str | None = None
    created_at: str
    updated_at: str


class ModuleSettingUpdate(BaseModel):
    """Request schema for updating a setting value."""

    value: str = Field(..., description="New value (as string)")


class ModuleSettingCreate(BaseModel):
    """Request schema for creating a new setting."""

    module: str = Field(..., max_length=50, description="Module name")
    key: str = Field(..., max_length=100, description="Setting key")
    value: str = Field(..., description="Setting value")
    value_type: str = Field(default="string", pattern="^(string|int|bool|json)$")
    description: str | None = None


# ── Endpoints ─────────────────────────────────────────────────


@router.get("", response_model=ApiResponse)
async def get(
    current_user: RequiredUser,
    module: str | None = Query(None, description="Filter by module name"),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List all module settings, optionally filtered by module."""
    query = select(ModuleSetting).where(~ModuleSetting.is_deleted)

    if module:
        query = query.where(ModuleSetting.module == module)

    query = query.order_by(ModuleSetting.module, ModuleSetting.key)

    result = await db.execute(query)
    settings = result.scalars().all()

    return ApiResponse(
        data=[
            ModuleSettingResponse(
                id=str(s.id),
                module=s.module,
                key=s.key,
                value=s.value,
                value_type=s.value_type,
                description=s.description,
                created_at=s.created_at.isoformat(),
                updated_at=s.updated_at.isoformat(),
            )
            for s in settings
        ]
    )


@router.get("/{module}/{key}", response_model=ApiResponse)  # type: ignore[no-redef]
async def get(  # noqa: F811
    module: str,
    key: str,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a specific setting by module and key."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return ApiResponse(code=404, message="Setting not found")

    return ApiResponse(
        data=ModuleSettingResponse(
            id=str(setting.id),
            module=setting.module,
            key=setting.key,
            value=setting.value,
            value_type=setting.value_type,
            description=setting.description,
            created_at=setting.created_at.isoformat(),
            updated_at=setting.updated_at.isoformat(),
        )
    )


@router.put("/{module}/{key}", response_model=ApiResponse)
async def put(
    module: str,
    key: str,
    data: ModuleSettingUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Update a setting value."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return ApiResponse(code=404, message="Setting not found")

    setting.value = data.value
    setting.updated_by = current_user.id

    await db.commit()
    await db.refresh(setting)

    return ApiResponse(
        data=ModuleSettingResponse(
            id=str(setting.id),
            module=setting.module,
            key=setting.key,
            value=setting.value,
            value_type=setting.value_type,
            description=setting.description,
            created_at=setting.created_at.isoformat(),
            updated_at=setting.updated_at.isoformat(),
        )
    )


@router.post("", response_model=ApiResponse, status_code=201)
async def post(
    data: ModuleSettingCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new module setting."""
    # Check for duplicate
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == data.module,
            ModuleSetting.key == data.key,
            ~ModuleSetting.is_deleted,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return ApiResponse(code=409, message="Setting already exists")

    setting = ModuleSetting(
        module=data.module,
        key=data.key,
        value=data.value,
        value_type=data.value_type,
        description=data.description,
        created_by=current_user.id,
        updated_by=current_user.id,
    )

    db.add(setting)
    await db.commit()
    await db.refresh(setting)

    return ApiResponse(
        data=ModuleSettingResponse(
            id=str(setting.id),
            module=setting.module,
            key=setting.key,
            value=setting.value,
            value_type=setting.value_type,
            description=setting.description,
            created_at=setting.created_at.isoformat(),
            updated_at=setting.updated_at.isoformat(),
        )
    )


@router.delete("/{module}/{key}", response_model=ApiResponse)
async def delete(
    module: str,
    key: str,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Soft delete a module setting."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            ~ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return ApiResponse(code=404, message="Setting not found")

    setting.is_deleted = True
    setting.updated_by = current_user.id

    await db.commit()
    return ApiResponse(message="Setting deleted")
