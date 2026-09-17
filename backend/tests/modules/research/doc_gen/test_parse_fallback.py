"""`_parse_one` 分级兜底链的单测（不依赖数据库、对象存储与真实模型）。

背景：资料解析的可靠性是文档生成的地基。旧实现把 Office 等二进制格式 base64 后
塞进 prompt 让模型「提取文字」——LLM 不是 zip/OLE 解码器，只会回「无法识别」或编造
内容。这里锁定三条不变量：

1. 库解析成功就不再往下走（不白花 OCR / 视觉调用）；
2. Office 等容器格式**绝不会**被送去给模型解码（防止旧反模式回归）；
3. 只有「图片 / PDF」这两类可能「有画面没文字层」的文件才走视觉兜底，
   且视觉调用失败只是降级，不拖垮任务。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.core.llm import llm_client
from app.modules.research.doc_gen import pipeline
from app.modules.research.doc_gen.parsing import ParseResult, TextBlock
from app.modules.research.doc_gen.runtime_config import RuntimeConfig


def _record(name: str) -> Any:
    """DocGenInputFile 的最小替身（_parse_one 只读写这些属性）。"""
    return type(
        "Rec",
        (),
        {
            "job_id": "job-1",
            "file_id": f"f-{name}",
            "object_key": f"obj/{name}",
            "original_filename": name,
            "mime_type": "",
            "role": "material",
            "page_count": 0,
            "char_count": 0,
            "parse_status": "pending",
            "warnings": None,
        },
    )()


def _result(blocks: list[TextBlock], *, pages: int = 1, warnings: list[str] | None = None) -> ParseResult:
    return ParseResult(
        blocks=blocks,
        page_count=pages,
        char_count=sum(len(b.text) for b in blocks),
        ocr_used=False,
        warnings=warnings or [],
        format_name="Word",
    )


def _block(text: str = "正文") -> TextBlock:
    return TextBlock(file_id="f", page=1, index=0, text=text, kind="paragraph")


def _config(**overrides: Any) -> RuntimeConfig:
    base = RuntimeConfig(
        max_pages_per_file=80,
        max_ocr_pages_per_file=30,
        parse_timeout_seconds=30,
        llm_call_timeout_seconds=30,
        ocr_structured_enabled=False,
        vision_fallback_enabled=True,
        vision_max_pages=5,
    )
    return replace(base, **overrides)


@pytest.fixture
def vision_spy(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """把视觉模型调用换成 spy，既能断言是否被调用，也能模拟不可用。"""
    spy = AsyncMock(return_value="视觉识别出的文字")
    monkeypatch.setattr(llm_client, "chat_vision", spy)
    return spy


@pytest.fixture
def fake_pdf_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    """把 PDF 转图换成返回一张 2x2 的假图，避免依赖 poppler。"""
    from PIL import Image

    def _convert(path: str, **kwargs: Any) -> list[Any]:
        return [Image.new("RGB", (2, 2))]

    import pdf2image

    monkeypatch.setattr(pdf2image, "convert_from_path", _convert)


async def test_library_success_skips_vision(monkeypatch: pytest.MonkeyPatch, vision_spy: AsyncMock) -> None:
    """库解析拿到文字：直接 done，不再调用视觉模型。"""
    monkeypatch.setattr(pipeline, "_load_object", AsyncMock(return_value=b"payload"))
    parser = AsyncMock(return_value=_result([_block("甲氧基含量 99.2%")], pages=3))
    monkeypatch.setattr(pipeline, "parse_file", parser)

    record = _record("质量标准.docx")
    blocks, warnings, pages = await pipeline._parse_one(record, _config(), handle=None)

    assert [b.text for b in blocks] == ["甲氧基含量 99.2%"]
    assert pages == 3
    assert record.parse_status == "done"
    assert warnings == []
    assert parser.await_count == 1
    assert vision_spy.await_count == 0


async def test_office_container_never_sent_to_model(
    monkeypatch: pytest.MonkeyPatch, vision_spy: AsyncMock
) -> None:
    """Office/OLE 容器解析不出文字时**不**走视觉兜底——模型读不懂 zip/OLE。

    这是旧实现（base64 塞 prompt）失败的根因，用这条测试锁死回归。
    """
    monkeypatch.setattr(pipeline, "_load_object", AsyncMock(return_value=b"PK\x03\x04junk"))
    monkeypatch.setattr(pipeline, "parse_file", AsyncMock(return_value=_result([], pages=0)))

    record = _record("工艺参数.xlsx")
    blocks, warnings, _ = await pipeline._parse_one(record, _config(), handle=None)

    assert blocks == []
    assert vision_spy.await_count == 0
    assert record.parse_status == "failed"
    assert any("另存为" in w for w in warnings)
    assert any("另存为" in w for w in record.warnings or [])


async def test_vision_fallback_for_scanned_pdf(
    monkeypatch: pytest.MonkeyPatch, vision_spy: AsyncMock, fake_pdf_pages: None
) -> None:
    """扫描版 PDF：库解析无结果 → 转图交给视觉模型。"""
    monkeypatch.setattr(pipeline, "_load_object", AsyncMock(return_value=b"%PDF-1.7 junk"))
    monkeypatch.setattr(pipeline, "parse_file", AsyncMock(return_value=_result([], pages=0)))

    record = _record("文献扫描件.pdf")
    blocks, warnings, pages = await pipeline._parse_one(record, _config(), handle=None)

    assert [b.text for b in blocks] == ["视觉识别出的文字"]
    assert pages == 1
    assert record.parse_status == "done"
    assert vision_spy.await_count == 1
    assert any("视觉模型" in w for w in warnings)


async def test_vision_unavailable_degrades_to_failed(
    monkeypatch: pytest.MonkeyPatch, vision_spy: AsyncMock, fake_pdf_pages: None
) -> None:
    """视觉模型不可用（未登记 vision 配置）：降级为失败并给出可执行提示，不抛异常。"""
    vision_spy.side_effect = RuntimeError("no vision config")
    monkeypatch.setattr(pipeline, "_load_object", AsyncMock(return_value=b"%PDF-1.7 junk"))
    monkeypatch.setattr(pipeline, "parse_file", AsyncMock(return_value=_result([], pages=0)))

    record = _record("文献扫描件.pdf")
    blocks, warnings, _ = await pipeline._parse_one(record, _config(), handle=None)

    assert blocks == []
    assert record.parse_status == "failed"
    assert any("视觉模型不可用" in w for w in warnings)
    assert any("另存为" in w for w in warnings)


async def test_structured_ocr_second_pass(monkeypatch: pytest.MonkeyPatch, vision_spy: AsyncMock) -> None:
    """开启结构化 OCR 时：库解析无结果后，用 PP-StructureV3 通道再试一次。"""
    monkeypatch.setattr(pipeline, "_load_object", AsyncMock(return_value=b"%PDF-1.7 junk"))
    parser = AsyncMock(return_value=_result([], pages=0))
    monkeypatch.setattr(pipeline, "parse_file", parser)

    record = _record("文献扫描件.pdf")
    await pipeline._parse_one(record, _config(ocr_structured_enabled=True, vision_fallback_enabled=False), handle=None)

    assert parser.await_count == 2
    assert parser.await_args is not None
    assert parser.await_args.kwargs["ocr_structured"] is True
