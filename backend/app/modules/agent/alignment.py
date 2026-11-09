"""换源页序列对齐。

接口只有一个：`align(old_pages, new_pages) -> AlignedDiff`。

隐藏的实现包含三件事：

1. **页指纹**：只用「归一化页文字 + 备注 + 形状数 + 文本形状坐标摘要」。
   刻意不用渲染图 hash —— DPI / 字体环境一变，整份 PPT 的图 hash 全变，
   会把「什么都没改」误判成「全页变更」。
2. **序列比对**：`difflib.SequenceMatcher` 找 equal / replace / insert / delete 块，
   插页不会让后续页全部错位。
3. **变更页配对**：replace 块里按文本相似度二次配对。
   不配对的话，改一页会被识别成「删一页 + 加一页」，那一页的讲稿就白丢了。

纯函数、无 IO、无数据库，可直接单测。
"""

from __future__ import annotations

import difflib
import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

#: 页面被判定为「同一页但内容变了」的最低文本相似度
CHANGE_SIMILARITY_THRESHOLD = 0.6

DiffStatus = Literal["unchanged", "changed", "added", "removed"]

#: 页版式载荷。新解析产出 {width, height, shapes} 字典；历史数据可能是裸形状列表
Layout = dict[str, Any] | list[dict[str, Any]]

_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class PageSnapshot:
    """用于对齐的一页快照。index 为 1 起的源 PPT 页序。"""

    index: int
    page_text: str = ""
    notes: str = ""
    layout: Layout = field(default_factory=list)
    fingerprint: str | None = None

    @property
    def title(self) -> str:
        """差异表里展示用的短标题。"""
        raw = self.page_text.strip() or self.notes.strip() or f"第 {self.index} 页"
        first_line = raw.splitlines()[0].strip()
        return first_line[:40] + ("…" if len(first_line) > 40 else "")


@dataclass(frozen=True)
class DiffEntry:
    """差异表的一行。old_index / new_index 为空表示新增或删除。"""

    status: DiffStatus
    old_index: int | None
    new_index: int | None
    title: str
    similarity: float = 0.0


@dataclass(frozen=True)
class AlignedDiff:
    """换源比对结果；用户确认之前不落库。"""

    unchanged: list[tuple[int, int]]
    changed: list[tuple[int, int]]
    added: list[int]
    removed: list[int]
    old_count: int
    new_count: int
    entries: list[DiffEntry]

    @property
    def has_changes(self) -> bool:
        return bool(self.changed or self.added or self.removed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "unchanged": len(self.unchanged),
            "changed": len(self.changed),
            "added": len(self.added),
            "removed": len(self.removed),
            "old_count": self.old_count,
            "new_count": self.new_count,
            "has_changes": self.has_changes,
            "entries": [
                {
                    "status": e.status,
                    "old_index": e.old_index,
                    "new_index": e.new_index,
                    "title": e.title,
                    "similarity": round(e.similarity, 3),
                }
                for e in self.entries
            ],
        }


def normalize_text(value: str | None) -> str:
    """归一化页文字：全半角统一、去空白、压缩空行。

    只做「不改变语义」的归一化，避免把真实改动吃掉。
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", value).replace("\u00a0", " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def _shapes(layout: Any) -> list[dict[str, Any]]:
    """layout 允许纯形状列表或 {width,height,shapes} 字典。"""
    if isinstance(layout, dict):
        shapes = layout.get("shapes")
        return [s for s in shapes if isinstance(s, dict)] if isinstance(shapes, list) else []
    if isinstance(layout, list):
        return [s for s in layout if isinstance(s, dict)]
    return []


def _layout_signature(layout: Any) -> str:
    """形状坐标按万分之一个画布单位取整，容忍渲染环境的微小偏移。

    图片形状没有文字，只换图时文字与坐标完全不变，必须把图片内容摘要纳入，
    否则「换了一张图」会被判成「未变」，页图永远不重渲。
    """
    parts: list[str] = []
    for shape in layout:
        text = normalize_text(str(shape.get("text") or ""))
        image_sha = str(shape.get("image_sha") or "")
        if not text and not image_sha:
            continue
        try:
            left = int(round(float(shape.get("left") or 0) / 10000))
            top = int(round(float(shape.get("top") or 0) / 10000))
            width = int(round(float(shape.get("width") or 0) / 10000))
            height = int(round(float(shape.get("height") or 0) / 10000))
        except (TypeError, ValueError):
            continue
        label = text if text else f"pic:{image_sha[:16]}"
        parts.append(f"{label}@{left},{top},{width},{height}")
    return "|".join(parts)


def build_fingerprint(
    page_text: str | None,
    notes: str | None,
    layout: Layout | None = None,
) -> str:
    """页内容指纹：文字 + 备注 + 形状数 + 文本形状坐标摘要。"""
    shapes = _shapes(layout)
    raw = "\n".join(
        (
            normalize_text(page_text),
            normalize_text(notes),
            str(len(shapes)),
            _layout_signature(shapes),
        )
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _similarity(left: PageSnapshot, right: PageSnapshot) -> float:
    a = normalize_text(left.page_text)
    b = normalize_text(right.page_text)
    if not a and not b:
        # 纯图片页：文字都为空时退化为备注比较
        a, b = normalize_text(left.notes), normalize_text(right.notes)
    if not a and not b:
        # 都没有文字，保守判为同一页（真实是否变化交给渲染图 hash 终判）
        return 1.0
    matcher = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if matcher.real_quick_ratio() < CHANGE_SIMILARITY_THRESHOLD:
        return 0.0
    return matcher.ratio()


def align(old_pages: list[PageSnapshot], new_pages: list[PageSnapshot]) -> AlignedDiff:
    """对齐新旧页序列，输出未变 / 变更 / 新增 / 删除四类结果。"""
    old_fps = [page.fingerprint or build_fingerprint(page.page_text, page.notes, page.layout) for page in old_pages]
    new_fps = [page.fingerprint or build_fingerprint(page.page_text, page.notes, page.layout) for page in new_pages]

    matcher = difflib.SequenceMatcher(None, old_fps, new_fps, autojunk=False)

    unchanged: list[tuple[int, int]] = []
    changed: list[tuple[int, int]] = []
    added: list[int] = []
    removed: list[int] = []
    entries: list[DiffEntry] = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                old_i, new_j = i1 + offset, j1 + offset
                unchanged.append((old_i + 1, new_j + 1))
                entries.append(
                    DiffEntry(
                        status="unchanged",
                        old_index=old_i + 1,
                        new_index=new_j + 1,
                        title=old_pages[old_i].title,
                        similarity=1.0,
                    )
                )
            continue

        if tag == "insert":
            for new_j in range(j1, j2):
                added.append(new_j + 1)
                entries.append(
                    DiffEntry(
                        status="added",
                        old_index=None,
                        new_index=new_j + 1,
                        title=new_pages[new_j].title,
                    )
                )
            continue

        if tag == "delete":
            for old_i in range(i1, i2):
                removed.append(old_i + 1)
                entries.append(
                    DiffEntry(
                        status="removed",
                        old_index=old_i + 1,
                        new_index=None,
                        title=old_pages[old_i].title,
                    )
                )
            continue

        # replace：先按相似度贪心配对，配对成功的算「同一页内容变更」
        old_block = list(range(i1, i2))
        new_block = list(range(j1, j2))
        candidates: list[tuple[float, int, int]] = []
        for old_i in old_block:
            for new_j in new_block:
                score = _similarity(old_pages[old_i], new_pages[new_j])
                if score >= CHANGE_SIMILARITY_THRESHOLD:
                    candidates.append((score, old_i, new_j))
        candidates.sort(reverse=True)

        paired_old: dict[int, tuple[int, float]] = {}
        paired_new: dict[int, tuple[int, float]] = {}
        for score, old_i, new_j in candidates:
            if old_i in paired_old or new_j in paired_new:
                continue
            paired_old[old_i] = (new_j, score)
            paired_new[new_j] = (old_i, score)

        for old_i in old_block:
            if old_i in paired_old:
                new_j, score = paired_old[old_i]
                changed.append((old_i + 1, new_j + 1))
                entries.append(
                    DiffEntry(
                        status="changed",
                        old_index=old_i + 1,
                        new_index=new_j + 1,
                        title=new_pages[new_j].title,
                        similarity=score,
                    )
                )
            else:
                removed.append(old_i + 1)
                entries.append(
                    DiffEntry(
                        status="removed",
                        old_index=old_i + 1,
                        new_index=None,
                        title=old_pages[old_i].title,
                    )
                )

        for new_j in new_block:
            if new_j not in paired_new:
                added.append(new_j + 1)
                entries.append(
                    DiffEntry(
                        status="added",
                        old_index=None,
                        new_index=new_j + 1,
                        title=new_pages[new_j].title,
                    )
                )

    entries.sort(key=lambda e: (e.new_index or 10**6, e.old_index or 10**6))
    return AlignedDiff(
        unchanged=unchanged,
        changed=changed,
        added=sorted(added),
        removed=sorted(removed),
        old_count=len(old_pages),
        new_count=len(new_pages),
        entries=entries,
    )
