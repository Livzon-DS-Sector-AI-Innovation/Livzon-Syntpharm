"""Tests for the document parser's staged OCR failure handling.

The seam now raises a typed `OCRError`. Until each caller is migrated, this parser
must keep returning a degraded string — so these tests lock the fallback decision log
and the degraded return, not a raised error.
"""

from __future__ import annotations

import logging

import pdf2image
import pytest

from app.platform.integrations.ai.document_parser import DocumentParser
from app.shared.ocr_service import OCRError


class FailingOcrService:
    """Stands in for the OCR singleton and always fails."""

    def extract(self, image: object, output_format: str = "text") -> str:
        raise OCRError(
            input_name="scan.pdf",
            engine="pp_structurev3",
            output_format="markdown",
            cause=ValueError("model exploded"),
        )


def extra(record: logging.LogRecord, name: str) -> object:
    """Read a structured field attached through logging's `extra`."""
    return getattr(record, name)


def test_ocr_failure_is_logged_with_context_and_returns_degraded_text(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(pdf2image, "convert_from_path", lambda *args, **kwargs: [object()])
    monkeypatch.setattr("app.shared.ocr_service.get_ocr_service", lambda: FailingOcrService())
    caplog.set_level(logging.INFO)

    result = DocumentParser._extract_pdf_ocr("scan.pdf")

    assert result.startswith("[OCR提取失败")
    record = next(record for record in caplog.records if getattr(record, "ocr_engine", None))
    assert extra(record, "ocr_engine") == "pp_structurev3"
    assert extra(record, "ocr_output_format") == "markdown"
    assert extra(record, "file") == "scan.pdf"
    assert record.exc_info is not None


def test_scanned_pdf_fallback_decision_is_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr("pypdf.PdfReader", _FakePdfReader)
    monkeypatch.setattr(DocumentParser, "_extract_pdf_ocr", staticmethod(lambda *args, **kwargs: "ocr text"))
    caplog.set_level(logging.INFO)

    text = DocumentParser._extract_pdf("scan.pdf")

    assert text == "ocr text"
    record = next(record for record in caplog.records if record.message == "PDF 无文本层，回退到 OCR")
    assert extra(record, "file") == "scan.pdf"
    assert extra(record, "extracted_chars") == 0


class _FakePage:
    def extract_text(self) -> str:
        return ""


class _FakePdfReader:
    def __init__(self, path: str) -> None:
        self.pages = [_FakePage()]
