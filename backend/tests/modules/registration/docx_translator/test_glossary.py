"""术语表解析/导出与引擎加载。"""

from __future__ import annotations

from io import BytesIO

import pytest
from openpyxl import Workbook

from app.modules.registration.docx_translator.glossary import (
    Glossary,
    GlossaryError,
    build_excel_terms,
    parse_excel_terms,
)


def _xlsx(rows: list[list[object]]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_excel_round_trip() -> None:
    rows = parse_excel_terms(_xlsx([["英文", "中文"], ["Batch Production Record", "批生产记录"]]))
    assert rows == [("Batch Production Record", "批生产记录")]

    exported = parse_excel_terms(build_excel_terms(rows))
    assert exported == rows


def test_parse_excel_rejects_wrong_headers() -> None:
    with pytest.raises(GlossaryError, match="英文"):
        parse_excel_terms(_xlsx([["source", "target"], ["a", "b"]]))


def test_parse_excel_skips_empty_rows() -> None:
    rows = parse_excel_terms(_xlsx([["英文", "中文"], ["Specifications", "质量标准"], [None, None]]))
    assert rows == [("Specifications", "质量标准")]


def test_glossary_dedupes_case_insensitively() -> None:
    glossary = Glossary()
    glossary.load_from_terms({"Deviation": "偏差", "deviation": "偏差2"})
    assert glossary.get_term_count() == 1
    assert glossary.get_terms() == {"Deviation": "偏差"}
    assert glossary.is_loaded() is True
