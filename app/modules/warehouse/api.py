from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import success_response
from app.modules.warehouse.schemas import (
    PackagingMaterialListResponse,
    PackagingMaterialResponse,
    ProductInventoryListResponse,
    ProductInventoryResponse,
    RawMaterialListResponse,
    RawMaterialResponse,
    WarehouseFeishuConfigApiResponse,
    WarehouseFeishuConfigUpsert,
    WarehouseFeishuConnectivityApiResponse,
    WarehouseFeishuRawRecordApiResponse,
    WarehouseFeishuTableBatchEnableApiResponse,
    WarehouseFeishuTableBatchEnablePayload,
    WarehouseFeishuTableEnableApiResponse,
    WarehouseFeishuTableEnablePayload,
    WarehouseFeishuTableListApiResponse,
    WarehouseFeishuTableResponse,
    WarehouseFeishuTableSyncApiResponse,
    WarehouseFeishuWsStatusApiResponse,
)
from app.modules.warehouse.service import WarehouseService
from app.shared.module_api import create_module_router
from app.shared.module_registry import MODULES_BY_CODE

router = create_module_router(MODULES_BY_CODE["warehouse"])


def get_warehouse_service(
    session: AsyncSession = Depends(get_db),
) -> WarehouseService:

    return WarehouseService(session)


@router.get(
    "/raw-materials",
    summary="原辅料库存列表",
    response_model=RawMaterialListResponse,
)
async def list_raw_materials(
    current_user: CurrentUser,
    service: WarehouseService = Depends(get_warehouse_service),
):

    items = await service.list_raw_materials()

    data = [
        RawMaterialResponse.model_validate(item).model_dump(mode="json")
        for item in items
    ]

    return success_response(data=data)


@router.get(
    "/packaging-materials",
    summary="包材库存列表",
    response_model=PackagingMaterialListResponse,
)
async def list_packaging_materials(
    current_user: CurrentUser,
    service: WarehouseService = Depends(get_warehouse_service),
):

    items = await service.list_packaging_materials()

    data = [
        PackagingMaterialResponse.model_validate(item).model_dump(mode="json")
        for item in items
    ]

    return success_response(data=data)


@router.get(
    "/products",
    summary="成品库存列表",
    response_model=ProductInventoryListResponse,
)
async def list_products(
    current_user: CurrentUser,
    service: WarehouseService = Depends(get_warehouse_service),
):

    items = await service.list_products()

    data = [
        ProductInventoryResponse.model_validate(item).model_dump(mode="json")
        for item in items
    ]

    return success_response(data=data)


@router.get(
    "/feishu-config",
    summary="获取仓储飞书配置",
    response_model=WarehouseFeishuConfigApiResponse,
)
async def get_feishu_config(
    current_user: CurrentUser,
    service: WarehouseService = Depends(get_warehouse_service),
):

    data = await service.get_feishu_config_response()

    return success_response(data=data.model_dump(mode="json"))


@router.put(
    "/feishu-config",
    summary="保存仓储飞书配置",
    response_model=WarehouseFeishuConfigApiResponse,
)
async def save_feishu_config(
    current_user: CurrentUser,
    payload: WarehouseFeishuConfigUpsert,
    service: WarehouseService = Depends(get_warehouse_service),
):

    data = await service.save_feishu_config(payload)

    return success_response(data=data.model_dump(mode="json"))


@router.post(
    "/feishu-config/test",
    summary="测试仓储飞书连通性",
    response_model=WarehouseFeishuConnectivityApiResponse,
)
async def test_feishu_config(
    current_user: CurrentUser,
    payload: WarehouseFeishuConfigUpsert | None = None,
    service: WarehouseService = Depends(get_warehouse_service),
):

    data = await service.test_feishu_connectivity(payload)

    return success_response(data=data.model_dump(mode="json"))


@router.get(
    "/feishu/tables",
    summary="获取仓储飞书数据表目录",
    response_model=WarehouseFeishuTableListApiResponse,
)
async def list_feishu_tables(
    current_user: CurrentUser,
    business_domain: str | None = None,
    keyword: str | None = None,
    enabled: bool | None = None,
    service: WarehouseService = Depends(get_warehouse_service),
):

    items = await service.list_feishu_tables(
        business_domain=business_domain,
        keyword=keyword,
        enabled=enabled,
    )

    data = [
        WarehouseFeishuTableResponse.model_validate(item).model_dump(mode="json")
        for item in items
    ]

    return success_response(data=data)


@router.post(
    "/feishu/tables/refresh",
    summary="刷新仓储飞书数据表目录",
    response_model=WarehouseFeishuTableListApiResponse,
)
async def refresh_feishu_tables(
    current_user: CurrentUser,
    service: WarehouseService = Depends(get_warehouse_service),
):

    items = await service.refresh_feishu_tables()

    data = [
        WarehouseFeishuTableResponse.model_validate(item).model_dump(mode="json")
        for item in items
    ]

    return success_response(data=data)


@router.post(
    "/feishu/tables/enabled/batch",
    summary="批量启用或停用仓储飞书数据表同步",
    response_model=WarehouseFeishuTableBatchEnableApiResponse,
)
async def set_feishu_tables_enabled(
    current_user: CurrentUser,
    payload: WarehouseFeishuTableBatchEnablePayload,
    service: WarehouseService = Depends(get_warehouse_service),
):

    items = await service.set_feishu_tables_enabled(
        payload.table_ids,
        payload.is_enabled,
    )

    data = [
        WarehouseFeishuTableResponse.model_validate(item).model_dump(mode="json")
        for item in items
    ]

    return success_response(data=data)


@router.patch(
    "/feishu/tables/{table_id}/enabled",
    summary="启用或停用仓储飞书数据表同步",
    response_model=WarehouseFeishuTableEnableApiResponse,
)
async def set_feishu_table_enabled(
    current_user: CurrentUser,
    table_id: UUID,
    payload: WarehouseFeishuTableEnablePayload,
    service: WarehouseService = Depends(get_warehouse_service),
):

    table = await service.set_feishu_table_enabled(table_id, payload.is_enabled)

    data = WarehouseFeishuTableResponse.model_validate(table).model_dump(mode="json")

    return success_response(data=data)


@router.post(
    "/feishu/tables/{table_id}/sync",
    summary="同步仓储飞书数据表记录快照",
    response_model=WarehouseFeishuTableSyncApiResponse,
)
async def sync_feishu_table(
    current_user: CurrentUser,
    table_id: UUID,
    service: WarehouseService = Depends(get_warehouse_service),
):

    data = await service.sync_feishu_table(table_id)

    return success_response(data=data.model_dump(mode="json"))


@router.get(
    "/feishu/tables/{table_id}/records",
    summary="读取仓储飞书数据表本地记录快照",
    response_model=WarehouseFeishuRawRecordApiResponse,
)
async def get_feishu_table_records(
    current_user: CurrentUser,
    table_id: UUID,
    keyword: str | None = None,
    field: str | None = None,
    field_operator: str | None = Query(
        default=None,
        description="字段筛选条件：contains/eq/ne/gt/gte/lt/lte",
    ),
    field_value: str | None = Query(default=None, description="字段筛选值"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: WarehouseService = Depends(get_warehouse_service),
):

    data = await service.get_feishu_table_records(
        table_id,
        keyword=keyword,
        field=field,
        field_operator=field_operator,
        field_value=field_value,
        page=page,
        page_size=page_size,
    )

    return success_response(data=data.model_dump(mode="json"))


@router.get(
    "/feishu/domains/{business_domain}/records",
    summary="读取仓储业务域启用表本地记录快照",
    response_model=WarehouseFeishuRawRecordApiResponse,
)
async def get_feishu_domain_records(
    current_user: CurrentUser,
    business_domain: str,
    table_id: UUID | None = None,
    keyword: str | None = None,
    field: str | None = None,
    field_operator: str | None = Query(
        default=None,
        description="字段筛选条件：contains/eq/ne/gt/gte/lt/lte",
    ),
    field_value: str | None = Query(default=None, description="字段筛选值"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    service: WarehouseService = Depends(get_warehouse_service),
):

    data = await service.get_feishu_domain_records(
        business_domain,  # type: ignore[arg-type]
        table_id=table_id,
        keyword=keyword,
        field=field,
        field_operator=field_operator,
        field_value=field_value,
        page=page,
        page_size=page_size,
    )

    return success_response(data=data.model_dump(mode="json"))


@router.get(
    "/feishu/ws/status",
    summary="查询仓储飞书 WebSocket 状态",
    response_model=WarehouseFeishuWsStatusApiResponse,
)
async def get_feishu_ws_status(current_user: CurrentUser):

    from app.modules.warehouse.ws_client import get_ws_status

    return success_response(data=(await get_ws_status()).model_dump(mode="json"))


@router.post(
    "/feishu/ws/restart",
    summary="重启仓储飞书 WebSocket 长连接",
    response_model=WarehouseFeishuWsStatusApiResponse,
)
async def restart_feishu_ws(current_user: CurrentUser):

    from app.modules.warehouse.ws_client import restart_ws_from_db

    return success_response(data=(await restart_ws_from_db()).model_dump(mode="json"))
