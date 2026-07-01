"""Production API routes."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse
from app.modules.production.schemas import (
    BatchCreate,
    BatchMaterialCreate,
    BatchMaterialResponse,
    BatchMaterialUpdate,
    BatchResponse,
    BatchStatusUpdate,
    BatchUpdate,
    MaterialBalanceResponse,
    MaterialBalanceUpdate,
    PlanTaskCreate,
    PlanTaskResponse,
    PlanTaskUpdate,
    ProcessParameterCreate,
    ProcessParameterResponse,
    ProcessSpecCreate,
    ProcessSpecResponse,
    ProcessSpecUpdate,
    ProcessStepCreate,
    ProcessStepResponse,
    ProcessStepUpdate,
    ProductionPlanCreate,
    ProductionPlanResponse,
    ProductionPlanUpdate,
    ProductionRecordCreate,
    ProductionRecordResponse,
    ProductionRecordUpdate,
)
from app.modules.production.service import ProductionService

router = APIRouter()


# ============ Batch Routes ============


@router.get("/batches", response_model=ApiResponse, summary="获取批次列表")
async def get_batches(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    product_code: str | None = None,
    batch_no: str | None = None,
    exclude_cancelled: str | None = Query(
        None, description="是否排除已取消的批次，传入 'true' 或 'false'"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取批次列表"""

    service = ProductionService(db)

    skip = (page - 1) * page_size

    # 将字符串参数转换为布尔值

    exclude_cancelled_bool = (
        exclude_cancelled is not None and exclude_cancelled.lower() == "true"
    )

    batches, total = await service.get_batches(
        skip, page_size, status, product_code, batch_no, exclude_cancelled_bool
    )

    return ApiResponse(
        data=[BatchResponse.model_validate(b) for b in batches],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/batches/{batch_id}", response_model=ApiResponse, summary="获取批次详情")
async def get_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取批次详情"""

    service = ProductionService(db)

    batch = await service.get_batch(batch_id)

    if not batch:
        return ApiResponse(code=404, message="批次不存在")

    return ApiResponse(data=BatchResponse.model_validate(batch))


@router.post("/batches", response_model=ApiResponse, summary="创建批次")
async def create_batch(
    data: BatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建批次"""

    service = ProductionService(db)

    batch = await service.create_batch(data)

    await db.commit()

    return ApiResponse(data=BatchResponse.model_validate(batch))


@router.put("/batches/{batch_id}", response_model=ApiResponse, summary="更新批次")
async def update_batch(
    batch_id: uuid.UUID,
    data: BatchUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新批次"""

    service = ProductionService(db)

    batch = await service.update_batch(batch_id, data)

    if not batch:
        return ApiResponse(code=404, message="批次不存在")

    await db.commit()

    return ApiResponse(data=BatchResponse.model_validate(batch))


@router.put(
    "/batches/{batch_id}/status", response_model=ApiResponse, summary="更新批次状态"
)
async def update_batch_status(
    batch_id: uuid.UUID,
    data: BatchStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新批次状态"""

    service = ProductionService(db)

    try:
        batch = await service.update_batch_status(batch_id, data)

        if not batch:
            return ApiResponse(code=404, message="批次不存在")

        await db.commit()

        return ApiResponse(data=BatchResponse.model_validate(batch))

    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.delete("/batches/{batch_id}", response_model=ApiResponse, summary="删除批次")
async def delete_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除批次"""

    service = ProductionService(db)

    result = await service.delete_batch(batch_id)

    if not result:
        return ApiResponse(code=404, message="批次不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ BatchMaterial Routes ============


@router.get(
    "/batches/{batch_id}/materials",
    response_model=ApiResponse,
    summary="获取批次物料列表",
)
async def get_batch_materials(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取批次物料列表"""

    service = ProductionService(db)

    materials = await service.get_batch_materials(batch_id)

    return ApiResponse(
        data=[BatchMaterialResponse.model_validate(m) for m in materials]
    )


@router.post(
    "/batches/{batch_id}/materials", response_model=ApiResponse, summary="添加批次物料"
)
async def add_batch_material(
    batch_id: uuid.UUID,
    data: BatchMaterialCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """添加批次物料"""

    service = ProductionService(db)

    material = await service.add_batch_material(batch_id, data.model_dump())

    await db.commit()

    return ApiResponse(data=BatchMaterialResponse.model_validate(material))


@router.put(
    "/materials/{material_id}", response_model=ApiResponse, summary="更新批次物料"
)
async def update_batch_material(
    material_id: uuid.UUID,
    data: BatchMaterialUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新批次物料"""

    service = ProductionService(db)

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    material = await service.update_batch_material(material_id, update_data)

    if not material:
        return ApiResponse(code=404, message="物料不存在")

    await db.commit()

    return ApiResponse(data=BatchMaterialResponse.model_validate(material))


@router.delete(
    "/materials/{material_id}", response_model=ApiResponse, summary="删除批次物料"
)
async def delete_batch_material(
    material_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除批次物料"""

    service = ProductionService(db)

    result = await service.delete_batch_material(material_id)

    if not result:
        return ApiResponse(code=404, message="物料不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ ProductionPlan Routes ============


@router.get("/plans", response_model=ApiResponse, summary="获取生产计划列表")
async def get_plans(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    plan_month: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取生产计划列表"""

    service = ProductionService(db)

    skip = (page - 1) * page_size

    plans, total = await service.get_plans(skip, page_size, status, plan_month)

    return ApiResponse(
        data=[ProductionPlanResponse.model_validate(p) for p in plans],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/plans/{plan_id}", response_model=ApiResponse, summary="获取生产计划详情")
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取生产计划详情"""

    service = ProductionService(db)

    plan = await service.get_plan(plan_id)

    if not plan:
        return ApiResponse(code=404, message="计划不存在")

    return ApiResponse(data=ProductionPlanResponse.model_validate(plan))


@router.post("/plans", response_model=ApiResponse, summary="创建生产计划")
async def create_plan(
    data: ProductionPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建生产计划"""

    service = ProductionService(db)

    plan = await service.create_plan(data)

    await db.commit()

    return ApiResponse(data=ProductionPlanResponse.model_validate(plan))


@router.put("/plans/{plan_id}", response_model=ApiResponse, summary="更新生产计划")
async def update_plan(
    plan_id: uuid.UUID,
    data: ProductionPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新生产计划"""

    service = ProductionService(db)

    plan = await service.update_plan(plan_id, data)

    if not plan:
        return ApiResponse(code=404, message="计划不存在")

    await db.commit()

    return ApiResponse(data=ProductionPlanResponse.model_validate(plan))


@router.delete("/plans/{plan_id}", response_model=ApiResponse, summary="删除生产计划")
async def delete_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除生产计划"""

    service = ProductionService(db)

    result = await service.delete_plan(plan_id)

    if not result:
        return ApiResponse(code=404, message="计划不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ PlanTask Routes ============


@router.get(
    "/plans/{plan_id}/tasks", response_model=ApiResponse, summary="获取计划任务列表"
)
async def get_plan_tasks(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取计划任务列表"""

    service = ProductionService(db)

    tasks = await service.get_tasks(plan_id)

    return ApiResponse(data=[PlanTaskResponse.model_validate(t) for t in tasks])


@router.post("/tasks", response_model=ApiResponse, summary="创建计划任务")
async def create_task(
    data: PlanTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建计划任务"""

    service = ProductionService(db)

    task = await service.create_task(data)

    await db.commit()

    return ApiResponse(data=PlanTaskResponse.model_validate(task))


@router.put("/tasks/{task_id}", response_model=ApiResponse, summary="更新计划任务")
async def update_task(
    task_id: uuid.UUID,
    data: PlanTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新计划任务"""

    service = ProductionService(db)

    task = await service.update_task(task_id, data)

    if not task:
        return ApiResponse(code=404, message="任务不存在")

    await db.commit()

    return ApiResponse(data=PlanTaskResponse.model_validate(task))


@router.delete("/tasks/{task_id}", response_model=ApiResponse, summary="删除计划任务")
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除计划任务"""

    service = ProductionService(db)

    result = await service.delete_task(task_id)

    if not result:
        return ApiResponse(code=404, message="任务不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ ProcessSpec Routes ============


@router.get("/process-specs", response_model=ApiResponse, summary="获取工艺规程列表")
async def get_process_specs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    status: str | None = None,
    product_code: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取工艺规程列表"""

    service = ProductionService(db)

    skip = (page - 1) * page_size

    specs, total = await service.get_process_specs(
        skip, page_size, status, product_code
    )

    return ApiResponse(
        data=[ProcessSpecResponse.model_validate(s) for s in specs],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get(
    "/process-specs/{spec_id}", response_model=ApiResponse, summary="获取工艺规程详情"
)
async def get_process_spec(
    spec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取工艺规程详情"""

    service = ProductionService(db)

    spec = await service.get_process_spec(spec_id)

    if not spec:
        return ApiResponse(code=404, message="工艺规程不存在")

    return ApiResponse(data=ProcessSpecResponse.model_validate(spec))


@router.post("/process-specs", response_model=ApiResponse, summary="创建工艺规程")
async def create_process_spec(
    data: ProcessSpecCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建工艺规程"""

    service = ProductionService(db)

    spec = await service.create_process_spec(data)

    await db.commit()

    return ApiResponse(data=ProcessSpecResponse.model_validate(spec))


@router.put(
    "/process-specs/{spec_id}", response_model=ApiResponse, summary="更新工艺规程"
)
async def update_process_spec(
    spec_id: uuid.UUID,
    data: ProcessSpecUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新工艺规程"""

    service = ProductionService(db)

    spec = await service.update_process_spec(spec_id, data)

    if not spec:
        return ApiResponse(code=404, message="工艺规程不存在")

    await db.commit()

    return ApiResponse(data=ProcessSpecResponse.model_validate(spec))


@router.delete(
    "/process-specs/{spec_id}", response_model=ApiResponse, summary="删除工艺规程"
)
async def delete_process_spec(
    spec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除工艺规程"""

    service = ProductionService(db)

    result = await service.delete_process_spec(spec_id)

    if not result:
        return ApiResponse(code=404, message="工艺规程不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ ProcessStep Routes =====


@router.get(
    "/process-specs/{spec_id}/steps",
    response_model=ApiResponse,
    summary="获取工艺步骤列表",
)
async def get_process_steps(
    spec_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取工艺步骤列表"""

    service = ProductionService(db)

    steps = await service.get_steps(spec_id)

    return ApiResponse(data=[ProcessStepResponse.model_validate(s) for s in steps])


@router.post("/steps", response_model=ApiResponse, summary="创建工艺步骤")
async def create_process_step(
    data: ProcessStepCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建工艺步骤"""

    service = ProductionService(db)

    step = await service.create_process_step(data)

    await db.commit()

    return ApiResponse(data=ProcessStepResponse.model_validate(step))


@router.put("/steps/{step_id}", response_model=ApiResponse, summary="更新工艺步骤")
async def update_process_step(
    step_id: uuid.UUID,
    data: ProcessStepUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新工艺步骤"""

    service = ProductionService(db)

    step = await service.update_process_step(step_id, data)

    if not step:
        return ApiResponse(code=404, message="步骤不存在")

    await db.commit()

    return ApiResponse(data=ProcessStepResponse.model_validate(step))


@router.delete("/steps/{step_id}", response_model=ApiResponse, summary="删除工艺步骤")
async def delete_process_step(
    step_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除工艺步骤"""

    service = ProductionService(db)

    result = await service.delete_process_step(step_id)

    if not result:
        return ApiResponse(code=404, message="步骤不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ ProcessParameter Routes ============


@router.get(
    "/steps/{step_id}/parameters",
    response_model=ApiResponse,
    summary="获取工艺参数列表",
)
async def get_process_parameters(
    step_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取工艺参数列表"""

    service = ProductionService(db)

    params = await service.get_parameters(step_id)

    return ApiResponse(
        data=[ProcessParameterResponse.model_validate(p) for p in params]
    )


@router.post("/parameters", response_model=ApiResponse, summary="创建工艺参数")
async def create_process_parameter(
    data: ProcessParameterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建工艺参数"""

    service = ProductionService(db)

    param = await service.create_process_parameter(data)

    await db.commit()

    return ApiResponse(data=ProcessParameterResponse.model_validate(param))


@router.delete(
    "/parameters/{param_id}", response_model=ApiResponse, summary="删除工艺参数"
)
async def delete_process_parameter(
    param_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除工艺参数"""

    service = ProductionService(db)

    result = await service.delete_process_parameter(param_id)

    if not result:
        return ApiResponse(code=404, message="参数不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ ProductionRecord Routes ============


@router.get(
    "/batches/{batch_id}/records",
    response_model=ApiResponse,
    summary="获取生产记录列表",
)
async def get_production_records(
    batch_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取生产记录列表"""

    service = ProductionService(db)

    skip = (page - 1) * page_size

    records = await service.get_records(batch_id, skip, page_size)

    return ApiResponse(
        data=[ProductionRecordResponse.model_validate(r) for r in records]
    )


@router.post("/records", response_model=ApiResponse, summary="创建生产记录")
async def create_production_record(
    data: ProductionRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建生产记录"""

    service = ProductionService(db)

    record = await service.create_production_record(data)

    await db.commit()

    return ApiResponse(data=ProductionRecordResponse.model_validate(record))


@router.put("/records/{record_id}", response_model=ApiResponse, summary="更新生产记录")
async def update_production_record(
    record_id: uuid.UUID,
    data: ProductionRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新生产记录"""

    service = ProductionService(db)

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    record = await service.update_production_record(record_id, update_data)

    if not record:
        return ApiResponse(code=404, message="记录不存在")

    await db.commit()

    return ApiResponse(data=ProductionRecordResponse.model_validate(record))


@router.delete(
    "/records/{record_id}", response_model=ApiResponse, summary="删除生产记录"
)
async def delete_production_record(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除生产记录"""

    service = ProductionService(db)

    result = await service.delete_production_record(record_id)

    if not result:
        return ApiResponse(code=404, message="记录不存在")

    await db.commit()

    return ApiResponse(message="删除成功")


# ============ MaterialBalance Routes ============


@router.get(
    "/batches/{batch_id}/balance", response_model=ApiResponse, summary="获取物料平衡"
)
async def get_material_balance(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取物料平衡"""

    service = ProductionService(db)

    balance = await service.get_material_balance(batch_id)

    if not balance:
        return ApiResponse(code=404, message="物料平衡不存在")

    return ApiResponse(data=MaterialBalanceResponse.model_validate(balance))


@router.post(
    "/batches/{batch_id}/balance/calculate",
    response_model=ApiResponse,
    summary="计算物料平衡",
)
async def calculate_material_balance(
    batch_id: uuid.UUID,
    min_balance_rate: float = Query(95.0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """计算物料平衡"""

    service = ProductionService(db)

    balance = await service.calculate_material_balance(batch_id, min_balance_rate)

    if not balance:
        return ApiResponse(code=404, message="批次不存在")

    await db.commit()

    return ApiResponse(data=MaterialBalanceResponse.model_validate(balance))


@router.put(
    "/batches/{batch_id}/balance", response_model=ApiResponse, summary="更新物料平衡"
)
async def update_material_balance(
    batch_id: uuid.UUID,
    data: MaterialBalanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新物料平衡"""

    service = ProductionService(db)

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    balance = await service.update_material_balance(batch_id, update_data)

    if not balance:
        return ApiResponse(code=404, message="物料平衡不存在")

    await db.commit()

    return ApiResponse(data=MaterialBalanceResponse.model_validate(balance))


# ============ 压差统计路由 ============

from app.modules.production.pressure import router as pressure_router

router.include_router(pressure_router, tags=["压差统计"])
