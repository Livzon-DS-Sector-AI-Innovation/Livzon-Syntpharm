"""质量检验台账：限值解析、三层判定、标准表解析与项目桥接的单元测试。

不依赖数据库，全部为纯函数级验证，重点覆盖真实样本里踩过的坑：
- 带度数符号的反向区间 `-153°～-170°`
- Word 修订插入（w:ins）里的文字必须读到
- 批号/中文分数/单值目标值/等级型标准的处理
"""

from __future__ import annotations

import io
import zipfile

import pytest

from app.modules.quality.qc_report.constants import (
    LEVEL_INTERNAL,
    LEVEL_NORMAL,
    LEVEL_OOS,
    LEVEL_PENDING,
    LEVEL_SKIP,
    LEVEL_TREND,
    VALUE_TYPE_GRADE,
    VALUE_TYPE_QUAL,
    VALUE_TYPE_QUANT,
)
from app.modules.quality.qc_report.service.bridge import bridge_items, normalize_name
from app.modules.quality.qc_report.service.docx_parser import parse_standard_docx
from app.modules.quality.qc_report.service.judge import (
    JudgeItem,
    aggregate_level,
    compile_item_limits,
    judge_value,
)
from app.modules.quality.qc_report.service.limits import INACTIVE_LIMIT, infer_value_type, parse_limit
from app.modules.quality.qc_report.service.xlsx_parser import ColumnHeader


class TestParseLimit:
    @pytest.mark.parametrize(
        ("text", "lower", "upper"),
        [
            ("8.0%～11.0%", 8.0, 11.0),
            ("8.0%～11.0％", 8.0, 11.0),
            ("6.0 ～8.0", 6.0, 8.0),
            ("495～545", 495.0, 545.0),
            # 反向区间要摆正
            ("-153°～-170°", -170.0, -153.0),
        ],
    )
    def test_interval(self, text: str, lower: float, upper: float) -> None:
        limit = parse_limit(text)
        assert limit.lower == lower
        assert limit.upper == upper
        assert limit.is_active

    @pytest.mark.parametrize(
        ("text", "upper"),
        [
            ("≤0.5%", 0.5),
            ("＜0.20EU/mg", 0.2),
            ("≤6000粒/g", 6000.0),
            # 复合表述取最后一段上限
            ("≥10µm：应≤6000粒/g", 6000.0),
            # 中文分数
            ("应不得过百万分之二十", 20.0),
            ("不得过万分之三", 300.0),
        ],
    )
    def test_upper_only(self, text: str, upper: float) -> None:
        limit = parse_limit(text)
        assert limit.upper == upper
        assert limit.lower is None

    def test_lower_only(self) -> None:
        limit = parse_limit("≥84.0%")
        assert limit.lower == 84.0
        assert limit.upper is None

    @pytest.mark.parametrize("text", ["", "/", "未作规定，仅将检验结果进行记录并发报告", None])
    def test_no_standard(self, text: str | None) -> None:
        assert parse_limit(text) == INACTIVE_LIMIT

    def test_single_value_is_not_a_range(self) -> None:
        """内控写 `517` 是目标值，不能当成上下限，否则只有恰好 517 才算合格。"""
        limit = parse_limit("517")
        assert not limit.is_active

    def test_grade_and_qual_are_not_numeric(self) -> None:
        assert not parse_limit("≤Y7/YG7/OY7").is_active
        assert not parse_limit("应符合规定").is_active
        assert not parse_limit("不得浓于1号浊度标准液").is_active

    def test_contains(self) -> None:
        limit = parse_limit("8.0～11.0")
        assert limit.contains(8.0)
        assert limit.contains(11.0)
        assert not limit.contains(11.01)
        assert not limit.contains(7.99)


class TestInferValueType:
    def test_numeric_standard(self) -> None:
        assert infer_value_type("8.0%～11.0%", "8.5%～10.5%", "8.5%～10.1%") == VALUE_TYPE_QUANT

    def test_text_standard(self) -> None:
        assert infer_value_type("应符合规定", None, None) == VALUE_TYPE_QUAL

    def test_grade_standard(self) -> None:
        assert infer_value_type("≤Y7/YG7/OY7", "≤Y6/YG6/OY6", None) == VALUE_TYPE_GRADE

    def test_text_typed_but_numeric_standard(self) -> None:
        """细菌内毒素在标准表里标成「文本」，但标准是 ＜0.20，应按数值处理。"""
        assert infer_value_type("＜0.20EU/mg", "＜0.05EU/mg", None) == VALUE_TYPE_QUANT


class TestJudgeValue:
    @staticmethod
    def _water() -> JudgeItem:
        return JudgeItem(
            item_name="水分（%）",
            value_type=VALUE_TYPE_QUANT,
            legal_text="8.0%～11.0%",
            internal_text="8.5%～10.5%",
            sigma_text="8.5%～10.1%",
        )

    def test_three_layers(self) -> None:
        item = self._water()
        limits = compile_item_limits(item)
        assert judge_value(item, "11.2", limits).level == LEVEL_OOS  # TC-04
        assert judge_value(item, "10.6", limits).level == LEVEL_INTERNAL  # TC-03
        assert judge_value(item, "10.3", limits).level == LEVEL_TREND  # TC-02
        assert judge_value(item, "9.1", limits).level == LEVEL_NORMAL  # TC-01

    def test_missing_value_is_pending(self) -> None:
        item = self._water()
        assert judge_value(item, None).level == LEVEL_PENDING
        assert judge_value(item, "  ").level == LEVEL_PENDING

    def test_missing_layer_is_skipped(self) -> None:
        """没有 3σ 就不判黄；没有内控就不会橙。"""
        item = JudgeItem(
            item_name="总杂质（%）",
            value_type=VALUE_TYPE_QUANT,
            legal_text="≤2.0%",
            internal_text=None,
            sigma_text=None,
        )
        assert judge_value(item, "1.8").level == LEVEL_NORMAL
        assert judge_value(item, "2.5").level == LEVEL_OOS

    def test_qual_negative_words(self) -> None:
        item = JudgeItem(item_name="无菌", value_type=VALUE_TYPE_QUAL, legal_text="应符合规定")
        assert judge_value(item, "符合规定").level == LEVEL_NORMAL
        assert judge_value(item, "不符合规定").level == LEVEL_OOS
        assert judge_value(item, "结晶性不符合规定").level == LEVEL_OOS

    def test_grade_project_skipped(self) -> None:
        item = JudgeItem(
            item_name="溶液颜色",
            value_type=VALUE_TYPE_GRADE,
            legal_text="≤Y7/YG7/OY7",
        )
        assert judge_value(item, "Y3/YG3/OY3").level == LEVEL_SKIP

    def test_record_only_skipped(self) -> None:
        item = JudgeItem(item_name="松密度", value_type=VALUE_TYPE_QUANT, is_record_only=True)
        assert judge_value(item, "0.53").level == LEVEL_SKIP

    def test_numeric_project_with_text_value_falls_back(self) -> None:
        """标准是数值、但实测值录成文字时不能判待检。"""
        item = JudgeItem(item_name="重金属", value_type=VALUE_TYPE_QUANT, legal_text="应不得过百万分之二十")
        assert judge_value(item, "符合规定").level == LEVEL_NORMAL
        assert judge_value(item, "不符合规定").level == LEVEL_OOS


class TestAggregateLevel:
    def test_priority(self) -> None:
        assert aggregate_level(["normal", "oos", "internal"]) == LEVEL_OOS
        assert aggregate_level(["normal", "internal", "trend"]) == LEVEL_INTERNAL
        assert aggregate_level(["normal", "trend"]) == LEVEL_TREND
        assert aggregate_level(["normal", "normal"]) == LEVEL_NORMAL

    def test_pending_and_skip_ignored(self) -> None:
        assert aggregate_level(["pending", "skip", "normal"]) == LEVEL_NORMAL
        assert aggregate_level(["pending", "skip"]) == LEVEL_PENDING


def _build_docx(*rows: list[str], with_ins: bool = False) -> bytes:
    """构造最小 docx，只写 word/document.xml（解析器只读这个）。"""
    w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    tr_xml = []
    for row in rows:
        cells = []
        for cell in row:
            if with_ins and "05" in cell:
                before, after = cell.split("05", 1)
                run = (
                    f"<w:r><w:t>{before}</w:t></w:r>"
                    f"<w:ins><w:r><w:t>05</w:t></w:r></w:ins>"
                    f"<w:r><w:t>{after}</w:t></w:r>"
                )
            else:
                run = f"<w:r><w:t>{cell}</w:t></w:r>"
            cells.append(f"<w:tc><w:p>{run}</w:p></w:tc>")
        tr_xml.append(f"<w:tr>{''.join(cells)}</w:tr>")
    document = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<w:document xmlns:w="{w}"><w:body><w:tbl>{"".join(tr_xml)}</w:tbl></w:body></w:document>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


class TestParseStandardDocx:
    def test_basic_sections(self) -> None:
        content = _build_docx(
            ["字段", "类型/格式", "说明"],
            ["品名", "文本", ""],
            ["批号", "数字", ""],
            ["水分（%）", "数字", "标准：8.0%～11.0%，企业内控：8.5%～10.5%，3σ标准：8.5%～10.1%"],
            ["重金属", "文本", "应不得过百万分之二十"],
        )
        parsed = parse_standard_docx(content)
        assert [item.item_name for item in parsed.items] == ["水分（%）", "重金属"]
        water = parsed.items[0]
        assert water.legal_text == "8.0%～11.0%"
        assert water.internal_text == "8.5%～10.5%"
        assert water.sigma_text == "8.5%～10.1%"
        assert water.unit == "%"
        # 基础字段行不能当成检验项目
        assert all("品名" not in item.item_name for item in parsed.items)

    def test_revision_insert_text_is_read(self) -> None:
        """w:ins 里的 05 必须读到，否则 ＜0.05EU/mg 会变成 ＜0.EU/mg。"""
        content = _build_docx(
            ["字段", "类型/格式", "说明"],
            ["细菌内毒素", "文本", "标准：＜0.20EU/mg，企业内控：＜0.05EU/mg"],
            with_ins=True,
        )
        parsed = parse_standard_docx(content)
        assert parsed.items[0].internal_text == "＜0.05EU/mg"

    def test_missing_table_raises(self) -> None:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("word/document.xml", "<document></document>")
        with pytest.raises(Exception):
            parse_standard_docx(buffer.getvalue())


class TestBridge:
    @staticmethod
    def _columns(*names: str) -> list[ColumnHeader]:
        return [
            ColumnHeader(index=index, letter=letter, name=name)
            for index, (name, letter) in enumerate(zip(names, "BCDEFGHIJ"), start=2)
        ]

    def test_normalize_strips_prefix_and_parentheses(self) -> None:
        assert normalize_name("有关物质-最大杂质（%）") == "最大杂质"
        assert normalize_name("残留溶媒-甲醇（%）") == "甲醇"
        assert normalize_name("【性状】") == "性状"

    def test_auto_and_pending(self) -> None:
        columns = self._columns("比旋度（°）", "最大杂质（%）", "高效液相色谱")
        result = bridge_items(["比旋度（°）", "有关物质-最大杂质（%）", "鉴别（1）"], columns)
        assert {match.item_name for match in result.auto} == {"比旋度（°）", "有关物质-最大杂质（%）"}
        assert [item.item_name for item in result.pending] == ["鉴别（1）"]
        assert [column.name for column in result.extra_columns] == ["高效液相色谱"]

    def test_saved_mapping_reused(self) -> None:
        columns = self._columns("高效液相色谱", "红外光谱")
        result = bridge_items(["鉴别（1）"], columns, existing_mapping={"鉴别（1）": "红外光谱"})
        assert len(result.auto) == 1
        assert result.auto[0].column_name == "红外光谱"
        assert result.pending == []

    def test_one_column_used_once(self) -> None:
        columns = self._columns("溶液澄清度（1.2g→10ml）", "溶液澄清度")
        result = bridge_items(["溶液澄清度", "溶液澄清度"], columns)
        matched = {match.column_index for match in result.auto}
        assert len(matched) == len(result.auto)  # 同一列不会被两项占用
