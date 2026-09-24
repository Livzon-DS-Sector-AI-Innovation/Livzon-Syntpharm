"""PaddleOCR service wrapper for the application.

Supports both PP-OCR (simple text extraction) and PP-StructureV3 (structured document analysis)
with a hybrid approach that allows automatic or manual engine selection.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Literal

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

OCR_ENGINE_PP_OCR = "pp_ocr"
OCR_ENGINE_PP_STRUCTURE = "pp_structurev3"
_EMPTY_OUTPUT_ERROR = "未提取到文本内容"


class OCRError(Exception):
    """A typed OCR failure that carries the context a caller needs.

    This is an internal error, not an HTTP status mapping (ADR-0002). Endpoint
    layers translate it: a job records it, an endpoint decides what the user sees.
    """

    def __init__(self, *, input_name: str, engine: str, output_format: str, cause: BaseException) -> None:
        super().__init__(f"{engine} 提取失败 ({input_name}): {cause}")
        self.input_name = input_name
        self.engine = engine
        self.output_format = output_format
        self.cause = cause


class ExtractionOutcome(BaseModel):
    """Typed extraction result — the additive contract consumers migrate to.

    The dictionary-shaped results stay available until the contract step, so
    existing readers keep working while callers move over one at a time.
    """

    text: str = ""
    markdown: str = ""
    structure: dict[str, Any] = Field(default_factory=dict)
    page_count: int = 0
    degraded: bool = False
    error: str | None = None


def _input_name(image_input: str | Path | Image.Image) -> str:
    """A log-safe name for the input: the filename, never the full path."""
    if isinstance(image_input, (str, Path)):
        return Path(image_input).name
    return "image"


def _degraded_error(is_empty: bool) -> tuple[bool, str | None]:
    """Map "no content extracted" onto the outcome's degraded/error pair."""
    return (True, _EMPTY_OUTPUT_ERROR) if is_empty else (False, None)


class OCRService:
    """PaddleOCR service supporting both PP-OCR and PP-StructureV3."""

    def __init__(
        self,
        *,
        ocr_engine: Any | None = None,
        structure_engine: Any | None = None,
    ) -> None:
        """Initialize the pipelines, or accept injected engines.

        Injecting both engines is the test seam: tests exercise the seam's own
        logging, error typing and outcome contract without loading any model.
        """
        self.pp_ocr = ocr_engine if ocr_engine is not None else self._build_ocr_engine()
        self.pp_structure = structure_engine if structure_engine is not None else self._build_structure_engine()

    @staticmethod
    def _build_ocr_engine() -> Any:
        """Create the PP-OCR pipeline (fast, simple text extraction)."""
        from paddleocr import PaddleOCR

        engine = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PP-OCR initialized with PP-OCRv6")
        return engine

    @staticmethod
    def _build_structure_engine() -> Any:
        """Create the PP-StructureV3 pipeline (tables, formulas, layout, Markdown)."""
        from paddleocr import PPStructureV3

        engine = PPStructureV3(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PP-StructureV3 initialized")
        return engine

    def _to_input(self, image_input: str | Path | Image.Image) -> str | np.ndarray:
        """Convert input to format expected by PaddleOCR."""
        if isinstance(image_input, Image.Image):
            return np.array(image_input)
        elif isinstance(image_input, Path):
            return str(image_input)
        else:
            return image_input

    def _is_pdf(self, image_input: str | Path | Image.Image) -> bool:
        """Check if input is a PDF file."""
        if isinstance(image_input, (str, Path)):
            path = Path(image_input) if not isinstance(image_input, Path) else image_input
            return path.suffix.lower() == ".pdf"
        return False

    def _predict(self, engine: Any, engine_name: str, image_input: str | Path | Image.Image, output_format: str) -> Any:
        """Run one engine call, logging and re-raising failures as a typed error.

        This is the single logging point: every extraction failure is recorded here
        with a traceback plus structured context, then raised as `OCRError`.
        """
        try:
            return engine.predict(self._to_input(image_input))
        except Exception as cause:
            logger.exception(
                "OCR 提取失败",
                extra={
                    "ocr_input": _input_name(image_input),
                    "ocr_engine": engine_name,
                    "ocr_output_format": output_format,
                },
            )
            raise OCRError(
                input_name=_input_name(image_input),
                engine=engine_name,
                output_format=output_format,
                cause=cause,
            ) from cause

    def _text_with_pages(self, image_input: str | Path | Image.Image) -> tuple[str, int]:
        """Extract text plus the number of page results the engine returned."""
        result = self._predict(self.pp_ocr, OCR_ENGINE_PP_OCR, image_input, "text")

        texts: list[str] = []
        for res in result:
            if "rec_texts" in res:
                texts.extend(res["rec_texts"])

        return "\n".join(texts), len(result)

    def extract_text(self, image_input: str | Path | Image.Image) -> str:
        """
        Extract text from image using PP-OCR (fast, simple text extraction).

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            Extracted text as a single string

        Raises:
            OCRError: when the engine fails.
        """
        text, _ = self._text_with_pages(image_input)
        return text

    def extract_with_positions(self, image_input: str | Path | Image.Image) -> list[dict[str, Any]]:
        """
        Extract text with bounding boxes and confidence scores using PP-OCR.

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            List of dicts with keys: text, bbox (x_min, y_min, x_max, y_max), confidence

        Raises:
            OCRError: when the engine fails.
        """
        result = self._predict(self.pp_ocr, OCR_ENGINE_PP_OCR, image_input, "positions")

        blocks = []
        for res in result:
            if "rec_texts" in res and "rec_scores" in res and "rec_polys" in res:
                texts = res["rec_texts"]
                scores = res["rec_scores"]
                polys = res["rec_polys"]

                for text, score, poly in zip(texts, scores, polys):
                    x_coords = [p[0] for p in poly]
                    y_coords = [p[1] for p in poly]
                    bbox = (
                        int(min(x_coords)),
                        int(min(y_coords)),
                        int(max(x_coords)),
                        int(max(y_coords)),
                    )

                    blocks.append({"text": text, "bbox": bbox, "confidence": float(score)})

        return blocks

    def extract_structure(self, image_input: str | Path | Image.Image) -> dict[str, Any]:
        """
        Extract structured document content using PP-StructureV3.
        Detects layout, tables, formulas, and preserves document structure.

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            Dictionary with structured content including:
            - markdown: Markdown representation
            - json: JSON representation
            - layout: Layout detection results
            - tables: Extracted tables

        Raises:
            OCRError: when the engine fails.
        """
        output, _ = self._structure_with_pages(image_input, "structure")
        return output

    def _structure_with_pages(
        self,
        image_input: str | Path | Image.Image,
        output_format: str = "structure",
    ) -> tuple[dict[str, Any], int]:
        """Extract structured content plus the number of page results.

        `output_format` is the format the *caller* asked for, so a failure reports the
        format that was requested rather than the engine that happened to serve it.
        """
        result = self._predict(self.pp_structure, OCR_ENGINE_PP_STRUCTURE, image_input, output_format)

        # Extract structured data from result
        output = {"markdown": "", "json": {}, "layout": [], "tables": []}

        for res in result:
            # Get Markdown output
            if hasattr(res, "markdown"):
                md_info = res.markdown
                if isinstance(md_info, dict):
                    output["markdown"] = md_info.get("markdown_texts", "")
                elif isinstance(md_info, str):
                    output["markdown"] = md_info
            elif hasattr(res, "save_to_markdown"):
                import tempfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    res.save_to_markdown(save_path=tmpdir)
                    md_files = list(Path(tmpdir).glob("*.md"))
                    if md_files:
                        output["markdown"] = md_files[0].read_text(encoding="utf-8")

            # Get JSON output
            if hasattr(res, "json"):
                output["json"] = res.json

            # Extract layout and table information from result
            if "parsing_res_list" in res:
                for item in res["parsing_res_list"]:
                    if "block_label" in item:
                        if item["block_label"] == "table":
                            output["tables"].append(item)  # type: ignore[attr-defined]
                        output["layout"].append(item)  # type: ignore[attr-defined]

        return output, len(result)

    def extract_markdown(self, image_input: str | Path | Image.Image) -> str:
        """
        Extract document as Markdown using PP-StructureV3.
        Best for documents with tables, formulas, and complex layouts.

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            Markdown representation of the document

        Raises:
            OCRError: when the engine fails.
        """
        structure, _ = self._structure_with_pages(image_input, "markdown")
        return str(structure.get("markdown", ""))

    def extract_outcome(
        self,
        image_input: str | Path | Image.Image,
        output_format: Literal["text", "markdown", "structure"] = "text",
    ) -> ExtractionOutcome:
        """Extract and return the typed outcome (the additive contract).

        Empty output is reported through `degraded` and `error` rather than raised,
        so the caller decides what a blank result means. Engine failures raise
        `OCRError`.

        Raises:
            OCRError: when the engine fails.
            ValueError: when `output_format` is not supported.
        """
        if output_format == "text":
            text, page_count = self._text_with_pages(image_input)
            degraded, error = _degraded_error(not text.strip())
            return ExtractionOutcome(text=text, page_count=page_count, degraded=degraded, error=error)

        if output_format == "markdown":
            structure, page_count = self._structure_with_pages(image_input, "markdown")
            markdown = str(structure.get("markdown", ""))
            degraded, error = _degraded_error(not markdown.strip())
            return ExtractionOutcome(markdown=markdown, page_count=page_count, degraded=degraded, error=error)

        if output_format == "structure":
            structure, page_count = self._structure_with_pages(image_input, "structure")
            degraded, error = _degraded_error(not structure.get("markdown") and not structure.get("tables"))
            return ExtractionOutcome(structure=structure, page_count=page_count, degraded=degraded, error=error)

        raise ValueError(f"Unknown output_format: {output_format}. Use 'text', 'markdown' or 'structure'")

    def extract(
        self,
        image_input: str | Path | Image.Image,
        engine: str | None = None,
        output_format: str = "text",
    ) -> str | list[dict[str, Any]] | dict[str, Any]:
        """
        Hybrid extraction method with automatic or manual engine selection.

        Args:
            image_input: File path (str or Path) or PIL Image object
            engine: "pp_ocr", "pp_structurev3", or None for auto-detection
            output_format: "text", "markdown", "json", "positions", "structure"

        Returns:
            Extracted content in the specified format
        """
        # Auto-detect engine if not specified
        if engine is None:
            if self._is_pdf(image_input):
                engine = "pp_structurev3"
            else:
                engine = "pp_ocr"

        # Route to appropriate engine and format
        if engine == "pp_ocr":
            if output_format == "positions":
                return self.extract_with_positions(image_input)
            else:
                return self.extract_text(image_input)

        elif engine == "pp_structurev3":
            if output_format == "markdown":
                return self.extract_markdown(image_input)
            elif output_format == "json":
                result = self._structure_with_pages(image_input, "json")[0]
                return result.get("json", {})  # type: ignore[no-any-return]
            elif output_format == "structure":
                return self.extract_structure(image_input)
            else:  # text
                result = self._structure_with_pages(image_input, "text")[0]
                return result.get("markdown", "")  # type: ignore[no-any-return]

        else:
            raise ValueError(f"Unknown engine: {engine}. Use 'pp_ocr' or 'pp_structurev3'")


class FakeOCRService:
    """No-op OCR service for e2e — returns empty/fake results, no model download."""

    def extract_text(self, image_input: str | Path | Image.Image) -> str:
        return ""

    def extract_with_positions(self, image_input: str | Path | Image.Image) -> list[dict[str, Any]]:
        return []

    def extract_structure(self, image_input: str | Path | Image.Image) -> dict[str, Any]:
        return {"markdown": "", "tables": []}

    def extract_markdown(self, image_input: str | Path | Image.Image) -> str:
        return ""

    def extract(
        self, image_input: str | Path | Image.Image, output_format: str = "text", **kwargs: Any
    ) -> str | dict[str, Any]:
        if output_format == "text":
            return ""
        return {"markdown": "", "tables": []}


# Global instance
_ocr_service: OCRService | FakeOCRService | None = None
_ocr_lock = threading.Lock()
_ocr_initializing = False


def init_ocr() -> None:
    """Initialize the OCR service (thread-safe)."""
    global _ocr_service, _ocr_initializing
    with _ocr_lock:
        if _ocr_service is not None:
            return
        _ocr_initializing = True
    try:
        from app.core.config import get_settings

        if get_settings().APP_ENV == "e2e":
            logger.info("e2e mode: using FakeOCRService (no model download)")
            with _ocr_lock:
                _ocr_service = FakeOCRService()
                _ocr_initializing = False
            return
        logger.info("Initializing OCR service...")
        service = OCRService()
        with _ocr_lock:
            _ocr_service = service
            _ocr_initializing = False
        logger.info("OCR service initialized successfully")
    except Exception:
        with _ocr_lock:
            _ocr_initializing = False
        logger.exception("Failed to initialize OCR service")


def get_ocr_service() -> OCRService | FakeOCRService:
    """Get the OCR service instance."""
    if _ocr_service is None:
        if _ocr_initializing:
            raise RuntimeError("OCR service is still initializing (loading ML models). Please try again in a moment.")
        raise RuntimeError("OCR service not initialized. Call init_ocr() first.")
    return _ocr_service
