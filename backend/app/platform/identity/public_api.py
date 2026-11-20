"""Identity 模块对外公开的 API。

其他模块只能通过本文件调用 identity 的内部实现，不得直接 import
`app.platform.identity.service`（AGENTS.md 模块所有权规则）。
"""

from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import select

from app.core.database import AsyncSession  # type: ignore[attr-defined]
from app.platform.identity.models import User
from app.platform.identity.service import _verify_feishu_callback_signature

__all__ = ["resolve_user_names", "verify_feishu_callback_signature"]


async def resolve_user_names(db: AsyncSession, user_ids: Iterable[UUID]) -> dict[UUID, str]:
    """批量把用户 ID 解析为姓名，供其他模块回显「操作人」等场景使用。

    其他模块需要显示人员姓名时调用本函数，不要直接查询 identity 的 ORM 模型。
    """
    ids = set(user_ids)
    if not ids:
        return {}
    result = await db.execute(select(User).where(User.id.in_(ids)))
    return {user.id: user.name for user in result.scalars().all()}


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
