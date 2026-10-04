"""解析缓存测试：哈希稳定性与「缓存不可用即降级并熔断」。

写库/读库路径依赖真实数据库，这里只钉住两条不依赖 DB 的契约：
内容哈希的稳定与敏感、以及后端异常时的降级行为（部署未跑迁移时不能每文件报错）。
"""

from __future__ import annotations

import pytest

from app.modules.research.doc_gen import parse_cache


def test_content_hash_is_stable_and_sensitive() -> None:
    """同一内容哈希稳定；内容变了哈希必变（缓存键因此不会串用）。"""
    assert parse_cache.content_hash(b"abc") == parse_cache.content_hash(b"abc")
    assert parse_cache.content_hash(b"abc") != parse_cache.content_hash(b"abd")


async def test_unavailable_backend_degrades_and_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    """表缺失（session 工厂抛错）时降级为 None，并在本进程内熔断、不再反复尝试。"""
    calls = {"factory": 0}

    def _broken_factory() -> object:
        calls["factory"] += 1
        raise RuntimeError('relation "research.doc_gen_parse_cache" does not exist')

    parse_cache.reset_state_for_tests()
    monkeypatch.setattr("app.core.database.async_session_factory", _broken_factory)

    try:
        assert await parse_cache.load_blocks("f1", b"data") is None
        assert await parse_cache.load_blocks("f1", b"data") is None
        assert calls["factory"] == 1  # 第一次失败即熔断，第二次不再触库
        # 写入路径同样熔断：不再尝试
        await parse_cache.save_blocks(b"data", [], [], 0, "x.pdf")
        assert calls["factory"] == 1
    finally:
        parse_cache.reset_state_for_tests()
