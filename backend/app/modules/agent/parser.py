"""PPT 解析与讲稿切分。

两个职责：
1. 把上传的 `.ppt/.pptx` 变成「页数 + 每页文本/备注」（`.ppt` 先经 LibreOffice 转 `.pptx`）；
2. 把独立讲稿（纯文本或 docx）按页切开，并给出缺页/多页提示。

讲稿分页写法（任选其一，行首匹配）：
    第 3 页 / ## 第3页 / Page 3 / page 3 / [3] / #3 / === 3 === / 3.
没有分页标记时依次尝试：分页符 `\\f` → 空行分段（段数与页数相等才采用）。
"""

import hashlib
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.modules.agent.alignment import build_fingerprint

logger = logging.getLogger(__name__)

#: soffice 单次转换超时（秒）
SOFFICE_TIMEOUT = 180

#: 单页表格单元格抽取上限：单元格过多会挤占讲稿 prompt 预算，也让高亮候选膨胀
MAX_TABLE_CELLS = 60

#: 独占一行的分页标记；`3.` / `3、` 这种短行也算标记
_PAGE_MARKER = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:"
    r"第\s*(\d{1,3})\s*页"
    r"|[Pp]age\s*(\d{1,3})"
    r"|===\s*(\d{1,3})\s*==="
    r"|\[(\d{1,3})\]"
    r"|#(\d{1,3})"
    r"|(\d{1,3})\s*[.、)]\s*$"
    r")\s*[:：]?\s*$"
)

#: 标记后面直接跟正文的写法（「第 1 页：开场白」），只对无歧义的前五种形式生效。
#: 刻意不包含 `3.` 形式：`3.15 质量标准` 这类正文开头会被误判成第 3 页。
_PAGE_MARKER_INLINE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:"
    r"第\s*(?P<zh>\d{1,3})\s*页"
    r"|[Pp]age\s*(?P<en>\d{1,3})"
    r"|===\s*(?P<bar>\d{1,3})\s*==="
    r"|\[(?P<bracket>\d{1,3})\]"
    r"|#(?P<hash>\d{1,3})"
    r")\s*[:：]?\s*(?P<rest>\S.*)$"
)


class ParserError(ValueError):
    """解析失败（格式不支持、文件损坏、页数不匹配等），message 直接给用户看。"""


@dataclass(frozen=True)
class ParsedSlide:
    slide_no: int
    text: str
    notes: str
    #: 形状坐标清单：{"width","height","shapes":[...]}，单位为 EMU；
    #: 换源对齐取其中文字与坐标，视觉引导取其中文本框位置
    layout: dict[str, Any] = field(default_factory=dict)
    #: 页内容指纹（文字 + 备注 + 形状数 + 坐标摘要）
    fingerprint: str = ""


@dataclass
class ScriptParseResult:
    """讲稿切分结果与提示。"""

    slides: dict[int, str] = field(default_factory=dict)
    missing_pages: list[int] = field(default_factory=list)
    extra_pages: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_pages and not self.extra_pages


def _first_group(match: re.Match[str], names: tuple[str, ...]) -> int | None:
    for name in names:
        value = match.groupdict().get(name)
        if value:
            return int(value)
    return None


def _marker_and_rest(line: str) -> tuple[int | None, str]:
    """识别分页标记，返回 (页码, 标记行内的正文)。"""
    match = _PAGE_MARKER.match(line)
    if match:
        for group in match.groups():
            if group:
                return int(group), ""
        return None, ""

    inline = _PAGE_MARKER_INLINE.match(line)
    if inline:
        page = _first_group(inline, ("zh", "en", "bar", "bracket", "hash"))
        if page is not None:
            return page, (inline.group("rest") or "").strip()
    return None, ""


def split_script(text: str, slide_count: int) -> ScriptParseResult:
    """按页切分讲稿，并校验与 PPT 页数是否对齐。"""
    result = ScriptParseResult()
    raw = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not raw.strip():
        result.missing_pages = list(range(1, slide_count + 1))
        result.warnings.append("讲稿为空")
        return result

    current: int | None = None
    bucket: dict[int, list[str]] = {}

    for line in raw.split("\n"):
        page, inline_text = _marker_and_rest(line)
        if page is not None:
            current = page
            bucket.setdefault(current, [])
            if inline_text:
                bucket[current].append(inline_text)
            continue
        if current is None:
            continue
        bucket[current].append(line)

    if bucket:
        result.slides = {page: "\n".join(lines).strip() for page, lines in bucket.items() if "\n".join(lines).strip()}
    else:
        result.slides = _split_without_markers(raw, slide_count, result)

    expected = set(range(1, slide_count + 1))
    result.missing_pages = sorted(expected - set(result.slides))
    result.extra_pages = sorted(page for page in result.slides if page not in expected)
    if result.missing_pages:
        result.warnings.append("讲稿缺少页码：" + "、".join(str(page) for page in result.missing_pages))
    if result.extra_pages:
        result.warnings.append("讲稿页码超过 PPT 页数：" + "、".join(str(page) for page in result.extra_pages))
    return result


def _split_without_markers(raw: str, slide_count: int, result: ScriptParseResult) -> dict[int, str]:
    """没有分页标记时的兜底：分页符 → 空行分段。"""
    if "\f" in raw:
        chunks = [chunk.strip() for chunk in raw.split("\f")]
        chunks = [chunk for chunk in chunks if chunk]
        if len(chunks) == slide_count:
            return {index + 1: chunk for index, chunk in enumerate(chunks)}
        result.warnings.append(f"按分页符切出 {len(chunks)} 段，与 ppt 页数 {slide_count} 不一致，未自动采用")

    blocks = [block.strip() for block in re.split(r"\n\s*\n", raw) if block.strip()]
    if len(blocks) == slide_count:
        return {index + 1: block for index, block in enumerate(blocks)}

    result.warnings.append("讲稿未找到分页标记（如「第 1 页」），且无法按空行自动对齐，请手工按页补全")
    return {1: raw.strip()} if slide_count == 1 else {}


def read_script_file(path: str | Path) -> str:
    """读取讲稿文件：.txt/.md 直接读，.docx 抽段落。"""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        from docx import Document

        document = Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ParserError(f"讲稿格式不支持：{suffix or '未知'}（仅支持 .txt/.md/.docx）")


def convert_to_pptx(source: str | Path, work_dir: str | Path) -> Path:
    """`.ppt` → `.pptx`。已是 pptx 时原样返回。"""
    src = Path(source)
    if src.suffix.lower() == ".pptx":
        return src
    if src.suffix.lower() != ".ppt":
        raise ParserError(f"不支持的文件格式：{src.suffix or '未知'}（仅支持 .ppt/.pptx）")

    target_dir = Path(work_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    _run_soffice(["--convert-to", "pptx", "--outdir", str(target_dir), str(src)])
    converted = target_dir / f"{src.stem}.pptx"
    if not converted.exists():
        raise ParserError("PPT 转换失败：旧版 .ppt 未能转换为 .pptx，请另存为 .pptx 后重试")
    return converted


def _soffice_env(work_dir: str | Path) -> dict[str, str]:
    """每次调用独立 UserInstallation，避免并发任务互相锁死 LibreOffice profile。"""
    import os

    profile = Path(work_dir) / "lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(profile)
    return env


def _run_soffice(args: list[str], work_dir: str | Path = ".") -> None:
    binary = shutil.which("soffice") or shutil.which("libreoffice")
    if not binary:
        raise ParserError("服务器未安装 LibreOffice，无法解析/转换 PPT")
    profile = Path(work_dir) / "lo-profile"
    command = [binary, f"-env:UserInstallation=file://{profile.resolve()}", "--headless", *args]
    try:
        completed = subprocess.run(  # noqa: S603 - 参数由服务端拼装，不含用户输入拼接
            command,
            capture_output=True,
            text=True,
            timeout=SOFFICE_TIMEOUT,
            check=False,
            env=_soffice_env(work_dir),
        )
    except subprocess.TimeoutExpired as exc:
        raise ParserError("PPT 解析超时，请检查文件是否过大或损坏") from exc
    if completed.returncode != 0:
        logger.error("soffice failed: %s", completed.stderr[-2000:])
        raise ParserError("PPT 解析失败，请确认文件可正常用 PowerPoint/WPS 打开")


def _image_sha(shape: Any) -> str:
    """图片形状的内容 sha256；非图片或取不到时返回空串。"""
    if not hasattr(shape, "image"):
        return ""
    try:
        blob = shape.image.blob
    except Exception:  # noqa: BLE001 - EMF/WMF 等格式 python-pptx 可能读不出来
        logger.debug("图片内容读取失败，跳过摘要: %s", shape.name)
        return ""
    return hashlib.sha256(blob).hexdigest()


def _shape_box(shape: Any) -> tuple[int, int, int, int] | None:
    """形状在页面上的 EMU 框；无有效几何（占位符/损坏）时返回 None。"""
    try:
        left = int(shape.left or 0)
        top = int(shape.top or 0)
        width = int(shape.width or 0)
        height = int(shape.height or 0)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return left, top, width, height


def _group_text(shape: Any) -> str:
    """递归收集组合形状内的文本。

    组内子形状的坐标是「组内坐标系」的偏移，直接拿来当页面坐标会亮错位置，
    所以这里只取文本（讲稿需要），坐标仍用整组在页面上的外框。
    """
    parts: list[str] = []
    for child in getattr(shape, "shapes", ()) or ():
        if getattr(child, "has_text_frame", False):
            text = child.text_frame.text.strip()
            if text:
                parts.append(text)
        if hasattr(child, "shapes"):
            nested = _group_text(child)
            if nested:
                parts.append(nested)
    return "\n".join(parts)


def _table_payload(shape: Any) -> tuple[str, list[dict[str, Any]]]:
    """表格 → (整表文字, 单元格清单)。

    python-pptx 的单元格**没有** left/top 属性，只能按行列宽高累加算几何；
    合并单元格只在合并起点出一条记录，并把宽高按跨度放大。
    """
    box = _shape_box(shape)
    if box is None:
        return "", []
    origin_left, origin_top = box[0], box[1]
    try:
        table = shape.table
        widths = [max(0, int(column.width or 0)) for column in table.columns]
        heights = [max(0, int(row.height or 0)) for row in table.rows]
    except Exception:  # noqa: BLE001 - 结构异常的表格当作无文本形状，不影响整页解析
        logger.debug("表格结构读取失败，跳过单元格: %s", shape.name)
        return "", []

    texts: list[str] = []
    cells: list[dict[str, Any]] = []
    top = origin_top
    for row_index in range(len(heights)):
        left = origin_left
        for column_index in range(len(widths)):
            width = widths[column_index]
            if len(cells) < MAX_TABLE_CELLS:
                try:
                    cell = table.cell(row_index, column_index)
                except IndexError:
                    cell = None
                if cell is not None and not cell.is_spanned:
                    span_width = max(1, int(getattr(cell, "span_width", 1) or 1))
                    span_height = max(1, int(getattr(cell, "span_height", 1) or 1))
                    cell_width = sum(widths[column_index : column_index + span_width]) or width
                    cell_height = sum(heights[row_index : row_index + span_height]) or heights[row_index]
                    text = (cell.text or "").strip()
                    if text:
                        texts.append(text)
                    if cell_width > 0 and cell_height > 0:
                        cells.append(
                            {
                                "row": row_index + 1,
                                "col": column_index + 1,
                                "text": text,
                                "left": left,
                                "top": top,
                                "width": cell_width,
                                "height": cell_height,
                            }
                        )
            left += width
        top += heights[row_index]
    return "\n".join(texts), cells


def parse_pptx(pptx_path: str | Path) -> list[ParsedSlide]:
    """解析 pptx，返回每页文本与备注。"""
    from pptx import Presentation

    try:
        presentation = Presentation(str(pptx_path))
    except Exception as exc:  # noqa: BLE001 - 第三方库异常类型不稳定，统一转成用户可读提示
        raise ParserError("PPT 文件损坏或不是有效的 .pptx，请重新导出后再上传") from exc

    slide_width = int(presentation.slide_width or 0)
    slide_height = int(presentation.slide_height or 0)

    slides: list[ParsedSlide] = []
    for index, slide in enumerate(presentation.slides, start=1):
        texts: list[str] = []
        shapes: list[dict[str, Any]] = []
        for shape in slide.shapes:
            shape_text = ""
            cells: list[dict[str, Any]] = []
            if shape.has_text_frame:
                shape_text = shape.text_frame.text.strip()
            elif getattr(shape, "has_table", False):
                # 表格文字此前完全丢失（表格不是 text_frame），讲稿根本看不到数据
                shape_text, cells = _table_payload(shape)
            elif hasattr(shape, "shapes"):
                shape_text = _group_text(shape)
            if shape_text:
                texts.append(shape_text)

            box = _shape_box(shape)
            if box is None:
                # 个别占位符没有有效几何信息，跳过即可，不影响文字抽取
                logger.debug("跳过无坐标形状: %s", shape.name)
                continue
            payload: dict[str, Any] = {
                "name": shape.name,
                "kind": str(getattr(shape, "shape_type", "")),
                "text": shape_text,
                "left": box[0],
                "top": box[1],
                "width": box[2],
                "height": box[3],
                # 图片内容摘要：换图但文字/坐标不变时，靠它识别出「这页变了」
                "image_sha": _image_sha(shape),
            }
            if cells:
                payload["cells"] = cells
            shapes.append(payload)

        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text.strip()

        layout = {"width": slide_width, "height": slide_height, "shapes": shapes}
        page_text = "\n".join(texts)
        slides.append(
            ParsedSlide(
                slide_no=index,
                text=page_text,
                notes=notes,
                layout=layout,
                fingerprint=build_fingerprint(page_text, notes, layout),
            )
        )

    if not slides:
        raise ParserError("PPT 中没有可识别的幻灯片")
    return slides
