"""Identity 模块对外公开的 API。

其他模块只能通过本文件调用 identity 的内部实现，不得直接 import
`app.platform.identity.service`（AGENTS.md 模块所有权规则）。
"""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.platform.identity.models import User
from app.platform.identity.service import _verify_feishu_callback_signature
from app.platform.identity.service import ensure_identity_user as _ensure_identity_user

__all__ = [
    "ensure_identity_user",
    "resolve_person_user_id",
    "resolve_user_names",
    "verify_feishu_callback_signature",
]


def verify_feishu_callback_signature(
    *,
    encrypt_key: str | None,
    raw_body: bytes,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
) -> bool:
    """校验飞书回调签名（HMAC-SHA256）。

    未配置 `encrypt_key` 时返回 `True`，由调用方的 verification token 校验兜底。
    """
    return _verify_feishu_callback_signature(
        encrypt_key=encrypt_key,
        raw_body=raw_body,
        timestamp=timestamp,
        nonce=nonce,
        signature=signature,
    )


async def resolve_user_names(db: AsyncSession, user_ids: Iterable[UUID]) -> dict[UUID, str]:
    """批量把用户 ID 解析为姓名，供其他模块回显「操作人」等场景使用。

    其他模块需要显示人员姓名时调用本函数，不要直接查询 identity 的 ORM 模型。
    """
    ids = set(user_ids)
    if not ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(ids)))
    return {user.id: user.name for user in result.scalars().all()}


async def ensure_identity_user(session: AsyncSession, employee_profile_id: UUID) -> UUID:
    """按 HR 员工档案幂等地确保存在平台账号，返回 ``identity.users.id``。

    权限授予仍以 ``identity.users.id`` 为键；被授权人可能尚未登录，授权前先
    通过本函数物化账号行（#219 预授权接缝）。
    """
    user = await _ensure_identity_user(session, employee_profile_id)
    return user.id


async def resolve_person_user_id(session: AsyncSession, person_id: UUID) -> UUID | None:
    """把人员引用归一化成 ``identity.users.id``（#219 迁移期兼容接缝）。

    前端选择器返回的是 ``hr.employee_profiles.id``，而旧业务列的外键仍是
    ``identity.users.id``。这里先按账号 id 查；查不到就把入参当作 HR 档案 id，
    按需建号（幂等）后返回账号 id；两者都不存在时返回 ``None``。

    待业务列全部改指 ``employee_profiles.id`` 后可删除本函数。
    """
    user = await session.get(User, person_id)
    if user is not None and not user.is_deleted:
        return user.id
    try:
        return await ensure_identity_user(session, person_id)
    except AppException:
        return None
