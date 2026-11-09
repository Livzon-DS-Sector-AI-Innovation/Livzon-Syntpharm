"""隐患台账字段修复的回归测试。

覆盖：
1. AI 整改初审的整改回复取值（Bitable 只填「纠正预防措施」时兜底 capa_measures）
2. 上传图片压缩（未超限零重编码、超限等比压缩）
3. Bitable 字段定义缓存按 TTL 刷新（新建列无需重启即可回写）
"""

from __future__ import annotations

import io
from typing import Any, cast

import pytest
from PIL import Image

from app.core.image_utils import MAX_EDGE, compress_image
from app.modules.safety.feishu import bitable_handler
from app.modules.safety.feishu.bitable_client import SafetyBitableClient
from app.modules.safety.service.hazard import resolve_rectification_reply


class TestResolveRectificationReply:
    """AI 初审输入不能因为字段改向而为空。"""

    def test_prefers_rectification_reply(self) -> None:
        assert resolve_rectification_reply("已更换密封圈", "补充巡检频次") == "已更换密封圈"

    def test_falls_back_to_capa_measures(self) -> None:
        # Bitable 入站只写 capa_measures 的场景
        assert resolve_rectification_reply(None, "补充巡检频次") == "补充巡检频次"

    def test_returns_empty_when_both_missing(self) -> None:
        assert resolve_rectification_reply(None, None) == ""


def _jpeg_bytes(size: tuple[int, int]) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (120, 30, 30)).save(buf, format="JPEG", quality=95)
    return buf.getvalue()


class TestCompressImage:
    def test_small_image_untouched(self) -> None:
        data = _jpeg_bytes((320, 240))
        out, ext, content_type = compress_image(data, "small.jpg", "image/jpeg")
        assert out == data
        assert ext == ".jpg"
        assert content_type == "image/jpeg"

    def test_large_image_downscaled(self) -> None:
        data = _jpeg_bytes((4000, 3000))
        out, ext, content_type = compress_image(data, "big.jpg", "image/jpeg")
        assert len(out) < len(data)
        assert ext == ".jpg"
        assert content_type == "image/jpeg"
        with Image.open(io.BytesIO(out)) as img:
            assert max(img.size) <= MAX_EDGE

    def test_non_image_passthrough(self) -> None:
        data = b"not an image"
        out, ext, content_type = compress_image(data, "a.pdf", "application/pdf")
        assert out == data
        assert ext == ".pdf"
        assert content_type == "application/pdf"


class _StubBitableClient:
    def __init__(self, fields: list[dict[str, Any]]) -> None:
        self.fields = fields
        self.calls = 0

    async def list_fields(self) -> list[dict[str, Any]]:
        self.calls += 1
        return self.fields


def _as_client(stub: _StubBitableClient) -> SafetyBitableClient:
    """测试桩只需要 list_fields，按结构当真实客户端用。"""
    return cast(SafetyBitableClient, stub)


def _expire_field_cache() -> None:
    """把缓存时间推到 TTL 之外，模拟 Bitable 表结构已变化。"""
    loaded_at = bitable_handler._field_cache_loaded_at
    assert loaded_at is not None
    bitable_handler._field_cache_loaded_at = loaded_at - (bitable_handler._FIELD_CACHE_TTL_SECONDS + 1)


class TestBitableFieldCache:
    @pytest.fixture(autouse=True)
    def _reset_cache(self) -> Any:
        saved = (
            bitable_handler._field_name_cache,
            bitable_handler._option_map_cache,
            bitable_handler._field_type_cache,
            bitable_handler._field_cache_loaded_at,
        )
        bitable_handler._field_name_cache = None
        bitable_handler._option_map_cache = None
        bitable_handler._field_type_cache = None
        bitable_handler._field_cache_loaded_at = None
        yield
        (
            bitable_handler._field_name_cache,
            bitable_handler._option_map_cache,
            bitable_handler._field_type_cache,
            bitable_handler._field_cache_loaded_at,
        ) = saved

    async def test_cache_hit_within_ttl_and_refresh_after_ttl(self) -> None:
        client = _StubBitableClient([{"field_id": "f1", "field_name": "检查名称", "type": 1}])

        await bitable_handler._get_field_definitions(_as_client(client))
        assert client.calls == 1
        assert "检查名称" in (bitable_handler._field_type_cache or {})

        # TTL 内命中缓存，不再请求接口
        await bitable_handler._get_field_definitions(_as_client(client))
        assert client.calls == 1

        # 缓存过期后重新加载，Bitable 新建的列无需重启即可生效
        _expire_field_cache()
        client.fields = [
            {"field_id": "f1", "field_name": "检查名称", "type": 1},
            {"field_id": "f2", "field_name": "新列", "type": 1},
        ]
        await bitable_handler._get_field_definitions(_as_client(client))
        assert client.calls == 2
        assert "新列" in (bitable_handler._field_type_cache or {})

    async def test_refresh_failure_keeps_old_cache(self) -> None:
        client = _StubBitableClient([{"field_id": "f1", "field_name": "检查名称", "type": 1}])
        await bitable_handler._get_field_definitions(_as_client(client))

        class _FailingClient(_StubBitableClient):
            async def list_fields(self) -> list[dict[str, Any]]:
                self.calls += 1
                raise RuntimeError("bitable unavailable")

        failing = _FailingClient([])
        _expire_field_cache()
        await bitable_handler._get_field_definitions(_as_client(failing))

        assert "检查名称" in (bitable_handler._field_type_cache or {})
