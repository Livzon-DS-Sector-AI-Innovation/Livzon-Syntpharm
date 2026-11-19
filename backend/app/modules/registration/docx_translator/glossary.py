"""DOCX 翻译 —— 术语表。

平台内术语表以数据库为准（`registration.docx_translation_terms`），
运行期一次性读入内存供翻译引擎使用；xlsx 导入/导出用 openpyxl 处理。
"""

from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path

from openpyxl import Workbook, load_workbook

logger = logging.getLogger(__name__)

# 允许的列名（大小写不敏感）
_EN_COLUMNS = ("英文", "english", "en")
_ZH_COLUMNS = ("中文", "chinese", "cn")

EXCEL_HEADERS = ("英文", "中文")


class GlossaryError(ValueError):
    """术语表文件格式不可用，消息可直接回显给用户。"""


class Glossary:
    """术语表管理器（大小写不敏感匹配，保留原始大小写用于展示）。"""

    def __init__(self) -> None:
        self._terms_lower: dict[str, str] = {}
        self._terms_display: dict[str, str] = {}
        self._terms_by_lower_display: dict[str, str] = {}
        self._loaded = False

    def load_from_terms(self, terms: dict[str, str]) -> None:
        """按 {英文: 中文} 加载；重复英文（大小写不同）保留首次出现的写法。"""
        self._terms_lower = {}
        self._terms_display = {}
        self._terms_by_lower_display = {}
        for src, tgt in terms.items():
            src = src.strip()
            tgt = tgt.strip()
            if not src or not tgt:
                continue
            key = src.lower()
            self._terms_lower[key] = tgt
            if key not in self._terms_by_lower_display:
                self._terms_by_lower_display[key] = src
                self._terms_display[src] = tgt
        self._loaded = bool(self._terms_lower)

    def is_loaded(self) -> bool:
        return self._loaded

    def get_term_count(self) -> int:
        return len(self._terms_lower)

    def get_terms(self) -> dict[str, str]:
        """返回 {源词: 目标词}，按翻译方向套用后的映射。"""
        return dict(self._terms_display)


def _pick_columns(headers: list[str]) -> tuple[int, int]:
    """从表头定位英文列与中文列，返回 (en_index, zh_index)。"""
    lowered = [str(h).strip().lower() if h is not None else "" for h in headers]
    en_idx = next((i for i, h in enumerate(lowered) if h in _EN_COLUMNS), -1)
    zh_idx = next((i for i, h in enumerate(lowered) if h in _ZH_COLUMNS), -1)
    if en_idx < 0 or zh_idx < 0:
        shown = "、".join(h for h in headers if h) or "（空）"
        raise GlossaryError(f"未找到「英文」「中文」列，当前表头为：{shown}")
    return en_idx, zh_idx


def parse_excel_terms(data: bytes) -> list[tuple[str, str]]:
    """解析 xlsx，返回 [(英文, 中文)]；表头或内容不可用时抛 GlossaryError。"""
    try:
        wb = load_workbook(filename=BytesIO(data), read_only=True, data_only=True)
    except Exception as e:  # noqa: BLE001 - openpyxl 抛出的异常类型不稳定
        logger.warning("glossary xlsx parse failed", extra={"biz_module": "registration"})
        raise GlossaryError("无法读取该 Excel 文件，请确认是 .xlsx 格式") from e

    try:
        ws = wb.active
        if ws is None:
            raise GlossaryError("Excel 中没有可用的工作表")
        rows = ws.iter_rows(values_only=True)
        try:
            header_row = next(rows)
        except StopIteration as e:
            raise GlossaryError("Excel 内容为空") from e
        headers = [str(h) if h is not None else "" for h in header_row]
        en_idx, zh_idx = _pick_columns(headers)

        terms: list[tuple[str, str]] = []
        for row in rows:
            en = str(row[en_idx]).strip() if en_idx < len(row) and row[en_idx] is not None else ""
            zh = str(row[zh_idx]).strip() if zh_idx < len(row) and row[zh_idx] is not None else ""
            if not en or not zh or en.lower() in ("nan", "none"):
                continue
            terms.append((en, zh))
        if not terms:
            raise GlossaryError("Excel 中没有可导入的术语（英文与中文均不能为空）")
        return terms
    finally:
        wb.close()


def parse_excel_file(path: str | Path) -> list[tuple[str, str]]:
    """从磁盘路径解析 xlsx（内置术语表种子使用）。"""
    return parse_excel_terms(Path(path).read_bytes())


def build_excel_terms(rows: list[tuple[str, str]]) -> bytes:
    """导出术语表为 xlsx 字节流。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "术语表"
    ws.append(list(EXCEL_HEADERS))
    for en, zh in rows:
        ws.append([en, zh])
    ws.column_dimensions["A"].width = 46
    ws.column_dimensions["B"].width = 32
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
