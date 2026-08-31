"""PaddleOCR service wrapper for the application.

Supports both PP-OCR (simple text extraction) and PP-StructureV3 (structured document analysis)
with a hybrid approach that allows automatic or manual engine selection.
"""

import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

# Global lock for serializing OCR calls
_ocr_lock = threading.Lock()


def _get_ocr_app_root() -> Path:
    """推导 OCR 子进程的代码根目录（包含 app 包的目录），容器内外自洽。

    本文件位于 <root>/app/shared/ocr_service.py，向上三级即 <root>：
    容器内为 /app，宿主机为 backend/ 的真实路径。可用 OCR_APP_ROOT 覆盖。
    """
    return Path(os.environ.get("OCR_APP_ROOT") or Path(__file__).resolve().parents[2])


def get_ocr_lock() -> threading.Lock:
    """Get the global lock for OCR serialization."""
    return _ocr_lock


def count_pdf_pages(file_path: str | Path) -> int:
    """统计 PDF 页数：pypdf 优先（耐受非规范"暗伤"文件），pdfplumber 兜底。

    背景：pdfplumber 底层 pdfminer 对部分扫描件会漏读为 0 页
    （2026-08-24 实测：华辰授权书丽珠(1).pdf，poppler/pypdf 读 1 页，pdfplumber 读 0 页）。
    """
    try:
        from pypdf import PdfReader

        pages = len(PdfReader(str(file_path)).pages)
        if pages > 0:
            return pages
    except Exception:
        pass
    import pdfplumber

    with pdfplumber.open(str(file_path)) as pdf:
        return len(pdf.pages)


class OCRService:
    """PaddleOCR service supporting both PP-OCR and PP-StructureV3."""

    def __init__(self) -> Any:  # type: ignore[misc]
        """Initialize both PaddleOCR pipelines."""
        from paddleocr import PaddleOCR, PPStructureV3

        # PP-OCR for simple text extraction (fast)
        # PP-OCRv6 is the default, supports 50 languages including zh, en, vi, id
        self.pp_ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PP-OCR initialized with PP-OCRv6")

        # PP-StructureV3 for structured document analysis
        # Supports tables, formulas, layout detection, Markdown output
        self.pp_structure = PPStructureV3(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )
        logger.info("PP-StructureV3 initialized")

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

    def extract_text(self, image_input: str | Path | Image.Image) -> str:
        """
        Extract text from image using PP-OCR (fast, simple text extraction).

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            Extracted text as a single string
        """
        input_data = self._to_input(image_input)
        result = self.pp_ocr.predict(input_data)

        texts = []
        for res in result:
            if hasattr(res, "res") and "rec_texts" in res.res:
                texts.extend(res.res["rec_texts"])

        return "\n".join(texts)

    def extract_with_positions(self, image_input: str | Path | Image.Image) -> list[dict[str, Any]]:
        """
        Extract text with bounding boxes and confidence scores using PP-OCR.

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            List of dicts with keys: text, bbox (x_min, y_min, x_max, y_max), confidence
        """
        input_data = self._to_input(image_input)
        result = self.pp_ocr.predict(input_data)

        blocks = []
        for res in result:
            if hasattr(res, "res"):
                rec_data = res.res
                if "rec_texts" in rec_data and "rec_scores" in rec_data and "rec_polys" in rec_data:
                    texts = rec_data["rec_texts"]
                    scores = rec_data["rec_scores"]
                    polys = rec_data["rec_polys"]

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
        """
        input_data = self._to_input(image_input)
        result = self.pp_structure.predict(input_data)

        # Extract structured data from result
        output = {"markdown": "", "json": {}, "layout": [], "tables": []}

        for res in result:
            # Get Markdown output
            if hasattr(res, "save_to_markdown"):
                import tempfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    res.save_to_markdown(save_path=tmpdir)
                    # Read the generated markdown file
                    md_files = list(Path(tmpdir).glob("*.md"))
                    if md_files:
                        output["markdown"] = md_files[0].read_text(encoding="utf-8")

            # Get JSON output
            if hasattr(res, "save_to_json"):
                import json
                import tempfile

                with tempfile.TemporaryDirectory() as tmpdir:
                    res.save_to_json(save_path=tmpdir)
                    # Read the generated JSON file
                    json_files = list(Path(tmpdir).glob("*.json"))
                    if json_files:
                        with open(json_files[0], encoding="utf-8") as f:
                            output["json"] = json.load(f)

            # Extract layout and table information from result
            if hasattr(res, "res"):
                res_data = res.res
                if "layout_parsing_res" in res_data:
                    for item in res_data["layout_parsing_res"]:
                        if "block_label" in item:
                            if item["block_label"] == "table":
                                output["tables"].append(item)  # type: ignore[attr-defined]
                            output["layout"].append(item)  # type: ignore[attr-defined]

        return output

    def extract_markdown(self, image_input: str | Path | Image.Image) -> str:
        """
        Extract document as Markdown using PP-StructureV3.
        Best for documents with tables, formulas, and complex layouts.

        Args:
            image_input: File path (str or Path) or PIL Image object

        Returns:
            Markdown representation of the document
        """
        result = self.extract_structure(image_input)
        return result.get("markdown", "")  # type: ignore[no-any-return]

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
                result = self.extract_structure(image_input)
                return result.get("json", {})  # type: ignore[no-any-return]
            elif output_format == "structure":
                return self.extract_structure(image_input)
            else:  # text
                result = self.extract_structure(image_input)
                return result.get("markdown", "")  # type: ignore[no-any-return]

        else:
            raise ValueError(f"Unknown engine: {engine}. Use 'pp_ocr' or 'pp_structurev3'")

    @staticmethod
    def _run_ocr_in_subprocess(
        file_path: Path,
        timeout: int = 300,
        min_memory_gb: float = 8.0,
    ) -> dict[str, Any]:
        """Run OCR inference for entire PDF in isolated subprocess.

        Args:
            file_path: Path to the PDF file
            timeout: Timeout in seconds (default 300)
            min_memory_gb: Minimum available memory in GB (default 8.0)

        Returns:
            Dict with OCR result containing 'pages' list

        Raises:
            RuntimeError: If subprocess fails or times out
        """
        import json
        import os
        import signal
        import subprocess
        import tempfile

        import psutil

        # Check available memory before starting
        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)
        if available_gb < min_memory_gb:
            raise RuntimeError(f"Insufficient memory: {available_gb:.1f}GB available, need at least {min_memory_gb}GB")

        # Get page count for timeout calculation
        total_pages = count_pdf_pages(file_path)

        # Calculate timeout: max(provided, 120 + 60 * pages)
        calculated_timeout = 300 + 120 * total_pages
        actual_timeout = max(timeout, calculated_timeout)

        logger.info(f"Starting OCR subprocess for {total_pages} pages, timeout={actual_timeout}s")

        # Create temporary files for result and logs
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            output_file = Path(tmp.name)

        log_file = output_file.with_suffix(".log")

        try:
            # Prepare subprocess command using python -m
            cmd = [
                sys.executable,
                "-m",
                "app.shared.ocr_worker",
                str(file_path),
                "pp_structurev3",
                str(output_file),
            ]

            # Set environment variables
            env = os.environ.copy()
            env["PYTHONPATH"] = str(_get_ocr_app_root())
            env["OMP_NUM_THREADS"] = "1"
            env["MKL_NUM_THREADS"] = "1"
            env["OPENBLAS_NUM_THREADS"] = "1"

            # Start subprocess with new session, redirect stdout/stderr to log file
            with open(log_file, "w") as log_f:
                proc = subprocess.Popen(
                    cmd,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    env=env,
                    start_new_session=True,
                    cwd=str(_get_ocr_app_root()),
                )

                try:
                    # Wait for completion with timeout
                    proc.wait(timeout=actual_timeout)

                    # Read result from temporary file
                    if output_file.exists():
                        result_text = output_file.read_text()
                        result: dict[str, Any] = json.loads(result_text)

                        if not result.get("success"):
                            # Append log tail to error message
                            if log_file.exists():
                                log_tail = log_file.read_text().splitlines()[-50:]
                                error_detail = "\n".join(log_tail)
                                raise RuntimeError(
                                    f"{result.get('error', 'Unknown error')}\n\nWorker log:\n{error_detail}"
                                )
                            else:
                                raise RuntimeError(result.get("error", "Unknown error"))

                        return result
                    else:
                        raise RuntimeError("Worker did not produce output file")

                except subprocess.TimeoutExpired:
                    # Kill the entire process group
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        proc.wait()
                    except (ProcessLookupError, OSError):
                        pass

                    # Read log tail for debugging
                    error_msg = f"OCR inference timed out after {actual_timeout} seconds ({total_pages} pages)"
                    if log_file.exists():
                        log_tail = log_file.read_text().splitlines()[-50:]
                        error_msg += "\n\nWorker log (last 50 lines):\n" + "\n".join(log_tail)

                    raise RuntimeError(error_msg)

        finally:
            # Clean up temporary files
            if output_file.exists():
                output_file.unlink()
            if log_file.exists():
                log_file.unlink()


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
