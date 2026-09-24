"""Tests for the OCR seam contract: typed error, typed outcome, injectable engine.

The engine is injected, so these tests never load PaddleOCR models — the seam's own
logging, error typing and outcome contract are what is under test.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, cast

import pytest
from fastapi import HTTPException

from app.core.exceptions import AppException
from app.shared.ocr_service import ExtractionOutcome, OCRError, OCRService


class FakeOcrEngine:
    """Stands in for PaddleOCR: records calls, and can fail or stall on demand."""

    def __init__(self, *, texts: list[str] | None = None, error: Exception | None = None, delay: float = 0.0) -> None:
        self.texts = ["hello", "world"] if texts is None else texts
        self.error = error
        self.delay = delay
        self.calls: list[Any] = []

    def predict(self, input_data: Any) -> list[dict[str, Any]]:
        self.calls.append(input_data)
        if self.delay:
            time.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return [{"rec_texts": self.texts}]


class FakeStructureResult(dict[str, Any]):
    """Mimics the PP-StructureV3 result object: a dict with markdown and json attributes."""

    def __init__(self, markdown: str) -> None:
        super().__init__({"parsing_res_list": []})
        self.markdown: dict[str, str] | str = {"markdown_texts": markdown}
        self.json: dict[str, Any] = {"blocks": []}


class FakeStructureEngine:
    """Stands in for PP-StructureV3."""

    def __init__(self, *, markdown: str = "# title", error: Exception | None = None) -> None:
        self.markdown = markdown
        self.error = error
        self.calls: list[Any] = []

    def predict(self, input_data: Any) -> list[FakeStructureResult]:
        self.calls.append(input_data)
        if self.error is not None:
            raise self.error
        return [FakeStructureResult(self.markdown)]


def build_service(
    *,
    ocr: FakeOcrEngine | None = None,
    structure: FakeStructureEngine | None = None,
) -> tuple[OCRService, FakeOcrEngine, FakeStructureEngine]:
    ocr_engine = ocr or FakeOcrEngine()
    structure_engine = structure or FakeStructureEngine()
    service = OCRService(ocr_engine=ocr_engine, structure_engine=structure_engine)
    return service, ocr_engine, structure_engine


def extra(record: logging.LogRecord, name: str) -> Any:
    """Read a structured field attached through logging's `extra`."""
    return getattr(record, name)


class TestInjectedEngine:
    def test_text_extraction_uses_the_injected_engine(self) -> None:
        service, ocr, _ = build_service()

        assert service.extract_text("scan.png") == "hello\nworld"
        assert ocr.calls == ["scan.png"]

    def test_structure_extraction_uses_the_injected_engine(self) -> None:
        service, _, structure = build_service()

        assert service.extract_structure("scan.pdf")["markdown"] == "# title"
        assert structure.calls == ["scan.pdf"]


class TestTypedFailure:
    def test_failure_raises_a_typed_error_with_context(self) -> None:
        cause = ValueError("model exploded")
        service, _, _ = build_service(ocr=FakeOcrEngine(error=cause))

        with pytest.raises(OCRError) as caught:
            service.extract_text("scan.pdf")

        failure = caught.value
        assert failure.input_name == "scan.pdf"
        assert failure.engine == "pp_ocr"
        assert failure.output_format == "text"
        assert failure.cause is cause
        assert "model exploded" in str(failure)

    def test_failure_is_logged_with_a_traceback_and_context(self, caplog: pytest.LogCaptureFixture) -> None:
        caplog.set_level(logging.ERROR)
        service, _, _ = build_service(ocr=FakeOcrEngine(error=ValueError("boom")))

        with pytest.raises(OCRError):
            service.extract_text("scan.pdf")

        record = next(record for record in caplog.records if record.name == "app.shared.ocr_service")
        assert record.exc_info is not None
        assert extra(record, "ocr_engine") == "pp_ocr"
        assert extra(record, "ocr_output_format") == "text"
        assert extra(record, "ocr_input") == "scan.pdf"

    def test_failure_is_not_an_http_exception(self) -> None:
        """The seam's error is internal; endpoint layers translate it (ADR-0002)."""
        assert not issubclass(OCRError, AppException)
        assert not issubclass(OCRError, HTTPException)

    def test_structure_failure_reports_the_structure_engine(self) -> None:
        service, _, _ = build_service(structure=FakeStructureEngine(error=RuntimeError("bad layout")))

        with pytest.raises(OCRError) as caught:
            service.extract_markdown("scan.pdf")

        assert caught.value.engine == "pp_structurev3"
        assert caught.value.output_format == "markdown"

    def test_hanging_engine_is_not_interrupted_by_the_seam(self) -> None:
        """A hanging engine blocks the caller: timeouts belong to the caller or the job."""
        release = threading.Event()

        class HangingEngine(FakeOcrEngine):
            def predict(self, input_data: Any) -> list[dict[str, Any]]:
                self.calls.append(input_data)
                release.wait(timeout=2)
                return [{"rec_texts": ["late"]}]

        service = OCRService(ocr_engine=HangingEngine(), structure_engine=FakeStructureEngine())
        results: list[str] = []
        worker = threading.Thread(target=lambda: results.append(service.extract_text("scan.png")))

        worker.start()
        worker.join(timeout=0.05)
        assert results == []  # still blocked — the seam applied no timeout of its own

        release.set()
        worker.join(timeout=2)
        assert results == ["late"]


class TestTypedOutcome:
    def test_outcome_reports_text_and_page_count(self) -> None:
        service, _, _ = build_service()

        outcome = service.extract_outcome("scan.png")

        assert isinstance(outcome, ExtractionOutcome)
        assert outcome.text == "hello\nworld"
        assert outcome.page_count == 1
        assert outcome.degraded is False
        assert outcome.error is None

    def test_outcome_marks_empty_output_as_degraded_without_raising(self) -> None:
        service, _, _ = build_service(ocr=FakeOcrEngine(texts=[]))

        outcome = service.extract_outcome("scan.png")

        assert outcome.text == ""
        assert outcome.degraded is True
        assert outcome.error

    def test_outcome_for_markdown_reports_the_markdown(self) -> None:
        service, _, _ = build_service(structure=FakeStructureEngine(markdown="# report"))

        outcome = service.extract_outcome("scan.pdf", output_format="markdown")

        assert outcome.markdown == "# report"
        assert outcome.degraded is False

    def test_outcome_propagates_the_typed_failure(self) -> None:
        service, _, _ = build_service(ocr=FakeOcrEngine(error=ValueError("no engine")))

        with pytest.raises(OCRError):
            service.extract_outcome("scan.png")

    def test_unknown_output_format_is_rejected(self) -> None:
        service, _, _ = build_service()

        # Deliberately bypass the Literal type so the runtime guard is exercised.
        with pytest.raises(ValueError, match="Unknown output_format"):
            service.extract_outcome("scan.png", output_format=cast(Any, "nonsense"))
