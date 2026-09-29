"""知识库服务层的纯函数测试：状态计数与上传限制（不连数据库、不打 RAGFlow）。"""

from __future__ import annotations

import uuid

import pytest

from app.core.config import RagflowSettings
from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research.knowledge_base import service
from app.modules.research.knowledge_base.models import RdKbDocument, RdKnowledgeBase


def _kb() -> RdKnowledgeBase:
    return RdKnowledgeBase(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        name="米诺地尔-项目知识库",
        ragflow_dataset_id="ds-1",
        chunk_method="naive",
        status="active",
        document_count=3,
        chunk_count=42,
        token_count=9000,
    )


def _doc(run: str) -> RdKbDocument:
    row = RdKbDocument(
        kb_id=uuid.uuid4(),
        ragflow_document_id=f"doc-{run}",
        file_name="米诺地尔项目调研报告.docx",
        file_ext=".docx",
        size_bytes=1024,
        run_status=run,
        progress=1.0 if run == "DONE" else 0.3,
    )
    row.id = uuid.uuid4()
    return row


def test_document_payload_maps_run_status() -> None:
    payload = service.document_payload(_doc("DONE"))

    assert payload["run"] == "DONE"
    assert payload["progress"] == 1.0
    assert payload["file_name"] == "米诺地尔项目调研报告.docx"
    assert payload["progress_msg"] == ""
    assert payload["last_error"] == ""


def test_knowledge_base_payload_counts_document_states() -> None:
    documents = [_doc("DONE"), _doc("DONE"), _doc("RUNNING"), _doc("UNSTART"), _doc("FAIL")]
    payload = service.knowledge_base_payload(_kb(), project_name="米诺地尔", documents=documents)

    assert payload["project_name"] == "米诺地尔"
    assert payload["parsed_count"] == 2
    assert payload["parsing_count"] == 2
    assert payload["failed_count"] == 1
    assert payload["chunk_count"] == 42


def test_knowledge_base_payload_without_documents() -> None:
    payload = service.knowledge_base_payload(_kb())
    assert (payload["parsed_count"], payload["parsing_count"], payload["failed_count"]) == (0, 0, 0)


async def test_limits_reports_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Settings:
        ragflow = RagflowSettings(base_url="http://ragflow:9380", api_key="key")

    monkeypatch.setattr(service, "get_settings", lambda: _Settings())
    limits = await service.limits()

    assert limits["configured"] is True
    assert ".pdf" in limits["allowed_extensions"]
    assert ".exe" not in limits["allowed_extensions"]
    assert limits["max_files"] == service.MAX_FILES_PER_UPLOAD


async def test_limits_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Settings:
        ragflow = RagflowSettings()

    monkeypatch.setattr(service, "get_settings", lambda: _Settings())
    assert (await service.limits())["configured"] is False


# ---------------------------------------------------------------------------
# 预览 / 下载
# ---------------------------------------------------------------------------


async def test_document_image_rejects_foreign_image_id() -> None:
    """RAGFlow 取图端点不校验库归属，这里必须挡住别的数据集的图。"""
    kb = _kb()  # ragflow_dataset_id = "ds-1"

    with pytest.raises(NotFoundException):
        await service.document_image(kb, "ds-2-abc123")
    with pytest.raises(NotFoundException):
        await service.document_image(kb, "")


async def test_document_image_returns_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    kb = _kb()

    class _Client:
        async def download_image(self, image_id: str) -> tuple[bytes, str]:
            return b"jpeg-bytes", "image/jpeg"

    monkeypatch.setattr(service, "RagflowClient", _Client)

    content, content_type = await service.document_image(kb, "ds-1-abc123")

    assert content == b"jpeg-bytes"
    assert content_type == "image/jpeg"


async def test_document_image_missing_remote_object(monkeypatch: pytest.MonkeyPatch) -> None:
    """远端返回空内容（对象不存在）时按不存在处理，而不是回一个空图片。"""
    kb = _kb()

    class _Client:
        async def download_image(self, image_id: str) -> tuple[bytes, str]:
            return b"", "application/octet-stream"

    monkeypatch.setattr(service, "RagflowClient", _Client)

    with pytest.raises(NotFoundException):
        await service.document_image(kb, "ds-1-abc123")


def test_chunk_payload_maps_ragflow_fields() -> None:
    payload = service.chunk_payload(
        {
            "id": "c1",
            "content": "米诺地尔通过扩张血管增加头皮血流",
            "positions": [[1, 10.0, 20.0, 30.0, 40.0]],
            "docnm_kwd": "米诺地尔项目调研报告.docx",
            "image_id": "img-1",
        }
    )

    assert payload["id"] == "c1"
    assert payload["content"].startswith("米诺地尔")
    assert payload["positions"] == [[1, 10.0, 20.0, 30.0, 40.0]]
    # RAGFlow 的 docnm_kwd 是文档名，前端字段名统一成 document_keyword
    assert payload["document_keyword"] == "米诺地尔项目调研报告.docx"
    assert payload["image_id"] == "img-1"
    assert payload["available"] is True


def test_chunk_payload_tolerates_missing_fields() -> None:
    payload = service.chunk_payload({})

    assert payload["id"] == ""
    assert payload["content"] == ""
    assert payload["positions"] == []
    assert payload["document_keyword"] == ""
    assert payload["available"] is True


async def test_document_file_falls_back_to_extension_mime(monkeypatch: pytest.MonkeyPatch) -> None:
    """RAGFlow 回 octet-stream 时按本地记录的扩展名补 MIME（否则浏览器只能下载）。"""
    kb = _kb()
    row = _doc("DONE")

    class _Client:
        async def download_document(self, dataset_id: str, document_id: str) -> tuple[bytes, str, str]:
            return b"bytes", "application/octet-stream", ""

    monkeypatch.setattr(service, "RagflowClient", _Client)

    content, content_type = await service.document_file(kb, row)

    assert content == b"bytes"
    assert content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def test_document_file_converts_office_to_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """浏览器渲染不了 .doc/.xls(x)/.ppt，预览要求 as_pdf 时改回 PDF 字节流。"""
    kb = _kb()
    row = _doc("DONE")
    converted: list[str] = []

    class _Client:
        async def download_document(self, dataset_id: str, document_id: str) -> tuple[bytes, str, str]:
            return b"office-bytes", "application/msword", ""

    class _Converter:
        def convert_bytes_to_pdf(self, content: bytes, filename: str) -> bytes | None:
            converted.append(filename)
            return b"%PDF-1.7 converted"

    monkeypatch.setattr(service, "RagflowClient", _Client)
    monkeypatch.setattr(service, "get_file_conversion", lambda: _Converter())

    content, content_type = await service.document_file(kb, row, as_pdf=True)

    assert converted == [row.file_name]
    assert content == b"%PDF-1.7 converted"
    assert content_type == "application/pdf"


async def test_document_file_falls_back_when_conversion_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """转换失败（如未装 libreoffice）不能让预览整条链路失败，回退原件。"""
    kb = _kb()
    row = _doc("DONE")

    class _Client:
        async def download_document(self, dataset_id: str, document_id: str) -> tuple[bytes, str, str]:
            return b"office-bytes", "application/msword", ""

    class _Converter:
        def convert_bytes_to_pdf(self, content: bytes, filename: str) -> bytes | None:
            return None

    monkeypatch.setattr(service, "RagflowClient", _Client)
    monkeypatch.setattr(service, "get_file_conversion", lambda: _Converter())

    content, content_type = await service.document_file(kb, row, as_pdf=True)

    assert content == b"office-bytes"
    assert content_type == "application/msword"


async def test_document_file_skips_conversion_for_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """本身就是 PDF：不再浪费一次 LibreOffice 调用。"""
    kb = _kb()
    row = _doc("DONE")
    row.file_name = "米诺地尔项目调研报告.pdf"
    row.file_ext = ".pdf"

    class _Client:
        async def download_document(self, dataset_id: str, document_id: str) -> tuple[bytes, str, str]:
            return b"%PDF-1.4 original", "application/pdf", ""

    class _Converter:
        def convert_bytes_to_pdf(self, content: bytes, filename: str) -> bytes | None:  # pragma: no cover
            raise AssertionError("PDF 不应触发转换")

    monkeypatch.setattr(service, "RagflowClient", _Client)
    monkeypatch.setattr(service, "get_file_conversion", lambda: _Converter())

    content, content_type = await service.document_file(kb, row, as_pdf=True)

    assert content == b"%PDF-1.4 original"
    assert content_type == "application/pdf"


async def test_document_file_requires_ready_kb() -> None:
    kb = _kb()
    kb.status = "creating"

    with pytest.raises(BadRequestException) as exc:
        await service.document_file(kb, _doc("DONE"))

    assert "尚未就绪" in str(exc.value)
