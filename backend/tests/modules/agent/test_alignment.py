"""页序列对齐单测：指纹稳定性、插页/删页/改页的配对。

纯函数用例，不依赖数据库。重点守两件事：
1. 「什么都没改」不能因为空白或全半角差异被判成变更；
2. 改一页不能被识别成「删一页 + 加一页」——那页的讲稿就丢了。
"""

from app.modules.agent.alignment import (
    CHANGE_SIMILARITY_THRESHOLD,
    PageSnapshot,
    align,
    build_fingerprint,
    normalize_text,
)


def _layout(text: str, *, left: int = 100000, top: int = 200000, image_sha: str | None = None) -> list[dict]:
    shape: dict = {
        "name": "标题",
        "kind": "text",
        "text": text,
        "left": left,
        "top": top,
        "width": 3000000,
        "height": 600000,
    }
    if image_sha:
        shape["image_sha"] = image_sha
    return [shape]


def _page(index: int, text: str, *, notes: str = "", layout: list[dict] | None = None) -> PageSnapshot:
    return PageSnapshot(index=index, page_text=text, notes=notes, layout=layout or [])


# ── 归一化与指纹 ───────────────────────────────────────────────────────────


def test_normalize_text_unifies_width_and_whitespace() -> None:
    assert normalize_text("  全角Ａ　与   空格\n\n换行 ") == "全角A 与 空格 换行"
    assert normalize_text(None) == ""
    assert normalize_text("　") == ""


def test_build_fingerprint_ignores_formatting_noise() -> None:
    left = build_fingerprint(" 含量测定 HPLC ", "备注", _layout("标题"))
    right = build_fingerprint("含量测定\u3000HPLC", " 备注 ", _layout("标题"))
    assert left == right


def test_build_fingerprint_tracks_text_notes_and_layout() -> None:
    base = build_fingerprint("第一页", "备注", _layout("标题"))
    assert base != build_fingerprint("第一页改了", "备注", _layout("标题"))
    assert base != build_fingerprint("第一页", "备注改了", _layout("标题"))
    assert base != build_fingerprint("第一页", "备注", _layout("标题", left=150000))
    assert base != build_fingerprint("第一页", "备注", _layout("标题", top=250000))


def test_build_fingerprint_treats_shape_count_as_change() -> None:
    one = build_fingerprint("第一页", "", _layout("标题"))
    two = build_fingerprint("第一页", "", _layout("标题") + _layout("正文", top=900000))
    assert one != two


def test_build_fingerprint_catches_image_swap_without_text() -> None:
    """纯图页文字与坐标都不变，只换图时必须判为变更，否则页图永不重渲。"""
    old = build_fingerprint("", "", [{"kind": "picture", "image_sha": "a" * 64, "width": 100, "height": 100}])
    new = build_fingerprint("", "", [{"kind": "picture", "image_sha": "b" * 64, "width": 100, "height": 100}])
    assert old != new


# ── 对齐 ──────────────────────────────────────────────────────────────────


def test_align_identical_deck_reports_no_changes() -> None:
    pages = [_page(1, "封面"), _page(2, "目录"), _page(3, "正文")]
    diff = align(pages, pages)

    assert diff.has_changes is False
    assert diff.unchanged == [(1, 1), (2, 2), (3, 3)]
    assert diff.changed == [] and diff.added == [] and diff.removed == []
    assert diff.old_count == 3 and diff.new_count == 3
    assert all(entry.status == "unchanged" and entry.similarity == 1.0 for entry in diff.entries)


def test_align_insert_keeps_following_pages_matched() -> None:
    old = [_page(1, "封面"), _page(2, "目录")]
    new = [_page(1, "封面"), _page(2, "新增的插图页"), _page(3, "目录")]
    diff = align(old, new)

    assert diff.added == [2]
    assert diff.removed == []
    # 目录从第 2 页平移到第 3 页，仍然算未变（讲稿跟着 slide_uid 走）
    assert diff.unchanged == [(1, 1), (2, 3)]
    assert diff.has_changes is True


def test_align_delete_reports_removed_page() -> None:
    old = [_page(1, "封面"), _page(2, "过渡页"), _page(3, "正文")]
    new = [_page(1, "封面"), _page(2, "正文")]
    diff = align(old, new)

    assert diff.removed == [2]
    assert diff.added == []
    assert diff.unchanged == [(1, 1), (3, 2)]


def test_align_content_change_pairs_instead_of_add_remove() -> None:
    old = [_page(1, "封面"), _page(2, "本期销售情况回顾与下一步计划"), _page(3, "结尾")]
    new = [_page(1, "封面"), _page(2, "本期销售情况回顾与下一步重点计划"), _page(3, "结尾")]
    diff = align(old, new)

    assert diff.changed == [(2, 2)]
    assert diff.added == [] and diff.removed == []
    assert diff.unchanged == [(1, 1), (3, 3)]


def test_align_unrelated_replacement_becomes_remove_plus_add() -> None:
    old = [_page(1, "封面"), _page(2, "旧内容：渠道费用说明")]
    new = [_page(1, "封面"), _page(2, "全新的质量体系认证进度")]
    diff = align(old, new)

    assert diff.changed == []
    assert diff.removed == [2]
    assert diff.added == [2]


def test_align_similarity_threshold_is_respected() -> None:
    old = [_page(1, "销售数据分析报表")]
    new = [_page(1, "销售数据分析报表" + "完全不同" * 10)]
    diff = align(old, new)

    if diff.changed:
        assert diff.entries[0].similarity >= CHANGE_SIMILARITY_THRESHOLD
    else:
        assert diff.removed == [1] and diff.added == [1]


def test_align_entries_sorted_by_new_index_for_display() -> None:
    old = [_page(1, "封面"), _page(2, "目录"), _page(3, "结尾")]
    new = [_page(1, "封面"), _page(2, "结尾")]
    diff = align(old, new)

    new_indexes = [entry.new_index for entry in diff.entries if entry.new_index is not None]
    assert new_indexes == sorted(new_indexes)


def test_to_dict_counts_match_lists() -> None:
    old = [_page(1, "封面"), _page(2, "本期销售情况回顾与下一步计划")]
    new = [_page(1, "封面"), _page(2, "本期销售情况回顾与下一步重点计划")]
    payload = align(old, new).to_dict()

    assert payload["unchanged"] == 1
    assert payload["changed"] == 1
    assert payload["old_count"] == 2 and payload["new_count"] == 2
    assert payload["has_changes"] is True
    assert isinstance(payload["entries"], list)


def test_title_truncates_long_first_line() -> None:
    page = _page(1, "甲" * 100)
    assert page.title.endswith("…")
    assert len(page.title) == 41


def test_title_falls_back_to_notes_then_index() -> None:
    assert _page(1, "", notes="第一行备注\n第二行").title == "第一行备注"
    assert _page(7, "", notes="").title == "第 7 页"
