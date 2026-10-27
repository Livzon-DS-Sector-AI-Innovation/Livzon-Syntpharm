# mypy: ignore-errors
"""审计日志过期清理函数单元测试。"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.platform.audit.cleanup import cleanup_expired_audit_logs


def _select_result(ids: list):
    """构造 execute 返回的 select 结果 mock：scalars().all() -> ids。"""
    result = MagicMock()
    result.scalars.return_value.all.return_value = ids
    return result


async def test_cleanup_skips_when_retention_not_positive():
    """保留期 <= 0 时跳过清理，不触碰数据库。"""
    with patch("app.platform.audit.cleanup.async_session_factory") as factory:
        result = await cleanup_expired_audit_logs(retention_days=0)

    assert result == 0
    factory.assert_not_called()


async def test_cleanup_deletes_expired_in_batches():
    """正常路径：分批删除过期记录，直到没有更多过期记录。"""
    id1 = "00000000-0000-0000-0000-000000000001"
    id2 = "00000000-0000-0000-0000-000000000002"

    fake_session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = fake_session
    factory = MagicMock(return_value=cm)

    # 第一轮：select 返回 2 个 id -> delete -> commit
    # 第二轮：select 返回空 -> 结束
    fake_session.execute.side_effect = [
        _select_result([id1, id2]),
        MagicMock(),
        _select_result([]),
    ]

    with patch("app.platform.audit.cleanup.async_session_factory", factory):
        result = await cleanup_expired_audit_logs(retention_days=7)

    assert result == 2
    assert fake_session.execute.await_count == 3
    assert fake_session.commit.await_count == 1


async def test_cleanup_reads_retention_from_settings_when_none():
    """retention_days=None 时读取配置 AUDIT_RETENTION_DAYS。"""
    fake_session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = fake_session
    factory = MagicMock(return_value=cm)

    fake_session.execute.side_effect = [_select_result([])]

    with (
        patch("app.platform.audit.cleanup.async_session_factory", factory),
        patch("app.platform.audit.cleanup.get_settings") as get_settings,
    ):
        get_settings.return_value.AUDIT_RETENTION_DAYS = 14
        result = await cleanup_expired_audit_logs()

    assert result == 0
    get_settings.assert_called_once()
