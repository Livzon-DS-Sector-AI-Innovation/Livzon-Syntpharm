"""母本结构解析：把 Word 母本解析成「可填槽位」定义并缓存。

为什么由模型来判定槽位：业务方不愿重做模板、也不接受加占位符，而母本里
并没有机器可读的填空标记（``template_structure`` 一直是空的）。因此首次生成时
把母本的「段落 / 表格单元格」扁平化成候选位置，交给模型判断哪些需要填写，
判定结果按母本存储键缓存 —— 同一份母本只分析一次，换版自动失效。
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from docx import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.core.llm import llm_client
from app.modules.research.doc_template import store
from app.modules.research.report_gen.config import ReportGenConfig

logger = logging.getLogger(__name__)

# 版本 2 起槽位带人工编辑痕迹（is_enabled / origin / edited_fields）；
# 读老结构时按「全部启用、无人工修改」补齐，不因版本差异触发一次花钱的重解析。
STRUCTURE_VERSION = 2
# 允许人工改、并且值得记进 edited_fields 的字段
_SLOT_EDITABLE_FIELDS = ("anchor", "hint", "is_enabled", "label", "owner_hint", "slot_key", "value_type")
# 候选位上限：母本动辄上百段落，全量送模型既慢又贵；优先送「空位」
MAX_PARAGRAPH_CANDIDATES = 320
MAX_CELL_CANDIDATES = 480
# 一次送给模型的候选清单字符上限，超出后只送靠前的空位
MAX_PROMPT_CHARS = 24000
_MAX_PARAGRAPH_TEXT = 80
_MAX_CELL_TEXT = 200
_VALUE_TYPES = ("text", "long_text", "number", "date", "list")

_SYSTEM_PROMPT = """你是医药研发报告模板的结构分析专家。
用户会给出 Word 母本里所有「可填写位置」的清单（段落与表格单元格），
你的任务是判断：这份模板里哪些位置是**需要填写内容**的槽位。

判定原则：
1. 只挑真正需要写入业务信息的位置：品种名称、批号、日期、结论、数据、责任部门等。
2. 表格里「字段名右侧/下方的空格」通常就是要填的槽位；表头、章节标题、说明文字、
   已写死的编号不选。
3. 相邻空位属于同一行的，按「字段名」理解：填的是字段值。
4. 同一信息在正文与表格重复出现时，各自都算槽位（填同一个值）。
5. 宁可少选，也不要选到正文叙述段落。

只返回 JSON，不要任何解释，格式：
{"slots":[{"candidate_id":"t0r1c1p0","slot_key":"drug_name","label":"品种名称",
"value_type":"text","owner_hint":"注册部","hint":"填写品种通用名"}]}
- candidate_id 必须来自清单里的 id；
- slot_key 用英文 snake_case，在同一模板内唯一且语义稳定；
- value_type 取 text/long_text/number/date/list；
- owner_hint 为资料缺失时应找的部门（如 注册部/质量部/生产部/市场部）。"""


@dataclass(slots=True)
class ParagraphRef:
    index: int
    text: str
    style: str


@dataclass(slots=True)
class CellRef:
    table_index: int
    row: int
    col: int
    para_index: int
    text: str
    style: str
    label: str


def fingerprint(text: str) -> str:
    """文本指纹：忽略空白差异，用于回写时校验锚点是否漂移。"""
    normalized = re.sub(r"\s+", "", text or "")
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def open_document(data: bytes) -> Any:
    """打开 docx；损坏或不是 Word 文件时给出可读错误。"""
    try:
        return Document(BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - python-docx 抛的异常类型不稳定
        raise BadRequestException("Word 母本无法解析，请确认上传的是有效的 docx 文件") from exc


def paragraph_refs(document: Any) -> list[ParagraphRef]:
    refs: list[ParagraphRef] = []
    for index, paragraph in enumerate(document.paragraphs):
        style = ""
        try:
            style = paragraph.style.name or ""
        except AttributeError:  # 样式表缺失的极端文档
            style = ""
        refs.append(ParagraphRef(index=index, text=(paragraph.text or "").strip(), style=style))
    return refs


def cell_refs(document: Any) -> list[CellRef]:
    """按 (表, 行, 列, 段) 展开单元格；合并单元格只取第一次出现。

    去重标识用底层节点的树内路径而不是 ``id()``：python-docx 每次访问
    ``row.cells`` 都会新建包装对象，底层 lxml 元素代理也会被回收后重建，
    ``id()`` 会被后续单元格复用，导致正常单元格被误判成「合并单元格已出现」
    而整格漏收（大表格会静默缺槽位）。树内路径同一节点恒定，跨行跨列唯一。
    """
    refs: list[CellRef] = []
    for table_index, table in enumerate(document.tables):
        seen: set[str] = set()
        for row_index, row in enumerate(table.rows):
            for col_index, cell in enumerate(row.cells):
                tc = cell._tc  # noqa: SLF001 - 识别合并单元格需要底层 w:tc 节点
                marker = tc.getroottree().getpath(tc)  # 同一节点路径恒定，不受对象回收影响
                if marker in seen:
                    continue
                seen.add(marker)
                for para_index, paragraph in enumerate(cell.paragraphs):
                    try:
                        style = paragraph.style.name or ""
                    except AttributeError:
                        style = ""
                    refs.append(
                        CellRef(
                            table_index=table_index,
                            row=row_index,
                            col=col_index,
                            para_index=para_index,
                            text=(paragraph.text or "").strip(),
                            style=style,
                            label=f"表格{table_index + 1} 第{row_index + 1}行第{col_index + 1}列",
                        )
                    )
    return refs


def _candidate_id(kind: str, ref: ParagraphRef | CellRef) -> str:
    if kind == "paragraph":
        assert isinstance(ref, ParagraphRef)
        return f"p{ref.index}"
    assert isinstance(ref, CellRef)
    return f"t{ref.table_index}r{ref.row}c{ref.col}p{ref.para_index}"


def _context_of(texts: list[str], position: int, limit: int = 40) -> str:
    """取当前位置之前最近的非空文本，帮助模型理解这是哪个字段。"""
    for offset in range(position - 1, max(position - 6, -1), -1):
        candidate = texts[offset]
        if candidate:
            return candidate[:limit]
    return ""


def build_candidates(paragraphs: list[ParagraphRef], cells: list[CellRef]) -> list[dict[str, Any]]:
    """生成候选清单：空位优先保留，避免长母本的叙述段落挤掉真正的填空位。"""
    candidates: list[dict[str, Any]] = []

    texts = [ref.text for ref in paragraphs]
    kept_paragraphs = 0
    for para_ref in paragraphs:
        if para_ref.text and len(para_ref.text) > _MAX_PARAGRAPH_TEXT:
            continue
        if kept_paragraphs >= MAX_PARAGRAPH_CANDIDATES:
            break
        kept_paragraphs += 1
        candidates.append(
            {
                "candidate_id": _candidate_id("paragraph", para_ref),
                "kind": "paragraph",
                "label": f"正文第{para_ref.index + 1}段",
                "text": para_ref.text,
                "style": para_ref.style,
                "context": _context_of(texts, para_ref.index),
                "anchor": {
                    "kind": "paragraph",
                    "index": para_ref.index,
                    "text": para_ref.text,
                    "style": para_ref.style,
                    "fingerprint": fingerprint(para_ref.text),
                },
            }
        )

    kept_cells = 0
    cell_texts = [ref.text for ref in cells]
    # 每个表格内顺序即阅读顺序，上文取同表内靠前的单元格文本
    for position, cell_ref in enumerate(cells):
        if cell_ref.text and len(cell_ref.text) > _MAX_CELL_TEXT:
            continue
        if kept_cells >= MAX_CELL_CANDIDATES:
            break
        kept_cells += 1
        candidates.append(
            {
                "candidate_id": _candidate_id("table_cell", cell_ref),
                "kind": "table_cell",
                "label": cell_ref.label,
                "text": cell_ref.text,
                "style": cell_ref.style,
                "context": _context_of(cell_texts, position),
                "anchor": {
                    "kind": "table_cell",
                    "table_index": cell_ref.table_index,
                    "row": cell_ref.row,
                    "col": cell_ref.col,
                    "para_index": cell_ref.para_index,
                    "text": cell_ref.text,
                    "style": cell_ref.style,
                    "fingerprint": fingerprint(cell_ref.text),
                },
            }
        )
    return candidates


def _render_candidate_lines(candidates: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    used = 0
    for item in sorted(candidates, key=lambda c: (bool(c["text"]), len(c["text"]))):
        line = (
            f'{item["candidate_id"]} | {item["label"]} | 样式:{item["style"] or "-"} | '
            f'当前内容:{"（空）" if not item["text"] else item["text"]} | '
            f'上一行:{item["context"] or "（无）"}'
        )
        used += len(line) + 1
        if used > MAX_PROMPT_CHARS:
            break
        lines.append(line)
    return "\n".join(lines)


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value or "").strip("_").lower()
    slug = re.sub(r"_{2,}", "_", slug)
    return slug[:60] or fallback


def _align_model_slots(raw: dict[str, Any], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把模型输出对齐到真实候选位；命中不到的条目直接丢弃（模型偶有臆造 id）。"""
    by_id = {item["candidate_id"]: item for item in candidates}
    slots: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    raw_slots = raw.get("slots")
    if not isinstance(raw_slots, list):
        return slots

    for index, item in enumerate(raw_slots):
        if not isinstance(item, dict):
            continue
        candidate = by_id.get(str(item.get("candidate_id") or "").strip())
        if candidate is None:
            continue
        slot_key = _slug(str(item.get("slot_key") or ""), f"slot_{index + 1}")
        if slot_key in used_keys:
            slot_key = f"{slot_key}_{index + 1}"
        used_keys.add(slot_key)

        value_type = str(item.get("value_type") or "text").strip().lower()
        slots.append(
            {
                "slot_key": slot_key,
                "label": str(item.get("label") or candidate["label"])[:200],
                "value_type": value_type if value_type in _VALUE_TYPES else "text",
                "owner_hint": str(item.get("owner_hint") or "")[:100] or None,
                "hint": str(item.get("hint") or "")[:300] or None,
                "location": candidate["label"],
                "anchor": candidate["anchor"],
            }
        )
    return [normalize_slot(slot) for slot in slots]


def _optional_text(value: Any, limit: int) -> str | None:
    text = str(value or "").strip()
    return text[:limit] or None


def anchor_key(anchor: Any) -> tuple[Any, ...]:
    """锚点的结构性标识，用于合并时判断「是不是同一个位置」。

    ``fingerprint`` 不参与相等判断：它只用来提示母本文本是否被改过，把它算进
    比对键会让一次无关的措辞修订把所有槽位都当成新位置。
    表格锚点带上 ``para_index``：同一个单元格里可能有多段，段落不同就是两个槽位。
    """
    if not isinstance(anchor, dict):
        return ("unknown",)
    kind = str(anchor.get("kind") or "")
    if kind == "paragraph":
        return ("paragraph", int(anchor.get("index") or 0))
    if kind == "table_cell":
        return (
            "table_cell",
            int(anchor.get("table_index") or 0),
            int(anchor.get("row") or 0),
            int(anchor.get("col") or 0),
            int(anchor.get("para_index") or 0),
        )
    return (kind or "unknown",)


def normalize_slot(slot: Any) -> dict[str, Any]:
    """把单个槽位补齐成当前形态；老结构缺的新字段按默认值补上。"""
    data = slot if isinstance(slot, dict) else {}
    value_type = str(data.get("value_type") or "text").strip().lower()
    origin = "manual" if str(data.get("origin") or "") == "manual" else "ai"
    raw_edited = data.get("edited_fields")
    edited = (
        [str(field) for field in raw_edited if str(field) in _SLOT_EDITABLE_FIELDS]
        if isinstance(raw_edited, list)
        else []
    )
    return {
        "slot_key": str(data.get("slot_key") or ""),
        "label": str(data.get("label") or "")[:200],
        "value_type": value_type if value_type in _VALUE_TYPES else "text",
        "owner_hint": _optional_text(data.get("owner_hint"), 100),
        "hint": _optional_text(data.get("hint"), 300),
        "location": str(data.get("location") or ""),
        "anchor": dict(data.get("anchor") or {}),
        # 只有显式 false 才算停用：老结构里没有这个键，必须视为启用
        "is_enabled": data.get("is_enabled") is not False,
        "origin": origin,
        "edited_fields": edited,
    }


def _normalized_slots(structure: Any) -> list[dict[str, Any]]:
    data = structure if isinstance(structure, dict) else {}
    raw_slots = data.get("slots")
    if not isinstance(raw_slots, list):
        return []
    return [normalize_slot(slot) for slot in raw_slots if isinstance(slot, dict)]


def normalize_structure(structure: Any) -> dict[str, Any]:
    """统一结构 JSON 形态：只保留已知字段，槽位补齐人工痕迹字段。"""
    data = structure if isinstance(structure, dict) else {}
    return {
        "version": STRUCTURE_VERSION,
        "source_key": data.get("source_key"),
        "analyzed_at": data.get("analyzed_at"),
        # 人工保存结构的痕迹：edited_at 同时充当并发编辑的乐观令牌
        "edited_at": data.get("edited_at"),
        "edited_by": data.get("edited_by"),
        "slots": _normalized_slots(data),
    }


def enabled_slots(structure: Any) -> list[dict[str, Any]]:
    """生成链路使用的槽位：停用槽位不建行、不下发、不回写。"""
    return [slot for slot in _normalized_slots(structure) if slot["is_enabled"]]


def structure_is_stale(structure: Any, source_key: str | None) -> bool:
    """结构是否来自另一份母本；过期结构不能作为编辑基础保存。"""
    if not isinstance(structure, dict):
        return True
    current = structure.get("source_key")
    if not current:
        return True
    return str(current) != str(source_key or "")


def _merge_one(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """同一锚点：人工改过的字段取人工值，其余字段跟 AI 走。"""
    merged = dict(new)
    edited = list(old["edited_fields"])
    for field in edited:
        if field == "anchor":
            # 锚点和展示位置是一体的，换绑后必须一起保留
            merged["anchor"] = old["anchor"]
            merged["location"] = old["location"]
        elif field == "slot_key":
            merged["slot_key"] = old["slot_key"]
        else:
            merged[field] = old[field]
    merged["origin"] = "manual" if old["origin"] == "manual" or edited else "ai"
    merged["edited_fields"] = edited
    return merged


def _document_order(slot: dict[str, Any]) -> tuple[int, int, int, int, int]:
    """按母本阅读顺序排序：正文段落在前，表格按表/行/列/段。"""
    anchor = slot.get("anchor") or {}
    if anchor.get("kind") == "table_cell":
        return (
            1,
            int(anchor.get("table_index") or 0),
            int(anchor.get("row") or 0),
            int(anchor.get("col") or 0),
            int(anchor.get("para_index") or 0),
        )
    return (0, int(anchor.get("index") or 0), 0, 0, 0)


def _ensure_unique_keys(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    used: set[str] = set()
    result: list[dict[str, Any]] = []
    for index, slot in enumerate(slots):
        key = slot["slot_key"] or f"slot_{index + 1}"
        if key in used:
            suffix = 2
            while f"{key}_{suffix}" in used:
                suffix += 1
            key = f"{key}_{suffix}"
        used.add(key)
        result.append({**slot, "slot_key": key})
    return result


def merge_slots(
    existing: list[dict[str, Any]] | None, ai_slots: list[dict[str, Any]] | None
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """按锚点合并一次重解析结果，返回 (合并后槽位, 统计)。

    - 同一锚点：人工改过的字段保留，其余字段用 AI 的新判断；
    - AI 新增锚点：追加；
    - 旧槽位在本次识别里消失：人工动过（origin=manual 或 edited_fields 非空）
      就保留，否则移除 —— 人工劳动不丢，AI 的误选能被清掉。
    """
    old_by_anchor: dict[tuple[Any, ...], dict[str, Any]] = {}
    for slot in _normalized_slots({"slots": existing or []}):
        old_by_anchor.setdefault(anchor_key(slot["anchor"]), slot)

    ai_by_anchor: dict[tuple[Any, ...], dict[str, Any]] = {}
    for slot in _normalized_slots({"slots": ai_slots or []}):
        ai_by_anchor.setdefault(anchor_key(slot["anchor"]), slot)

    merged: list[dict[str, Any]] = []
    kept = 0
    removed = 0
    for key, old in old_by_anchor.items():
        new = ai_by_anchor.get(key)
        if new is None:
            if old["origin"] == "manual" or old["edited_fields"]:
                merged.append(old)
                kept += 1
            else:
                removed += 1
            continue
        merged.append(_merge_one(old, new))
        kept += 1

    added = 0
    for key, slot in ai_by_anchor.items():
        if key in old_by_anchor:
            continue
        merged.append(slot)
        added += 1

    merged = sorted(_ensure_unique_keys(merged), key=_document_order)
    return merged, {"added": added, "kept": kept, "removed": removed}


def edited_fields_between(old: Any, new: Any) -> list[str]:
    """保存时比对库中旧值，算出这次真正被人改过的字段。"""
    before = normalize_slot(old)
    after = normalize_slot(new)
    changed: list[str] = []
    for field in _SLOT_EDITABLE_FIELDS:
        if field == "anchor":
            if anchor_key(before["anchor"]) != anchor_key(after["anchor"]):
                changed.append(field)
            continue
        if (before.get(field) or None) != (after.get(field) or None):
            changed.append(field)
    return sorted(changed)


def validate_slots(slots: list[Any], candidate_keys: set[tuple[Any, ...]]) -> None:
    """保存前校验：标识唯一、名称非空、锚点必须落在当前母本里。

    ``candidate_keys`` 为空集合表示跳过锚点校验（母本不可读的场景由上层先行拦截）。
    """
    if not slots:
        raise BadRequestException("槽位结构不能为空，至少保留一个槽位")
    seen: dict[str, int] = {}
    for index, raw in enumerate(slots):
        slot = normalize_slot(raw)
        key = slot["slot_key"].strip()
        if not key:
            raise BadRequestException(f"第 {index + 1} 个槽位缺少标识（slot_key）")
        if key in seen:
            raise BadRequestException(f"槽位标识重复：{key}（第 {seen[key]} 个与第 {index + 1} 个）")
        seen[key] = index + 1
        if not slot["label"].strip():
            raise BadRequestException(f"槽位 {key} 缺少名称")
        if candidate_keys and anchor_key(slot["anchor"]) not in candidate_keys:
            raise BadRequestException(f"槽位 {key} 绑定的位置不在当前母本中，请重新识别或换个位置")


async def _analyze_with_model(
    template: Any, candidates: list[dict[str, Any]], config: ReportGenConfig
) -> list[dict[str, Any]]:
    lines = _render_candidate_lines(candidates)
    user_prompt = (
        f"交付物类型：{template.deliverable_type}\n"
        f"所属阶段：{template.stage}\n"
        f"模板名称：{template.name}\n\n"
        f"可填写位置清单（共 {len(candidates)} 条）：\n{lines}"
    )
    raw = await llm_client.chat_json(
        [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        **config.structure_model.call_kwargs(),
    )
    slots = _align_model_slots(raw, candidates)
    if not slots:
        raise BadRequestException("未能从母本中识别出可填写的槽位，请确认模板内容是否完整")
    return slots


async def ensure_structure(
    session: AsyncSession,
    template: Any,
    config: ReportGenConfig,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """取槽位结构：命中缓存直接返回，否则解析母本并写回 ``template_structure``。"""
    cached = template.template_structure
    if (
        not force
        and isinstance(cached, dict)
        and cached.get("source_key")
        and cached.get("source_key") == template.file_object_key
        and isinstance(cached.get("slots"), list)
        and cached["slots"]
    ):
        # 老结构（version 1）在这里补齐人工痕迹字段，但不写库、不触发重解析
        return normalize_structure(cached)

    # 母本换版后旧结构的锚点已失效，只能整份重解析：这里显式记下被丢弃的人工修改量，
    # 避免“改了半天的槽位在某次生成后悄悄消失”无从追查。
    previous_source = cached.get("source_key") if isinstance(cached, dict) else None
    if previous_source and previous_source != template.file_object_key:
        discarded = [
            slot
            for slot in (normalize_structure(cached).get("slots") or [])
            if slot.get("origin") == "manual" or slot.get("edited_fields")
        ]
        if discarded:
            logger.warning(
                "report-gen structure invalidated by new template file",
                extra={"template_id": str(template.id), "dropped_manual_slots": len(discarded)},
            )

    if not template.file_object_key:
        raise BadRequestException("该交付物模板还没有上传 Word 母本，无法生成报告")
    data = store.load_bytes(template.file_object_key)
    if not data:
        raise BadRequestException("母本文件已丢失，请重新上传模板")

    document = open_document(data)
    candidates = build_candidates(paragraph_refs(document), cell_refs(document))
    if not candidates:
        raise BadRequestException("母本中没有可填写的位置，无法生成报告")

    slots = await _analyze_with_model(template, candidates, config)
    structure = {
        "version": STRUCTURE_VERSION,
        "source_key": template.file_object_key,
        "analyzed_at": datetime.now(UTC).isoformat(),
        "slots": slots,
    }
    template.template_structure = structure
    await session.flush()
    logger.info(
        "report-gen template structure resolved",
        extra={"template_id": str(template.id), "slot_count": len(slots)},
    )
    return structure


def dumps_structure(structure: dict[str, Any]) -> str:
    """给步骤/日志用的紧凑摘要，不含母本原文。"""
    return json.dumps(
        {"source_key": structure.get("source_key"), "slot_count": len(structure.get("slots") or [])},
        ensure_ascii=False,
    )


__all__ = [
    "CellRef",
    "ParagraphRef",
    "STRUCTURE_VERSION",
    "anchor_key",
    "build_candidates",
    "cell_refs",
    "dumps_structure",
    "edited_fields_between",
    "enabled_slots",
    "ensure_structure",
    "fingerprint",
    "merge_slots",
    "normalize_slot",
    "normalize_structure",
    "open_document",
    "paragraph_refs",
    "structure_is_stale",
    "validate_slots",
]
