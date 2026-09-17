"""PaddleOCR service wrapper with subprocess isolation.

OCR runs in a separate process (ocr_worker.py) to isolate PaddleOCR segfaults.
If the worker crashes, the main backend process is unaffected and can restart it.

Supports both PP-OCR (simple text extraction) and PP-StructureV3 (structured
document analysis) with a hybrid approach that allows automatic or manual engine
selection.
"""

import json
import logging
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

WORKER_SCRIPT = str(Path(__file__).parent / "ocr_worker.py")
REQUEST_TIMEOUT = 300  # 5 minutes per request


class SubprocessOCRService:
    """OCR service that runs PaddleOCR in an isolated subprocess.

    Communicates with ocr_worker.py via stdin/stdout JSON protocol.
    If the worker crashes (e.g. SIGSEGV), it is automatically restarted.
    """

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self._start_worker()

    def _start_worker(self) -> None:
        """Start (or restart) the OCR worker subprocess."""
        if self._proc is not None:
            try:
                self._proc.kill()
                self._proc.wait(timeout=5)
            except Exception:
                pass

        self._proc = subprocess.Popen(
            [sys.executable, WORKER_SCRIPT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,  # line-buffered
        )

        # Wait for ready signal
        try:
            while True:
                line = self._proc.stdout.readline()  # type: ignore[union-attr]
                if not line:
                    stderr_output = ""
                    if self._proc.stderr:
                        stderr_output = self._proc.stderr.read(4096).decode(errors="replace")
                    raise RuntimeError(f"OCR worker exited unexpectedly. stderr: {stderr_output}")
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    # Skip non-JSON lines (e.g. PaddleOCR debug output leaking to stdout)
                    logger.debug("OCR worker non-JSON output: %s", line[:200])
                    continue
                status = msg.get("status", "")
                if status == "ready":
                    logger.info("OCR worker subprocess ready")
                    return
                elif status == "error":
                    raise RuntimeError(f"OCR worker init error: {msg.get('message', 'unknown')}")
                else:
                    logger.info("OCR worker: %s", msg.get("message", status))
        except Exception:
            self._read_stderr()
            raise

    def _read_stderr(self) -> str:
        """Read any available stderr output for debugging."""
        stderr_output = ""
        if self._proc and self._proc.stderr:
            import select

            ready, _, _ = select.select([self._proc.stderr], [], [], 0.1)
            if ready:
                stderr_output = self._proc.stderr.read(8192).decode(errors="replace")
                if stderr_output:
                    logger.error("OCR worker stderr: %s", stderr_output[:2000])
        return stderr_output

    def _send_request(
        self,
        input_path: str,
        engine: str,
        method: str,
        timeout: int = REQUEST_TIMEOUT,
    ) -> Any:
        """Send a request to the worker and wait for response."""
        with self._lock:
            request_id = str(uuid.uuid4())
            request = json.dumps({
                "id": request_id,
                "input_path": input_path,
                "engine": engine,
                "method": method,
            })

            try:
                assert self._proc is not None and self._proc.stdin is not None
                self._proc.stdin.write((request + "\n").encode())
                self._proc.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                logger.warning("OCR worker pipe broken: %s — restarting", e)
                self._start_worker()
                raise RuntimeError("OCR worker crashed (broken pipe), restarted") from e

            # Read response with timeout using a thread
            result: list[str | None] = [None]
            error: list[BaseException | None] = [None]

            def _reader() -> None:
                try:
                    assert self._proc is not None and self._proc.stdout is not None
                    result[0] = self._proc.stdout.readline()
                except Exception as e:
                    error[0] = e

            t = threading.Thread(target=_reader, daemon=True)
            t.start()
            t.join(timeout=timeout)

            if t.is_alive():
                # Timeout — kill and restart
                logger.error("OCR request timed out after %ds — killing worker", timeout)
                try:
                    self._proc.kill()
                except Exception:
                    pass
                self._start_worker()
                raise RuntimeError(f"OCR request timed out after {timeout}s")

            if error[0]:
                raise RuntimeError(f"OCR read error: {error[0]}") from error[0]

            line = result[0]
            if not line:
                # Worker crashed
                stderr_output = self._read_stderr()
                logger.warning("OCR worker crashed (no response). stderr: %s", stderr_output[:500])
                self._start_worker()
                raise RuntimeError(f"OCR worker crashed, restarted. stderr: {stderr_output[:500]}")

            response = json.loads(line)
            if response.get("status") == "error":
                msg = response.get("message", "unknown")
                tb = response.get("traceback", "")
                logger.error("OCR error: %s\n%s", msg, tb)
                raise RuntimeError(f"OCR error: {msg}")

            return response.get("data")

    # ── Input helpers ──────────────────────────────────────────────

    def _to_path(self, image_input: str | Path | Image.Image | np.ndarray) -> str:
        """Convert input to a file path the worker can read."""
        if isinstance(image_input, Image.Image):
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            image_input.save(tmp.name)
            tmp.close()
            return tmp.name
        elif isinstance(image_input, np.ndarray):
            # numpy array → save as image
            img = Image.fromarray(image_input)
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            img.save(tmp.name)
            tmp.close()
            return tmp.name
        elif isinstance(image_input, Path):
            return str(image_input)
        return image_input  # type: ignore[return-value]

    def _is_pdf(self, image_input: str | Path | Image.Image) -> bool:
        if isinstance(image_input, (str, Path)):
            path = Path(image_input) if not isinstance(image_input, Path) else image_input
            return path.suffix.lower() == ".pdf"
        return False

    # ── Public API (same interface as before) ──────────────────────

    def extract_text(self, image_input: str | Path | Image.Image) -> str:
        path = self._to_path(image_input)
        return self._send_request(path, "pp_ocr", "extract_text")  # type: ignore[return-value]

    def extract_with_positions(
        self, image_input: str | Path | Image.Image
    ) -> list[dict[str, Any]]:
        path = self._to_path(image_input)
        return self._send_request(path, "pp_ocr", "extract_with_positions")  # type: ignore[return-value]

    def extract_structure(self, image_input: str | Path | Image.Image) -> dict[str, Any]:
        path = self._to_path(image_input)
        return self._send_request(path, "pp_structure", "extract_structure")  # type: ignore[return-value]

    def extract_markdown(self, image_input: str | Path | Image.Image) -> str:
        path = self._to_path(image_input)
        return self._send_request(path, "pp_structure", "extract_markdown")  # type: ignore[return-value]

    def extract(
        self,
        image_input: str | Path | Image.Image,
        engine: str | None = None,
        output_format: str = "text",
    ) -> str | list[dict[str, Any]] | dict[str, Any]:
        if engine is None:
            engine = "pp_structure" if self._is_pdf(image_input) else "pp_ocr"

        if engine == "pp_ocr":
            if output_format == "positions":
                return self.extract_with_positions(image_input)
            return self.extract_text(image_input)

        elif engine in ("pp_structurev3", "pp_structure"):
            if output_format == "markdown":
                return self.extract_markdown(image_input)
            elif output_format == "json":
                result = self.extract_structure(image_input)
                return result.get("json", {})  # type: ignore[return-value]
            elif output_format == "structure":
                return self.extract_structure(image_input)
            else:  # text → return markdown from structure
                return self.extract_markdown(image_input)

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
_ocr_service: SubprocessOCRService | FakeOCRService | None = None
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
        logger.info("Initializing OCR service (subprocess mode)...")
        service = SubprocessOCRService()
        with _ocr_lock:
            _ocr_service = service
            _ocr_initializing = False
        logger.info("OCR service initialized successfully")
    except Exception:
        with _ocr_lock:
            _ocr_initializing = False
        logger.exception("Failed to initialize OCR service")


def get_ocr_service() -> SubprocessOCRService | FakeOCRService | None:
    """Get the OCR service instance.

    Returns None if OCR service is disabled or not initialized (instead of raising).
    Callers should handle None gracefully.
    """
    if _ocr_service is None:
        if _ocr_initializing:
            logger.warning("OCR service is still initializing (loading ML models)")
            return None
        logger.debug("OCR service not initialized (disabled or init failed)")
        return None
    return _ocr_service
