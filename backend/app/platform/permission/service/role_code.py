"""角色编码自动生成。

用户建角色只填名称与权限，编码由系统生成：

- 模块角色：`{module}:role-001`、`{module}:role-002` …（模块内递增）
- 平台 / 全局角色：`platform:role-001` …（全局递增）

编码仍是「模块:名称」两段式，因此天然满足 `assert_role_code_valid` 的格式与保留字规则；
并发创建靠 `permission.roles.code` 的唯一约束兜底（调用方捕获 IntegrityError 后重算重试）。
"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.permission.models import Role

PLATFORM_SCOPE = "platform"
_SEQ_WIDTH = 3


def role_code_prefix(module_code: str | None) -> str:
    """编码前缀：模块角色用模块码，平台角色统一用 `platform`。"""
    return f"{module_code or PLATFORM_SCOPE}:role-"


def _parse_sequence(code: str, prefix: str) -> int:
    suffix = code[len(prefix) :]
    match = re.fullmatch(r"(\d+)", suffix)
    return int(match.group(1)) if match else 0


async def next_role_code(db: AsyncSession, module_code: str | None) -> str:
    """按同前缀已有编码取最大序号 +1，返回三位补零的新编码。

    只做「读 + 计算」，不落库；真正并发安全由唯一约束 + 调用方重试保证。
    """
    prefix = role_code_prefix(module_code)
    result = await db.execute(
        select(Role.code).where(
            Role.code.startswith(prefix),
            Role.is_deleted == False,  # noqa: E712
        )
    )
    max_seq = max((_parse_sequence(code, prefix) for code in result.scalars().all()), default=0)
    return f"{prefix}{max_seq + 1:0{_SEQ_WIDTH}d}"


__all__ = ["PLATFORM_SCOPE", "next_role_code", "role_code_prefix"]
