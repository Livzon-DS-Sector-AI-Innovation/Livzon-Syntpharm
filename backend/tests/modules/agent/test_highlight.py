"""页内视觉引导单测：分句、形状命中、时长分配与缓存指纹。

纯函数用例，不依赖数据库、不渲染视频。重点守三件事：
1. 各段时间之和严格等于旁白时长（否则成片音画会漂移）；
2. 命中不到就返回空 boxes，宁可不亮也不能亮错；
3. 换样式或挪版式必须让视觉指纹变化，否则旧片段被复用、高亮静默失效。
"""

from app.modules.agent.highlight import (
    LONG_SENTENCE_CHARS,
    HighlightBox,
    HighlightPlan,
    HighlightStep,
    build_plan,
    iter_shapes,
    match_shapes,
    plan_signature,
    slide_size,
    split_sentences,
    visual_fingerprint,
)


def _layout(*shapes: dict, width: int = 12192000, height: int = 6858000) -> dict:
    return {"width": width, "height": height, "shapes": list(shapes)}


def _shape(text: str, *, left: int = 600000, top: int = 400000, width: int = 3000000, height: int = 600000) -> dict:
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
        "这个句子里包含了很多很多的内容要讲清楚"
        "，需要按逗号再切一次才能显示得下这一屏"
        "，最后再补一句完整的结尾说明。"
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
