"""顶栏待办已读判定单测（不连库）。

覆盖：
- 内容指纹随状态 / 当前环节 / 判定依据变化；
- 只有指纹一致才算已读，内容推进会重新提醒；
- 未读数口径 = 待办总数 - 命中已读键数；
- 批量标记去重（PG upsert 不允许同语句重复冲突键）与空列表。
"""

from __future__ import annotations

import pytest

from app.platform.workbench.constants import MATCH_PERSON, MATCH_ROLE
from app.platform.workbench.read_marks import (
    item_key,
    normalize_marks,
    read_key_set,
    todo_fingerprint,
)
from app.platform.workbench.schemas import TodoReadMark
from app.platform.workbench.service import _to_model
from app.shared.workbench_types import WorkbenchItem


def _item(**overrides: object) -> WorkbenchItem:
    values: dict[str, object] = {
        "id": "item-1",
        "source": "quality.deviation.todos",
        "module_key": "quality",
        "module_label": "质量管理",
        "doc_type_label": "偏差台账",
        "title": "投料量偏差",
        "status": "pending_qa_review",
        "step_label": "QA 审核",
        "match_kind": MATCH_PERSON,
    }
    values.update(overrides)
    return WorkbenchItem(**values)  # type: ignore[arg-type]


def _mark(item: WorkbenchItem, fingerprint: str | None = None) -> TodoReadMark:
    return TodoReadMark(
        source=item.source,
        item_id=item.id,
        fingerprint=fingerprint if fingerprint is not None else todo_fingerprint(item),
    )


# ── 指纹 ──────────────────────────────────────────────────────────


def test_fingerprint_stable_for_same_content() -> None:
    assert todo_fingerprint(_item()) == todo_fingerprint(_item())


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "pending_qc_review"},
        {"step_label": "QC 审核"},
        {"match_kind": MATCH_ROLE},
    ],
)
def test_fingerprint_changes_when_content_changes(overrides: dict[str, object]) -> None:
    assert todo_fingerprint(_item()) != todo_fingerprint(_item(**overrides))


def test_fingerprint_handles_missing_step() -> None:
    assert todo_fingerprint(_item(step_label=None)) == "pending_qa_review||person"


# ── 已读命中 ──────────────────────────────────────────────────────


def test_read_key_set_matches_same_fingerprint() -> None:
    item = _item()
    stored = {item_key(item): todo_fingerprint(item)}
    assert read_key_set([item], stored) == {item_key(item)}


def test_read_key_set_ignores_stale_fingerprint() -> None:
    item = _item(status="pending_qc_review")
    stored = {item_key(item): todo_fingerprint(_item(status="pending_qa_review"))}
    assert read_key_set([item], stored) == set()


def test_read_key_set_ignores_unknown_item() -> None:
    assert read_key_set([_item()], {}) == set()


def test_unread_total_is_total_minus_read() -> None:
    read_item = _item(id="a")
    unread_item = _item(id="b")
    changed_item = _item(id="c", status="pending_qc_review")
    items = [read_item, unread_item, changed_item]
    stored = {
        item_key(read_item): todo_fingerprint(read_item),
        item_key(changed_item): todo_fingerprint(_item(id="c")),
    }

    read_keys = read_key_set(items, stored)
    assert len(read_keys) == 1
    assert len(items) - len(read_keys) == 2


# ── 批量标记 ──────────────────────────────────────────────────────


def test_normalize_marks_dedupes_and_keeps_last() -> None:
    item = _item()
    stale = _mark(item, fingerprint="old")
    fresh = _mark(item, fingerprint="new")

    normalized = normalize_marks([stale, fresh])

    assert normalized == [fresh]


def test_normalize_marks_keeps_order() -> None:
    first = _mark(_item(id="a"))
    second = _mark(_item(id="b"))

    assert normalize_marks([first, second]) == [first, second]


def test_normalize_marks_empty() -> None:
    assert normalize_marks([]) == []


# ── 响应模型 ──────────────────────────────────────────────────────


def test_to_model_exposes_fingerprint_and_read_flag() -> None:
    item = _item()

    unread_model = _to_model(item, set())
    assert unread_model.is_read is False
    assert unread_model.fingerprint == todo_fingerprint(item)

    read_model = _to_model(item, {item_key(item)})
    assert read_model.is_read is True


def test_to_model_without_read_keys_defaults_to_unread() -> None:
    model = _to_model(_item())
    assert model.is_read is False
