"""Drug API endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import DataResponse
from app.modules.registration import service
from app.modules.registration.models.review import ReviewNode
from app.modules.registration.schemas.drug import (
    DrugCreate,
    DrugResponse,
    DrugUpdate,
    DrugWithNodesResponse,
)
from app.modules.registration.schemas.review import ReviewNodeConfig

router = APIRouter()


@router.get("/", summary="获取药品列表")
async def list_drugs(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:drug:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[DrugWithNodesResponse]]:
    """获取所有药品及其审评节点"""
    drugs = await service.get_drugs(db)
    data = [DrugWithNodesResponse.model_validate(d) for d in drugs]
    return DataResponse[list[DrugWithNodesResponse]](data=data)


@router.post("/", summary="创建药品")
async def create_drug(
    current_user: RequiredUser,
    data: DrugCreate,
    ctx: PermissionContext = Depends(require_permission("registration:drug:create")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[DrugResponse]:
    """创建新药品"""
    drug = await service.create_drug(db, data)
    return DataResponse[DrugResponse](data=DrugResponse.model_validate(drug))


@router.get("/nodes", summary="获取审评节点配置")
async def get_review_nodes(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("registration:drug:read")),
) -> DataResponse[list[ReviewNodeConfig]]:
    """获取10个审评节点的配置信息"""
    nodes = [ReviewNodeConfig(**n) for n in ReviewNode.get_all()]
    return DataResponse[list[ReviewNodeConfig]](data=nodes)


@router.get("/{drug_id}", summary="获取药品详情")
async def get_drug(
    current_user: RequiredUser,
    drug_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:drug:read")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[DrugWithNodesResponse]:
    """获取单个药品及其审评节点"""
    drug = await service.get_drug(db, drug_id)
    return DataResponse[DrugWithNodesResponse](data=DrugWithNodesResponse.model_validate(drug))


@router.put("/{drug_id}", summary="更新药品")
async def update_drug(
    current_user: RequiredUser,
    drug_id: uuid.UUID,
    data: DrugUpdate,
    ctx: PermissionContext = Depends(require_permission("registration:drug:update")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[DrugWithNodesResponse]:
    """更新药品信息及审评节点"""
    drug = await service.update_drug(db, drug_id, data)
    return DataResponse[DrugWithNodesResponse](data=DrugWithNodesResponse.model_validate(drug))


@router.delete("/{drug_id}", summary="删除药品")
async def delete_drug(
    current_user: RequiredUser,
    drug_id: uuid.UUID,
    ctx: PermissionContext = Depends(require_permission("registration:drug:delete")),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[None]:
    """删除药品"""
    await service.delete_drug(db, drug_id)
    return DataResponse[None](message="删除成功")
