"""File conversion service — converts document formats using libreoffice (headless).

Follows the same singleton pattern as ocr_service.py.
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


class FileConversionService:
    """Converts document formats using libreoffice (headless)."""

    def convert_to_docx(self, source_path: Path) -> Path | None:
        """Convert .doc to .docx. Returns path to .docx file, or None on failure.

        Caches the converted file alongside the source as ``<stem>.converted.docx``.
        """
        abs_path = source_path.resolve()

        if abs_path.suffix.lower() != ".doc":
            return None

        if not abs_path.exists():
            logger.warning("Source file not found: %s", abs_path)
            return None

        cached = abs_path.parent / f"{abs_path.stem}.converted.docx"
        if cached.exists():
            return cached

        sibling = abs_path.with_suffix(".docx")
        if sibling.exists() and sibling != abs_path:
            return sibling

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                result = subprocess.run(
                    [
                        "libreoffice",
                        "--headless",
                        "--norestore",
                        "--safe-mode",
                        "--convert-to",
                        "docx",
                        "--outdir",
                        tmpdir,
                        str(abs_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    converted = Path(tmpdir) / (abs_path.stem + ".docx")
                    if converted.exists():
                        try:
                            shutil.copy2(str(converted), str(cached))
                            logger.info("Cached .doc conversion: %s", cached)
                        except Exception:
                            logger.warning("Failed to cache conversion result", exc_info=True)
                        return cached

                stderr = result.stderr.strip() if result.stderr else ""
                logger.warning("libreoffice conversion failed (rc=%d): %s", result.returncode, stderr)
                return None
        except subprocess.TimeoutExpired:
            logger.warning("libreoffice conversion timed out: %s", abs_path.name)
            return None
        except FileNotFoundError:
            logger.warning("libreoffice not installed, cannot convert .doc files")
            return None
        except Exception:
            logger.exception("libreoffice conversion failed")
            return None


_conversion_service: FileConversionService | None = None


def init_file_conversion() -> None:
    """Initialize the file conversion service (no-op, libreoffice is a CLI tool)."""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = FileConversionService()
        logger.info("File conversion service initialized")


def get_file_conversion() -> FileConversionService:
    """Get the file conversion service singleton."""
    global _conversion_service
    if _conversion_service is None:
        _conversion_service = FileConversionService()
    return _conversion_service
