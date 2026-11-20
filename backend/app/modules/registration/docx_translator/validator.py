"""DOCX 翻译 —— 结果校验。

移植自 docx-translator/scripts/validator.py，去掉 print 报告（平台用日志 +
接口返回结构化统计）。
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from .engine_models import TextUnit, TranslationResult

logger = logging.getLogger(__name__)

Stats = dict[str, Any]


class Validator:
    """翻译结果验证器。"""

    def validate(self, units: list[TextUnit], results: list[TranslationResult]) -> Stats:
        """统计成功/失败段落，返回成功率与失败明细。"""
        result_map = {r.unit_id: r for r in results}

        by_location: Counter[str] = Counter()
        failed_details: list[dict[str, Any]] = []
        success = 0
        failed = 0
        skipped_empty = 0

        for unit in units:
            if unit.is_empty:
                skipped_empty += 1
                continue

            result = result_map.get(unit.id)
            if result is None:
                failed += 1
                by_location[unit.location_type] += 1
                failed_details.append(
                    {
                        "id": unit.id,
                        "location": unit.location_type,
                        "table_path": unit.table_path,
                        "reason": "未找到翻译结果",
                        "original": unit.text[:80] + "..." if len(unit.text) > 80 else unit.text,
                    }
                )
                continue

            if result.success and result.translated_text:
                success += 1
            else:
                failed += 1
                by_location[unit.location_type] += 1
                failed_details.append(
                    {
                        "id": unit.id,
                        "location": unit.location_type,
                        "table_path": unit.table_path,
                        "reason": result.error_message or "翻译结果为空",
                        "original": unit.text[:80] + "..." if len(unit.text) > 80 else unit.text,
                    }
                )

        total = success + failed
        return {
            "total_units": len(units),
            "success": success,
            "failed": failed,
            "skipped_empty": skipped_empty,
            "success_rate": (success / total * 100) if total else 0.0,
            "by_location": dict(by_location),
            "failed_details": failed_details[:50],
        }

    def log_report(self, stats: Stats) -> None:
        logger.info(
            "docx translation report: success=%s failed=%s rate=%.1f%%",
            stats.get("success"),
            stats.get("failed"),
            stats.get("success_rate", 0.0),
            extra={"biz_module": "registration"},
        )

    def validate_post_save(
        self,
        output_path: str,
        units: list[TextUnit],
        results: list[TranslationResult],
        mode: str = "bilingual",
    ) -> Stats:
        """保存后二次校验：bilingual 数蓝段，replace 算原文残留率。"""
        if mode == "replace":
            return self._validate_replace_post_save(output_path, units, results)
        return self._validate_bilingual_post_save(output_path, units, results)

    def _validate_bilingual_post_save(
        self,
        output_path: str,
        units: list[TextUnit],
        results: list[TranslationResult],
    ) -> Stats:
        from docx import Document
        from docx.oxml.ns import qn

        doc = Document(output_path)
        count = 0
        seen: set[Any] = set()

        def _check_para(p_elem: Any) -> None:
            nonlocal count
            if p_elem in seen:
                return
            seen.add(p_elem)
            for run in p_elem.findall(qn("w:r")):
                rpr = run.find(qn("w:rPr"))
                if rpr is None:
                    continue
                color = rpr.find(qn("w:color"))
                if color is not None and color.get(qn("w:val")) == "0000FF":
                    count += 1
                    break

        def _recurse(elem: Any) -> None:
            if elem.tag == qn("w:p"):
                _check_para(elem)
                return
            for child in elem:
                _recurse(child)

        _recurse(doc.element.body)

        unit_map = {u.id: u for u in units}
        seen_paras: set[int] = set()
        expected = 0
        for r in results:
            if not (r.success and r.translated_text):
                continue
            unit = unit_map.get(r.unit_id)
            if unit is None:
                continue
            para_id = id(unit.paragraph_element)
            if para_id not in seen_paras:
                seen_paras.add(para_id)
                expected += 1

        discrepancy = max(0, expected - count)
        return {
            "expected_translations": expected,
            "actual_blue_paragraphs": count,
            "discrepancy": discrepancy,
            "match": discrepancy == 0,
        }

    def _validate_replace_post_save(
        self,
        output_path: str,
        units: list[TextUnit],
        results: list[TranslationResult],
    ) -> Stats:
        from docx import Document
        from docx.oxml.ns import qn

        Document(output_path)
        result_map = {r.unit_id: r for r in results}

        def _get_para_text(p_elem: Any) -> str:
            parts: list[str] = []
            for run in p_elem.findall(qn("w:r")):
                t = run.find(qn("w:t"))
                if t is not None and t.text:
                    parts.append(t.text)
            return "".join(parts)

        total_replaced = 0
        untranslated = 0
        for unit in units:
            if unit.is_empty:
                continue
            result = result_map.get(unit.id)
            if not result or not result.success or not result.translated_text:
                continue
            total_replaced += 1
            if _get_para_text(unit.paragraph_element).strip() != unit.text.strip():
                continue
            if not re.search(r"[a-zA-Z\u4e00-\u9fff]", unit.text.strip()):
                continue
            untranslated += 1

        residual_rate = (untranslated / total_replaced * 100) if total_replaced else 0.0
        return {
            "total_replaced": total_replaced,
            "untranslated": untranslated,
            "residual_rate": residual_rate,
            "match": residual_rate <= 5.0,
        }


__all__ = ["Stats", "Validator"]
