"""候选锚点位置枚举：供人工「新增填写项」时点选，自动生成可解析的锚点。

设计（与「从检测到的候选位置选取」的决策一致）：

- **复用 ``spec_draft`` 的 5 个规则扫描器**枚举母本里所有可锚定位置（页眉字段/表格/
  标签段落/彩色提示/章节空白），锚点由规则产出、保证渲染期可解析；
- **过滤掉已被现有槽位占用的位置**（按 anchor 签名去重），只留「尚未被占用」的候选；
- **AI 不参与定位**——定位是安全敏感操作（锚点错则渲染失败），全交给规则；AI 只在
  ``spec_ai_draft`` 里补语义。

用户在前端点选某个候选 → 后端用其 ``anchor`` 直接建槽位，不易出错。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel

from app.modules.research.doc_gen.spec_draft import draft_spec_from_bytes
from app.modules.research.doc_gen.template_spec import Anchor, Slot, TemplateSpec

logger = logging.getLogger(__name__)


class AnchorCandidate(BaseModel):
    """母本里一个尚未被占用、可锚定的候选位置。

    ``anchor`` 可被前端原样回传，后端用它直接建新槽位（无需用户手写锚点）。
    ``context`` 给出章节/表头/段落标签等线索，帮助用户判断该位置是不是想要的。
    """

    label: str
    kind: Literal["field", "paragraph", "table", "image"]
    anchor: Anchor
    context: str = ""


def anchor_signature(anchor: Anchor) -> str:
    """锚点的稳定签名：用于判断某位置是否已被现有槽位占用（忽略 None 字段）。"""
    return json.dumps(anchor.model_dump(exclude_none=True), sort_keys=True, ensure_ascii=False)


def _candidate_context(slot: Slot) -> str:
    """从槽位的锚点/列头拼一句人话上下文，帮用户认出这个位置。"""
    parts: list[str] = []
    anchor = slot.anchors[0] if slot.anchors else None
    if anchor is not None:
        if anchor.heading:
            parts.append(f"章节：{anchor.heading}")
        if anchor.table_header:
            parts.append(f"表格：{anchor.table_header}")
        if anchor.paragraph_label:
            parts.append(f"段落标签：{anchor.paragraph_label}")
        if anchor.header_contains:
            parts.append(f"页眉：{anchor.header_contains}")
    if slot.columns:
        parts.append("表头：" + " | ".join(c.label for c in slot.columns))
    return "；".join(parts)


def list_anchor_candidates(
    data: bytes,
    existing: TemplateSpec | None = None,
    *,
    hint_colors: Sequence[str] | None = None,
) -> list[AnchorCandidate]:
    """枚举母本中尚未被 ``existing`` 槽位占用的可锚定位置。

    ``data`` 是母本 docx 字节；``existing`` 是当前规格（None 表示空模板，全部位置皆候选）。
    返回按母本出现顺序排列的候选列表（规则扫描器的产出顺序）。
    """
    draft = draft_spec_from_bytes(data, hint_colors=tuple(hint_colors) if hint_colors is not None else None)
    occupied: set[str] = set()
    if existing is not None:
        for slot in existing.slots:
            for anchor in slot.anchors:
                occupied.add(anchor_signature(anchor))

    candidates: list[AnchorCandidate] = []
    seen: set[str] = set()
    for slot in draft.slots:
        if not slot.anchors:
            continue
        anchor = slot.anchors[0]
        signature = anchor_signature(anchor)
        if signature in occupied or signature in seen:
            continue
        seen.add(signature)
        candidates.append(
            AnchorCandidate(
                label=slot.label,
                kind=slot.kind,
                anchor=anchor,
                context=_candidate_context(slot),
            )
        )
    logger.info(
        "枚举候选锚点位置",
        extra={"draft_slots": len(draft.slots), "occupied": len(occupied), "candidates": len(candidates)},
    )
    return candidates


def generate_slot_key(spec: TemplateSpec, prefix: str = "manual") -> str:
    """生成一个在 ``spec`` 中唯一的槽位 key（``manual_1``、``manual_2`` …）。

    人工新增的槽位没有业务语义 key，用递增序号保证唯一即可；渲染只认锚点不认 key。
    """
    existing = set(spec.slot_keys)
    index = 1
    while f"{prefix}_{index}" in existing:
        index += 1
    return f"{prefix}_{index}"


def add_slot_to_spec(
    spec: TemplateSpec,
    *,
    anchor: Anchor,
    label: str,
    kind: Literal["field", "paragraph", "table", "image"] = "field",
    expects: Literal["text", "number", "date", "percent"] = "text",
    required: bool = False,
    query_hint: str = "",
    search_terms: Sequence[str] | None = None,
    key: str | None = None,
) -> Slot:
    """在 ``spec`` 末尾追加一个由候选锚点构造的新槽位（纯函数：就地修改并返回新槽位）。

    定位由规则产出的 ``anchor`` 决定（渲染安全铁律：AI/人工都不手写锚点），用户只
    补「叫什么、要什么类型」的语义。约束（任一不满足都抛 ``ValueError``，由服务层转
    400，绝不静默降级）：

    - ``label`` 去空白后不能为空；
    - 不接受 ``kind="table"``——表格槽位还需列定义与 ``table_rows`` 锚点，超出「点选
      候选位置新增」的范围；
    - ``anchor`` 不能与现有槽位已占用的位置重复（按 :func:`anchor_signature` 去重）；
    - ``key`` 缺省时自动生成唯一的 ``manual_N``；显式传入则不得与现有 key 冲突。

    构造出的 ``Slot`` 会经其自身校验器（至少一个锚点）兜底，随后追加到 ``spec.slots``。
    """
    clean_label = label.strip()
    if not clean_label:
        raise ValueError("填写项名称不能为空")
    if kind == "table":
        raise ValueError("表格类填写项需配置列定义，暂不支持通过「新增填写项」添加")

    signature = anchor_signature(anchor)
    for slot in spec.slots:
        if any(anchor_signature(existing) == signature for existing in slot.anchors):
            raise ValueError("该位置已被现有填写项占用，无需重复添加")

    slot_key = (key or "").strip() or generate_slot_key(spec)
    if slot_key in set(spec.slot_keys):
        raise ValueError(f"填写项标识 {slot_key} 已存在")

    new_slot = Slot(
        key=slot_key,
        label=clean_label,
        kind=kind,
        required=required,
        expects=expects,
        query_hint=query_hint.strip(),
        search_terms=list(search_terms) if search_terms else [],
        review_state="auto",
        anchors=[anchor],
    )
    spec.slots.append(new_slot)
    logger.info(
        "人工新增填写项",
        extra={"slot_key": new_slot.key, "kind": new_slot.kind, "anchor_type": anchor.type},
    )
    return new_slot


__all__ = [
    "AnchorCandidate",
    "add_slot_to_spec",
    "anchor_signature",
    "generate_slot_key",
    "list_anchor_candidates",
]
