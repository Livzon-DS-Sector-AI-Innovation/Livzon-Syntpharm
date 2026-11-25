"""部门联系人新增时按 HR 组织自动带出部门负责人。

覆盖两条规则：

- 只读解析只看 HR 组织：``leader_ids`` 里的空串必须过滤（多数部门都是 ``[""]``），
  且只有**部门全名精确命中**才采用，避免模糊匹配把别的部门的负责人串过来；
- 写库时 HR 解析到负责人就以 HR 为准（前端该字段只读），HR 没维护时保留客户端
  传值（前端此时已降级为可手选），避免「部门负责人审核」环节无人可审。
"""

from __future__ import annotations

import uuid
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr import public_api as hr_public_api
from app.modules.quality.qms.deviation_config_schemas import (
    DepartmentContactCreateRequest,
    DepartmentContactLeaderData,
)
from app.modules.quality.qms.deviation_config_service import DeviationConfigService

#: resolve_department_leader 只用 db 透传给 HR 接缝（已被 patch），这里给个占位对象
_PLACEHOLDER_DB = cast(AsyncSession, object())


def _service() -> DeviationConfigService:
    return DeviationConfigService(_PLACEHOLDER_DB)


def _patch_department(
    monkeypatch: pytest.MonkeyPatch,
    row: dict[str, Any] | None,
) -> None:
    async def fake_row(session: AsyncSession, name: str) -> dict[str, Any] | None:
        return row

    monkeypatch.setattr(hr_public_api, "find_department_row_by_name", fake_row)


async def test_resolve_leader_ignores_empty_leader_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """``leader_ids=[""]`` 视为没有负责人，且不应继续查档案。"""
    _patch_department(monkeypatch, {"id": "dept-1", "name": "101车间", "leader_ids": [""]})

    async def fail_profile(session: AsyncSession, open_id: str) -> dict[str, Any]:
        raise AssertionError("空 leader_ids 不应查询员工档案")

    monkeypatch.setattr(hr_public_api, "get_profile_by_open_id", fail_profile)

    leader = await _service().resolve_department_leader("101车间")

    assert leader.resolved is False
    assert leader.dept_head_profile_id is None


async def test_resolve_leader_requires_exact_department_name(monkeypatch: pytest.MonkeyPatch) -> None:
    """模糊命中（后缀/包含）不算：负责人不能从近似名的别的部门串过来。"""
    _patch_department(monkeypatch, {"id": "dept-1", "name": "质量保证部（旧）", "leader_ids": ["ou_x"]})

    leader = await _service().resolve_department_leader("质量保证部")

    assert leader.resolved is False
    assert leader.department == "质量保证部"


async def test_resolve_leader_returns_first_hr_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """有负责人时取第一个，返回 HR 档案 id / 姓名 / 头像（写库时再归一成账号 id）。"""
    _patch_department(monkeypatch, {"id": "dept-1", "name": "注册部", "leader_ids": ["ou_head", "ou_backup"]})
    seen: list[str] = []

    async def fake_profile(session: AsyncSession, open_id: str) -> dict[str, Any] | None:
        seen.append(open_id)
        return {"id": "profile-1", "name": "张三", "avatar_url": "https://example.com/a.png"}

    monkeypatch.setattr(hr_public_api, "get_profile_by_open_id", fake_profile)

    leader = await _service().resolve_department_leader("注册部")

    assert seen == ["ou_head"]
    assert leader.resolved is True
    assert leader.dept_head_profile_id == "profile-1"
    assert leader.dept_head_name == "张三"
    assert leader.dept_head_avatar == "https://example.com/a.png"


async def test_resolve_leader_stops_when_profile_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """负责人 open_id 在 HR 档案里查不到（已离职/未同步）时按未解析处理。"""
    _patch_department(monkeypatch, {"id": "dept-1", "name": "注册部", "leader_ids": ["ou_head"]})

    async def fake_profile(session: AsyncSession, open_id: str) -> None:
        return None

    monkeypatch.setattr(hr_public_api, "get_profile_by_open_id", fake_profile)

    leader = await _service().resolve_department_leader("注册部")

    assert leader.resolved is False
    assert leader.dept_head_profile_id is None


def test_apply_department_leader_overrides_client_value() -> None:
    """HR 有负责人：客户端传的值被覆盖（前端已把该字段锁成只读）。"""
    client_id = uuid.uuid4()
    profile_id = uuid.uuid4()
    payload = DepartmentContactCreateRequest(department="注册部", dept_head_id=client_id)
    leader = DepartmentContactLeaderData(
        department="注册部",
        resolved=True,
        dept_head_profile_id=str(profile_id),
        dept_head_name="张三",
    )

    updated = DeviationConfigService._apply_department_leader(payload, leader)

    assert updated.dept_head_id == profile_id
    assert payload.dept_head_id == client_id  # 入参不被就地修改


def test_apply_department_leader_keeps_client_value_when_unresolved() -> None:
    """HR 没维护负责人：保留手选值，不把用户填的负责人清空。"""
    client_id = uuid.uuid4()
    payload = DepartmentContactCreateRequest(department="101车间", dept_head_id=client_id)

    updated = DeviationConfigService._apply_department_leader(
        payload,
        DepartmentContactLeaderData(department="101车间"),
    )

    assert updated.dept_head_id == client_id
