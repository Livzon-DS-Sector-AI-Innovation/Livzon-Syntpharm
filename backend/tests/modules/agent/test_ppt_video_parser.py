"""PPT 解析与讲稿切分单测（TC-001/TC-002 的输入侧保障）。

覆盖：
- pptx 页序、每页文本、演讲者备注的读取；
- 讲稿按页标记切分、缺页/超页提示、无标记时的兜底策略；
- 非法格式与损坏文件必须抛 ParserError（message 直接给用户看）。
"""

import io
from pathlib import Path

import pytest
from PIL import Image
from pptx import Presentation
from pptx.util import Emu

from app.modules.agent.parser import (
    MAX_TABLE_CELLS,
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


# ── 可高亮元素：表格 / 组合 / 图片 ─────────────────────────────────────────


def _png_bytes(width: int = 8, height: int = 8) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buffer, format="PNG")
    return buffer.getvalue()


def _make_rich_pptx(path: Path) -> Path:
    """一页里同时放文本框、表格、组合形状与图片。"""
    presentation = Presentation()
    slide = presentation.slides.add_slide(presentation.slide_layouts[6])

    title = slide.shapes.add_textbox(Emu(600000), Emu(300000), Emu(6000000), Emu(800000))
    title.text_frame.text = "发酵工艺流程"

    table_shape = slide.shapes.add_table(2, 2, Emu(1000000), Emu(1500000), Emu(4000000), Emu(1200000))
    table = table_shape.table
    table.cell(0, 0).text = "产线"
    table.cell(0, 1).text = "收率"
    table.cell(1, 0).text = "A线"
    table.cell(1, 1).text = "91%"

    group = slide.shapes.add_group_shape()
    inner = group.shapes.add_textbox(Emu(100000), Emu(100000), Emu(1500000), Emu(500000))
    inner.text_frame.text = "组内要点"
    group.left = Emu(500000)
    group.top = Emu(4000000)
    group.width = Emu(3000000)
    group.height = Emu(1000000)

    slide.shapes.add_picture(io.BytesIO(_png_bytes()), Emu(6000000), Emu(4000000), Emu(800000), Emu(600000))

    presentation.save(str(path))
    return path


def test_parse_pptx_extracts_table_cells_with_geometry(tmp_path: Path) -> None:
    slides = parse_pptx(_make_rich_pptx(tmp_path / "rich.pptx"))
    slide = slides[0]

    table = next(shape for shape in slide.layout["shapes"] if shape.get("cells"))
    cells = table["cells"]
    assert len(cells) == 4
    assert {(cell["row"], cell["col"]): cell["text"] for cell in cells}[(2, 2)] == "91%"
    # 单元格几何由行列宽高累加得到：同一行往右递增、同一列往下递增
    first, second = cells[0], cells[1]
    assert second["left"] > first["left"]
    assert second["top"] == first["top"]
    assert cells[2]["top"] > first["top"]
    # 表格文字以前完全丢失，现在必须进页面正文，讲稿才看得到数据
    assert "91%" in slide.text
    assert "收率" in slide.text


def test_parse_pptx_extracts_group_text_and_frame(tmp_path: Path) -> None:
    slides = parse_pptx(_make_rich_pptx(tmp_path / "rich.pptx"))
    slide = slides[0]

    group = next(shape for shape in slide.layout["shapes"] if "GROUP" in str(shape["kind"]))
    assert "组内要点" in group["text"]
    # 组合按整组外框亮，子形状的相对坐标不能直接当页面坐标用
    assert group["left"] == 500000
    assert group["width"] == 3000000
    assert "组内要点" in slide.text


def test_parse_pptx_keeps_picture_as_highlight_candidate(tmp_path: Path) -> None:
    slides = parse_pptx(_make_rich_pptx(tmp_path / "rich.pptx"))

    picture = next(shape for shape in slides[0].layout["shapes"] if str(shape["kind"]).startswith("PICTURE"))
    assert picture["text"] == ""
    assert picture["image_sha"]
    assert picture["width"] > 0 and picture["height"] > 0


def test_parse_pptx_table_cell_limit_is_finite() -> None:
    # 上限只是防 prompt 预算被挤爆，这里守住常量语义即可
    assert 0 < MAX_TABLE_CELLS <= 200
