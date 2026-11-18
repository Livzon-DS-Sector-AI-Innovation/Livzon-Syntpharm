"""隐患通知身份解析器。

职责：将隐患记录中的姓名/部门文本字段解析为飞书 open_id，
     供 send_user_card() 发送 DM 通知。

#219：数据源改为 HR 主数据（``hr.employee_profiles`` / ``hr.departments``），
统一经 HR ``public_api`` 只读访问，不再读 ``identity.users`` /
``identity.departments``（后者已下线）。解析结果只依赖 ``open_id``。

解析链路：
  ① 责任人        ← rectification_responsible_person_name
  ② 部门负责人    ← department → 部门 leader_ids
  ③ 分管领导      ← department → 父部门 leader_ids
  ④ 隐患发现人    ← discovered_by_name / discovered_by
  ⑤ 分管安全员    ← department → DEPT_CONFIG safety_officer
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from app.modules.safety.feishu.dept_config import DEPARTMENT_CONFIG

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.safety.models import HazardReport

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 返回类型
# ═══════════════════════════════════════════════════════════════


@dataclass
class ResolvedPerson:
    """身份解析结果 — 包含发送飞书通知所需的全部标识。"""

    open_id: str
    user_id: str
    name: str
    department: str | None = None
    id: str = ""  # identity.users UUID

    def to_dict(self) -> dict[str, str | None]:
        return {
            "open_id": self.open_id,
            "user_id": self.user_id,
            "name": self.name,
            "department": self.department,
            "id": self.id or None,
        }

    def __repr__(self) -> str:
        return f"ResolvedPerson(open_id={self.open_id!r}, user_id={self.user_id!r}, name={self.name!r})"


NameMatchStatus = Literal["matched", "not_found", "ambiguous"]


@dataclass
class NameMatch:
    """严格姓名匹配结果（三态）。

    status:
      - matched    唯一命中，person 可用
      - not_found  查无此人（含姓名为空），person 为 None
      - ambiguous  同名多人且无法唯一消歧，person 为 None，candidates 供人工核对

    strict 语义：宁可留空交给人工，也不"取第一个"造成静默错配。
    """

    status: NameMatchStatus
    name: str = ""
    person: ResolvedPerson | None = None
    candidates: list[ResolvedPerson] = field(default_factory=list)

    @property
    def is_matched(self) -> bool:
        return self.status == "matched" and self.person is not None


# ═══════════════════════════════════════════════════════════════
# 身份解析器
# ═══════════════════════════════════════════════════════════════


class IdentityResolver:
    """隐患通知身份解析器。

    用法：
        resolver = IdentityResolver(session)
        person = await resolver.resolve_department_leader("生产部")
        if person:
            await send_user_card(open_id=person.open_id, ...)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ── 公开方法 ──────────────────────────────────────────────

    async def resolve_by_name(
        self,
        name: str,
        department_hint: str | None = None,
    ) -> ResolvedPerson | None:
        """按姓名查找用户 → open_id。

        Args:
            name: 用户姓名（如 Bitable「责任人」字段值）
            department_hint: 部门提示，多命中时用于消歧

        Returns:
            ResolvedPerson | None
        """
        if not name or not name.strip():
            logger.warning("resolve_by_name: name 为空，跳过")
            return None

        name = name.strip()
        user = await self._find_user_by_name(name, department_hint)
        if user is None:
            logger.warning("resolve_by_name: 未找到用户 name=%r", name)
            return None

        return self._user_to_person(user)

    async def resolve_by_name_strict(
        self,
        name: str,
        department_hint: str | None = None,
    ) -> NameMatch:
        """严格按姓名匹配，用于写入业务外键（隐患检查人员 / 整改责任人）。

        与 resolve_by_name 的差异：同名多人且部门无法唯一消歧时不再"取第一个"，
        而是返回 ambiguous（person 为空），由调用方留空并转人工指定。
        """
        raw = (name or "").strip()
        if not raw:
            return NameMatch(status="not_found", name="")

        users = await self._find_users_by_name(raw)
        if not users:
            logger.warning("resolve_by_name_strict: 未找到用户 name=%r", raw)
            return NameMatch(status="not_found", name=raw)

        if len(users) == 1:
            return NameMatch(status="matched", person=self._user_to_person(users[0]), name=raw)

        if department_hint:
            filtered = [
                u
                for u in users
                if department_hint in "".join(str(item) for item in (u.get("department_names") or []))
            ]
            if len(filtered) == 1:
                logger.info(
                    "resolve_by_name_strict: %r 同名 %d 人，部门消歧 → %r",
                    raw,
                    len(users),
                    filtered[0].get("name"),
                )
                return NameMatch(status="matched", person=self._user_to_person(filtered[0]), name=raw)
            if filtered:
                users = filtered

        logger.warning(
            "resolve_by_name_strict: %r 同名 %d 人无法唯一消歧，拒绝绑定（待人工指定）",
            raw,
            len(users),
        )
        return NameMatch(
            status="ambiguous",
            name=raw,
            candidates=[self._user_to_person(u) for u in users],
        )

    async def resolve_department_leader(
        self,
        department_name: str,
    ) -> ResolvedPerson | None:
        """按部门名称查找部门负责人 → open_id。

        查找链路（配置优先）：
          1. DEPT_CONFIG → 命中则用 leader 姓名 → resolve_by_name
          2. identity.departments → 匹配部门 → 取 leader_user_id → _find_user_by_user_id

        Args:
            department_name: 部门名称（如 HazardReport.department）

        Returns:
            ResolvedPerson | None
        """
        dept = await self._find_department_by_name(department_name)
        if dept is None:
            logger.warning("resolve_department_leader: 未找到部门 %r", department_name)
            return None
        dept_name = str(dept.get("name") or "")

        # ── 配置优先：Bitable 人工维护的部门负责人 ──
        config = DEPARTMENT_CONFIG.get(dept_name)
        if config and config.get("leader"):
            leader_name = config["leader"]
            logger.info(
                "resolve_department_leader: %r → config leader %r",
                department_name,
                leader_name,
            )
            return await self.resolve_by_name(leader_name, department_hint=dept_name)

        # ── 回退：HR 部门主数据的 leader_ids（飞书 open_id 列表） ──
        leader_ids = [str(item) for item in (dept.get("leader_ids") or []) if item]
        leader: dict[str, Any] | None = None
        for leader_id in leader_ids:
            leader = await self._find_user_by_user_id(leader_id)
            if leader is not None:
                break
        if leader is None:
            logger.warning(
                "resolve_department_leader: 部门 %r 无可用负责人（leader_ids=%s）",
                dept_name,
                leader_ids,
            )
            return None

        logger.info(
            "resolve_department_leader: %r → %r (leader of %r)",
            department_name,
            leader.get("name"),
            dept_name,
        )
        return self._user_to_person(leader, dept_name)

    async def resolve_supervising_leader(
        self,
        department_name: str,
    ) -> ResolvedPerson | None:
        """按部门名称查找分管领导 → open_id。

        查找链路（配置优先）：
          1. DEPT_CONFIG → 命中且有 supervisor → 用 supervisor 姓名 → resolve_by_name
          2. identity.departments → 父部门 leader → _find_user_by_user_id

        Args:
            department_name: 部门名称（如 HazardReport.department）

        Returns:
            ResolvedPerson | None
        """
        dept = await self._find_department_by_name(department_name)
        if dept is None:
            logger.warning("resolve_supervising_leader: 未找到部门 %r", department_name)
            return None

        # ── 配置优先：Bitable 人工维护的分管领导 ──
        dept_name = str(dept.get("name") or "")
        config = DEPARTMENT_CONFIG.get(dept_name)
        if config and config.get("supervisor"):
            supervisor_name = config["supervisor"]
            logger.info(
                "resolve_supervising_leader: %r → config supervisor %r",
                department_name,
                supervisor_name,
            )
            return await self.resolve_by_name(supervisor_name, department_hint=dept_name)

        # ── 回退：HR 部门主数据的父部门 leader_ids ──
        parent_feishu_id = str(dept.get("parent_feishu_department_id") or "")
        if not parent_feishu_id:
            logger.info("resolve_supervising_leader: %r 无父部门，无分管领导", dept_name)
            return None

        parent_dept = await self._find_department_by_id(parent_feishu_id)
        if parent_dept is None:
            logger.warning(
                "resolve_supervising_leader: 父部门 %r 不在 hr.departments",
                parent_feishu_id,
            )
            return None

        leader_ids = [str(item) for item in (parent_dept.get("leader_ids") or []) if item]
        leader: dict[str, Any] | None = None
        for leader_id in leader_ids:
            leader = await self._find_user_by_user_id(leader_id)
            if leader is not None:
                break
        if leader is None:
            logger.warning(
                "resolve_supervising_leader: 父部门 %r 无可用负责人（leader_ids=%s）",
                parent_dept.get("name"),
                leader_ids,
            )
            return None

        logger.info(
            "resolve_supervising_leader: %r → 父部门 %r → leader %r",
            department_name,
            parent_dept.get("name"),
            leader.get("name"),
        )
        return self._user_to_person(leader, str(parent_dept.get("name") or ""))

    async def resolve_safety_officer(
        self,
        department_name: str,
    ) -> ResolvedPerson | None:
        """按部门名称查找分管安全员 → open_id。

        查找链路（仅配置）：
          1. DEPT_CONFIG → 命中且有 safety_officer → 用姓名 → resolve_by_name
          2. 无配置 → 返回 None（不报错，部门可能暂未指定安全员）

        Args:
            department_name: 部门名称（如 HazardReport.department）

        Returns:
            ResolvedPerson | None
        """
        dept = await self._find_department_by_name(department_name)
        if dept is None:
            logger.warning("resolve_safety_officer: 未找到部门 %r", department_name)
            return None

        dept_name = str(dept.get("name") or "")
        config = DEPARTMENT_CONFIG.get(dept_name)
        if not config or not config.get("safety_officer"):
            logger.info("resolve_safety_officer: 部门 %r 未配置安全员", dept_name)
            return None

        officer_name = config["safety_officer"]
        logger.info(
            "resolve_safety_officer: %r → config safety_officer %r",
            department_name,
            officer_name,
        )
        return await self.resolve_by_name(officer_name, department_hint=dept_name)

    # ── 隐患模型便捷方法 ──────────────────────────────────────

    async def resolve_responsible_person(
        self,
        hazard: HazardReport,
    ) -> ResolvedPerson | None:
        """① 责任人：rectification_responsible_person_name → open_id。"""
        if not hazard.rectification_responsible_person_name:
            logger.warning(
                "hazard %s: rectification_responsible_person_name 为空",
                hazard.hazard_no,
            )
            return None
        return await self.resolve_by_name(
            hazard.rectification_responsible_person_name,
            department_hint=hazard.department,
        )

    async def resolve_hazard_department_leader(
        self,
        hazard: HazardReport,
    ) -> ResolvedPerson | None:
        """② 部门负责人：hazard.department → 部门 leader → open_id。"""
        if not hazard.department:
            logger.warning(
                "hazard %s: department 为空",
                hazard.hazard_no,
            )
            return None
        return await self.resolve_department_leader(hazard.department)

    async def resolve_hazard_supervising_leader(
        self,
        hazard: HazardReport,
    ) -> ResolvedPerson | None:
        """③ 分管领导：hazard.department → 父部门 leader → open_id。"""
        if not hazard.department:
            logger.warning(
                "hazard %s: department 为空",
                hazard.hazard_no,
            )
            return None
        return await self.resolve_supervising_leader(hazard.department)

    async def resolve_discoverer(
        self,
        hazard: HazardReport,
    ) -> ResolvedPerson | None:
        """④ 隐患发现人：discovered_by_name → open_id。"""
        if not hazard.discovered_by_name:
            logger.warning(
                "hazard %s: discovered_by_name 为空",
                hazard.hazard_no,
            )
            return None
        return await self.resolve_by_name(
            hazard.discovered_by_name,
            department_hint=hazard.department,
        )

    async def resolve_hazard_safety_officer(
        self,
        hazard: HazardReport,
    ) -> ResolvedPerson | None:
        """⑤ 分管安全员：hazard.department → DEPT_CONFIG safety_officer → open_id。"""
        if not hazard.department:
            logger.warning(
                "hazard %s: department 为空",
                hazard.hazard_no,
            )
            return None
        return await self.resolve_safety_officer(hazard.department)

    # ═══════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════

    @staticmethod
    def _user_to_person(
        user: dict[str, Any],
        department: str | None = None,
    ) -> ResolvedPerson:
        """将 HR 人员档案（``hr.employee_profiles`` 序列化结果）转为 ResolvedPerson。

        #219：人员主数据改为 HR 档案，飞书通知统一走 ``open_id``（档案不保存
        user_id / union_id），因此 ``user_id`` 留空。
        """
        names = user.get("department_names") or []
        return ResolvedPerson(
            open_id=str(user.get("open_id") or ""),
            user_id="",
            name=str(user.get("name") or ""),
            department=department or (str(names[-1]) if names else None),
            id=str(user.get("id") or ""),
        )

    async def _find_users_by_name(self, name: str) -> list[dict[str, Any]]:
        """在 HR 人员主数据中按姓名精确匹配，返回全部命中（含同名）。"""
        from app.modules.hr.public_api import find_profiles_by_name

        return await find_profiles_by_name(self._session, name)

    async def _find_user_by_name(
        self,
        name: str,
        department_hint: str | None = None,
    ) -> dict[str, Any] | None:
        """在 HR 人员主数据中按姓名查找用户（宽松：多命中时取第一个）。

        策略：
          1. 精确匹配 name
          2. 命中 1 个 → 直接返回
          3. 命中 > 1 个且有 department_hint → 用部门消歧
          4. 命中 0 个 → 返回 None
        """
        users = await self._find_users_by_name(name)

        if not users:
            return None

        if len(users) == 1:
            return users[0]

        # 多人同名，尝试用部门提示消歧
        if department_hint:
            filtered = [
                u
                for u in users
                if department_hint in "".join(str(item) for item in (u.get("department_names") or []))
            ]
            if len(filtered) == 1:
                logger.info(
                    "_find_user_by_name: %r 多命中 %d，部门消歧 → %r",
                    name,
                    len(users),
                    filtered[0].get("name"),
                )
                return filtered[0]
            if filtered:
                logger.warning(
                    "_find_user_by_name: %r 部门消歧后仍有 %d 人，取第一个",
                    name,
                    len(filtered),
                )
                return filtered[0]

        logger.warning(
            "_find_user_by_name: %r 匹配 %d 人，无法消歧，取第一个",
            name,
            len(users),
        )
        return users[0]

    async def _find_user_by_user_id(self, user_id: str) -> dict[str, Any] | None:
        """按飞书 id 在 HR 人员主数据中查找（档案只保存 open_id）。"""
        from app.modules.hr.public_api import find_profile_by_feishu_id

        return await find_profile_by_feishu_id(self._session, user_id)

    async def _find_user_by_email(self, email: str) -> dict[str, Any] | None:
        """按 email 查找人员（Bitable open_id 与档案 open_id 不匹配时的回退）。"""
        from app.modules.hr.public_api import find_profile_by_email

        return await find_profile_by_email(self._session, email)

    async def _find_department_by_name(self, name: str) -> dict[str, Any] | None:
        """在 HR 部门主数据中匹配部门（精确 → 结尾匹配 → 包含）。"""
        from app.modules.hr.public_api import find_department_row_by_name

        return await find_department_row_by_name(self._session, name)

    async def _find_department_by_id(self, feishu_department_id: str) -> dict[str, Any] | None:
        """按 feishu_department_id 精确查找部门。"""
        from app.modules.hr.public_api import get_department_row_by_feishu_id

        return await get_department_row_by_feishu_id(self._session, feishu_department_id)
