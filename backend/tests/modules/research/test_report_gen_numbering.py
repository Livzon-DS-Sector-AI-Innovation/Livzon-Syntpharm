"""目录编号解析与顺延：阿拉伯 / 中文 / 括号 / 章节四种常见写法都要能接上。"""

from __future__ import annotations

from app.modules.research.report_gen.numbering import bump_number, parse_number, strip_number


def test_parse_arabic_multilevel() -> None:
    token = parse_number("4.4. 路线4")
    assert token is not None
    assert token.parts == [4, 4]
    assert token.separator == ". "
    assert token.render() == "4.4"
    bumped = bump_number(token)
    assert bumped is not None and bumped.render() == "4.5"


def test_parse_chinese_enumeration() -> None:
    token = parse_number("四、路线4")
    assert token is not None
    assert token.chinese is True
    assert token.parts == [4]
    assert token.separator == "、"
    bumped = bump_number(token)
    assert bumped is not None and bumped.render() == "五"


def test_parse_chinese_ten() -> None:
    token = parse_number("十、路线10")
    assert token is not None and token.parts == [10]
    bumped = bump_number(token)
    assert bumped is not None and bumped.render() == "十一"


def test_parse_parenthesized() -> None:
    chinese = parse_number("（四）路线4")
    assert chinese is not None
    assert chinese.head == "（" and chinese.tail == "）"
    chinese_bumped = bump_number(chinese)
    assert chinese_bumped is not None and chinese_bumped.render() == "（五）"

    arabic = parse_number("(4) 路线4")
    assert arabic is not None
    arabic_bumped = bump_number(arabic)
    assert arabic_bumped is not None and arabic_bumped.render() == "(5)"


def test_parse_chapter_heading() -> None:
    chinese = parse_number("第四章 工艺路线")
    assert chinese is not None
    assert chinese.head == "第" and chinese.tail == "章"
    chinese_bumped = bump_number(chinese)
    assert chinese_bumped is not None and chinese_bumped.render() == "第五章"

    arabic = parse_number("第4章 工艺路线")
    assert arabic is not None
    arabic_bumped = bump_number(arabic)
    assert arabic_bumped is not None and arabic_bumped.render() == "第5章"


def test_strip_number_removes_prefix_only() -> None:
    assert strip_number("4.5 路线5") == "路线5"
    assert strip_number("四、路线5") == "路线5"
    assert strip_number("（五）路线5") == "路线5"
    assert strip_number("第五章 工艺路线") == "工艺路线"
    assert strip_number("路线5") == "路线5"


def test_unrecognized_prefix_is_left_alone() -> None:
    assert parse_number("附录A 数据") is None
    assert strip_number("附录A 数据") == "附录A 数据"
