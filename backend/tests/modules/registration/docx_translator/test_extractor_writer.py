"""提取/回写/校验：段落、表格、页眉页脚跳过，双语插入与替换模式。"""

from __future__ import annotations

from pathlib import Path

from docx import Document

from app.modules.registration.docx_translator.engine_models import TextUnit, TranslationResult
from app.modules.registration.docx_translator.extractor import DocxExtractor
from app.modules.registration.docx_translator.validator import Validator
from app.modules.registration.docx_translator.writer import DocxWriter


def _build_docx(path: Path) -> None:
    doc = Document()
    doc.add_paragraph("Batch Production Record")
    doc.add_paragraph("")
    doc.add_paragraph("5 kg material")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Specifications"
    table.rows[0].cells[1].text = "Deviation Report"
    doc.sections[0].header.paragraphs[0].text = "CONFIDENTIAL HEADER"
    doc.save(str(path))


def _fake_results(units: list[TextUnit]) -> list[TranslationResult]:
    results: list[TranslationResult] = []
    for unit in units:
        results.append(
            TranslationResult(
                unit_id=unit.id,
                original_text=unit.text,
                translated_text="" if unit.is_empty else f"译文:{unit.text}",
                success=True,
            )
        )
    return results


def test_extract_skips_header_and_empty(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    _build_docx(source)

    _doc, units = DocxExtractor().extract(str(source))
    texts = [unit.text for unit in units]
    assert "Batch Production Record" in texts
    assert "Specifications" in texts
    assert "CONFIDENTIAL HEADER" not in texts
    assert all(unit.location_type != "header" for unit in units)


def test_bilingual_write_inserts_blue_paragraphs(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    _build_docx(source)
    doc, units = DocxExtractor().extract(str(source))
    results = _fake_results(units)

    out = tmp_path / "out_bi.docx"
    DocxWriter(mode="bilingual", target_lang="zh").write(doc, str(out), units, results)

    stats = Validator().validate_post_save(str(out), units, results, mode="bilingual")
    assert stats["match"] is True
    assert stats["actual_blue_paragraphs"] > 0


def test_replace_write_replaces_text(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    _build_docx(source)
    doc, units = DocxExtractor().extract(str(source))
    results = _fake_results(units)

    out = tmp_path / "out_zh.docx"
    DocxWriter(mode="replace", target_lang="zh").write(doc, str(out), units, results)

    reloaded = Document(str(out))
    body_text = "\n".join(p.text for p in reloaded.paragraphs)
    assert "译文:Batch Production Record" in body_text
    assert "Batch Production Record" not in [line.strip() for line in body_text.split("\n")]


def test_validator_reports_success_rate(tmp_path: Path) -> None:
    source = tmp_path / "sample.docx"
    _build_docx(source)
    _doc, units = DocxExtractor().extract(str(source))
    results = _fake_results(units)
    results[0].success = False
    results[0].translated_text = ""

    stats = Validator().validate(units, results)
    assert stats["failed"] == 1
    assert 0 < stats["success_rate"] < 100
    assert stats["failed_details"][0]["id"] == units[0].id
