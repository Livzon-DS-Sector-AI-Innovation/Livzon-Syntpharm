"""候选锚点位置枚举：供人工「新增填写项」时点选，自动生成可解析的锚点。

设计（与「从检测到的候选位置选取」的决策一致）：

- **复用 ``spec_draft`` 的规则扫描器**枚举母本里所有可锚定位置（页眉字段/表格/
  标签段落/彩色提示/章节空白），锚点由规则产出、保证渲染期可解析；
- **补扫规则草拟刻意丢弃的位置**：草拟阶段对「拿不准」的表格（双行表头、占位符
  数据行）会整表跳过，这里把它们重新枚举成候选，交人工确认——漏识别不再无解；
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

from docx.document import Document as DocxDocument
from pydantic import BaseModel, Field

from app.modules.research.doc_gen.grid import cell_text, distinct_row_cells
from app.modules.research.doc_gen.renderer import open_document
from app.modules.research.doc_gen.spec_draft import (
    _is_placeholder,
    _is_seq_header,
    _pick_header,
    draft_spec_from_bytes,
    pending_rows,
)
from app.modules.research.doc_gen.template_spec import (
    Anchor,
    ColumnSpec,
    Slot,
    TableSpec,
    TemplateSpec,
)

logger = logging.getLogger(__name__)


class AnchorCandidate(BaseModel):
    """母本里一个尚未被占用、可锚定的候选位置。

    ``anchor`` 可被前端原样回传，后端用它直接建新槽位（无需用户手写锚点）。
    ``context`` 给出章节/表头/段落标签等线索，帮助用户判断该位置是不是想要的。
    ``columns`` 仅表格候选携带：表头列名，人工确认后即可建 ``table_rows`` 槽位。
    """

    label: str
    kind: Literal["field", "paragraph", "table", "image"]
    anchor: Anchor
    context: str = ""
    columns: list[str] = Field(default_factory=list)
    header_rows: int = 1  # 表格候选：表头占几行（双行表头=2），人工新增表格槽位时透传


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

    草拟「宁缺毋滥」丢弃的表格（双行表头、表头空格、无空行但带占位符）随后由
    :func:`_missed_table_candidates` 补扫成整表/单元格候选——漏识别不再没有出口。
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
                columns=[c.label for c in slot.columns],
                header_rows=slot.table.header_rows if slot.table is not None else 1,
            )
        )
    candidates.extend(_missed_table_candidates(data, occupied, seen))
    logger.info(
        "枚举候选锚点位置",
        extra={"draft_slots": len(draft.slots), "occupied": len(occupied), "candidates": len(candidates)},
    )
    return candidates


def _table_anchor_headers(headers: Sequence[str], filled: frozenset[int]) -> list[str]:
    """锚点关键词只保留母本真实存在的表头文本（补位的「列N」原文没有，不能进锚点）。"""
    return [text for pos, text in enumerate(headers) if text and pos not in filled]


def _missed_table_candidates(data: bytes, occupied: set[str], seen: set[str]) -> list[AnchorCandidate]:
    """补扫草拟规则丢弃的表格位置：整表候选 + 显式占位符单元格候选。

    与草拟共用 :func:`spec_draft._pick_header` / :func:`spec_draft._is_placeholder`，
    保证候选锚点与自动槽位同源、渲染期同样可解析；是否成槽交人工在「新增填写项」
    里点选确认。整表候选已占用/已列出时不再拆单元格，避免同一张表重复回填。
    """
    try:
        doc: DocxDocument = open_document(data)
    except Exception:
        logger.debug("[doc_gen] 候选补扫：母本无法打开，跳过表格候选", exc_info=True)
        return []
    out: list[AnchorCandidate] = []
    for t_idx, table in enumerate(doc.tables, start=1):
        rows = list(table.rows)
        picked = _pick_header(table)
        if picked is not None:
            headers, header_rows, filled, _review, _grid_like = picked
        else:
            # 草拟连表头都选不出（首行多格为空、双行也不合格）：只要首行 ≥2 格
            # 且有非空文本，仍列为整表候选，列语义交人工核对
            first = [cell_text(c) for c in distinct_row_cells(rows[0])] if rows else []
            if len(first) < 2 or not any(first):
                continue
            headers = [text or f"列{pos + 1}" for pos, text in enumerate(first)]
            header_rows, filled = 1, frozenset(i for i, text in enumerate(first) if not text)
        anchor = Anchor(type="table_rows", table_header=_table_anchor_headers(headers, filled))
        if not anchor.table_header:
            continue
        table_sig = anchor_signature(anchor)
        if table_sig in occupied or table_sig in seen:
            continue
        # 只列「有待填迹象」的表：全填好的固定结构表（目录、说明表）做候选是噪音
        seq_key = next(
            (f"c{pos + 1}" for pos, text in enumerate(headers) if _is_seq_header(text)),
            None,
        )
        has_empty, has_placeholder, has_partial, _total = pending_rows(rows, headers, header_rows, seq_key)
        if not (has_empty or has_placeholder or has_partial):
            continue
        seen.add(table_sig)
        out.append(
            AnchorCandidate(
                label=" / ".join(headers),
                kind="table",
                anchor=anchor,
                context=f"表 {t_idx} · 表头：{' / '.join(headers)}",
                columns=list(headers),
                header_rows=header_rows,
            )
        )
        # 占位符单元格（"/"、"—" 等显式「这里要填」标记）：坐标锚点 + guard 行标签
        for ri in range(header_rows, len(rows)):
            texts = [cell_text(c) for c in distinct_row_cells(rows[ri])]
            row_label = next((text for text in texts if text and not _is_placeholder(text)), "")
            if not row_label:
                continue  # 整行无真实文本，坐标锚点没有可校验的 guard，放弃
            for pos, text in enumerate(texts):
                if not text or not _is_placeholder(text):
                    continue
                col_header = headers[pos] if pos < len(headers) else f"列{pos + 1}"
                cell_anchor = Anchor(
                    type="table_cell",
                    table_header=list(anchor.table_header),
                    row_index=ri,
                    col_index=pos,
                    guard=row_label,
                )
                sig = anchor_signature(cell_anchor)
                if sig in occupied or sig in seen:
                    continue
                seen.add(sig)
                out.append(
                    AnchorCandidate(
                        label=f"{col_header}（{row_label}）",
                        kind="field",
                        anchor=cell_anchor,
                        context=f"表 {t_idx} · 行「{row_label}」· 列「{col_header}」",
                    )
                )
    return out


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
    columns: Sequence[str] | None = None,
    header_rows: int = 1,
) -> Slot:
    """在 ``spec`` 末尾追加一个由候选锚点构造的新槽位（纯函数：就地修改并返回新槽位）。

    定位由规则产出的 ``anchor`` 决定（渲染安全铁律：AI/人工都不手写锚点），用户只
    补「叫什么、要什么类型」的语义。约束（任一不满足都抛 ``ValueError``，由服务层转
    400，绝不静默降级）：

    - ``label`` 去空白后不能为空；
    - ``kind="table"``：必须配 ``table_rows`` 锚点（来自整表候选）且给出 ``columns``
      列名——列定义按顺序生成 ``c1..cN``，与草拟槽位同构；
    - ``table_cell`` 坐标锚点（``row_index``/``col_index``）必须带 ``guard``：模板
      增删行后坐标会漂移，无校验文本宁可拒绝也不允许填错格子；
    - ``anchor`` 不能与现有槽位已占用的位置重复（按 :func:`anchor_signature` 去重）；
    - ``key`` 缺省时自动生成唯一的 ``manual_N``；显式传入则不得与现有 key 冲突。

    构造出的 ``Slot`` 会经其自身校验器（至少一个锚点）兜底，随后追加到 ``spec.slots``。
    """
    clean_label = label.strip()
    if not clean_label:
        raise ValueError("填写项名称不能为空")
    if kind == "table":
        if anchor.type != "table_rows" or not anchor.table_header:
            raise ValueError("表格类填写项需要 table_rows 锚点，请从候选列表中选择整表位置")
        clean_columns = [text.strip() for text in (columns or []) if text.strip()]
        if not clean_columns:
            raise ValueError("表格类填写项需要列定义（columns），请从候选列表中选择带表头的整表位置")
    elif anchor.type == "table_cell" and anchor.row_index is not None and not (anchor.guard or "").strip():
        raise ValueError("单元格坐标锚点必须携带 guard 校验文本，防止模板变更后填错格子")

    signature = anchor_signature(anchor)
    for slot in spec.slots:
        if any(anchor_signature(existing) == signature for existing in slot.anchors):
            raise ValueError("该位置已被现有填写项占用，无需重复添加")

    slot_key = (key or "").strip() or generate_slot_key(spec)
    if slot_key in set(spec.slot_keys):
        raise ValueError(f"填写项标识 {slot_key} 已存在")

    table: TableSpec | None = None
    column_specs: list[ColumnSpec] = []
    if kind == "table":
        column_specs = [
            ColumnSpec(key=f"c{pos + 1}", label=text, max_chars=200) for pos, text in enumerate(clean_columns)
        ]
        table = TableSpec(header_rows=max(1, header_rows), row_limit=60)

    new_slot = Slot(
        key=slot_key,
        label=clean_label,
        kind=kind,
        required=required,
        expects=expects,
        query_hint=query_hint.strip(),
        search_terms=list(search_terms) if search_terms else [],
        review_state="auto",
        table=table,
        columns=column_specs,
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
