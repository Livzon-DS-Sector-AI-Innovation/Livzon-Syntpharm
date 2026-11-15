"""参考资料（引用源）分组：把写入记录按来源名聚合成「来源 → 引用位置」。

引用源不再写进 Word 文档：它属于审阅信息，不是报告内容，写进正文既破坏母本版面，
也没人会在成稿里读它。现在由详情页右栏「参考资料」展示，并支持点条目定位回正文。

纯函数：只读 slot 行、不碰数据库、不调模型。生成期（tools）与展示期（review）
共用同一份分组口径，避免「页面上列的引用位置和当初写的不一致」。
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from app.modules.research.report_gen.render import (
    KIND_APPEND_PARAGRAPH,
    KIND_PARAGRAPH,
    KIND_REFERENCES,
    KIND_TABLE_CELL,
)

# 单个来源最多列几处位置，超出用「等 N 处」收尾：面板要能扫读，不能变成裹脚布
MAX_LOCATIONS = 8


@dataclass(slots=True)
class ReferenceLocation:
    """一处引用位置；``key`` 为空表示该位置在文档里没有可点击的锚点。"""

    key: str | None
    label: str

    def brief(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label}


@dataclass(slots=True)
class ReferenceGroup:
    """一个来源及其在正文里的全部落点。"""

    index: int
    name: str
    total: int = 0
    locations: list[ReferenceLocation] = field(default_factory=list)

    def entry(self) -> str:
        """文本条目，沿用 ``[1] 来源（用于：…）`` 的旧格式（日志与导出都在用）。"""
        shown = self.locations[:MAX_LOCATIONS]
        detail = "、".join(item.label for item in shown)
        if self.total > len(shown):
            detail += f" 等 {self.total} 处"
        return f"[{self.index}] {self.name}（用于：{detail}）"


def _anchor_of(row: Any) -> dict[str, Any]:
    anchor = getattr(row, "anchor", None)
    return anchor if isinstance(anchor, dict) else {}


def _source_names(row: Any) -> list[str]:
    """来源名：优先 anchor 里的列表（一格多来源），兜底 row.source_name。"""
    names = _anchor_of(row).get("source_names")
    if isinstance(names, list):
        return [str(item).strip() for item in names if str(item or "").strip()]
    raw = str(getattr(row, "source_name", "") or "").strip()
    return [raw] if raw else []


def _location_key(row: Any, anchor: dict[str, Any], kind: str) -> str | None:
    """点击定位用的位置 key；``None`` = 这一条在正文里没有可点的位置。"""
    if kind in (KIND_PARAGRAPH, KIND_TABLE_CELL):
        return str(getattr(row, "slot_key", "") or "").strip() or None
    if kind == KIND_APPEND_PARAGRAPH:
        # 追加段落依附在「插在谁后面」的位置上，点它就跳到那片正文
        return str(anchor.get("after") or "").strip() or None
    return None


def _location_of(row: Any) -> ReferenceLocation | None:
    anchor = _anchor_of(row)
    kind = str(anchor.get("kind") or KIND_PARAGRAPH)
    if kind == KIND_REFERENCES:
        return None
    label = str(anchor.get("location") or "").strip()
    if not label:
        return None
    return ReferenceLocation(key=_location_key(row, anchor, kind), label=label)


def build_reference_groups(rows: Iterable[Any], *, limit: int = MAX_LOCATIONS) -> list[ReferenceGroup]:
    """按来源名聚合写入记录，按首次出现排序；同一来源在正文多处使用合并成一条。"""
    grouped: dict[str, list[ReferenceLocation]] = {}
    for row in rows:
        if not str(getattr(row, "value", "") or "").strip():
            continue
        location = _location_of(row)
        if location is None:
            continue
        for name in _source_names(row):
            bucket = grouped.setdefault(name, [])
            if all(item.label != location.label for item in bucket):
                bucket.append(location)

    groups: list[ReferenceGroup] = []
    for index, (name, locations) in enumerate(grouped.items(), start=1):
        groups.append(
            ReferenceGroup(index=index, name=name, total=len(locations), locations=locations[:limit])
        )
    return groups


def format_reference_entries(groups: list[ReferenceGroup]) -> list[str]:
    return [group.entry() for group in groups]


__all__ = [
    "MAX_LOCATIONS",
    "ReferenceGroup",
    "ReferenceLocation",
    "build_reference_groups",
    "format_reference_entries",
]
