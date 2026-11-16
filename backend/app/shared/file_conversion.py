"""File conversion service — converts document formats using libreoffice (headless).

Follows the same singleton pattern as ocr_service.py.
"""

import hashlib
import logging
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

#: 默认转换超时（本地文件路径场景，沿用历史 120s）
_DEFAULT_TIMEOUT = 120

#: 在线预览场景的字节转换超时（HTTP 请求内，AGENTS.md 要求不超过 5s）
_PREVIEW_TIMEOUT = 5

#: libreoffice 并发上限：同一 user profile 并发实例会互相锁死，串行化到 2 个
_MAX_CONCURRENT_CONVERSIONS = 2

_UNSAFE_FILENAME_CHARS = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff._-]+")


def _safe_stem(filename: str) -> str:
    stem = Path(filename).stem or "document"
    cleaned = _UNSAFE_FILENAME_CHARS.sub("_", stem).strip("._")
    return cleaned[:80] or "document"


# 字节流转 PDF 的缓存目录与容量上限：预览会重复点，同一份文件不重复转换
_PDF_CACHE_DIR = Path(tempfile.gettempdir()) / "office-pdf-preview-cache"
_PDF_CACHE_MAX_FILES = 200
# 单次转换超时：大表格/多图文档偏慢，给足时间但不无限等。
# HTTP 请求内调用由调用方再套 5 秒硬超时（超时后本次转换仍在后台跑完并落缓存，
# 下次预览命中缓存即时返回），这里只需保证不会无限占用并发名额。
_CONVERT_TIMEOUT_SECONDS = 60


class FileConversionService:
    """Converts document formats using libreoffice (headless)."""

    _semaphore = threading.BoundedSemaphore(_MAX_CONCURRENT_CONVERSIONS)

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

        data = self._run_libreoffice(abs_path.read_bytes(), abs_path.name, timeout=_DEFAULT_TIMEOUT)
        if data is None:
            return None
        try:
            cached.write_bytes(data)
            logger.info("Cached .doc conversion: %s", cached)
        except Exception:
            logger.warning("Failed to cache conversion result", exc_info=True)
        return cached

    def convert_bytes_to_docx(self, data: bytes, filename: str, timeout: int = _PREVIEW_TIMEOUT) -> bytes | None:
        """Convert in-memory .doc bytes to .docx bytes (no filesystem cache).

        调用方负责结果缓存；本方法只保证「限并发 + 限时 + 失败返回 None」。
        """
        return self._run_libreoffice(data, filename, timeout=timeout)

    def _run_libreoffice(self, data: bytes, filename: str, *, timeout: int) -> bytes | None:
        if not data:
            return None
        suffix = Path(filename).suffix.lower() or ".doc"
        stem = _safe_stem(filename)

        # 排队等待与转换共享同一时间预算：HTTP 请求内调用时总耗时不得突破 timeout。
        deadline = time.monotonic() + timeout
        if not self._semaphore.acquire(timeout=timeout):
            logger.warning("libreoffice conversion queue saturated, skipped: %s", filename)
            return None
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                logger.warning("libreoffice conversion budget exhausted while queued: %s", filename)
                return None
            with tempfile.TemporaryDirectory() as tmpdir:
                source = Path(tmpdir) / f"{stem}{suffix}"
                source.write_bytes(data)
                outdir = Path(tmpdir) / "out"
                outdir.mkdir()
                result = subprocess.run(
                    [
                        "libreoffice",
                        "--headless",
                        "--norestore",
                        "--safe-mode",
                        "--convert-to",
                        "docx",
                        "--outdir",
                        str(outdir),
                        str(source),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=remaining,
                )
                if result.returncode == 0:
                    converted = outdir / f"{source.stem}.docx"
                    if converted.exists():
                        return converted.read_bytes()
                    logger.warning("libreoffice produced no output for %s", filename)
                    return None

                stderr = result.stderr.strip() if result.stderr else ""
                logger.warning("libreoffice conversion failed (rc=%d): %s", result.returncode, stderr)
                return None
        except subprocess.TimeoutExpired:
            logger.warning("libreoffice conversion timed out: %s", filename)
            return None
        except FileNotFoundError:
            logger.warning("libreoffice not installed, cannot convert .doc files")
            return None
        except Exception:
            logger.exception("libreoffice conversion failed")
            return None
        finally:
            self._semaphore.release()

    def convert_bytes_to_pdf(self, content: bytes, filename: str) -> bytes | None:
        """把 Office 文档字节流转成 PDF 字节流（在线预览用）。失败返回 None。

        为什么要转：浏览器只能原生渲染 pdf/图片/纯文本，``.doc``/``.xls``/``.xlsx``/
        ``.ppt`` 这类格式直接内联打开只会触发下载，用户看到的「无法预览」就是这个原因。
        转换结果按内容 sha256 缓存在临时目录，重复预览不再调用 LibreOffice。

        并发安全：每次转换用独立的 UserInstallation 配置目录，避免多个 soffice
        实例争抢同一个用户配置而互相失败。
        """
        if not content:
            return None
        digest = hashlib.sha256(content).hexdigest()
        cached = _PDF_CACHE_DIR / f"{digest}.pdf"
        if cached.exists():
            try:
                return cached.read_bytes()
            except OSError:
                logger.warning("读取 PDF 预览缓存失败，重新转换", exc_info=True)

        suffix = Path(filename or "").suffix or ".bin"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                source = Path(tmpdir) / f"source{suffix}"
                source.write_bytes(content)
                profile = Path(tmpdir) / "profile"
                result = subprocess.run(
                    [
                        "libreoffice",
                        "--headless",
                        "--norestore",
                        f"-env:UserInstallation=file://{profile}",
                        "--convert-to",
                        "pdf",
                        "--outdir",
                        tmpdir,
                        str(source),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=_CONVERT_TIMEOUT_SECONDS,
                )
                converted = Path(tmpdir) / "source.pdf"
                if result.returncode != 0 or not converted.exists():
                    stderr = (result.stderr or "").strip()
                    logger.warning("libreoffice 转 PDF 失败 (rc=%s): %s", result.returncode, stderr)
                    return None
                pdf = converted.read_bytes()
        except subprocess.TimeoutExpired:
            logger.warning("libreoffice 转 PDF 超时: %s", filename)
            return None
        except FileNotFoundError:
            logger.warning("未安装 libreoffice，无法转换 %s", filename)
            return None
        except Exception:
            logger.exception("libreoffice 转 PDF 失败")
            return None

        try:
            _PDF_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _prune_pdf_cache()
            cached.write_bytes(pdf)
        except OSError:
            logger.warning("写入 PDF 预览缓存失败（不影响本次预览）", exc_info=True)
        return pdf


def _prune_pdf_cache() -> None:
    """缓存超过上限时按修改时间淘汰最旧的文件。"""
    try:
        files = sorted(_PDF_CACHE_DIR.glob("*.pdf"), key=lambda path: path.stat().st_mtime)
    except OSError:
        return
    for stale in files[: max(0, len(files) - _PDF_CACHE_MAX_FILES + 1)]:
        try:
            stale.unlink()
        except OSError:
            logger.debug("清理 PDF 预览缓存失败: %s", stale, exc_info=True)


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
