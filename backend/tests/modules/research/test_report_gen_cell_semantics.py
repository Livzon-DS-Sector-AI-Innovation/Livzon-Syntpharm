"""单元格语义层的单元测试。

线上实际出过两类错填，这里按「同样的值 + 同样的格子」回归：

- 把「其他名称 / 英文名 / 化学名称 / CAS号」写进意见栏；
- 把「米诺地尔 / Minoxidil / 分子量」按顺序塞进成本表的数值列。
"""

from __future__ import annotations

from app.modules.research.report_gen.cell_semantics import (
    EXPECT_CAS,
    EXPECT_FORMULA,
    EXPECT_NUMBER,
    EXPECT_OPINION,
    EXPECT_TEXT,
    expect_of,
    is_bare_field_label,
    validate_cell_value,
)


def test_expect_of_priority() -> None:
    # 意见优先：「审核意见」里也含「意见」，不能被后面的数值词抢走
    assert expect_of("技术部意见") == EXPECT_OPINION
    assert expect_of("审核意见") == EXPECT_OPINION
    # 强格式列
    assert expect_of("CAS号") == EXPECT_CAS
    assert expect_of("分子式") == EXPECT_FORMULA
    # 数值列：行列都看
    assert expect_of("研发投入") == EXPECT_NUMBER
    assert expect_of("", "自研成本 › 研发周期") == EXPECT_NUMBER
    # 其余按普通文本
    assert expect_of("知识产权") == EXPECT_TEXT
    assert expect_of("", "") == EXPECT_TEXT


def test_bare_field_label_detection() -> None:
    assert is_bare_field_label("其他名称") is True
    assert is_bare_field_label("英文名") is True
    assert is_bare_field_label("CAS号") is True
    assert is_bare_field_label("CAS 号") is True
    # 内容不是标签
    assert is_bare_field_label("米诺地尔") is False
    assert is_bare_field_label("建议按变更控制流程执行。") is False


def test_field_label_is_refused_outside_its_own_cell() -> None:
    reason = validate_cell_value(value="其他名称", expect=EXPECT_TEXT, row_hint="技术部意见")
    assert reason is not None
    assert "字段名" in reason
    # 同一字段名写进它自己的格子是正常的
    assert validate_cell_value(value="药品名称", expect=EXPECT_TEXT, row_hint="药品名称") is None


def test_opinion_cell_only_accepts_chinese_opinion() -> None:
    assert validate_cell_value(value="其他名称", expect=EXPECT_OPINION, row_hint="技术部意见") is not None
    assert validate_cell_value(value="Minoxidil", expect=EXPECT_OPINION, row_hint="技术部意见") is not None
    opinion = "建议补充稳定性数据后再定稿。"
    assert validate_cell_value(value=opinion, expect=EXPECT_OPINION, row_hint="技术部意见") is None
    assert validate_cell_value(value="同意", expect=EXPECT_OPINION, row_hint="技术部意见") is None


def test_cas_and_formula_cells() -> None:
    assert validate_cell_value(value="Minoxidil", expect=EXPECT_CAS, column_hint="CAS号") is not None
    assert validate_cell_value(value="38304-91-5", expect=EXPECT_CAS, column_hint="CAS号") is None
    assert validate_cell_value(value="米诺地尔", expect=EXPECT_FORMULA, column_hint="分子式") is not None
    assert validate_cell_value(value="C9H15N5O", expect=EXPECT_FORMULA, column_hint="分子式") is None


def test_number_cells() -> None:
    assert validate_cell_value(value="米诺地尔", expect=EXPECT_NUMBER, column_hint="自研成本 › 研发投入") is not None
    # 编号与分子式有数字也不能进数值列
    assert validate_cell_value(value="38304-91-5", expect=EXPECT_NUMBER, column_hint="目标成本") is not None
    assert validate_cell_value(value="C9H15N5O", expect=EXPECT_NUMBER, column_hint="目标成本") is not None
    # 带单位/区间/约数的写法要放行
    assert validate_cell_value(value="约 300 万元", expect=EXPECT_NUMBER, column_hint="目标成本") is None
    assert validate_cell_value(value="2-3 年", expect=EXPECT_NUMBER, column_hint="研发周期") is None
    assert validate_cell_value(value="209.25", expect=EXPECT_NUMBER, column_hint="分子量") is None


def test_empty_value_is_refused() -> None:
    assert validate_cell_value(value="   ", expect=EXPECT_TEXT) is not None
