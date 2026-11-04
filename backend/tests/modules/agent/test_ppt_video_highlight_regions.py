"""区域级高亮单测：区域三态、手绘矩形、句级微调与缓存指纹。

纯函数用例，不依赖数据库。重点守四件事：
1. 元素 id 必须能在 layout 里找到，找不到就丢（宁可不亮也不能亮错）；
2. `off` 的区域真的不高亮，`area` 的区域带着自己的颜色与底色透明度；
3. 手绘矩形按整页比例换算，且默认整页常亮；
4. 区域效果变化必须让视觉指纹变化，否则改了配置旧片段被复用、看着像没生效。
"""

from pathlib import Path
from typing import Any

from app.modules.agent import highlight, render
from app.modules.agent.highlight import (
    REGION_MODE_AREA,
    REGION_MODE_OFF,
    REGION_MODE_TEXT,
    ScriptSegment,
    boxes_for_segment,
    build_plan_for_segments,
    dump_region_config,
    element_index,
    parse_region_config,
    plan_signature,
    resolve_segments,
)

_PAGE_WIDTH = 12192000
_PAGE_HEIGHT = 6858000


def _layout(*shapes: dict[str, Any]) -> dict[str, Any]:
    return {"width": _PAGE_WIDTH, "height": _PAGE_HEIGHT, "shapes": list(shapes)}


def _shape(
    text: str, *, left: int = 600000, top: int = 400000, width: int = 3000000, height: int = 600000
) -> dict[str, Any]:
    return {"name": text, "kind": "text", "text": text, "left": left, "top": top, "width": width, "height": height}


def _ids(layout: dict[str, Any]) -> list[str]:
    return list(element_index(layout))


# ── 配置校验 ────────────────────────────────────────────────────────────────


def test_invalid_element_id_is_dropped() -> None:
    layout = _layout(_shape("发酵工艺"))
    config = parse_region_config({"regions": [{"id": "s99", "mode": REGION_MODE_TEXT}]}, layout)

    assert config.rules == {}


def test_color_and_alpha_are_normalized() -> None:
    layout = _layout(_shape("发酵工艺"))
    element_id = _ids(layout)[0]
    config = parse_region_config(
        {"regions": [{"id": element_id, "mode": REGION_MODE_AREA, "color": "ff3b30", "fill_alpha": 999}]},
        layout,
    )

    rule = config.rules[element_id]
    assert rule.color == "#FF3B30"
    assert rule.fill_alpha == 255


def test_bad_mode_and_bad_rect_are_dropped() -> None:
    layout = _layout(_shape("发酵工艺"))
    config = parse_region_config(
        {
            "regions": [
                {"id": "s0", "mode": "explode"},
                {"id": "rect:0", "mode": REGION_MODE_AREA, "rect": {"x": 0.9, "y": 0.1, "w": 0.5, "h": 0.2}},
            ]
        },
        layout,
    )

    assert config.rules == {}


def test_ids_are_kept_when_layout_missing() -> None:
    # 纯图片页解析不出形状：不能因为“校验不了”就把人工配置清空
    config = parse_region_config(
        {
            "regions": [
                {"id": "s7", "mode": REGION_MODE_OFF},
                {"id": "rect:0", "mode": REGION_MODE_AREA, "rect": {"x": 0.2, "y": 0.2, "w": 0.3, "h": 0.3}},
            ]
        },
        None,
    )

    assert set(config.rules) == {"s7", "rect:0"}


def test_dump_round_trip_keeps_effect() -> None:
    layout = _layout(_shape("发酵工艺"))
    element_id = _ids(layout)[0]
    stored = {
        "regions": [
            {"id": element_id, "mode": REGION_MODE_AREA, "color": "#FF3B30", "fill_alpha": 90},
            {"id": "rect:0", "mode": REGION_MODE_TEXT, "rect": {"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.4}},
        ],
        "sentences": [{"text": "这句话讲的是发酵工艺", "targets": [element_id], "mute": []}],
    }

    config = parse_region_config(stored, layout)
    dumped = dump_region_config(config)
    again = parse_region_config(dumped, layout)

    assert again == config
    assert dump_region_config(highlight.RegionConfig()) is None


# ── 区域三态 ────────────────────────────────────────────────────────────────


def test_off_region_is_not_highlighted() -> None:
    layout = _layout(_shape("发酵工艺"))
    element_id = _ids(layout)[0]
    config = parse_region_config({"regions": [{"id": element_id, "mode": REGION_MODE_OFF}]}, layout)

    boxes = boxes_for_segment(ScriptSegment(text="发酵工艺", targets=(element_id,)), layout, config=config)

    assert boxes == []


def test_area_region_carries_own_color_and_fill() -> None:
    layout = _layout(_shape("发酵工艺"))
    element_id = _ids(layout)[0]
    config = parse_region_config(
        {"regions": [{"id": element_id, "mode": REGION_MODE_AREA, "color": "#00FF00", "fill_alpha": 120}]},
        layout,
    )

    boxes = boxes_for_segment(ScriptSegment(text="发酵工艺", targets=(element_id,)), layout, config=config)

    assert len(boxes) == 1
    assert boxes[0].mode == REGION_MODE_AREA
    assert boxes[0].color == "#00FF00"
    assert boxes[0].fill_alpha == 120


def test_text_region_does_not_override_page_style_for_others() -> None:
    layout = _layout(_shape("第一行"), _shape("第二行", top=1200000))
    first, second = _ids(layout)
    config = parse_region_config({"regions": [{"id": first, "mode": REGION_MODE_TEXT}]}, layout)

    boxes = boxes_for_segment(ScriptSegment(text="第一行", targets=(first, second)), layout, config=config)

    index = element_index(layout)
    by_mode = {box.top: box.mode for box in boxes}
    assert by_mode[index[first].box.top] == REGION_MODE_TEXT
    assert by_mode[index[second].box.top] == ""  # 没配过的区域仍跟随页级样式


# ── 手绘矩形 ────────────────────────────────────────────────────────────────


def test_manual_rect_is_converted_to_emu() -> None:
    layout = _layout(_shape("发酵工艺"))
    config = parse_region_config(
        {"regions": [{"id": "rect:0", "mode": REGION_MODE_AREA, "rect": {"x": 0.25, "y": 0.5, "w": 0.5, "h": 0.25}}]},
        layout,
    )

    boxes = boxes_for_segment(ScriptSegment(text="与本页文字无关的一句话"), layout, config=config)

    assert [(box.left, box.top, box.width, box.height) for box in boxes] == [(3048000, 3429000, 6096000, 1714500)]


def test_manual_rect_is_always_on_but_can_be_muted() -> None:
    layout = _layout(_shape("发酵工艺"))
    config = parse_region_config(
        {"regions": [{"id": "rect:0", "mode": REGION_MODE_AREA, "rect": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}}]},
        layout,
    )

    kept = boxes_for_segment(ScriptSegment(text="随便一句"), layout, config=config)
    muted = boxes_for_segment(ScriptSegment(text="随便一句", mute=("rect:0",)), layout, config=config)

    assert len(kept) == 1
    assert muted == []


# ── 句级微调 ────────────────────────────────────────────────────────────────


def test_sentence_rule_replaces_targets() -> None:
    layout = _layout(_shape("第一行"), _shape("第二行", top=1200000))
    first, second = _ids(layout)
    config = parse_region_config(
        {"sentences": [{"text": "这句话讲的是第二行内容", "targets": [second], "mute": []}]},
        layout,
    )

    segments = resolve_segments("这句话讲的是第二行内容", layout, config=config)

    assert segments[0].targets == (second,)


def test_sentence_rule_survives_punctuation_only_edit() -> None:
    layout = _layout(_shape("第一行"))
    first = _ids(layout)[0]
    config = parse_region_config(
        {"sentences": [{"text": "这句话讲的是第一行内容。", "targets": [first]}]},
        layout,
    )

    segments = resolve_segments("这句话讲的是第一行内容!", layout, config=config)

    assert segments[0].targets == (first,)


def test_sentence_mute_removes_region() -> None:
    layout = _layout(_shape("第一行"), _shape("第二行", top=1200000))
    first, second = _ids(layout)
    config = parse_region_config(
        {"sentences": [{"text": "第一行和第二行", "targets": [first, second], "mute": [second]}]},
        layout,
    )

    segments = resolve_segments("第一行和第二行", layout, config=config)
    boxes = boxes_for_segment(segments[0], layout, config=config)

    assert [box.top for box in boxes] == [element_index(layout)[first].box.top]


# ── 缓存指纹 ────────────────────────────────────────────────────────────────


def test_region_effect_changes_visual_fingerprint() -> None:
    layout = _layout(_shape("发酵工艺"))
    element_id = _ids(layout)[0]
    segment = ScriptSegment(text="发酵工艺", targets=(element_id,))

    plain = build_plan_for_segments([segment], layout, [2000], 2000)
    area = build_plan_for_segments(
        [segment],
        layout,
        [2000],
        2000,
        config=parse_region_config({"regions": [{"id": element_id, "mode": REGION_MODE_AREA}]}, layout),
    )

    assert plan_signature(plain) != plan_signature(area)


# ── 渲染：逐框取画法 ────────────────────────────────────────────────────────


def _make_slide(path: Path) -> Path:
    """白底 + 一条黑色色块（模拟一行字）。"""
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (200, 100), (255, 255, 255))
    for x in range(20, 180):
        for y in range(40, 60):
            image.putpixel((x, y), (0, 0, 0))
    image.save(path, "PNG")
    return path


def _pixel(path: Path, x: int, y: int) -> tuple[int, int, int]:
    from PIL import Image

    with Image.open(path) as image:
        pixel = image.convert("RGB").getpixel((x, y))
    assert isinstance(pixel, tuple)
    red, green, blue = pixel[:3]
    return (int(red), int(green), int(blue))


def test_paints_apply_per_box(tmp_path: Path) -> None:
    source = _make_slide(tmp_path / "page.png")

    target = render.compose_highlight_frame(
        source,
        tmp_path / "frame.png",
        [(0, 0, 200, 30), (10, 30, 180, 40)],
        (200, 100),
        0,
        (255, 0, 0),
        0,
        kinds=["TEXT_BOX (17)", "TEXT_BOX (17)"],
        paints=[
            render.RegionPaint((0, 0, 255), text=False, fill_alpha=255),
            render.RegionPaint((255, 0, 0), text=True, recolor_strength=100),
        ],
    )

    assert _pixel(target, 100, 15) == (0, 0, 255)  # 区域变色：整块铺底色
    assert _pixel(target, 100, 50) == (255, 0, 0)  # 文字变色：只有字变红
    assert _pixel(target, 100, 35) == (255, 255, 255)  # 文字变色的框内空白不动
