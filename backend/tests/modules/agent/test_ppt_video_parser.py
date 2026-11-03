"""PPT 解析与讲稿切分单测（TC-001/TC-002 的输入侧保障）。

覆盖：
- pptx 页序、每页文本、演讲者备注的读取；
- 讲稿按页标记切分、缺页/超页提示、无标记时的兜底策略；
- 非法格式与损坏文件必须抛 ParserError（message 直接给用户看）。
"""

from pathlib import Path

import pytest
from pptx import Presentation

from app.modules.agent.parser import (
    ParserError,
    parse_pptx,
    read_script_file,
    split_script,
)


def _make_pptx(path: Path, pages: list[tuple[str, str]]) -> Path:
    """按 (正文, 备注) 生成最小 pptx。"""
    presentation = Presentation()
    layout = presentation.slide_layouts[5]  # 标题+内容布局，有可写文本框
    for body, notes in pages:
        slide = presentation.slides.add_slide(layout)
        slide.shapes.title.text = body.splitlines()[0] if body else ""
        if body:
            slide.notes_slide.notes_text_frame.text = notes
    presentation.save(str(path))
    return path


# ── pptx 解析 ───────────────────────────────────────────────────────


def test_parse_pptx_reads_page_order_text_and_notes(tmp_path: Path) -> None:
    pptx = _make_pptx(tmp_path / "deck.pptx", [("封面标题", "片头备注"), ("第二页标题", "正文备注")])

    slides = parse_pptx(pptx)

    assert [slide.slide_no for slide in slides] == [1, 2]
    assert "封面标题" in slides[0].text
    assert slides[1].text == "第二页标题"
    assert slides[0].notes == "片头备注"
    assert slides[1].notes == "正文备注"


def test_parse_pptx_rejects_corrupted_file(tmp_path: Path) -> None:
    broken = tmp_path / "broken.pptx"
    broken.write_bytes(b"not a zip at all")
    with pytest.raises(ParserError):
        parse_pptx(broken)


# ── 讲稿切分 ───────────────────────────────────────────────────────


def test_split_script_by_page_markers() -> None:
    text = "第 1 页：开场\n大家好\n\n## 第2页\n这是正文\n\nPage 3\n结束语"
    result = split_script(text, 3)

    assert result.ok
    assert result.slides[1] == "开场\n大家好"
    assert result.slides[2] == "这是正文"
    assert result.slides[3] == "结束语"


@pytest.mark.parametrize(
    "marker",
    ["第 2 页", "## 第2页", "Page 2", "page 2", "[2]", "#2", "=== 2 ===", "2."],
)
def test_split_script_accepts_common_markers(marker: str) -> None:
    result = split_script(f"第 1 页\n一\n{marker}\n二", 2)
    assert result.slides == {1: "一", 2: "二"}


def test_split_script_reports_missing_pages() -> None:
    result = split_script("第 1 页\n只有第一页", 3)

    assert not result.ok
    assert result.missing_pages == [2, 3]
    assert any("缺少页码" in warning for warning in result.warnings)


def test_split_script_reports_extra_pages() -> None:
    result = split_script("第 1 页\n一\n第 2 页\n二\n第 3 页\n三", 2)

    assert result.extra_pages == [3]
    assert any("超过 PPT 页数" in warning for warning in result.warnings)


def test_split_script_empty_marks_all_missing() -> None:
    result = split_script("   ", 2)
    assert result.missing_pages == [1, 2]
    assert result.slides == {}


def test_split_script_falls_back_to_blank_line_blocks() -> None:
    result = split_script("封面旁白\n\n正文旁白一\n\n正文旁白二", 3)
    assert result.ok
    assert result.slides[2] == "正文旁白一"


def test_split_script_form_feed_alignment() -> None:
    result = split_script("一\f二\f三", 3)
    assert result.ok
    assert result.slides[3] == "三"


def test_split_script_warns_when_no_marker_and_block_mismatch() -> None:
    result = split_script("整段没有分页标记的讲稿\n还在同一段", 3)
    assert result.slides == {}
    assert any("未找到分页标记" in warning for warning in result.warnings)


# ── 讲稿文件读取 ───────────────────────────────────────────────────


def test_read_script_file_txt(tmp_path: Path) -> None:
    path = tmp_path / "script.txt"
    path.write_text("第 1 页\n你好", encoding="utf-8")
    assert "你好" in read_script_file(path)


def test_read_script_file_rejects_unknown_suffix(tmp_path: Path) -> None:
    path = tmp_path / "script.pdf"
    path.write_bytes(b"%PDF-1.4")
    with pytest.raises(ParserError):
        read_script_file(path)
