"""页内视觉引导单测：分句、形状命中、时长分配与缓存指纹。

纯函数用例，不依赖数据库、不渲染视频。重点守三件事：
1. 各段时间之和严格等于旁白时长（否则成片音画会漂移）；
2. 命中不到就返回空 boxes，宁可不亮也不能亮错；
3. 换样式或挪版式必须让视觉指纹变化，否则旧片段被复用、高亮静默失效。
"""

from typing import Any

from app.modules.agent.highlight import (
    LONG_SENTENCE_CHARS,
    HighlightBox,
    HighlightPlan,
    HighlightStep,
    ScriptSegment,
    boxes_for_segment,
    build_plan,
    build_plan_for_segments,
    element_catalog,
    element_index,
    iter_elements,
    iter_shapes,
    match_shapes,
    merge_short_steps,
    plan_signature,
    resolve_segments,
    slide_size,
    split_sentences,
    stored_segments_hit,
    visual_fingerprint,
)


def _layout(*shapes: dict[str, Any], width: int = 12192000, height: int = 6858000) -> dict[str, Any]:
    return {"width": width, "height": height, "shapes": list(shapes)}


def _shape(
    text: str, *, left: int = 600000, top: int = 400000, width: int = 3000000, height: int = 600000
) -> dict[str, Any]:
    return {"name": text, "kind": "text", "text": text, "left": left, "top": top, "width": width, "height": height}


# ── 分句 ──────────────────────────────────────────────────────────────────


def test_split_sentences_by_end_punctuation() -> None:
    # NFKC 会把全角 ！？ 归一成半角，切分结果按归一化后的文本比对
    sentences = split_sentences("第一句话写得长一些。第二句话也写得长一些！第三句话同样长一些？")

    assert sentences == ["第一句话写得长一些。", "第二句话也写得长一些!", "第三句话同样长一些?"]


def test_split_sentences_returns_empty_for_blank() -> None:
    assert split_sentences("") == []
    assert split_sentences("   \n　") == []


def test_split_sentences_splits_long_sentence_by_comma() -> None:
    long_text = (
        "这个句子里包含了很多很多的内容要讲清楚，需要按逗号再切一次才能显示得下这一屏，最后再补一句完整的结尾说明。"
    )
    assert len(long_text) > LONG_SENTENCE_CHARS
    sentences = split_sentences(long_text)
    assert len(sentences) == 3


def test_split_sentences_merges_tiny_fragments() -> None:
    # 短于 6 字的分句会并回上一句，避免画面高频闪烁
    sentences = split_sentences("这一句稍微长一点，不会被合并掉。好。")
    assert len(sentences) == 1
    assert sentences[0].endswith("好。")


def test_split_sentences_respects_max_steps() -> None:
    text = "。".join(f"第{i}句话内容" for i in range(1, 11)) + "。"
    assert len(split_sentences(text, max_steps=3)) <= 3


# ── 形状命中 ──────────────────────────────────────────────────────────────


def test_iter_shapes_accepts_list_and_dict() -> None:
    assert len(iter_shapes([_shape("甲")])) == 1
    assert len(iter_shapes(_layout(_shape("甲")))) == 1
    assert iter_shapes(None) == []
    assert iter_shapes({"shapes": "不是列表"}) == []


def test_slide_size_reads_canvas() -> None:
    assert slide_size(_layout()) == (12192000, 6858000)
    assert slide_size([_shape("甲")]) is None
    assert slide_size({"width": 0, "height": 0}) is None


def test_match_shapes_hits_mentioned_shape() -> None:
    layout = _layout(_shape("含量测定"), _shape("有关物质", top=2000000))
    boxes = match_shapes("本页介绍含量测定方法。", layout)

    assert len(boxes) == 1
    box = boxes[0]
    # 外扩边距：左右各留白，避免描边压字
    assert box.left == 600000 - 60000
    assert box.top == 400000 - 40000
    assert box.width == 3000000 + 120000
    assert box.height == 600000 + 80000


def test_match_shapes_returns_empty_when_nothing_matches() -> None:
    layout = _layout(_shape("有关物质"))
    assert match_shapes("本页介绍含量测定方法。", layout) == []


def test_match_shapes_skips_too_short_and_invalid_shapes() -> None:
    layout = _layout(_shape("甲"), _shape("含量测定", width=0), {"text": "含量测定", "left": "坏值"})
    assert match_shapes("本页介绍含量测定方法。", layout) == []


def test_match_shapes_clamps_negative_origin() -> None:
    layout = _layout(_shape("含量测定", left=10000, top=10000))
    box = match_shapes("本页介绍含量测定方法。", layout)[0]
    assert box.left == 0
    assert box.top == 0


def test_match_shapes_carries_element_kind_for_recolor_split() -> None:
    """出帧要按元素类型分流：文本框染色，图片只描边，所以 kind 必须透传到 HighlightBox。"""
    picture = {
        "name": "图谱",
        "kind": "PICTURE (13)",
        "text": "含量测定图谱",
        "left": 600000,
        "top": 400000,
        "width": 3000000,
        "height": 2000000,
    }
    picture_box = match_shapes("本页展示含量测定图谱。", _layout(picture))[0]
    text_box = match_shapes("本页介绍含量测定方法。", _layout(_shape("含量测定方法")))[0]

    assert picture_box.kind == "PICTURE (13)"
    assert picture_box.is_text is False
    assert text_box.kind == "text"
    assert text_box.is_text is True


# ── 计划与时长 ────────────────────────────────────────────────────────────


def test_build_plan_sums_to_duration_exactly() -> None:
    plan = build_plan("第一句话内容。第二句话内容。第三句话内容。", _layout(), duration_ms=9000)

    assert plan.total_ms == 9000
    assert len(plan.steps) == 3
    assert plan.steps[0].start_ms == 0
    assert plan.steps[-1].end_ms == 9000
    for previous, current in zip(plan.steps, plan.steps[1:]):
        assert previous.end_ms == current.start_ms
    assert sum(step.duration_ms for step in plan.steps) == 9000


def test_build_plan_returns_empty_for_zero_duration_or_blank_script() -> None:
    assert build_plan("有讲稿。", _layout(), duration_ms=0).steps == []
    assert build_plan("", _layout(), duration_ms=5000).steps == []
    assert build_plan("有讲稿。", _layout(), duration_ms=0).total_ms == 0


def test_build_plan_has_boxes_tracks_hits() -> None:
    hit = build_plan("本页介绍含量测定方法。", _layout(_shape("含量测定")), duration_ms=4000)
    miss = build_plan("本页介绍含量测定方法。", _layout(), duration_ms=4000)

    assert hit.has_boxes is True
    assert miss.has_boxes is False


# ── 缓存指纹 ──────────────────────────────────────────────────────────────


def _plan(*steps: tuple[int, int, list[HighlightBox]]) -> HighlightPlan:
    return HighlightPlan(
        steps=[
            HighlightStep(text=f"第{i}句", start_ms=start, end_ms=end, boxes=boxes)
            for i, (start, end, boxes) in enumerate(steps)
        ],
        total_ms=steps[-1][1] if steps else 0,
    )


def test_plan_signature_is_stable_and_length_limited() -> None:
    box = HighlightBox(left=0, top=0, width=10, height=10)
    first = plan_signature(_plan((0, 1000, [box])))
    second = plan_signature(_plan((0, 1000, [box])))
    assert first == second
    assert len(first) == 16


def test_plan_signature_changes_with_split_or_boxes() -> None:
    box = HighlightBox(left=0, top=0, width=10, height=10)
    base = plan_signature(_plan((0, 1000, [box])))

    assert base != plan_signature(_plan((0, 1000, [])))
    assert base != plan_signature(_plan((0, 900, [box])))
    assert base != plan_signature(_plan((0, 1000, [HighlightBox(left=5, top=0, width=10, height=10)])))


def test_visual_fingerprint_tracks_style_and_layout() -> None:
    box = HighlightBox(left=0, top=0, width=10, height=10)
    plan = _plan((0, 1000, [box]))
    layout = _layout(_shape("含量测定"))

    base = visual_fingerprint(plan, layout, "dim")
    assert base == visual_fingerprint(plan, layout, "dim")
    # 换样式
    assert base != visual_fingerprint(plan, layout, "outline")
    # 挪版式（分句与高亮框不变，但页面位置变了）
    moved = _layout(_shape("含量测定", left=900000))
    assert base != visual_fingerprint(plan, moved, "dim")


def test_visual_fingerprint_differs_from_plan_signature() -> None:
    plan = _plan((0, 1000, []))
    assert visual_fingerprint(plan, _layout(), "dim") != plan_signature(plan)


# ── 可高亮元素与 id ───────────────────────────────────────────────────────


def _table(
    *,
    left: int = 1000000,
    top: int = 1000000,
    width: int = 4000000,
    height: int = 2000000,
) -> dict[str, Any]:
    return {
        "name": "数据表",
        "kind": "TABLE (19)",
        "text": "产线\n收率",
        "left": left,
        "top": top,
        "width": width,
        "height": height,
        "cells": [
            {
                "row": 1,
                "col": 1,
                "text": "产线",
                "left": left,
                "top": top,
                "width": 2000000,
                "height": 1000000,
            },
            {
                "row": 1,
                "col": 2,
                "text": "收率",
                "left": left + 2000000,
                "top": top,
                "width": 2000000,
                "height": 1000000,
            },
        ],
    }


def _picture() -> dict[str, Any]:
    # 图片没有文字，但仍然是合法的高亮目标
    return {
        "name": "示意图",
        "kind": "PICTURE (13)",
        "text": "",
        "left": 500000,
        "top": 500000,
        "width": 800000,
        "height": 600000,
    }


def test_iter_elements_gives_stable_ids_for_shapes_and_cells() -> None:
    layout = _layout(_shape("标题"), _table(), _picture())

    ids = [element.element_id for element in iter_elements(layout)]

    assert ids == ["s0", "s1", "s1.r1c1", "s1.r1c2", "s2"]
    assert element_index(layout)["s1.r1c2"].text == "收率"


def test_element_catalog_skips_decorative_and_truncates_text() -> None:
    layout = _layout(
        {
            "name": "装饰块",
            "kind": "AUTO_SHAPE (1)",
            "text": "",
            "left": 0,
            "top": 0,
            "width": 900000,
            "height": 900000,
        },
        _shape("字" * 80),
        _picture(),
    )

    catalog = element_catalog(layout, max_items=10)

    kinds = {item["id"]: item["text"] for item in catalog}
    assert "s0" not in kinds  # 无文字的装饰形状不该占用 prompt 预算
    assert "s1" in kinds
    assert kinds["s1"].endswith("…")
    assert len(kinds["s1"]) <= 41
    assert kinds["s2"] == "（无文字）"


def test_element_catalog_respects_item_limit() -> None:
    layout = _layout(*[_shape(f"要点{i}") for i in range(8)])
    assert len(element_catalog(layout, max_items=3)) == 3


# ── 讲稿段与绑定 ──────────────────────────────────────────────────────────


def test_stored_segments_hit_requires_same_script() -> None:
    layout = _layout(_shape("收率提升"))
    stored = [{"text": "收率提升。", "targets": ["s0"]}]

    assert stored_segments_hit(stored, "收率提升。", layout)
    assert not stored_segments_hit(stored, "收率大幅提升。", layout)
    assert not stored_segments_hit(None, "收率提升。", layout)


def test_resolve_segments_keeps_targets_when_script_matches() -> None:
    layout = _layout(_shape("收率提升"), _table())
    stored = [
        {"text": "本页讲收率提升。", "targets": ["s0"]},
        {"text": "表格里是分线数据。", "targets": ["s1.r1c2", "s99"]},
    ]

    segments = resolve_segments("本页讲收率提升。表格里是分线数据。", layout, stored)

    assert [segment.targets for segment in segments] == [("s0",), ("s1.r1c2",)]
    assert segments[0].text == "本页讲收率提升。"


def test_resolve_segments_falls_back_after_manual_edit() -> None:
    layout = _layout(_shape("收率提升"))
    stored = [{"text": "旧的讲稿。", "targets": ["s0"]}]

    segments = resolve_segments("换成了新的讲稿。", layout, stored)

    assert [segment.text for segment in segments] == ["换成了新的讲稿。"]
    assert segments[0].targets == ()


def test_resolve_segments_returns_empty_for_blank_script() -> None:
    assert resolve_segments("   ", _layout(_shape("甲")), [{"text": "旧的", "targets": []}]) == []


def test_resolve_segments_caps_step_count() -> None:
    script = "".join(f"第{i}句话内容。" for i in range(1, 10))
    segments = resolve_segments(script, _layout(), max_steps=3)
    assert len(segments) <= 3
    assert "".join(segment.text for segment in segments) == script


# ── 真实时长的时间轴 ──────────────────────────────────────────────────────


def test_build_plan_for_segments_uses_measured_durations() -> None:
    layout = _layout(_shape("收率提升"))
    segments = [ScriptSegment("第一段话。", ("s0",)), ScriptSegment("第二段话。")]
    # 两段音频 1200ms + 900ms，中间 100ms 停顿已由调用方计入第一段
    plan = build_plan_for_segments(segments, layout, [1300, 900], total_ms=2200)

    assert [step.start_ms for step in plan.steps] == [0, 1300]
    assert [step.end_ms for step in plan.steps] == [1300, 2200]
    assert sum(step.duration_ms for step in plan.steps) == 2200
    # 目标元素直取坐标，与句子文字无关
    assert plan.steps[0].boxes == [element_index(layout)["s0"].box]
    # 第二段既没绑定、文字也不重合，就不该亮（宁可不亮）
    assert plan.steps[1].boxes == []


def test_build_plan_for_segments_last_step_eats_rounding() -> None:
    segments = [ScriptSegment("一。"), ScriptSegment("二。")]
    plan = build_plan_for_segments(segments, _layout(), [1000, 999], total_ms=2005)

    assert plan.steps[-1].end_ms == 2005
    assert sum(step.duration_ms for step in plan.steps) == 2005


def test_build_plan_for_segments_falls_back_to_text_match() -> None:
    layout = _layout(_shape("含量测定"))
    plan = build_plan_for_segments([ScriptSegment("本页介绍含量测定方法。")], layout, [1500], 1500)

    assert plan.steps[0].boxes == match_shapes("本页介绍含量测定方法。", layout)


def test_build_plan_for_segments_returns_empty_without_duration() -> None:
    assert build_plan_for_segments([ScriptSegment("一。")], _layout(), [0], 0).steps == []
    assert build_plan_for_segments([], _layout(), [], 1000).steps == []


def test_boxes_for_segment_dedupes_cell_inside_table() -> None:
    layout = _layout(_table())
    segment = ScriptSegment("看这张表。", ("s0", "s0.r1c1"))

    boxes = boxes_for_segment(segment, layout)

    assert len(boxes) == 1
    assert boxes[0] == element_index(layout)["s0"].box


def test_merge_short_steps_keeps_total_duration() -> None:
    steps = [
        HighlightStep(text="短", start_ms=0, end_ms=300, boxes=[], targets=()),
        HighlightStep(text="长", start_ms=300, end_ms=3000, boxes=[], targets=("s0",)),
    ]

    merged = merge_short_steps(steps, min_dwell_ms=700)

    assert len(merged) == 1
    assert merged[0].start_ms == 0
    assert merged[0].end_ms == 3000
    assert merged[0].duration_ms == 3000
    assert merged[0].targets == ("s0",)
    assert merge_short_steps(steps, min_dwell_ms=0) == steps


def test_plan_signature_tracks_targets() -> None:
    box = HighlightBox(left=0, top=0, width=10, height=10)
    with_target = HighlightPlan(
        steps=[HighlightStep(text="句", start_ms=0, end_ms=1000, boxes=[box], targets=("s0",))], total_ms=1000
    )
    without = HighlightPlan(steps=[HighlightStep(text="句", start_ms=0, end_ms=1000, boxes=[box])], total_ms=1000)

    assert plan_signature(with_target) != plan_signature(without)


def test_visual_fingerprint_tracks_table_cell_geometry() -> None:
    plan = _plan((0, 1000, []))
    taller = _table()
    taller["cells"][0]["height"] = 1500000

    assert visual_fingerprint(plan, _layout(_table()), "dim") != visual_fingerprint(plan, _layout(taller), "dim")
