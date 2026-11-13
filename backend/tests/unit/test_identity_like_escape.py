# mypy: ignore-errors
"""identity 用户搜索的 ILIKE 转义（PR #188 审计 Category 15）。

用户输入的 `%` / `_` / `\\` 是 LIKE 元字符，不转义就会被当成通配符：
搜 "a_b" 会命中 "axb"，搜 "50%" 会命中所有以 50 开头的账号。
本文件守住两条搜索路径（用户管理 list_users、登录日志 list_logs）都走
`_like_pattern()` + `escape="\\\\"`。
"""

from typing import Any

from sqlalchemy.dialects import postgresql

from app.platform.identity.repository import LoginLogRepository, UserRepository

KEYWORD = "50%_off"
ESCAPED = "%50\\%\\_off%"


class _Result:
    """最小执行结果替身：count 返回 0，行集为空。"""

    def scalar_one(self) -> int:
        return 0

    def scalars(self) -> "_Result":
        return self

    def all(self) -> list[Any]:
        return []


class _Session:
    """记录所有被执行语句的会话替身（不连库）。"""

    def __init__(self) -> None:
        self.statements: list[Any] = []

    async def execute(self, stmt: Any, *args: Any, **kwargs: Any) -> _Result:
        self.statements.append(stmt)
        return _Result()

    def add(self, obj: Any) -> None:  # pragma: no cover - 未被调用
        raise AssertionError("list 查询不应写库")

    async def flush(self) -> None:  # pragma: no cover - 未被调用
        raise AssertionError("list 查询不应 flush")


def _where_sql(session: _Session) -> str:
    """把被执行的语句编译成 SQL 文本（含 ESCAPE 子句）。"""
    return " ".join(str(stmt.compile(dialect=postgresql.dialect())) for stmt in session.statements)


def _bound_params(session: _Session) -> set[str]:
    params: set[str] = set()
    for stmt in session.statements:
        params.update(str(value) for value in stmt.compile(dialect=postgresql.dialect()).params.values())
    return params


async def test_list_users_escapes_like_metacharacters() -> None:
    session = _Session()

    await UserRepository().list_users(session, keyword=KEYWORD)

    sql = _where_sql(session)
    assert "ILIKE" in sql
    assert "ESCAPE" in sql
    # 转义后的模式必须作为绑定参数出现，而不是把用户输入直接拼成通配符
    assert ESCAPED in _bound_params(session)


async def test_list_logs_escapes_like_metacharacters() -> None:
    session = _Session()

    await LoginLogRepository().list_logs(session, keyword=KEYWORD)

    sql = _where_sql(session)
    assert "ILIKE" in sql
    assert "ESCAPE" in sql
    assert ESCAPED in _bound_params(session)


async def test_plain_keyword_still_matches_as_contains() -> None:
    """普通中文关键词不受影响：仍然是 %关键词% 的包含匹配。"""
    session = _Session()

    await UserRepository().list_users(session, keyword="张")

    assert "%张%" in _bound_params(session)
