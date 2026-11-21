"""工作台聚合编排。

职责（数据取数各模块自己负责，本层只做编排）：
1. 取当前用户权限码集合下发各数据源（各源自行决定是否取数、能否按角色兜底）；
2. 逐源调用 ``public_api``，单源异常只降级该源，不影响其它源；
3. 按模块分组、计数、排序，转成响应模型。

跨模块边界：只 import 各模块的 ``public_api``，禁止直接 import 模块内部实现。
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.public_api import (
    list_capa_todos,
    list_deviation_processes,
    list_deviation_todos,
    list_inspection_processes,
    list_inspection_todos,
)
from app.modules.safety.public_api import list_hazard_processes, list_hazard_review_todos
from app.platform.identity.models import User
from app.platform.permission.service.management import effective_permission_codes
from app.platform.workbench.constants import (
    MATCH_PERSON,
    MODULE_QUALITY,
    MODULE_SAFETY,
    match_kind_label,
)
from app.platform.workbench.read_marks import (
    item_key,
    load_read_fingerprints,
    read_key_set,
    todo_fingerprint,
)
from app.platform.workbench.schemas import (
    ProcessSectionModel,
    TodoSectionModel,
    WorkbenchGroupModel,
    WorkbenchItemModel,
    WorkbenchOverviewData,
)
from app.shared.module_registry import MODULES_BY_CODE
from app.shared.workbench_types import WorkbenchItem, WorkbenchSourceResult

logger = logging.getLogger(__name__)

#: 分组展示顺序（质量管理在前）
_MODULE_ORDER: tuple[str, ...] = (MODULE_QUALITY, MODULE_SAFETY)


def _module_label(module_key: str, fallback: str) -> str:
    module = MODULES_BY_CODE.get(module_key)
    return module.name if module is not None else fallback


def _to_model(item: WorkbenchItem, read_keys: set[tuple[str, str]] | None = None) -> WorkbenchItemModel:
    return WorkbenchItemModel(
        id=item.id,
        source=item.source,
        module_key=item.module_key,
        module_label=item.module_label,
        doc_type_label=item.doc_type_label,
        title=item.title,
        doc_no=item.doc_no,
        status=item.status,
        status_label=item.status_label,
        step_label=item.step_label,
        match_kind=item.match_kind,
        match_kind_label=match_kind_label(item.match_kind),
        age_days=item.age_days,
        overdue=item.overdue,
        path=item.path,
        my_roles=list(item.my_roles),
        is_read=read_keys is not None and item_key(item) in read_keys,
        fingerprint=todo_fingerprint(item),
    )


def _group(
    items: list[WorkbenchItem],
    has_more_by_module: dict[str, bool],
    read_keys: set[tuple[str, str]] | None = None,
) -> list[WorkbenchGroupModel]:
    """按模块分组（质量 → 安全，空模块不返回）。

    ``read_keys`` 只有待办传：流程区块没有已读概念，传 ``None`` 时全部按未读渲染
    （但前端不消费流程的 ``is_read``，仅保持字段默认值）。
    """
    buckets: dict[str, list[WorkbenchItem]] = {key: [] for key in _MODULE_ORDER}
    for item in items:
        buckets.setdefault(item.module_key, []).append(item)

    groups: list[WorkbenchGroupModel] = []
    for module_key in (*_MODULE_ORDER, *(key for key in buckets if key not in _MODULE_ORDER)):
        bucket = buckets.get(module_key) or []
        if not bucket:
            continue
        groups.append(
            WorkbenchGroupModel(
                module_key=module_key,
                module_label=_module_label(module_key, bucket[0].module_label),
                count=len(bucket),
                has_more=has_more_by_module.get(module_key, False),
                items=[_to_model(item, read_keys) for item in bucket],
            )
        )
    return groups


def _todo_sort_key(item: WorkbenchItem) -> tuple[int, int, str]:
    """待办排序：超期优先，其次停留越久越靠前，最后按单据号稳定排序。"""
    return (0 if item.overdue else 1, -(item.age_days or 0), item.doc_no or item.id)


def _process_sort_key(item: WorkbenchItem) -> tuple[int, str]:
    """流程排序：最近有流转的靠前（age_days 越小越新）。"""
    return (item.age_days if item.age_days is not None else 10**6, item.doc_no or item.id)


async def _collect(
    source: str,
    awaitable: Awaitable[WorkbenchSourceResult],
    degraded: list[str],
) -> WorkbenchSourceResult:
    """执行单个数据源，失败降级为空结果并记录来源（不阻塞其它源）。"""
    try:
        return await awaitable
    except Exception:
        logger.warning(
            "workbench 数据源取数失败，已降级",
            extra={"source": source, "biz_module": "workbench"},
            exc_info=True,
        )
        degraded.append(source)
        return WorkbenchSourceResult()


async def build_overview(
    db: AsyncSession,
    user: User,
    *,
    todo_limit: int,
    process_limit: int,
) -> WorkbenchOverviewData:
    """组装首页工作台数据（一次请求内串行取各源，源数量有限且均带上限）。"""
    granted = await effective_permission_codes(db, user)

    degraded: list[str] = []
    todo_items: list[WorkbenchItem] = []
    todo_more: dict[str, bool] = {}
    process_items: list[WorkbenchItem] = []
    process_more: dict[str, bool] = {}

    deviation_todos = await _collect(
        "quality.deviation.todos",
        list_deviation_todos(db, user_id=user.id, granted=granted, limit=todo_limit),
        degraded,
    )
    inspection_todos = await _collect(
        "quality.inspection.todos",
        list_inspection_todos(db, granted=granted, limit=todo_limit),
        degraded,
    )
    capa_todos = await _collect(
        "quality.capa.todos",
        list_capa_todos(db, granted=granted, limit=todo_limit),
        degraded,
    )
    hazard_todos = await _collect(
        "safety.hazard.todos",
        list_hazard_review_todos(db, granted=granted, limit=todo_limit),
        degraded,
    )
    for result in (deviation_todos, inspection_todos, capa_todos, hazard_todos):
        todo_items.extend(result.items)
    todo_more[MODULE_QUALITY] = deviation_todos.has_more or inspection_todos.has_more or capa_todos.has_more
    todo_more[MODULE_SAFETY] = hazard_todos.has_more

    deviation_processes = await _collect(
        "quality.deviation.processes",
        list_deviation_processes(db, user_id=user.id, granted=granted, limit=process_limit),
        degraded,
    )
    inspection_processes = await _collect(
        "quality.inspection.processes",
        list_inspection_processes(db, user_id=user.id, granted=granted, limit=process_limit),
        degraded,
    )
    hazard_processes = await _collect(
        "safety.hazard.processes",
        list_hazard_processes(db, user_id=user.id, granted=granted, limit=process_limit),
        degraded,
    )
    for result in (deviation_processes, inspection_processes, hazard_processes):
        process_items.extend(result.items)
    process_more[MODULE_QUALITY] = deviation_processes.has_more or inspection_processes.has_more
    process_more[MODULE_SAFETY] = hazard_processes.has_more

    todo_items.sort(key=_todo_sort_key)
    process_items.sort(key=_process_sort_key)

    # 已读只在待办上生效：按本次涉及的数据源一次查出已读指纹，指纹不一致即视为新提醒
    stored_reads = await load_read_fingerprints(db, user.id, {item.source for item in todo_items})
    read_keys = read_key_set(todo_items, stored_reads)

    person_total = sum(1 for item in todo_items if item.match_kind == MATCH_PERSON)
    return WorkbenchOverviewData(
        todos=TodoSectionModel(
            total=len(todo_items),
            unread_total=len(todo_items) - len(read_keys),
            has_more=any(todo_more.values()),
            person_total=person_total,
            role_total=len(todo_items) - person_total,
            groups=_group(todo_items, todo_more, read_keys),
        ),
        processes=ProcessSectionModel(
            total=len(process_items),
            has_more=any(process_more.values()),
            groups=_group(process_items, process_more),
        ),
        generated_at=datetime.now(UTC),
        degraded_sources=degraded,
    )
