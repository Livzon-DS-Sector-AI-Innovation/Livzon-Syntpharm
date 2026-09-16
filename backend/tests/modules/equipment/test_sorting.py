"""设备列表排序集成测试（Ticket 01 返工）。

真实调用 repo.get_equipments 并断言返回顺序。
测试跑在开发库上（savepoint 隔离，结束后回滚），因此：
- 造数用 keyword 前缀把本测试的行从 2972 行真实数据中过滤出来再断言；
- asset_no / feishu_department_id 必须避开真实数据，防止唯一约束冲突。
"""

import time
import uuid
from datetime import date
from typing import Any

import pytest

from app.modules.equipment.models.equipment import Equipment
from app.modules.equipment.repository.equipment import get_equipments
from app.platform.identity.models import Department

_KEYWORD = "排序集成测试"


async def _create_equipment(db, *, asset_no: str, name: str, **fields) -> Equipment:
    row = Equipment(asset_no=asset_no, name=f"{_KEYWORD}{name}", **fields)
    db.add(row)
    await db.flush()
    return row


async def _create_department(db, *, name: str) -> Department:
    row = Department(feishu_department_id=f"test_{uuid.uuid4().hex}", name=f"{_KEYWORD}{name}")
    db.add(row)
    await db.flush()
    return row


async def _list_sorted(db, sort_by: str, sort_order: str = "asc") -> list[Equipment]:
    rows, _ = await get_equipments(
        db, keyword=_KEYWORD, sort_by=sort_by, sort_order=sort_order, page=1, page_size=50
    )
    return rows


async def test_asset_no_natural_sort_asc(db_session):
    await _create_equipment(db_session, asset_no="9900002", name="B")
    await _create_equipment(db_session, asset_no="991", name="A")
    await _create_equipment(db_session, asset_no="9900001", name="C")
    await _create_equipment(db_session, asset_no="Z9900001", name="Z")

    rows = await _list_sorted(db_session, "asset_no", "asc")
    assert [e.asset_no for e in rows] == ["991", "9900001", "9900002", "Z9900001"]


async def test_asset_no_natural_sort_desc(db_session):
    await _create_equipment(db_session, asset_no="9900002", name="B")
    await _create_equipment(db_session, asset_no="991", name="A")
    await _create_equipment(db_session, asset_no="Z9900001", name="Z")

    rows = await _list_sorted(db_session, "asset_no", "desc")
    assert [e.asset_no for e in rows] == ["Z9900001", "9900002", "991"]


async def test_asset_no_without_trailing_digits_lands_in_last_bucket(db_session):
    """无尾数值的异常编号落独立桶置后，不抛错"""
    await _create_equipment(db_session, asset_no="990001", name="N")
    await _create_equipment(db_session, asset_no="EQX", name="X")

    rows = await _list_sorted(db_session, "asset_no", "asc")
    assert [e.asset_no for e in rows] == ["990001", "EQX"]


async def test_department_name_sort_matches_display_name(db_session):
    dept_a = await _create_department(db_session, name="AAA部门")
    dept_b = await _create_department(db_session, name="BBB部门")
    await _create_equipment(db_session, asset_no="990001", name="B", department_id=dept_b.id)
    await _create_equipment(db_session, asset_no="990002", name="A", department_id=dept_a.id)

    rows = await _list_sorted(db_session, "department_name", "asc")
    assert [e.department_id for e in rows] == [dept_a.id, dept_b.id]


async def test_status_sorts_by_business_priority(db_session):
    await _create_equipment(db_session, asset_no="990001", name="A", status="在用")
    await _create_equipment(db_session, asset_no="990002", name="B", status="维修中")
    await _create_equipment(db_session, asset_no="990003", name="C", status="备用")

    rows = await _list_sorted(db_session, "status", "asc")
    assert [e.status for e in rows] == ["维修中", "备用", "在用"]


async def test_nullable_commissioning_date_sorts_nulls_last(db_session):
    await _create_equipment(db_session, asset_no="990001", name="A", commissioning_date=date(2021, 1, 1))
    await _create_equipment(db_session, asset_no="990002", name="B", commissioning_date=date(2020, 1, 1))
    await _create_equipment(db_session, asset_no="990003", name="C")

    rows = await _list_sorted(db_session, "commissioning_date", "asc")
    assert [e.asset_no for e in rows] == ["990002", "990001", "990003"]


async def test_same_sort_key_order_is_deterministic_across_runs(db_session):
    for i in range(3):
        await _create_equipment(db_session, asset_no=f"99000{i}", name="同名设备")

    first, _ = await get_equipments(
        db_session, keyword=_KEYWORD, sort_by="name", sort_order="asc", page=1, page_size=50
    )
    second, _ = await get_equipments(
        db_session, keyword=_KEYWORD, sort_by="name", sort_order="asc", page=1, page_size=50
    )
    assert [e.id for e in first] == [e.id for e in second]


async def test_unknown_sort_by_raises(db_session):
    with pytest.raises(ValueError, match="不支持的排序字段"):
        await get_equipments(db_session, keyword=_KEYWORD, sort_by="hack", sort_order="asc", page=1, page_size=10)


async def test_api_rejects_unknown_sort_by(auth_client):
    resp = await auth_client.get("/api/v1/equipment/equipments", params={"sort_by": "hack"})
    assert resp.status_code == 422


async def test_api_rejects_invalid_sort_order(auth_client):
    resp = await auth_client.get("/api/v1/equipment/equipments", params={"sort_order": "descending"})
    assert resp.status_code == 422


async def test_asset_no_natural_sort_keeps_spec_mixed_format_chain(db_session):
    """D3 混排分段：前导零与位宽不影响数值序，字母前缀单独成桶且置后"""
    for asset_no in ["9900004", "09900002", "Z9900005", "009900001", "9900003"]:
        await _create_equipment(db_session, asset_no=asset_no, name="混排")

    rows = await _list_sorted(db_session, "asset_no", "asc")
    assert [e.asset_no for e in rows] == ["009900001", "09900002", "9900003", "9900004", "Z9900005"]


@pytest.mark.parametrize("column", ["current_cost", "book_value"])
@pytest.mark.parametrize("sort_order", ["asc", "desc"])
async def test_nullable_cost_columns_keep_nulls_last_in_both_directions(db_session, column, sort_order):
    await _create_equipment(db_session, asset_no="990001", name="A", **{column: 300.0})
    await _create_equipment(db_session, asset_no="990002", name="B", **{column: 100.0})
    await _create_equipment(db_session, asset_no="990003", name="C")
    await _create_equipment(db_session, asset_no="990004", name="D", **{column: 200.0})

    rows = await _list_sorted(db_session, column, sort_order)
    expected = [100.0, 200.0, 300.0, None] if sort_order == "asc" else [300.0, 200.0, 100.0, None]
    assert [getattr(e, column) for e in rows] == expected


async def test_tied_sort_key_pages_without_duplicates_or_gaps(db_session):
    """D6：排序值完全相同时，靠 Equipment.id tiebreak 保证跨页序列稳定且行守恒"""
    for i in range(5):
        await _create_equipment(db_session, asset_no=f"99000{i}", name="并列设备")

    single, total = await get_equipments(
        db_session, keyword=_KEYWORD, sort_by="name", sort_order="asc", page=1, page_size=50
    )
    assert total == len(single) == 5

    paged: list[Any] = []
    for page in range(1, 4):
        rows, _ = await get_equipments(
            db_session, keyword=_KEYWORD, sort_by="name", sort_order="asc", page=page, page_size=2
        )
        paged.extend(e.id for e in rows)
    assert paged == [e.id for e in single]


async def test_api_422_body_lists_supported_sort_fields(auth_client):
    resp = await auth_client.get("/api/v1/equipment/equipments", params={"sort_by": "drop_table"})
    assert resp.status_code == 422
    body = resp.text
    for field in ["asset_no", "book_value", "department_name"]:
        assert field in body, f"422 响应体未列出支持字段 {field}: {body}"


_DATASET_BASELINE_ROWS = 2000
# asset_no 走自然序、status 走业务优先级、name 是中文列（PG collation 与 Python 码点序不同），
# 三者的期望序列都不能用 Python sorted() 判定；department_name 来自 JOIN，不是模型属性。
# 这里只对日期/数值列做单调性复核，其余字段的序由专项用例断言。
_MONOTONIC_CHECKABLE = ["commissioning_date", "current_cost", "book_value", "created_at"]
_ALL_SORT_FIELDS = ["asset_no", "name", "commissioning_date", "current_cost", "book_value", "department_name",
                    "status", "created_at"]


@pytest.mark.parametrize("sort_by", _ALL_SORT_FIELDS)
@pytest.mark.parametrize("sort_order", ["asc", "desc"])
async def test_full_dataset_sort_stays_within_budget(db_session, sort_by, sort_order):
    """回归：2972 行规模下逐个白名单字段排序，首页取数无可测退化"""
    _, total = await get_equipments(db_session, sort_by=sort_by, sort_order=sort_order, page=1, page_size=1)
    if total < _DATASET_BASELINE_ROWS:
        pytest.skip(f"当前数据量 {total} 行，低于验收基线 {_DATASET_BASELINE_ROWS} 行，跳过性能断言")

    started = time.perf_counter()
    rows, total = await get_equipments(
        db_session, sort_by=sort_by, sort_order=sort_order, page=1, page_size=200
    )
    elapsed = time.perf_counter() - started

    assert len(rows) == 200
    assert elapsed < 2, f"{sort_by}/{sort_order} 排序首页耗时 {elapsed:.2f}s（{total} 行），疑似退化"

    if sort_by in _MONOTONIC_CHECKABLE:
        keys = [getattr(e, sort_by) for e in rows]
        # NULLS LAST 成立时任何方向的首页都不该出现空值
        assert all(k is not None for k in keys), f"{sort_by} {sort_order} 首页混入空值，NULLS LAST 未生效"
        assert keys == sorted(keys, reverse=sort_order == "desc"), f"{sort_by} {sort_order} 结果非单调"


async def test_full_dataset_status_pages_are_row_conserving(db_session):
    """status 只有 5 个取值、并列极多，用它做全量翻页才能真验证 offset 分页确定性"""
    _, total = await get_equipments(db_session, sort_by="status", sort_order="asc", page=1, page_size=1)
    if total < _DATASET_BASELINE_ROWS:
        pytest.skip(f"当前数据量 {total} 行，低于验收基线 {_DATASET_BASELINE_ROWS} 行，跳过全量翻页")

    seen: list = []
    page = 1
    while len(seen) < total:
        rows, _ = await get_equipments(db_session, sort_by="status", sort_order="asc", page=page, page_size=200)
        assert rows, f"第 {page} 页提前返回空，行未取尽"
        seen.extend(e.id for e in rows)
        page += 1

    assert len(seen) == total
    assert len(set(seen)) == total, "全量翻页出现重复行，tiebreak 未生效"
