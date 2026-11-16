"""隐患类别改名 / 删除的 service 层回归测试。

背景：`update_hazard_category` 改名时会把 `safety.hazard_reports.hazard_category`
里引用旧名的记录一起同步（`rename_hazard_category_in_hazards`），
`delete_hazard_category` 走软删除。这两条路径此前只有 create 有测试覆盖，
这里用 fake repo 钉住内置类别、重名、同名、不存在四条边界与跨表同步的调用。

注：`repo` / `_audit` 在 service 上是强类型属性，替换成 `AsyncMock` 后不能再经由
`service.repo.xxx` 访问（mypy strict 会按真实签名报 attr-defined），
因此 `_service()` 把 mock 一并返回，断言统一走返回值里的 mock 对象。
"""

import uuid
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from app.modules.safety.service.hazard import BUILTIN_HAZARD_CATEGORIES, HazardService


def _row(name: str = "旧类别", *, deleted: bool = False, active: bool = True, sort_order: int = 100) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        sort_order=sort_order,
        is_deleted=deleted,
        is_active=active,
    )


def _service() -> tuple[HazardService, Any, Any]:
    """构造 service 并把 repo / _audit 换成 mock，返回可控的 mock 句柄。"""
    service = HazardService(session=cast(Any, AsyncMock()))
    repo = AsyncMock()
    audit = AsyncMock()
    service.repo = cast(Any, repo)
    service._audit = cast(Any, audit)  # type: ignore[method-assign]  # 换成 mock 以便断言审计调用
    return service, repo, audit


async def test_rename_syncs_ledger_and_writes_dictionary() -> None:
    """改名成功：字典表更新 + 台账同步 + 返回新名，且名称两侧空白被裁掉。"""
    service, repo, audit = _service()
    row = _row("旧类别")
    repo.get_hazard_category_by_id.return_value = row
    repo.get_hazard_category_by_name.return_value = None
    repo.rename_hazard_category_in_hazards.return_value = 3

    result = await service.update_hazard_category(row.id, "  新类别  ")

    assert result == {"id": str(row.id), "name": "新类别", "sort_order": 100, "is_builtin": False}
    repo.update_hazard_category.assert_awaited_once_with(
        row.id, {"name": "新类别", "is_deleted": False, "is_active": True}
    )
    repo.rename_hazard_category_in_hazards.assert_awaited_once_with("旧类别", "新类别")
    audit.assert_awaited_once()


async def test_rename_rejects_builtin_name() -> None:
    """改成内置类别名会被拒：内置 7 类不落字典表，改了会和合成项撞名。"""
    service, repo, _ = _service()

    with pytest.raises(ValueError, match="内置类别"):
        await service.update_hazard_category(uuid.uuid4(), BUILTIN_HAZARD_CATEGORIES[0])

    repo.update_hazard_category.assert_not_awaited()


async def test_rename_rejects_duplicate_name() -> None:
    """与另一条未删除记录重名时拒绝，且不做任何写入。"""
    service, repo, _ = _service()
    row = _row("旧类别")
    repo.get_hazard_category_by_id.return_value = row
    repo.get_hazard_category_by_name.return_value = _row("已有类别")

    with pytest.raises(ValueError, match="已存在"):
        await service.update_hazard_category(row.id, "已有类别")

    repo.rename_hazard_category_in_hazards.assert_not_awaited()


async def test_rename_allows_name_held_by_soft_deleted_row() -> None:
    """被软删除的同名记录不挡路：删掉后改回旧名是合理操作。"""
    service, repo, _ = _service()
    row = _row("旧类别")
    repo.get_hazard_category_by_id.return_value = row
    repo.get_hazard_category_by_name.return_value = _row("回收类别", deleted=True)
    repo.rename_hazard_category_in_hazards.return_value = 0

    result = await service.update_hazard_category(row.id, "回收类别")

    assert result["name"] == "回收类别"
    repo.rename_hazard_category_in_hazards.assert_awaited_once_with("旧类别", "回收类别")


async def test_rename_to_same_name_skips_ledger_sync() -> None:
    """名称没变时直接返回，不触发全表台账更新。"""
    service, repo, _ = _service()
    row = _row("同名类别")
    repo.get_hazard_category_by_id.return_value = row

    result = await service.update_hazard_category(row.id, "同名类别")

    assert result["name"] == "同名类别"
    repo.update_hazard_category.assert_not_awaited()
    repo.rename_hazard_category_in_hazards.assert_not_awaited()


async def test_rename_missing_or_deleted_raises_lookup() -> None:
    """主键不存在或已软删除时抛 LookupError，供 API 层映射 404。"""
    service, repo, _ = _service()
    repo.get_hazard_category_by_id.return_value = None
    with pytest.raises(LookupError):
        await service.update_hazard_category(uuid.uuid4(), "新名")

    repo.get_hazard_category_by_id.return_value = _row("已删类别", deleted=True)
    with pytest.raises(LookupError):
        await service.update_hazard_category(uuid.uuid4(), "新名")


async def test_delete_soft_deletes_without_touching_ledger() -> None:
    """删除只置软删标记，历史台账保留原类别名（不做回填）。"""
    service, repo, audit = _service()
    row = _row("待删类别")
    repo.get_hazard_category_by_id.return_value = row

    result = await service.delete_hazard_category(row.id)

    assert result == {"id": str(row.id), "name": "待删类别", "sort_order": 100, "is_builtin": False}
    repo.update_hazard_category.assert_awaited_once_with(row.id, {"is_deleted": True, "is_active": False})
    repo.rename_hazard_category_in_hazards.assert_not_awaited()
    audit.assert_awaited_once()


async def test_delete_missing_or_deleted_raises_lookup() -> None:
    """删除一个不存在 / 已删除的类别抛 LookupError，不重复写库。"""
    service, repo, _ = _service()
    repo.get_hazard_category_by_id.return_value = _row("已删类别", deleted=True)

    with pytest.raises(LookupError):
        await service.delete_hazard_category(uuid.uuid4())

    repo.update_hazard_category.assert_not_awaited()
