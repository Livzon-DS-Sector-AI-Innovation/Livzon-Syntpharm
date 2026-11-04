"""渲染原语：页图派生（预览大图 / 缩略图）。

只验证缩放规则与编码格式，不依赖 ffmpeg/soffice，可在任意环境跑。
"""

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from app.modules.agent import render


def _make_png(path: Path, width: int, height: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), (30, 120, 200)).save(path, "PNG")
    return path


def test_encode_jpeg_scales_down_keeping_aspect_ratio(tmp_path: Path) -> None:
    source = _make_png(tmp_path / "slide.png", 3000, 1688)

    target = render.encode_jpeg(source, tmp_path / "out" / "preview.jpg", render.PREVIEW_MAX_WIDTH, 88)

    with Image.open(target) as image:
        assert image.format == "JPEG"
        assert image.width == render.PREVIEW_MAX_WIDTH
        # 只等比缩小，不裁切：预览图与成片构图必须一致
        assert image.height == round(1688 * render.PREVIEW_MAX_WIDTH / 3000)


def test_encode_jpeg_never_upscales_small_page(tmp_path: Path) -> None:
    source = _make_png(tmp_path / "small.png", 800, 450)

    target = render.encode_jpeg(source, tmp_path / "out" / "thumb.jpg", render.PREVIEW_MAX_WIDTH, 78)

    with Image.open(target) as image:
        assert (image.width, image.height) == (800, 450)


def test_render_pdf_pages_renders_one_page_at_a_time_with_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """逐页拆图：内存只留单页，且按页码顺序回调（左栏进度条依赖它）。"""
    requested: list[int] = []
    reported: list[tuple[int, int]] = []

    def fake_convert(
        path: str, dpi: int = 150, fmt: str = "png", first_page: int = 1, last_page: int = 1
    ) -> list[Image.Image]:
        requested.append(first_page)
        assert first_page == last_page  # 一次只能拆一页，否则又回到整本驻留内存
        return [Image.new("RGB", (12, 9), (255, 255, 255))]

    monkeypatch.setattr("pdf2image.pdfinfo_from_path", lambda path: {"Pages": 3})
    monkeypatch.setattr("pdf2image.convert_from_path", fake_convert)

    paths = render.render_pdf_pages(
        tmp_path / "source.pdf",
        tmp_path / "png",
        dpi=150,
        on_page=lambda page, total: reported.append((page, total)),
    )

    assert requested == [1, 2, 3]
    assert [path.name for path in paths] == ["slide-001.png", "slide-002.png", "slide-003.png"]
    assert reported == [(1, 3), (2, 3), (3, 3)]


def test_pdf_page_count_wraps_poppler_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(path: str) -> dict[str, Any]:
        raise RuntimeError("poppler missing")

    monkeypatch.setattr("pdf2image.pdfinfo_from_path", boom)

    with pytest.raises(render.RenderError):
        render.pdf_page_count(tmp_path / "source.pdf")


def _list_durations(list_file: Path) -> list[float]:
    return [
        float(line.split()[1])
        for line in list_file.read_text(encoding="utf-8").splitlines()
        if line.startswith("duration ")
    ]


def test_build_highlighted_segment_closes_frame_durations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """帧时长 + 首尾留白必须与 -t 完全闭合，否则 concat -c copy 之后音画会逐渐漂移。"""
    commands: list[list[str]] = []

    def fake_run(command: list[str], timeout: int, cwd: str | Path | None = None) -> Any:
        commands.append(command)
        return None

    monkeypatch.setattr(render, "run_command", fake_run)
    first = _make_png(tmp_path / "frames" / "00.png", 20, 10)
    second = _make_png(tmp_path / "frames" / "01.png", 20, 10)
    list_file = tmp_path / "frames.txt"

    total_ms = render.build_highlighted_segment(
        [(first, 1200), (second, 600)],
        tmp_path / "voice.wav",
        tmp_path / "out.mp4",
        1800,
        head_padding_ms=400,
        tail_padding_ms=300,
        list_file=list_file,
        threads=2,
    )

    assert total_ms == 400 + 1800 + 300
    assert round(sum(_list_durations(list_file)) * 1000) == total_ms
    assert commands[0][commands[0].index("-t") + 1] == "2.500"


def _make_text_slide(path: Path) -> Path:
    """白底 + 一条黑色色块（模拟一行字），色块面积远小于底色。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (200, 100), (255, 255, 255))
    for x in range(20, 180):
        for y in range(40, 60):
            image.putpixel((x, y), (0, 0, 0))
    image.save(path, "PNG")
    return path


def _pixel(path: Path, x: int, y: int) -> tuple[int, int, int]:
    with Image.open(path) as image:
        pixel = image.convert("RGB").getpixel((x, y))
    assert isinstance(pixel, tuple)
    red, green, blue = pixel[:3]
    return (int(red), int(green), int(blue))


def test_compose_highlight_recolors_text_pixels_only(tmp_path: Path) -> None:
    """文字染色：框内字变主色，框内空白与框外背景都不动。"""
    source = _make_text_slide(tmp_path / "page.png")

    target = render.compose_highlight_frame(
        source,
        tmp_path / "frame.png",
        [(10, 30, 180, 40)],
        (200, 100),
        0,
        (255, 0, 0),
        0,
        kinds=["TEXT_BOX (17)"],
        recolor_strength=100,
    )

    assert _pixel(target, 100, 50) == (255, 0, 0)  # 字被染红
    assert _pixel(target, 100, 35) == (255, 255, 255)  # 框内空白保持原色
    assert _pixel(target, 5, 5) == (255, 255, 255)  # 框外背景不动


def test_compose_highlight_keeps_picture_unpainted(tmp_path: Path) -> None:
    """图片/图表只描边不染色：整块染色会糊成红色剪影。"""
    source = _make_text_slide(tmp_path / "page.png")

    target = render.compose_highlight_frame(
        source,
        tmp_path / "frame.png",
        [(10, 30, 180, 40)],
        (200, 100),
        0,
        (255, 0, 0),
        0,
        kinds=["PICTURE (13)"],
        recolor_strength=100,
    )

    assert _pixel(target, 100, 50) == (0, 0, 0)  # 前景保持原色


def test_compose_highlight_tints_visual_region_without_recoloring(tmp_path: Path) -> None:
    """视觉元素可加淡色底：颜色偏红但底色不被整块替换。"""
    source = _make_text_slide(tmp_path / "page.png")

    target = render.compose_highlight_frame(
        source,
        tmp_path / "frame.png",
        [(10, 30, 180, 40)],
        (200, 100),
        0,
        (255, 0, 0),
        0,
        kinds=["PICTURE (13)"],
        fill_alpha=28,
        recolor_strength=100,
    )

    red, green, _blue = _pixel(target, 100, 50)
    # 28/255 的主色叠加：仍以原色为主，只是明显偏向红
    assert red > 0 and green < 30
