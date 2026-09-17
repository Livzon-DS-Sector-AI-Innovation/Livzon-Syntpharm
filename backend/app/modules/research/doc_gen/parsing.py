"""研发文档生成 — 上传资料解析（文件类型 → 专用提取库）。

**支持的文档类型**（不含音频/视频；图片仅作为扫描件 OCR 回退通道保留）：

| 类型 | 扩展名 | 专用提取库 |
|---|---|---|
| PDF | .pdf | pdfplumber（逐页文字/表格）→ pypdf（回退）→ 全局 OCR 单例（无文字层） |
| Word | .docx .dotx | python-docx |
| Word 旧格式 | .doc .wps | LibreOffice headless 转 .docx → python-docx（回退：OLE 文本抢救） |
| Excel | .xlsx .xlsm .xltx .xltm | openpyxl |
| Excel 旧格式 | .xls .et | xlrd |
| PowerPoint | .pptx .ppsx .sldx | 标准库 zipfile + ElementTree（OOXML ``a:t`` 文本节点） |
| OpenDocument | .odt .ods .odp | 标准库 zipfile + ElementTree（content.xml 文本节点） |
| CSV/TSV | .csv .tsv | 标准库 csv |
| JSON | .json | 标准库 json（递归展开为「路径: 值」行） |
| XML | .xml | 标准库 xml.etree |
| HTML | .html .htm | 标准库 html.parser |
| RTF | .rtf | 内置 RTF 控制字剥离器（无第三方依赖） |
| 纯文本 | .txt .md .markdown .rst .log .ini .conf .csv 等 | 标准库文本读取 + 编码嗅探 |
| 图片 | .png .jpg .jpeg .bmp .webp .tif .tiff | app.shared.ocr_service 全局单例 |

三个稳定性契约：

1. **未知类型不报错**：扩展名不在表内时按 MIME → 魔数 → 文本可解码性逐级判定，
   能读出文字就读，读不出就记 warning 返回空结果。后台任务绝不允许崩溃。
2. **强制终止**：每个解析循环都在 ``_Guard.tick()`` 处检查「取消标志 + 硬超时」。
   同步解析跑在 ``asyncio.to_thread`` 里，外层 ``asyncio.wait_for`` 兜底：
   即使第三方库卡在 C 层无法响应，事件循环也不会被拖住，调用方仍能取消任务、
   前端仍能轮询，卡住的线程由 ``threading.Event`` 通知其尽快退出。
3. **空值处理**：文件缺失、0 字节、编码失败、库缺失、解析异常一律降级为 warning，
   返回已解析的部分结果。

OCR 一律通过 app.shared.ocr_service 的全局单例延迟获取（函数内 import + 调用），
禁止在模块顶层 import paddleocr 或初始化 OCR 引擎，避免拖慢启动且无法在测试中 mock。
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 仅含图片、必须走 OCR 的扩展名
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}

# docx 段落样式名包含以下片段即视为标题（兼容中英文 Word 样式）
_HEADING_HINTS = ("heading", "标题")

# 扫描件 PDF 逐页 OCR 的页数保护上限，避免超大文件拖垮后台任务
_MAX_OCR_PAGES = 50

# 抢救式提取的判定阈值：可读出文字至少要占文件字节的这个比例，否则视为不可读二进制
_MIN_SALVAGE_COVERAGE = 0.02
# 连续可打印片段达到该长度才收录，过滤 OLE 里的碎片与字段名
_MIN_SALVAGE_RUN = 8

TEXTUAL_EXTENSIONS = (".txt", ".md", ".markdown", ".rst", ".log", ".ini", ".conf", ".text")

_ABORT_CANCELLED = "cancelled"
_ABORT_TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class FormatSpec:
    """一种受支持文档类型的自述：扩展名、MIME、所用提取库。"""

    name: str
    extensions: tuple[str, ...]
    mimes: tuple[str, ...]
    library: str
    needs_ocr: bool = False


# 单一真相来源：上传校验白名单、前端 accept、解析分派表都由它派生
FORMATS: tuple[FormatSpec, ...] = (
    FormatSpec(
        "PDF",
        (".pdf",),
        ("application/pdf",),
        "pdfplumber（逐页文字）→ pypdf（回退）→ PaddleOCR（无文字层）",
    ),
    FormatSpec("Word", (".docx", ".dotx"), ("wordprocessingml.document", "wordprocessingml.template"), "python-docx"),
    FormatSpec("Word 97-2003", (".doc", ".wps"), ("msword", "wps-office"), "LibreOffice 转 .docx → python-docx"),
    FormatSpec(
        "Excel",
        (".xlsx", ".xlsm", ".xltx", ".xltm"),
        ("spreadsheetml.sheet", "spreadsheetml.template"),
        "openpyxl",
    ),
    FormatSpec("Excel 97-2003", (".xls", ".et"), ("ms-excel",), "xlrd"),
    FormatSpec(
        "PowerPoint",
        (".pptx", ".ppsx", ".sldx"),
        ("presentationml.presentation", "presentationml.slideshow"),
        "zipfile + ElementTree",
    ),
    FormatSpec(
        "OpenDocument",
        (".odt", ".ods", ".odp"),
        ("vnd.oasis.opendocument",),
        "zipfile + ElementTree",
    ),
    FormatSpec("CSV/TSV", (".csv", ".tsv"), ("csv", "tab-separated-values", "text/comma-separated-values"), "csv"),
    FormatSpec("JSON", (".json",), ("json",), "json"),
    FormatSpec("XML", (".xml",), ("xml",), "xml.etree"),
    FormatSpec("HTML", (".html", ".htm"), ("html",), "html.parser"),
    FormatSpec("RTF", (".rtf",), ("rtf", "rich-text-format"), "内置 RTF 剥离器"),
    FormatSpec("纯文本", TEXTUAL_EXTENSIONS, ("text/plain", "text/markdown"), "标准库文本读取 + 编码嗅探"),
    FormatSpec("图片（OCR）", tuple(sorted(IMAGE_EXTENSIONS)), ("image/",), "app.shared.ocr_service 全局单例", True),
)

_EXT_TO_FORMAT: dict[str, FormatSpec] = {ext: spec for spec in FORMATS for ext in spec.extensions}

# OOXML / ODF 都是 zip 容器，靠包内首层目录名区分具体类型
_ZIP_PACKAGE_HINTS = (("word/", "Word"), ("xl/", "Excel"), ("ppt/", "PowerPoint"))
_ODF_MIME_RE = re.compile(r"^application/vnd\.oasis\.opendocument\.(\w+)")


@dataclass(slots=True)
class TextBlock:
    """单个文本块。file_id 为调用方传入的稳定标识；page 从 1 开始；index 文件内从 0 递增。"""

    file_id: str
    page: int
    index: int
    text: str
    kind: str  # "heading" | "paragraph" | "table_row" | "sheet_row"


@dataclass(slots=True)
class ParseResult:
    """单个文件的解析结果。"""

    blocks: list[TextBlock]
    page_count: int
    char_count: int
    ocr_used: bool
    warnings: list[str]
    format_name: str = ""  # 实际使用的类型（回退时为「纯文本」等），供生成说明展示
    aborted: str = ""  # "" | "cancelled" | "timeout" | "not_found" | "empty" | "unsupported"


class ParseAbortError(Exception):
    """解析被强制终止（取消或超时）。内部信号，不向调用方抛出。"""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class _Guard:
    """取消 + 硬超时的检查点。解析循环每处理一个单元就 tick 一次。"""

    __slots__ = ("deadline", "reason", "should_cancel")

    def __init__(
        self,
        should_cancel: Callable[[], bool] | None = None,
        deadline: float | None = None,
    ) -> None:
        self.should_cancel = should_cancel
        self.deadline = deadline
        self.reason = ""

    def tick(self) -> None:
        if self.reason:
            raise ParseAbortError(self.reason)
        if self.should_cancel is not None and self.should_cancel():
            self.reason = _ABORT_CANCELLED
            raise ParseAbortError(self.reason)
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.reason = _ABORT_TIMEOUT
            raise ParseAbortError(self.reason)

    @staticmethod
    def none() -> _Guard:
        return _Guard()


class _Collector:
    """收集文本块，维护文件内 index 与全局字符上限（超限即截断）。"""

    def __init__(self, file_id: str, max_chars: int, guard: _Guard | None = None) -> None:
        self.file_id = file_id
        self.max_chars = max_chars
        self.blocks: list[TextBlock] = []
        self.char_count = 0
        self.truncated = False
        self.guard = guard or _Guard.none()

    def add(self, page: int, text: str, kind: str) -> bool:
        """追加一个块；返回 False 表示已达字符上限，调用方应停止继续解析。"""
        self.guard.tick()
        text = text.strip()
        if not text:
            return True
        remaining = self.max_chars - self.char_count
        if remaining <= 0:
            self.truncated = True
            return False
        if len(text) > remaining:
            text = text[:remaining]
            self.truncated = True
        self.blocks.append(TextBlock(self.file_id, page, len(self.blocks), text, kind))
        self.char_count += len(text)
        return not self.truncated

    def add_multiline(self, page: int, text: str, kind: str = "paragraph") -> bool:
        """按行拆分后逐行收集（用于 OCR 输出与纯文本）。"""
        for line in text.splitlines():
            if not self.add(page, line, kind):
                return False
        return True


def supported_extensions() -> list[str]:
    """全部受支持扩展名（上传校验与前端 accept 的唯一来源）。"""
    return sorted(_EXT_TO_FORMAT)


def supported_formats() -> list[dict[str, Any]]:
    """受支持类型清单（类型名、扩展名、所用提取库），供前端展示「支持哪些格式」。"""
    return [
        {
            "name": spec.name,
            "extensions": list(spec.extensions),
            "library": spec.library,
            "needs_ocr": spec.needs_ocr,
        }
        for spec in FORMATS
    ]


def _get_ocr_service() -> Any | None:
    """获取全局 OCR 单例；不可用（未初始化/异常/返回 None）时返回 None，不抛出。"""
    try:
        from app.shared import ocr_service as ocr_module

        service = ocr_module.get_ocr_service()
    except Exception:
        logger.exception("OCR 服务不可用")
        return None
    if service is None:
        # OCR 服务未初始化或被禁用，静默返回 None
        return None
    return service


def _ocr_images(images: list[Any], structured: bool = False) -> list[str]:
    """对一组 PIL 图片执行 OCR，返回每图文本。

    ``structured=True`` 走 PP-StructureV3 输出 Markdown（保留表格、标题层级与阅读顺序），
    比 PP-OCR 慢数倍，只在快速通道（PP-OCR）没拿到结果时启用做二次尝试。
    """
    service = _get_ocr_service()
    if service is None:
        raise RuntimeError("OCR 服务不可用")
    texts: list[str] = []
    for image in images:
        raw: Any = ""
        if structured:
            raw = service.extract(image, output_format="markdown")
            if isinstance(raw, dict):
                raw = str(raw.get("markdown") or "")
        else:
            raw = service.extract_text(image)
        texts.append(str(raw) if raw else "")
    return texts


# ─────────────────────────── 类型判定（扩展名 → MIME → 魔数） ───────────────────────────


def _format_by_extension(ext: str) -> FormatSpec | None:
    return _EXT_TO_FORMAT.get(ext.lower())


def _format_by_mime(mime: str) -> FormatSpec | None:
    """MIME 只作辅助：子类型里含关键片段即命中（如 application/vnd.ms-excel）。"""
    lowered = (mime or "").lower()
    if not lowered:
        return None
    for spec in FORMATS:
        for token in spec.mimes:
            if token in lowered:
                return spec
    return None


def _is_container(head: bytes) -> bool:
    """zip 容器（OOXML/ODF）或 OLE2 复合文档：细分不出具体类型时不能当文本读。"""
    return head.startswith(b"PK\x03\x04") or head.startswith(b"\xd0\xcf\x11\xe0")


def _sniff_magic(head: bytes) -> FormatSpec | None:
    """按文件头魔数判定类型，用于扩展名缺失或与实际内容不符的场景。"""
    if head.startswith(b"%PDF-"):
        return _format_by_extension(".pdf")
    if head.startswith(b"{\\rtf"):
        return _format_by_extension(".rtf")
    if _is_container(head):
        return None  # 容器类：交给 detect_format 细分，细分不出就按未知处理，不做文本抢救
    stripped = head.lstrip()
    if stripped[:14].lower().startswith(b"<!doctype html") or stripped[:6].lower().startswith(b"<html>"):
        return _format_by_extension(".html")
    if stripped[:5].lower().startswith(b"<?xml"):
        return _format_by_extension(".xml")
    if stripped[:1] in (b"{", b"["):
        return _format_by_extension(".json")
    return None


def _resolve_zip_package(path: Path) -> FormatSpec | None:
    """zip 容器按包内结构细分：OOXML 看首层目录，ODF 看 mimetype 条目。"""
    try:
        with zipfile.ZipFile(str(path)) as archive:
            names = [info.filename for info in archive.infolist()[:200]]
    except Exception:
        logger.exception("zip 容器无法打开", extra={"path_name": path.name})
        return None
    for prefix, label in _ZIP_PACKAGE_HINTS:
        if any(name.startswith(prefix) for name in names):
            return _format_by_extension({"Word": ".docx", "Excel": ".xlsx", "PowerPoint": ".pptx"}[label])
    if "mimetype" in names:
        try:
            with zipfile.ZipFile(str(path)) as archive:
                mime = archive.read("mimetype").decode("utf-8", "replace")
            match = _ODF_MIME_RE.match(mime.strip())
            if match:
                return _format_by_extension({"text": ".odt", "spreadsheet": ".ods", "presentation": ".odp"}.get(
                    match.group(1), ".odt"
                ))
        except Exception:
            logger.exception("ODF mimetype 条目读取失败", extra={"path_name": path.name})
    return None


def detect_format(path: Path, mime_hint: str | None = None) -> tuple[FormatSpec | None, str]:
    """判定文件类型，返回 (类型, 判定依据)。判定不到返回 (None, "")。"""
    ext = path.suffix.lower()
    spec = _format_by_extension(ext)
    if spec is not None:
        return spec, "extension"
    spec = _format_by_mime(mime_hint or "")
    if spec is not None:
        return spec, "mime"
    try:
        with open(path, "rb") as handle:
            head = handle.read(2048)
    except OSError:
        return None, "unreadable"
    if head.startswith(b"PK\x03\x04"):
        resolved = _resolve_zip_package(path)
        if resolved is not None:
            return resolved, "magic"
        return None, "container"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return None, "container"
    spec = _sniff_magic(head)
    if spec is not None:
        return spec, "magic"
    return None, ""


# ─────────────────────────── 各类型专用提取器 ───────────────────────────


def _parse_pdf(
    path: Path,
    collector: _Collector,
    warnings: list[str],
    max_pages: int | None = None,
    max_ocr_pages: int | None = None,
    ocr_structured: bool = False,
) -> tuple[int, bool]:
    """解析 PDF。优先 pdfplumber 逐页取文字；空白页回退 OCR。返回 (页数, 是否使用 OCR)。

    OCR 是 CPU 密集操作（扫描件每页数秒），因此页数与 OCR 页数都要设上限并在说明里告知，
    否则一份 300 页扫描专利能把任务拖到不可用。

    ``max_ocr_pages=0`` 表示显式禁用 OCR（调用方想先只拿文字层，OCR 留给上层兜底链）。
    """
    try:
        import pdfplumber
    except Exception:
        logger.exception("pdfplumber 不可用，PDF 改用 pypdf 回退")
        return _parse_pdf_pypdf(path, collector, warnings, max_pages=max_pages)

    page_count = 0
    ocr_used = False
    empty_pages: list[int] = []

    try:
        with pdfplumber.open(str(path)) as pdf:
            total_pages = len(pdf.pages)
            for page_no, page in enumerate(pdf.pages, start=1):
                if max_pages is not None and page_no > max_pages:
                    warnings.append(f"文件共 {total_pages} 页，仅解析前 {max_pages} 页")
                    page_count = total_pages
                    break
                page_count = page_no
                text = page.extract_text() or ""
                if text.strip():
                    if not collector.add_multiline(page_no, text):
                        return page_count, ocr_used
                else:
                    empty_pages.append(page_no)
            if max_pages is not None and total_pages > max_pages:
                page_count = total_pages
    except ParseAbortError:
        raise
    except Exception:
        logger.exception("pdfplumber 解析失败，改用 pypdf 回退", extra={"path_name": path.name})
        warnings.append("PDF 主解析器失败，已改用 pypdf 回退")
        return _parse_pdf_pypdf(path, collector, warnings, max_pages=max_pages)

    if empty_pages:
        if max_ocr_pages is not None and max_ocr_pages <= 0:
            warnings.append(f"{len(empty_pages)} 页无文字层，本次未启用 OCR")
        else:
            if max_ocr_pages is not None and len(empty_pages) > max_ocr_pages:
                warnings.append(f"{len(empty_pages)} 页无文字层，仅 OCR 前 {max_ocr_pages} 页，其余需人工补充")
                empty_pages = empty_pages[:max_ocr_pages]
            ocr_used = _ocr_pdf_pages(path, empty_pages, collector, warnings, structured=ocr_structured)

    if collector.char_count == 0:
        warnings.append("未能提取到文字")
    return page_count, ocr_used


def _parse_pdf_pypdf(
    path: Path, collector: _Collector, warnings: list[str], max_pages: int | None = None
) -> tuple[int, bool]:
    """pypdf 回退：只取页面文字，不做表格与 OCR。"""
    try:
        from pypdf import PdfReader
    except Exception:
        logger.exception("pypdf 也不可用")
        warnings.append("PDF 解析组件不可用")
        return 0, False
    page_count = 0
    try:
        reader = PdfReader(str(path))
        for page_no, page in enumerate(reader.pages, start=1):
            if max_pages is not None and page_no > max_pages:
                break
            page_count = page_no
            text = page.extract_text() or ""
            if text.strip() and not collector.add_multiline(page_no, text):
                break
    except ParseAbortError:
        raise
    except Exception:
        logger.exception("pypdf 解析失败", extra={"path_name": path.name})
        warnings.append("PDF 结构损坏，未能提取文字")
    if collector.char_count == 0:
        warnings.append("未能提取到文字")
    return page_count, False


def _ocr_pdf_pages(
    path: Path, pages: list[int], collector: _Collector, warnings: list[str], structured: bool = False
) -> bool:
    """对指定 PDF 页面做 OCR 回退，返回是否实际调用了 OCR。任何失败只记 warning。"""
    if _get_ocr_service() is None:
        warnings.append("扫描件无文字层，且 OCR 服务不可用")
        return False
    if structured:
        warnings.append("扫描件无文字层，已使用结构化 OCR（保留表格与版式）")
    else:
        warnings.append("扫描件无文字层，已使用 OCR")
    try:
        from pdf2image import convert_from_path
    except Exception:
        logger.exception("pdf2image 不可用，无法对扫描件执行 OCR")
        warnings.append("扫描件无文字层，OCR 转换组件不可用")
        return False

    targets = pages[:_MAX_OCR_PAGES]
    if len(pages) > _MAX_OCR_PAGES:
        warnings.append(f"扫描件页数过多，仅 OCR 前 {_MAX_OCR_PAGES} 页")
    try:
        # 批量转换所有页面（比逐页 convert_from_path 快 3-5 倍，减少进程启动开销）
        first_page = targets[0]
        last_page = targets[-1]
        all_images = convert_from_path(str(path), dpi=120, first_page=first_page, last_page=last_page)
        # 批量 OCR（PaddleOCR 支持 list[ndarray] 批量输入，比逐张调用更高效）
        all_texts = _ocr_images(list(all_images), structured=structured)
        for offset, page_no in enumerate(targets):
            collector.guard.tick()
            if offset < len(all_texts):
                text = all_texts[offset]
                if text and text.strip():
                    if not collector.add_multiline(page_no, text):
                        return True
    except ParseAbortError:
        raise
    except Exception:
        logger.exception("PDF 扫描件 OCR 失败")
        warnings.append("扫描件无文字层，已使用 OCR（部分页面识别失败）")
    return True


def _parse_docx(path: Path, collector: _Collector) -> None:
    """解析 docx/dotx：段落（Heading 样式标 heading）+ 表格行（单元格用 " | " 连接）。"""
    from docx import Document

    doc = Document(str(path))
    for para in doc.paragraphs:
        style_name = str(getattr(para.style, "name", "") or "")
        kind = "heading" if any(h in style_name.lower() for h in _HEADING_HINTS) else "paragraph"
        if not collector.add(1, para.text, kind):
            return
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if not collector.add(1, " | ".join(cells), "table_row"):
                return


def _parse_xlsx(path: Path, collector: _Collector) -> None:
    """解析 xlsx：openpyxl 逐行，page 为 sheet 序号（从 1 开始）。"""
    import openpyxl

    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    try:
        for sheet_no, ws in enumerate(wb.worksheets, start=1):
            for row in ws.iter_rows(values_only=True):
                cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                if not collector.add(sheet_no, " | ".join(cells), "sheet_row"):
                    return
    finally:
        wb.close()


def _parse_xls(path: Path, collector: _Collector) -> None:
    """解析 xls（旧格式）：xlrd 逐行，page 为 sheet 序号。"""
    import xlrd  # xlrd 未提供类型存根

    book = xlrd.open_workbook(str(path))
    for sheet_no in range(book.nsheets):
        sheet = book.sheet_by_index(sheet_no)
        for r in range(sheet.nrows):
            cells = [
                str(sheet.cell_value(r, c)).strip()
                for c in range(sheet.ncols)
                if str(sheet.cell_value(r, c)).strip()
            ]
            if not collector.add(sheet_no, " | ".join(cells), "sheet_row"):
                return


def _read_text(path: Path, collector: _Collector) -> str:
    """按多种编码尝试读取文本，返回解码结果；全部失败返回空串。"""
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030", "utf-16", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
        except Exception:
            logger.exception("文本解码异常", extra={"path_name": path.name, "encoding": encoding})
            return ""
    logger.warning("文本编码无法识别", extra={"path_name": path.name})
    return ""


def _parse_text_file(path: Path, collector: _Collector) -> None:
    """解析 txt/md：空行分段，无页概念统一 page=1。"""
    raw = _read_text(path, collector)
    for para in re.split(r"\n\s*\n", raw):
        joined = " ".join(line.strip() for line in para.splitlines() if line.strip())
        if not collector.add(1, joined, "paragraph"):
            return


def _parse_delimited(path: Path, collector: _Collector, delimiter: str) -> None:
    """解析 csv/tsv：标准库 csv 逐行，单元格用 " | " 连接，每 50 行记为一页。"""
    import csv
    from io import StringIO

    raw = _read_text(path, collector)
    if not raw.strip():
        return
    reader = csv.reader(StringIO(raw), delimiter=delimiter)
    for index, row in enumerate(reader, start=1):
        cells = [str(cell).strip() for cell in row if str(cell).strip()]
        if not collector.add(1 + index // 50, " | ".join(cells), "sheet_row"):
            return


def _flatten_json(value: Any, prefix: str, out: list[str], depth: int = 0) -> None:
    """把 JSON 结构展开成「路径: 值」行，供检索按行命中。"""
    if depth > 6 or len(out) > 5000:
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _flatten_json(item, f"{prefix}.{key}" if prefix else str(key), out, depth + 1)
    elif isinstance(value, list):
        for position, item in enumerate(value):
            _flatten_json(item, f"{prefix}[{position}]", out, depth + 1)
    elif value is not None:
        text = str(value).strip()
        if text:
            out.append(f"{prefix}: {text}" if prefix else text)


def _parse_json(path: Path, collector: _Collector, warnings: list[str]) -> None:
    import json

    raw = _read_text(path, collector)
    if not raw.strip():
        return
    try:
        data: Any = json.loads(raw)
    except Exception:
        logger.exception("JSON 解析失败，按纯文本处理", extra={"path_name": path.name})
        warnings.append("JSON 结构非法，已按纯文本读取")
        collector.add_multiline(1, raw)
        return
    lines: list[str] = []
    _flatten_json(data, "", lines)
    for line in lines:
        if not collector.add(1, line, "paragraph"):
            return


def _parse_xml(path: Path, collector: _Collector, warnings: list[str]) -> None:
    """解析 xml：逐元素输出「标签: 文本」，属性一并保留（资料里的参数常写在属性上）。"""
    import xml.etree.ElementTree as ET

    raw = _read_text(path, collector)
    if not raw.strip():
        return
    try:
        root = ET.fromstring(raw)
    except Exception:
        logger.exception("XML 解析失败，按纯文本处理", extra={"path_name": path.name})
        warnings.append("XML 结构非法，已按纯文本读取")
        collector.add_multiline(1, raw)
        return
    stack: list[ET.Element] = [root]
    while stack:
        element = stack.pop()
        attrs = " ".join(f"{key}={value}" for key, value in sorted(element.attrib.items()))
        text = " ".join((element.text or "").split())
        label = str(element.tag).rsplit("}", 1)[-1]
        line = " ".join(part for part in (f"{label}:", text, attrs) if part).strip()
        if line and line != f"{label}:":
            if not collector.add(1, line, "paragraph"):
                return
        stack.extend(reversed(list(element)))


class _HTMLTextExtractor(HTMLParser):
    """标准库 HTMLParser 子类：只收集可见文本，块级标签换行，跳过 script/style。"""

    _SKIP = {"script", "style", "noscript"}
    _BLOCK = {"p", "div", "br", "li", "ul", "ol", "tr", "table", "h1", "h2", "h3", "h4", "h5", "h6", "section"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.chunks: list[str] = []
        self._buffer: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        if tag in self._BLOCK:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in self._BLOCK:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data.strip():
            self._buffer.append(data.strip())

    def _flush(self) -> None:
        if self._buffer:
            self.chunks.append(" ".join(self._buffer))
            self._buffer = []

    def finish(self) -> list[str]:
        self._flush()
        return self.chunks


def _parse_html(path: Path, collector: _Collector, warnings: list[str]) -> None:
    raw = _read_text(path, collector)
    if not raw.strip():
        return
    parser = _HTMLTextExtractor()
    try:
        parser.feed(raw)
    except Exception:
        logger.exception("HTML 解析失败，按纯文本处理", extra={"path_name": path.name})
        warnings.append("HTML 结构异常，已按纯文本读取")
        collector.add_multiline(1, re.sub(r"<[^>]+>", " ", raw))
        return
    for chunk in parser.finish():
        if not collector.add(1, chunk, "paragraph"):
            return


_RTF_CTRL_RE = re.compile(r"\\[a-z]{1,32}-?\d{0,4} ?")
_RTF_UNICODE_RE = re.compile(r"\\'([0-9a-fA-F]{2})")


def _strip_rtf(raw: str) -> str:
    """剥离 RTF 控制字与样式表，保留正文；``\\uN`` 与 ``\\'xx`` 还原成字符。"""
    text = re.sub(r"\{\\\*\\[^{}]*\}", " ", raw)  # 样式表等忽略目标
    text = re.sub(r"\\stylesheet[^{}]*", " ", text)
    text = _RTF_CTRL_RE.sub(" ", text)
    text = re.sub(r"\\par[d]?", "\n", text)
    text = re.sub(r"\\line", "\n", text)

    def _unicode(match: re.Match[str]) -> str:
        number = int(match.group(1))
        return chr(number if number >= 0 else number + 65536) if number else ""

    text = re.sub(r"\\u(-?\d+)\s?", _unicode, text)
    text = _RTF_UNICODE_RE.sub(lambda m: chr(int(m.group(1), 16)), text)
    return re.sub(r"[{}]", "", text)


def _parse_rtf(path: Path, collector: _Collector, warnings: list[str]) -> None:
    raw = _read_text(path, collector)
    if not raw.strip():
        return
    stripped = _strip_rtf(raw)
    if not stripped.strip():
        warnings.append("RTF 未能提取到文字")
        return
    for para in re.split(r"\n\s*\n", stripped):
        joined = " ".join(line.strip() for line in para.splitlines() if line.strip())
        if not collector.add(1, joined, "paragraph"):
            return


def _xml_text_of(archive: zipfile.ZipFile, member: str, collector: _Collector, kinds: set[str]) -> bool:
    """读取 zip 内某个 xml 部件，按 kinds 指定的元素标签收集文本。返回 False 表示已达上限。"""
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(archive.read(member))
    except Exception:
        logger.exception("OOXML/ODF 部件解析失败", extra={"member": member})
        return True
    current: list[str] = []
    for element in root.iter():
        tag = str(element.tag).rsplit("}", 1)[-1]
        if tag in kinds:
            text = "".join(element.itertext()).strip()
            if not text:
                continue
            current.append(text)
            continue
        if tag in ("p", "tr", "list-item", "h"):
            if current:
                if not collector.add(1, " ".join(current), "paragraph"):
                    return False
                current = []
    if current:
        return collector.add(1, " ".join(current), "paragraph")
    return True


def _parse_ooxml_presentation(path: Path, collector: _Collector, warnings: list[str]) -> None:
    """pptx/ppsx：逐张幻灯片取 <a:t> 文本，page 为幻灯片序号。"""
    slide_re = re.compile(r"^ppt/slides/slide(\d+)\.xml$")
    try:
        with zipfile.ZipFile(str(path)) as archive:
            slides = sorted(
                ((int(m.group(1)), name) for name in archive.namelist() if (m := slide_re.match(name))),
                key=lambda item: item[0],
            )
            if not slides:
                warnings.append("未在演示文稿中找到幻灯片")
                return
            for number, member in slides:
                collector.guard.tick()
                if not _xml_text_of(archive, member, collector, {"t"}):
                    return
    except zipfile.BadZipFile:
        logger.exception("pptx 容器损坏", extra={"path_name": path.name})
        warnings.append("演示文稿文件损坏")


def _parse_opendocument(path: Path, collector: _Collector, warnings: list[str]) -> None:
    """odt/ods/odp：读 content.xml，按段落/表格行/单元格收集文本。"""
    try:
        with zipfile.ZipFile(str(path)) as archive:
            if "content.xml" not in archive.namelist():
                warnings.append("OpenDocument 缺少 content.xml")
                return
            kinds = {"text:p", "text:h", "table:table-cell", "text:span"}
            simple = {"p", "h", "table-cell", "span", "list-item"}
            if not _xml_text_of(archive, "content.xml", collector, kinds | simple):
                return
    except zipfile.BadZipFile:
        logger.exception("OpenDocument 容器损坏", extra={"path_name": path.name})
        warnings.append("OpenDocument 文件损坏")


# 可打印片段字符类：中日韩文字、拉丁字母数字与常见标点/单位符号
_PRINTABLE_CLASS = r"\u4e00-\u9fff\u3000-\u303fA-Za-z0-9\u00c0-\u024f，。；：、（）()%.\-/"
_PRINTABLE_RE = re.compile(f"[{_PRINTABLE_CLASS}]{{{_MIN_SALVAGE_RUN},}}")


# 高频中文虚词：真实中文文本里占比可观，随机字节解码出的"伪中日韩文"几乎不含
_CN_FUNCTION_CHARS = "的了和是在有与及对于为将由以于个中要可不能够已经发生研究"


def _looks_like_text(text: str) -> bool:
    """判断抢救出的字符串是否像自然语言。

    二进制按 utf-16 解码会得到大量合法的中日韩码位，光看"可打印比例"根本挡不住；
    一旦把这些碎片喂给模型，产出的槽位值会看起来像模像样却全是编造的。
    因此再加一道语言特征闸门：要么含足够多的高频中文虚词，要么以拉丁字母为主。
    """
    if not text:
        return False
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    if not cjk:
        letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
        return letters / max(1, len(text)) > 0.35
    function = sum(1 for ch in text if ch in _CN_FUNCTION_CHARS)
    letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    return function / cjk > 0.03 or letters / max(1, len(text)) > 0.3


# LibreOffice 转换超时（秒）：.doc 文件通常几秒内完成，大文件给 60 秒上限
_LIBREOFFICE_TIMEOUT = 60


def _convert_doc_to_docx(path: Path, warnings: list[str]) -> Path | None:
    """用 LibreOffice headless 把 .doc/.wps 转成 .docx，返回转换后路径；失败返回 None。

    Docker 镜像已预装 libreoffice（Dockerfile 第 18 行）。转换在临时目录进行，
    避免污染原文件。转换失败时静默降级，由调用方走 _salvage_text 兜底。
    """
    temp_dir = None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="docgen-convert-"))
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--convert-to", "docx",
                "--outdir", str(temp_dir),
                str(path),
            ],
            capture_output=True,
            timeout=_LIBREOFFICE_TIMEOUT,
            check=False,
        )
        if result.returncode != 0:
            logger.warning(
                "LibreOffice 转换失败",
                extra={"file": path.name, "returncode": result.returncode, "stderr": result.stderr[:200]},
            )
            return None
        # 转换后文件名：原文件名 + .docx
        converted = temp_dir / f"{path.stem}.docx"
        if not converted.exists():
            # LibreOffice 有时用原始扩展名，尝试查找任何 .docx
            docx_files = list(temp_dir.glob("*.docx"))
            if not docx_files:
                logger.warning("LibreOffice 转换后未找到 .docx 文件", extra={"file": path.name})
                return None
            converted = docx_files[0]
        warnings.append("旧版 Word（.doc）已通过 LibreOffice 转换为 .docx 解析")
        return converted
    except subprocess.TimeoutExpired:
        logger.warning("LibreOffice 转换超时", extra={"file": path.name, "timeout": _LIBREOFFICE_TIMEOUT})
        return None
    except FileNotFoundError:
        logger.warning("LibreOffice 未安装，无法转换 .doc 文件")
        return None
    except Exception:
        logger.exception("LibreOffice 转换异常", extra={"file": path.name})
        return None


def _salvage_text(data: bytes, collector: _Collector) -> int:
    """从二进制（旧版 OLE .doc/.wps 等）里抢救可读片段，返回收录片段数。

    只收录足够长的连续可打印串，并且整批片段还要过 ``_looks_like_text`` 闸门，
    避免把容器碎片当成正文喂给模型。
    """
    decoded = ""
    for encoding in ("utf-16-le", "utf-16-be", "gb18030", "latin-1"):
        try:
            candidate = data.decode(encoding, "ignore")
        except Exception:
            continue
        printable = sum(1 for ch in candidate if ch.isprintable() or ch in "\n\r\t")
        if candidate and printable / len(candidate) > 0.6:
            decoded = candidate
            break
    if not decoded:
        return 0
    fragments: list[str] = []
    for match in _PRINTABLE_RE.finditer(decoded):
        collector.guard.tick()
        fragment = " ".join(match.group(0).split())
        if len(fragment) >= _MIN_SALVAGE_RUN:
            fragments.append(fragment)
        if len(fragments) >= 400:
            break
    if not fragments or not _looks_like_text("".join(fragments)):
        return 0
    count = 0
    for fragment in fragments:
        collector.guard.tick()
        count += 1
        if not collector.add(1, fragment, "paragraph"):
            break
    return count


def _parse_generic_text(
    path: Path, collector: _Collector, warnings: list[str], *, allow_salvage: bool = True
) -> None:
    """未知类型的通用回退：先按文本读，读不出再抢救可打印片段。"""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = ""
    if text and sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t ") / max(1, len(text)) > 0.85:
        for para in re.split(r"\n\s*\n", text):
            joined = " ".join(line.strip() for line in para.splitlines() if line.strip())
            if not collector.add(1, joined, "paragraph"):
                return
        return
    collected = _salvage_text(data, collector) if allow_salvage else 0
    if collected and collector.char_count >= max(64, int(len(data) * _MIN_SALVAGE_COVERAGE)):
        warnings.append("未识别的文件类型，已按通用文本抢救式提取（可能有缺失）")
    else:
        collector.blocks.clear()
        collector.char_count = 0
        if allow_salvage:
            warnings.append("未识别的文件类型且无法读出文字")
        else:
            warnings.append("不支持的文件类型（无法识别为可解析的文档）")


def _parse_image(path: Path, collector: _Collector, warnings: list[str], structured: bool = False) -> bool:
    """解析图片：只能走 OCR。返回是否使用 OCR。"""
    service = _get_ocr_service()
    if service is None:
        warnings.append("图片需要 OCR，但 OCR 服务不可用")
        return False
    try:
        if structured:
            raw: Any = service.extract(str(path), output_format="markdown")
        else:
            raw = service.extract_text(str(path))
        if isinstance(raw, dict):
            raw = str(raw.get("markdown") or "")
    except Exception:
        logger.exception("图片 OCR 失败")
        warnings.append("图片 OCR 识别失败")
        return True
    text = str(raw) if raw else ""
    collector.add_multiline(1, text)
    if not text.strip():
        warnings.append("未能提取到文字")
    return True


def _dispatch(
    spec: FormatSpec,
    path: Path,
    collector: _Collector,
    warnings: list[str],
    max_pages: int | None,
    max_ocr_pages: int | None,
    ocr_structured: bool = False,
) -> tuple[int, bool]:
    """按已判定的类型分派到对应提取器。"""
    ext = spec.extensions[0]
    if ext == ".pdf":
        return _parse_pdf(
            path,
            collector,
            warnings,
            max_pages=max_pages,
            max_ocr_pages=max_ocr_pages,
            ocr_structured=ocr_structured,
        )
    if ext in (".docx", ".dotx"):
        _parse_docx(path, collector)
        return 0, False
    if ext in (".xlsx", ".xlsm", ".xltx", ".xltm"):
        _parse_xlsx(path, collector)
        return 0, False
    if ext in (".xls", ".et"):
        _parse_xls(path, collector)
        return 0, False
    if ext in (".pptx", ".ppsx", ".sldx"):
        _parse_ooxml_presentation(path, collector, warnings)
        return 0, False
    if ext in (".odt", ".ods", ".odp"):
        _parse_opendocument(path, collector, warnings)
        return 0, False
    if ext in (".csv", ".tsv"):
        _parse_delimited(path, collector, "\t" if ext == ".tsv" else ",")
        return 0, False
    if ext == ".json":
        _parse_json(path, collector, warnings)
        return 0, False
    if ext == ".xml":
        _parse_xml(path, collector, warnings)
        return 0, False
    if ext in (".html", ".htm"):
        _parse_html(path, collector, warnings)
        return 0, False
    if ext == ".rtf":
        _parse_rtf(path, collector, warnings)
        return 0, False
    if ext in TEXTUAL_EXTENSIONS:
        _parse_text_file(path, collector)
        return 0, False
    if ext in (".doc", ".wps"):
        # 优先用 LibreOffice 转成 .docx 再解析（Docker 镜像已预装）
        converted = _convert_doc_to_docx(path, warnings)
        if converted is not None:
            try:
                _parse_docx(converted, collector)
                # 转换成功后清理临时目录（_convert_doc_to_docx 创建的）
                parent = converted.parent
                if parent.name.startswith("docgen-convert-"):
                    shutil.rmtree(parent, ignore_errors=True)
                return 0, False
            except Exception:
                logger.exception("转换后的 .docx 解析失败", extra={"file": path.name})
                # 转换成功但解析失败，继续走 salvage 兜底
        # LibreOffice 不可用或转换失败，走 OLE 文本抢救
        collected = _salvage_text(path.read_bytes(), collector)
        fmt_label = "Word" if ext == ".doc" else "WPS"
        if collected:
            warnings.append(
                f"旧版 {fmt_label}（{ext}）转换失败，已抢救式提取（可能有缺失），建议另存为 .docx 后重新上传"
            )
        else:
            warnings.append(f"旧版 {fmt_label}（{ext}）未能提取文字，请另存为 .docx 后重新上传")
        return 0, False
    if ext in IMAGE_EXTENSIONS:
        return 0, _parse_image(path, collector, warnings, structured=ocr_structured)
    _parse_generic_text(path, collector, warnings)
    return 0, False


def _canonical_path(path: Path, spec: FormatSpec) -> tuple[Path, Path | None]:
    """类型是按 MIME/魔数判定时，磁盘后缀可能与真实类型不符，给它一个正确后缀的别名。

    openpyxl 之类会先按文件扩展名拒绝打开（不看内容），因此"识别出是 Excel 却打不开"
    必须在这里解决；优先硬链接避免大文件复制，跨文件系统时退化为复制。
    返回 (供解析的路径, 需清理的临时目录)。
    """
    if path.suffix.lower() in spec.extensions:
        return path, None
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="docgen-parse-"))
        alias = temp_dir / f"{path.stem or 'payload'}{spec.extensions[0]}"
        try:
            os.link(path, alias)
        except OSError:
            shutil.copy2(path, alias)
        return alias, temp_dir
    except OSError:
        logger.exception("创建解析别名失败，按原路径继续", extra={"path_name": path.name})
        return path, None


def parse_file_sync(
    path: str | Path,
    *,
    file_id: str,
    role: str = "material",
    max_chars: int = 2_000_000,
    max_pages: int | None = None,
    max_ocr_pages: int | None = None,
    mime_hint: str | None = None,
    should_cancel: Callable[[], bool] | None = None,
    deadline: float | None = None,
    ocr_structured: bool = False,
) -> ParseResult:
    """同步解析单个文件（在线程池里跑）。任何失败都降级为 warning 并返回部分结果。

    ``ocr_structured=True`` 时 OCR 走 PP-StructureV3 输出 Markdown（保留表格与版式），
    用于调用方的第二级兜底（快速 PP-OCR 无结果时再试）。
    """
    p = Path(path)
    warnings: list[str] = []
    guard = _Guard(should_cancel, deadline)
    collector = _Collector(file_id, max_chars, guard)
    if not p.exists():
        logger.warning("资料文件不存在", extra={"file_id": file_id, "path_name": p.name})
        return ParseResult([], 0, 0, False, [f"文件不存在：{p.name}"], "", "not_found")
    try:
        if p.stat().st_size == 0:
            return ParseResult([], 0, 0, False, [f"文件为空：{p.name}"], "", "empty")
    except OSError:
        logger.exception("文件状态读取失败", extra={"file_id": file_id, "path_name": p.name})
        return ParseResult([], 0, 0, False, [f"文件状态读取失败：{p.name}"], "", "not_found")

    spec, basis = detect_format(p, mime_hint)
    format_name = spec.name if spec is not None else "未知"
    logger.info(
        "开始解析资料文件",
        extra={
            "file_id": file_id,
            "role": role,
            "path_name": p.name,
            "format": format_name,
            "basis": basis or "fallback",
        },
    )
    page_count = 0
    ocr_used = False
    aborted = ""
    alias_dir: Path | None = None
    target = p
    if spec is not None:
        target, alias_dir = _canonical_path(p, spec)
    try:
        if spec is None:
            # 容器类（细分不出的 zip/OLE）不做文本抢救：二进制碎片会被解码成合法中日韩文，
            # 一旦喂给模型，槽位值会像模像样却全是编造的
            _parse_generic_text(p, collector, warnings, allow_salvage=basis != "container")
        else:
            page_count, ocr_used = _dispatch(
                spec, target, collector, warnings, max_pages, max_ocr_pages, ocr_structured
            )
    except ParseAbortError as exc:
        aborted = exc.reason
        logger.warning(
            "资料解析被强制终止",
            extra={"file_id": file_id, "path_name": p.name, "reason": exc.reason, "chars": collector.char_count},
        )
        warnings.append("解析已按请求强制终止" if exc.reason == _ABORT_CANCELLED else "解析超时，已强制终止")
    except Exception:
        logger.exception("解析文件失败", extra={"file_id": file_id, "path_name": p.name})
        warnings.append("文件解析失败，已返回部分结果")
    finally:
        if alias_dir is not None:
            shutil.rmtree(alias_dir, ignore_errors=True)

    if collector.truncated:
        warnings.append("文本超过上限已截断")
    if not collector.blocks and not aborted and not any(
        "未能提取" in w or "无法读出" in w or "不支持" in w for w in warnings
    ):
        warnings.append("未能提取到文字")
    if page_count == 0:
        page_count = max((b.page for b in collector.blocks), default=0)
    return ParseResult(
        blocks=collector.blocks,
        page_count=page_count,
        char_count=collector.char_count,
        ocr_used=ocr_used,
        warnings=warnings,
        format_name=spec.name if spec is not None else "通用文本回退",
        aborted=aborted,
    )


async def parse_file(
    path: str | Path,
    *,
    file_id: str,
    role: str = "material",
    max_chars: int = 2_000_000,
    max_pages: int | None = None,
    max_ocr_pages: int | None = None,
    mime_hint: str | None = None,
    timeout_seconds: float | None = None,
    should_cancel: Callable[[], bool] | None = None,
    abort_event: threading.Event | None = None,
    ocr_structured: bool = False,
) -> ParseResult:
    """解析单个上传文件为 TextBlock 序列（线程池执行 + 硬超时 + 可强制终止）。

    第三方解析库都是同步阻塞的，直接 await 会卡死事件循环——那样前端的取消请求和
    状态轮询都进不来，「强制终止」也就无从谈起。这里放线程池执行，外层 ``wait_for``
    兜底：即使库卡在 C 层不响应守卫，本协程仍会按时返回并把 ``abort_event`` 置位，
    让线程内的解析在下一个检查点退出。
    """
    event = abort_event or threading.Event()

    def _cancelled() -> bool:
        return event.is_set() or (should_cancel is not None and should_cancel())

    kwargs: dict[str, Any] = {
        "file_id": file_id,
        "role": role,
        "max_chars": max_chars,
        "max_pages": max_pages,
        "max_ocr_pages": max_ocr_pages,
        "mime_hint": mime_hint,
        "should_cancel": _cancelled,
        "ocr_structured": ocr_structured,
    }
    if timeout_seconds is not None and timeout_seconds > 0:
        kwargs["deadline"] = time.monotonic() + timeout_seconds
    try:
        if timeout_seconds is not None and timeout_seconds > 0:
            return await asyncio.wait_for(
                asyncio.to_thread(parse_file_sync, path, **kwargs), timeout=timeout_seconds
            )
        return await asyncio.to_thread(parse_file_sync, path, **kwargs)
    except TimeoutError:
        event.set()  # 通知线程内守卫在下一个检查点退出，避免线程长期滞留
        logger.warning("资料解析硬超时，已强制终止", extra={"file_id": file_id, "timeout": timeout_seconds})
        return ParseResult(
            blocks=[],
            page_count=0,
            char_count=0,
            ocr_used=False,
            warnings=[f"解析超过 {int(timeout_seconds or 0)} 秒未完成，已强制终止"],
            aborted=_ABORT_TIMEOUT,
        )


def parse_limits() -> dict[str, Any]:
    """解析能力自述（写入生成说明，便于运维核对「这台机器到底能读哪些格式」）。"""
    return {
        "formats": supported_formats(),
        "extensions": supported_extensions(),
        "libraries": {spec.name: spec.library for spec in FORMATS},
    }
