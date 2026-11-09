"""隐患 / 危险源台账的人员引用解析。

匹配规则（与 Bitable 同步侧 ``IdentityResolver.resolve_by_name_strict`` 保持一致）：
- 姓名命中 0 人 → ``not_found``：保留姓名 + 「待确认」；
- 姓名命中 1 人 → ``matched``：直接关联（返回用户 UUID，不再显示待确认）；
- 姓名命中多人 → 用该条隐患的 ``department`` 做消歧（``department in user.department``）：
  过滤后恰好 1 人 → ``matched``；0 人或多人 → ``ambiguous``，保留姓名 + 「待确认」。

设计要点：
- 读取时解析，固定 **2 次查询**：已绑定 UUID 查一次 ``identity.users``，姓名集合再查一次，
  避免按行 N+1；读取本身不写库，唯一命中的 UUID 由写入路径与 Alembic 数据迁移落库。
- ``pending`` 表示「姓名无法唯一解析」（同名多人或查无此人），与列表
  ``person_match=pending`` 筛选项口径一致。
- 危险源辨识台账的责任人可能是纯文本（含「公司主要负责人」这类文案），
  只做展示层头像匹配，不产生 id。
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.models import HazardReport
from app.modules.safety.schemas.hazard_identifications import HazardIdentificationResponse
from app.modules.safety.schemas.hazards import HazardReportResponse
from app.modules.safety.schemas.person_ref import PersonRef
from app.platform.identity.models import User

logger = logging.getLogger(__name__)

# 姓名快照的分隔符：中英文逗号、顿号、分号、斜杠（历史 Bitable 数据混用）
_NAME_SEPARATOR_RE = re.compile(r"[,，、;；/]+")

# 只取展示所需列，避免误传手机号 / 邮箱等敏感字段
_PERSON_COLUMNS = (User.id, User.name, User.department, User.avatar_thumb, User.avatar_url)


def split_person_names(raw: Any) -> list[str]:
    """把逗号分隔的姓名快照拆成列表（保持原顺序，去掉空项）。"""
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [part.strip() for part in _NAME_SEPARATOR_RE.split(str(raw)) if part.strip()]


def normalize_person_id(raw: Any) -> uuid.UUID | None:
    """把 str / UUID 统一成 UUID，非法值返回 None（历史数据可能写入空串或脏值）。"""
    if isinstance(raw, uuid.UUID):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return uuid.UUID(raw.strip())
        except ValueError:
            return None
    return None


def _row_to_ref(row: Any) -> PersonRef:
    user_id, name, department, avatar_thumb, avatar_url = row
    return PersonRef(
        id=user_id,
        name=name,
        avatar_url=avatar_thumb or avatar_url or None,
        department=department,
    )


NameMatchStatus = Literal["matched", "not_found", "ambiguous"]


def resolve_person_name(
    candidates: Sequence[PersonRef],
    name: str | None,
    department_hint: str | None = None,
) -> tuple[PersonRef | None, NameMatchStatus]:
    """判定姓名是否唯一匹配（读时解析 / 筛选 / 测试共用同一口径）。

    Args:
        candidates: 系统内同名的全部用户。
        name: 台账里的姓名快照（仅用于空值判定）。
        department_hint: 台账责任部门，同名多人时用于消歧（``hint in user.department``）。

    Returns:
        (命中的用户, 三态)。``matched`` 才算唯一；``ambiguous`` / ``not_found`` 均不绑定。
    """
    if not (name or "").strip() or not candidates:
        return None, "not_found"
    if len(candidates) == 1:
        return candidates[0], "matched"
    hint = (department_hint or "").strip()
    if hint:
        filtered = [ref for ref in candidates if ref.department and hint in ref.department]
        if len(filtered) == 1:
            return filtered[0], "matched"
        if filtered:
            return None, "ambiguous"
    return None, "ambiguous"


@dataclass
class PersonLookup:
    """一页数据的人员索引：按 UUID 命中，或按姓名唯一（含部门消歧）命中。"""

    by_id: dict[str, PersonRef] = field(default_factory=dict)
    by_name: dict[str, list[PersonRef]] = field(default_factory=dict)

    def ref(
        self,
        person_id: Any = None,
        name: str | None = None,
        *,
        department_hint: str | None = None,
        bind_by_name: bool = True,
    ) -> PersonRef | None:
        """组装单个人员的引用；无 ID 也无姓名时返回 None。

        ``bind_by_name=False`` 用于纯文本责任人（危险源辨识台账）：只补头像，不产生 id。
        """
        clean_name = (name or "").strip() or None
        bound_id = normalize_person_id(person_id)
        if bound_id is not None:
            found = self.by_id.get(str(bound_id))
            return PersonRef(
                id=bound_id,
                name=clean_name or (found.name if found else None),
                avatar_url=found.avatar_url if found else None,
                department=found.department if found else None,
                pending=False,
            )
        if clean_name is None:
            return None
        candidates = self.by_name.get(clean_name, [])
        if not bind_by_name:
            only = candidates[0] if len(candidates) == 1 else None
            return PersonRef(
                name=clean_name,
                avatar_url=only.avatar_url if only else None,
                department=only.department if only else None,
                pending=True,
            )
        matched, _status = resolve_person_name(candidates, clean_name, department_hint)
        if matched is None:
            # 同名多人无法消歧 / 查无此人：只保留姓名，走首字头像 + 待确认
            return PersonRef(name=clean_name, pending=True)
        # 唯一匹配直接关联：返回 UUID 并清除待确认，读取本身不写库
        return PersonRef(
            id=matched.id,
            name=clean_name,
            avatar_url=matched.avatar_url,
            department=matched.department,
            pending=False,
        )


async def load_person_lookup(
    db: AsyncSession,
    ids: Iterable[Any] = (),
    names: Iterable[str | None] = (),
) -> PersonLookup:
    """批量查询人员索引：按 UUID 一次、按姓名一次。"""
    id_set = {value for value in (normalize_person_id(i) for i in ids) if value is not None}
    name_set = {n.strip() for n in names if n and n.strip()}
    lookup = PersonLookup()

    if id_set:
        rows = (await db.execute(select(*_PERSON_COLUMNS).where(User.is_deleted == False, User.id.in_(id_set)))).all()  # noqa: E712
        for row in rows:
            ref = _row_to_ref(row)
            if ref.id is not None:
                lookup.by_id[str(ref.id)] = ref

    if name_set:
        rows = (
            await db.execute(select(*_PERSON_COLUMNS).where(User.is_deleted == False, User.name.in_(name_set)))  # noqa: E712
        ).all()
        grouped: dict[str, list[PersonRef]] = {}
        for row in rows:
            ref = _row_to_ref(row)
            if ref.name:
                grouped.setdefault(ref.name, []).append(ref)
        # 保留全部同名候选，由 resolve_person_name 按部门消歧
        lookup.by_name = grouped

    return lookup


# ── 隐患台账（hazard_reports）─────────────────────────────────────────


def _hazard_bound_ids(item: HazardReport) -> list[Any]:
    ids: list[Any] = [item.discovered_by, item.rectification_responsible_person]
    ids.extend(item.rectification_responsible_person_ids or [])
    return [value for value in ids if value]


def _hazard_names(item: HazardReport) -> list[str]:
    names: list[str | None] = [item.discovered_by_name, item.rectification_responsible_person_name]
    names.extend(split_person_names(item.rectification_responsible_person_names))
    return [name for name in names if name]


def _responsible_entries(item: HazardReport) -> list[tuple[Any, str | None]]:
    """整改负责人：按 names 顺序与 ids 对齐（历史单人字段兜底）。"""
    names = split_person_names(item.rectification_responsible_person_names)
    raw_ids = item.rectification_responsible_person_ids or []
    ids = [value for value in (normalize_person_id(i) for i in raw_ids) if value is not None]
    if names:
        return [(ids[index] if index < len(ids) else None, name) for index, name in enumerate(names)]
    if ids:
        return [(value, None) for value in ids]
    if item.rectification_responsible_person or item.rectification_responsible_person_name:
        return [(item.rectification_responsible_person, item.rectification_responsible_person_name)]
    return []


def _to_hazard_response(item: HazardReport, lookup: PersonLookup) -> HazardReportResponse:
    response = HazardReportResponse.model_validate(item)
    # 责任部门作为同名消歧提示，与 Bitable 同步口径一致
    response.discovered_by_person = lookup.ref(
        item.discovered_by, item.discovered_by_name, department_hint=item.department
    )
    entries = _responsible_entries(item)
    response.rectification_responsible_persons = [
        ref
        for ref in (
            lookup.ref(person_id, name, department_hint=item.department) for person_id, name in entries
        )
        if ref is not None
    ]
    return response


async def to_hazard_responses(db: AsyncSession, items: Sequence[HazardReport]) -> list[HazardReportResponse]:
    """把隐患 ORM 行批量序列化为响应（含人员引用），固定 2 次查询。"""
    if not items:
        return []
    ids: list[Any] = []
    names: list[str] = []
    for item in items:
        ids.extend(_hazard_bound_ids(item))
        names.extend(_hazard_names(item))
    lookup = await load_person_lookup(db, ids=ids, names=names)
    return [_to_hazard_response(item, lookup) for item in items]


async def to_hazard_response(db: AsyncSession, item: HazardReport) -> HazardReportResponse:
    """单条隐患响应（详情 / 写操作返回值）。"""
    return (await to_hazard_responses(db, [item]))[0]


# ── 危险源辨识台账（hazard_identifications）────────────────────────────
# 老台账导入的「责任人」是纯文本（含风险等级派生文案，如「公司主要负责人」），
# 语义不一定是具体用户：只做读时展示匹配，不写 id 也不改库。


def _identification_person_refs(item: Any, lookup: PersonLookup) -> list[PersonRef]:
    names = split_person_names(item.responsible_person)
    return [
        ref for ref in (lookup.ref(None, name, bind_by_name=False) for name in names) if ref is not None
    ]


async def to_hazard_identification_responses(
    db: AsyncSession,
    items: Sequence[Any],
) -> list[HazardIdentificationResponse]:
    """危险源辨识批量序列化：责任人按姓名唯一命中补充头像，未命中保留纯文本。"""
    if not items:
        return []
    names: list[str] = []
    for item in items:
        names.extend(split_person_names(item.responsible_person))
    lookup = await load_person_lookup(db, names=names)
    responses: list[HazardIdentificationResponse] = []
    for item in items:
        response = HazardIdentificationResponse.model_validate(item)
        response.responsible_person_users = _identification_person_refs(item, lookup)
        responses.append(response)
    return responses


async def to_hazard_identification_response(db: AsyncSession, item: Any) -> HazardIdentificationResponse:
    """单条危险源辨识响应（详情）。"""
    return (await to_hazard_identification_responses(db, [item]))[0]
