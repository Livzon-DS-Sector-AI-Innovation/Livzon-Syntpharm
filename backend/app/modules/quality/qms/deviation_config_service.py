"""偏差模块组织配置服务：部门联系人、通知设置、部门周确认。

设计约束：

- README 式配置表（``quality.department_contacts``）是审核处理人的唯一来源，
  这里只做增删改查，不参与流转判定；
- 通知设置写 ``core.module_settings``（module=``quality-deviation``，key=``NOTIFY``），
  与 :mod:`deviation_notify` 的读取口径保持同一份 JSON；
- 周确认以 (department, week_key) 为唯一键，重复提交按 upsert 处理。
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Iterable, Sequence
from datetime import UTC, date, datetime
from typing import Literal, NamedTuple

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.config_model import ModuleSetting
from app.core.exceptions import BadRequestException, NotFoundException
from app.platform.identity.models import User

from . import deviation_notify as notify
from .deviation_config_schemas import (
    DepartmentContactCreateRequest,
    DepartmentContactItem,
    DepartmentContactUpdateRequest,
    MemberOption,
    NotifyEvents,
    NotifySettingsItem,
    NotifySettingsUpdateRequest,
    NotifyTargetItem,
    NotifyTestResultData,
    WeeklyConfirmationItem,
    WeeklyConfirmationListData,
    WeeklyConfirmationUpsertRequest,
)
from .deviation_department_models import DepartmentContact, DepartmentWeeklyConfirmation
from .deviation_flow import HandlerDirectory, HandlerRef

logger = logging.getLogger(__name__)

_PERSON_FIELDS = ("dept_head_id", "production_head_id", "quality_head_id", "qa_reviewer_id", "qa_head_id")
_TOKEN_FIELDS = ("qa_staff_ids", "gmp_staff_ids", "additional_contacts")

#: 处理人字段 → 角色名（通知自检展示用）
_ROLE_LABELS: dict[str, str] = {
    "dept_head_id": "部门负责人",
    "production_head_id": "生产负责人",
    "quality_head_id": "质量负责人",
    "qa_reviewer_id": "所属QA",
    "qa_head_id": "QA负责人",
}


def current_week_key(today: date | None = None) -> str:
    """返回 ISO 周标识，如 ``2026-W46``。"""
    target = today or date.today()
    year, week, _ = target.isocalendar()
    return f"{year}-W{week:02d}"


def _normalize_tokens(tokens: Iterable[str] | None) -> list[str]:
    """去空、去重、保序。"""
    result: list[str] = []
    for token in tokens or []:
        cleaned = str(token).strip()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def _qa_staff_snapshot(
    qa_reviewer_id: uuid.UUID | None,
    qa_head_id: uuid.UUID | None,
) -> list[str]:
    """兼容数组快照：``[0]=所属 QA``、``[1]=QA 负责人``，去空保序。

    ``qa_staff_ids`` 已被两个独立字段取代，但导入脚本与历史读取方仍按位置取值，
    因此保存时回写一份快照，避免旧读取方读到过期数据。
    """
    return [str(value) for value in (qa_reviewer_id, qa_head_id) if value is not None]


class DeviationConfigService:
    """部门联系人 / 通知 / 周确认。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 部门联系人 ────────────────────────────────────────────────────

    async def list_contacts(self, keyword: str | None = None) -> list[DepartmentContactItem]:
        """列出全部启用中的部门联系人，按部门名排序。"""
        stmt = select(DepartmentContact).where(DepartmentContact.is_deleted.is_(False))  # noqa: E712
        if keyword and keyword.strip():
            stmt = stmt.where(DepartmentContact.department.ilike(f"%{keyword.strip()}%"))
        rows = (await self.db.execute(stmt.order_by(DepartmentContact.department.asc()))).scalars().all()
        names = await self._load_people(rows)
        return [self._to_item(row, names) for row in rows]

    async def create_contact(
        self,
        payload: DepartmentContactCreateRequest,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> DepartmentContactItem:
        """新增部门联系人；同名软删除行直接复用，避免唯一约束冲突。"""
        department = payload.department.strip()
        if not department:
            raise BadRequestException("请填写部门名称")
        await self._assert_users_exist(self._person_ids(payload))

        existing = (
            await self.db.execute(select(DepartmentContact).where(DepartmentContact.department == department))
        ).scalar_one_or_none()
        if existing is not None and not existing.is_deleted:
            raise BadRequestException("该部门已配置联系人，请直接编辑")

        if existing is not None:
            row = existing
            row.is_deleted = False
        else:
            row = DepartmentContact(department=department)
            self.db.add(row)

        self._apply_payload(row, payload)
        row.created_by = row.created_by or actor_id
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        logger.info("department contact created", extra={"app_module": "quality", "department": department})
        return self._to_item(row, await self._load_people([row]))

    async def update_contact(
        self,
        contact_id: uuid.UUID,
        payload: DepartmentContactUpdateRequest,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> DepartmentContactItem:
        """编辑部门联系人。部门名称为唯一键，不在本接口修改。"""
        row = await self._get_contact(contact_id)
        await self._assert_users_exist(self._person_ids(payload))

        fields = payload.model_dump(exclude_unset=True)
        for field_name in _PERSON_FIELDS:
            if field_name in fields:
                setattr(row, field_name, fields[field_name])
        for field_name in _TOKEN_FIELDS:
            if field_name in fields:
                setattr(row, field_name, _normalize_tokens(fields[field_name]))
        # 两个独立字段权威，数组只作兼容快照；只要 QA 字段变更就重建快照
        if "qa_reviewer_id" in fields or "qa_head_id" in fields:
            row.qa_staff_ids = _qa_staff_snapshot(row.qa_reviewer_id, row.qa_head_id)
        if "is_production_workshop" in fields and fields["is_production_workshop"] is not None:
            row.is_production_workshop = bool(fields["is_production_workshop"])
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)
        return self._to_item(row, await self._load_people([row]))

    async def delete_contact(self, contact_id: uuid.UUID, *, actor_id: uuid.UUID | None = None) -> uuid.UUID:
        """软删除部门联系人。"""
        row = await self._get_contact(contact_id)
        row.is_deleted = True
        row.updated_by = actor_id
        await self.db.commit()
        logger.info("department contact deleted", extra={"app_module": "quality", "department": row.department})
        return row.id

    async def member_options(self, keyword: str | None = None, limit: int = 50) -> list[MemberOption]:
        """人员候选（姓名 + 部门），供配置页下拉与搜索。"""
        stmt = select(User.id, User.name, User.department).where(User.is_deleted.is_(False))  # noqa: E712
        if keyword and keyword.strip():
            pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(or_(User.name.ilike(pattern), User.department.ilike(pattern)))
        rows = (await self.db.execute(stmt.order_by(User.name.asc()).limit(limit))).all()
        return [MemberOption(value=str(row.id), label=row.name or "-", description=row.department) for row in rows]

    # ── 通知设置 ──────────────────────────────────────────────────────

    async def get_notify_settings(self) -> NotifySettingsItem:
        """读取通知设置（缺省全开、无群聊）。"""
        settings = await notify.load_notify_settings()
        events = NotifyEvents(**{key: settings.enabled_for(key) for key in NotifyEvents.model_fields})
        return NotifySettingsItem(enabled=settings.enabled, chat_id=settings.chat_id, events=events)

    async def update_notify_settings(
        self,
        payload: NotifySettingsUpdateRequest,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> NotifySettingsItem:
        """写入通知设置（module=quality-deviation / key=NOTIFY，JSON 字符串）。"""
        value = json.dumps(
            {
                "enabled": payload.enabled,
                "chat_id": payload.chat_id.strip(),
                "events": payload.events.model_dump(),
            },
            ensure_ascii=False,
        )
        row = (
            await self.db.execute(
                select(ModuleSetting).where(
                    ModuleSetting.module == notify.MODULE,
                    ModuleSetting.key == notify.SETTING_KEY,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = ModuleSetting(
                module=notify.MODULE,
                key=notify.SETTING_KEY,
                value=value,
                value_type="json",
                description="偏差台账通知开关与群聊接收方",
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.db.add(row)
        else:
            row.is_deleted = False
            row.value = value
            row.value_type = "json"
            row.updated_by = actor_id
        await self.db.commit()
        return await self.get_notify_settings()

    async def send_notify_test(
        self,
        *,
        actor_id: uuid.UUID | None = None,
        actor_name: str = "",
    ) -> NotifyTestResultData:
        """给当前账号发测试卡片，并汇总各环节处理人的飞书绑定情况（自检用）。"""
        settings = get_settings()
        platform_ready = bool(settings.feishu.platform.app_id and settings.feishu.platform.app_secret)
        actor = await self.db.get(User, actor_id) if actor_id is not None else None
        self_ref = (
            HandlerRef(
                id=actor.id,
                name=actor.name or actor_name or "-",
                feishu_open_id=actor.feishu_open_id,
                feishu_user_id=actor.feishu_user_id,
            )
            if actor is not None
            else None
        )
        contacts = await self._notify_targets()

        sent = False
        if not platform_ready:
            error: str | None = "平台飞书应用凭证未配置（FEISHU__PLATFORM__APP_ID / APP_SECRET）"
        elif self_ref is None or not self_ref.feishu_id:
            error = "当前账号未绑定飞书标识，请先用飞书扫码登录一次后再试"
        else:
            error = None
            try:
                await notify.send_test_card(self_ref, operator_name=actor_name or self_ref.name)
                sent = True
            except Exception as exc:  # noqa: BLE001 - 自检接口要把失败原因返回给用户
                logger.warning(
                    "deviation notify test failed",
                    extra={"app_module": "quality", "user_id": str(actor_id)},
                    exc_info=True,
                )
                error = f"发送失败：{exc}"

        unbound = [item for item in contacts if not item.bound]
        if sent:
            message = "测试卡片已发送，请在飞书中查看"
            if unbound:
                message += f"；另有 {len(unbound)} 位环节处理人未绑定飞书，收不到流转通知"
        else:
            message = error or "测试卡片未发送"

        return NotifyTestResultData(
            platform_ready=platform_ready,
            self_bound=bool(self_ref and self_ref.feishu_id),
            sent=sent,
            error=error,
            message=message,
            contacts=contacts,
        )

    async def _notify_targets(self) -> list[NotifyTargetItem]:
        """各环节处理人的飞书绑定情况（按部门 + 角色，去重）。"""
        rows = (
            (
                await self.db.execute(
                    select(DepartmentContact).where(DepartmentContact.is_deleted.is_(False))  # noqa: E712
                )
            )
            .scalars()
            .all()
        )
        contacts = {row.department: row for row in rows if row.department}
        directory = await HandlerDirectory.load_for_ids(self.db, contacts)
        targets: list[NotifyTargetItem] = []
        seen: set[tuple[uuid.UUID, str]] = set()
        for department, contact in contacts.items():
            for field_name, role_label in _ROLE_LABELS.items():
                user_id = getattr(contact, field_name, None)
                if user_id is None or (user_id, role_label) in seen:
                    continue
                ref = directory.ref(user_id)
                if ref is None:
                    continue
                seen.add((user_id, role_label))
                targets.append(
                    NotifyTargetItem(
                        user_id=ref.id,
                        name=ref.name,
                        role=role_label,
                        department=department,
                        bound=bool(ref.feishu_id),
                    )
                )
        return targets

    # ── 部门周确认 ────────────────────────────────────────────────────

    async def list_weekly_confirmations(self, week_key: str | None = None) -> WeeklyConfirmationListData:
        """按周列出所有部门确认情况；未确认的部门也会返回（confirmed=false）。"""
        week = (week_key or "").strip() or current_week_key()
        contacts = (
            (
                await self.db.execute(
                    select(DepartmentContact)
                    .where(DepartmentContact.is_deleted.is_(False))  # noqa: E712
                    .order_by(DepartmentContact.department.asc())
                )
            )
            .scalars()
            .all()
        )
        rows = (
            (
                await self.db.execute(
                    select(DepartmentWeeklyConfirmation).where(
                        DepartmentWeeklyConfirmation.week_key == week,
                        DepartmentWeeklyConfirmation.is_deleted.is_(False),  # noqa: E712
                    )
                )
            )
            .scalars()
            .all()
        )
        by_department = {row.department: row for row in rows}
        names = await self._load_people(
            [],
            extra_ids=[row.confirmed_by_id for row in rows if row.confirmed_by_id],
        )

        items: list[WeeklyConfirmationItem] = []
        departments = [contact.department for contact in contacts]
        for department in departments:
            confirmation = by_department.get(department)
            items.append(
                WeeklyConfirmationItem(
                    department=department,
                    is_production_workshop=bool(
                        next((c.is_production_workshop for c in contacts if c.department == department), False)
                    ),
                    week_key=week,
                    confirmed=confirmation is not None,
                    production_status=_production_status(confirmation.production_status) if confirmation else None,
                    deviation_status=_deviation_status(confirmation.deviation_status) if confirmation else None,
                    confirmed_by_id=confirmation.confirmed_by_id if confirmation else None,
                    confirmed_by_name=names.get(str(confirmation.confirmed_by_id))
                    if confirmation and confirmation.confirmed_by_id
                    else None,
                    confirmed_at=confirmation.confirmed_at if confirmation else None,
                )
            )
        # 已确认但部门联系人已被删除的历史记录也要能看到
        for department, confirmation in by_department.items():
            if department in departments:
                continue
            items.append(
                WeeklyConfirmationItem(
                    department=department,
                    week_key=week,
                    confirmed=True,
                    production_status=_production_status(confirmation.production_status),
                    deviation_status=_deviation_status(confirmation.deviation_status),
                    confirmed_by_id=confirmation.confirmed_by_id,
                    confirmed_by_name=names.get(str(confirmation.confirmed_by_id))
                    if confirmation.confirmed_by_id
                    else None,
                    confirmed_at=confirmation.confirmed_at,
                )
            )

        return WeeklyConfirmationListData(
            week_key=week,
            items=items,
            confirmed_count=sum(1 for item in items if item.confirmed),
            total=len(items),
        )

    async def upsert_weekly_confirmation(
        self,
        payload: WeeklyConfirmationUpsertRequest,
        *,
        actor_id: uuid.UUID | None = None,
    ) -> WeeklyConfirmationItem:
        """提交本部门本周确认；重复提交覆盖上一次结果。"""
        department = payload.department.strip()
        if not department:
            raise BadRequestException("请选择部门")
        week = payload.week_key.strip() or current_week_key()

        row = (
            await self.db.execute(
                select(DepartmentWeeklyConfirmation).where(
                    DepartmentWeeklyConfirmation.department == department,
                    DepartmentWeeklyConfirmation.week_key == week,
                    DepartmentWeeklyConfirmation.is_deleted.is_(False),  # noqa: E712
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = DepartmentWeeklyConfirmation(department=department, week_key=week)
            self.db.add(row)
        row.production_status = payload.production_status
        row.deviation_status = payload.deviation_status
        row.confirmed_by_id = actor_id
        row.confirmed_at = datetime.now(UTC)
        row.updated_by = actor_id
        await self.db.commit()
        await self.db.refresh(row)

        names = await self._load_people([], extra_ids=[row.confirmed_by_id] if row.confirmed_by_id else [])
        contact = (
            await self.db.execute(
                select(DepartmentContact).where(
                    DepartmentContact.department == department,
                    DepartmentContact.is_deleted.is_(False),  # noqa: E712
                )
            )
        ).scalar_one_or_none()
        return WeeklyConfirmationItem(
            department=row.department,
            is_production_workshop=bool(contact.is_production_workshop) if contact else False,
            week_key=row.week_key,
            confirmed=True,
            production_status=_production_status(row.production_status),
            deviation_status=_deviation_status(row.deviation_status),
            confirmed_by_id=row.confirmed_by_id,
            confirmed_by_name=names.get(str(row.confirmed_by_id)) if row.confirmed_by_id else None,
            confirmed_at=row.confirmed_at,
        )

    async def get_weekly_confirmation(
        self,
        department: str,
        week_key: str | None = None,
    ) -> DepartmentWeeklyConfirmation | None:
        """周提醒任务使用：指定部门某一周的确认记录（无则 None）。"""
        week = (week_key or "").strip() or current_week_key()
        return (
            await self.db.execute(
                select(DepartmentWeeklyConfirmation).where(
                    DepartmentWeeklyConfirmation.department == department,
                    DepartmentWeeklyConfirmation.week_key == week,
                    DepartmentWeeklyConfirmation.is_deleted.is_(False),  # noqa: E712
                )
            )
        ).scalar_one_or_none()

    # ── 内部 ──────────────────────────────────────────────────────────

    async def _get_contact(self, contact_id: uuid.UUID) -> DepartmentContact:
        row = (
            await self.db.execute(
                select(DepartmentContact).where(
                    DepartmentContact.id == contact_id,
                    DepartmentContact.is_deleted.is_(False),  # noqa: E712
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise NotFoundException("部门联系人配置不存在")
        return row

    @staticmethod
    def _person_ids(
        payload: DepartmentContactCreateRequest | DepartmentContactUpdateRequest,
    ) -> list[uuid.UUID]:
        return [
            getattr(payload, field_name)
            for field_name in _PERSON_FIELDS
            if getattr(payload, field_name, None) is not None
        ]

    async def _assert_users_exist(self, user_ids: Sequence[uuid.UUID]) -> None:
        """外键字段先校验，避免提交时抛 IntegrityError 变成 500。"""
        if not user_ids:
            return
        rows = await self.db.execute(
            select(User.id).where(User.id.in_(set(user_ids)), User.is_deleted.is_(False))  # noqa: E712
        )
        found = {row.id for row in rows.all()}
        missing = [str(user_id) for user_id in user_ids if user_id not in found]
        if missing:
            raise BadRequestException("所选人员不存在或已停用")

    @staticmethod
    def _apply_payload(row: DepartmentContact, payload: DepartmentContactCreateRequest) -> None:
        row.dept_head_id = payload.dept_head_id
        row.production_head_id = payload.production_head_id
        row.quality_head_id = payload.quality_head_id
        row.qa_reviewer_id = payload.qa_reviewer_id
        row.qa_head_id = payload.qa_head_id
        # 新字段优先；两者都为空时保留调用方传入的历史数组（兼容导入脚本）
        row.qa_staff_ids = _qa_staff_snapshot(payload.qa_reviewer_id, payload.qa_head_id) or _normalize_tokens(
            payload.qa_staff_ids
        )
        row.gmp_staff_ids = _normalize_tokens(payload.gmp_staff_ids)
        row.additional_contacts = _normalize_tokens(payload.additional_contacts)
        row.is_production_workshop = bool(payload.is_production_workshop)

    def _to_item(self, row: DepartmentContact, people: dict[str, _Person]) -> DepartmentContactItem:
        return DepartmentContactItem(
            id=row.id,
            department=row.department,
            dept_head_id=row.dept_head_id,
            dept_head_name=_person_name(people, row.dept_head_id),
            dept_head_avatar=_person_avatar(people, row.dept_head_id),
            production_head_id=row.production_head_id,
            production_head_name=_person_name(people, row.production_head_id),
            production_head_avatar=_person_avatar(people, row.production_head_id),
            quality_head_id=row.quality_head_id,
            quality_head_name=_person_name(people, row.quality_head_id),
            quality_head_avatar=_person_avatar(people, row.quality_head_id),
            qa_reviewer_id=row.qa_reviewer_id,
            qa_reviewer_name=_person_name(people, row.qa_reviewer_id),
            qa_reviewer_avatar=_person_avatar(people, row.qa_reviewer_id),
            qa_head_id=row.qa_head_id,
            qa_head_name=_person_name(people, row.qa_head_id),
            qa_head_avatar=_person_avatar(people, row.qa_head_id),
            qa_staff_ids=list(row.qa_staff_ids or []),
            qa_staff_names=[
                _person_name(people, token, fallback=str(token)) or "-" for token in (row.qa_staff_ids or [])
            ],
            qa_staff_avatars=[_person_avatar(people, token) for token in (row.qa_staff_ids or [])],
            gmp_staff_ids=list(row.gmp_staff_ids or []),
            gmp_staff_names=[
                _person_name(people, token, fallback=str(token)) or "-" for token in (row.gmp_staff_ids or [])
            ],
            gmp_staff_avatars=[_person_avatar(people, token) for token in (row.gmp_staff_ids or [])],
            additional_contacts=list(row.additional_contacts or []),
            additional_contact_names=[
                _person_name(people, token, fallback=str(token)) or "-" for token in (row.additional_contacts or [])
            ],
            additional_contact_avatars=[_person_avatar(people, token) for token in (row.additional_contacts or [])],
            is_production_workshop=bool(row.is_production_workshop),
            updated_at=row.updated_at,
        )

    async def _load_people(
        self,
        rows: Iterable[DepartmentContact] | None = None,
        *,
        extra_ids: Iterable[uuid.UUID] | None = None,
    ) -> dict[str, _Person]:
        """一次查询解析所有人员（UUID 与飞书 open_id 混存都兼容），返回 token→(姓名, 头像)。"""
        uuid_ids: set[uuid.UUID] = set(extra_ids or ())
        text_tokens: set[str] = set()
        for row in rows or ():
            for field_name in _PERSON_FIELDS:
                value = getattr(row, field_name)
                if value is not None:
                    uuid_ids.add(value)
            for field_name in _TOKEN_FIELDS:
                for token in getattr(row, field_name) or []:
                    cleaned = str(token).strip()
                    if not cleaned:
                        continue
                    try:
                        uuid_ids.add(uuid.UUID(cleaned))
                    except ValueError:
                        text_tokens.add(cleaned)

        conditions = []
        if uuid_ids:
            conditions.append(User.id.in_(uuid_ids))
        if text_tokens:
            # 历史 token 可能存成 open_id，也可能落在 feishu_user_id，两边都查
            conditions.append(User.feishu_open_id.in_(text_tokens))
            conditions.append(User.feishu_user_id.in_(text_tokens))
        if not conditions:
            return {}

        user_rows = (
            await self.db.execute(
                select(
                    User.id,
                    User.name,
                    User.feishu_open_id,
                    User.feishu_user_id,
                    User.avatar_thumb,
                    User.avatar_url,
                ).where(
                    User.is_deleted.is_(False),  # noqa: E712
                    or_(*conditions),
                )
            )
        ).all()
        people: dict[str, _Person] = {}
        for user_row in user_rows:
            person = _Person(name=user_row.name or "-", avatar_url=user_row.avatar_thumb or user_row.avatar_url)
            people[str(user_row.id)] = person
            for token in (user_row.feishu_open_id, user_row.feishu_user_id):
                if token:
                    people.setdefault(token, person)
        return people


class _Person(NamedTuple):
    """人员展示信息：姓名 + 头像（飞书缩略图优先）。"""

    name: str
    avatar_url: str | None = None


def _person_name(
    people: dict[str, _Person],
    token: str | uuid.UUID | None,
    *,
    fallback: str | None = None,
) -> str | None:
    if not token:
        return None
    person = people.get(str(token))
    return person.name if person else fallback


def _person_avatar(people: dict[str, _Person], token: str | uuid.UUID | None) -> str | None:
    if not token:
        return None
    person = people.get(str(token))
    return person.avatar_url if person else None


def _production_status(value: str | None) -> Literal["production", "stopped"] | None:
    """库里的历史值收敛到枚举，未知值按空处理。"""
    if value == "production":
        return "production"
    if value == "stopped":
        return "stopped"
    return None


def _deviation_status(value: str | None) -> Literal["submitted", "unsubmitted"] | None:
    """库里的历史值收敛到枚举，未知值按空处理。"""
    if value == "submitted":
        return "submitted"
    if value == "unsubmitted":
        return "unsubmitted"
    return None


__all__ = ["DeviationConfigService", "current_week_key"]
