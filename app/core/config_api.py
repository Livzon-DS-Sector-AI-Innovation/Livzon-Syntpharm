"""Module settings API — CRUD for runtime configuration."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.core.database import get_db
from app.core.response import ApiResponse
from app.platform.identity.deps import get_current_user

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
async def list_settings(
    module: str | None = Query(None, description="Filter by module name"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all module settings, optionally filtered by module."""
    query = select(ModuleSetting).where(not ModuleSetting.is_deleted)

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


@router.get("/{module}/{key}", response_model=ApiResponse)
async def get_setting(
    module: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a specific setting by module and key."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            not ModuleSetting.is_deleted,
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
async def update_setting(
    module: str,
    key: str,
    data: ModuleSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Update a setting value."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            not ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return ApiResponse(code=404, message="Setting not found")

    setting.value = data.value
    setting.updated_by = current_user.id if current_user else None

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
async def create_setting(
    data: ModuleSettingCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a new module setting."""
    # Check for duplicate
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == data.module,
            ModuleSetting.key == data.key,
            not ModuleSetting.is_deleted,
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
        created_by=current_user.id if current_user else None,
        updated_by=current_user.id if current_user else None,
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
async def delete_setting(
    module: str,
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Soft delete a module setting."""
    result = await db.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == module,
            ModuleSetting.key == key,
            not ModuleSetting.is_deleted,
        )
    )
    setting = result.scalar_one_or_none()

    if not setting:
        return ApiResponse(code=404, message="Setting not found")

    setting.is_deleted = True
    setting.updated_by = current_user.id if current_user else None

    await db.commit()
    return ApiResponse(message="Setting deleted")
