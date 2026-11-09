"""按锚点把槽位内容回写进 Word 母本，并生成槽位对照表。

保排版的关键不是「重新生成一份文档」，而是在母本原件的段落对象上改文字：
- 段落内多个 run（Word 常有）→ 值写入首个 run，其余 run 清空，字体/字号/加粗都保留；
- 多行值 → 复制原段落样式逐行插入，不破坏段落间距与编号；
- 表格单元格内多段落 → 同样按行追加；
- 锚点漂移（母本换版、指纹不匹配）→ 邻域 + 指纹兜底，仍失败写占位并标
  ``anchor_unresolved``，绝不因为个别槽位中断整篇成稿。
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast

from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph

from app.modules.research.report_gen.structure import fingerprint, open_document

logger = logging.getLogger(__name__)

GAP_PREFIX = "待补充："
DEFAULT_OWNER = "相关部门"
# 母本里的填空位：连续下划线（半角/全角）。命中时只替换这一段，
# 保住「品种名称：」这类标签与首尾格式；命中不了才退回整段替换。
_BLANK_RE = re.compile(r"[_＿]{2,}")

STATE_LABELS = {
    "filled": "已填",
    "conflict": "多源冲突",
    "pending": "待确认",
    "gap": "缺口",
    "anchor_unresolved": "锚点未定位",
}


@dataclass(slots=True)
class SlotFill:
    """回写所需的槽位快照（与 ORM 行解耦，便于单测）。"""

    slot_key: str
    label: str
    anchor: dict[str, Any] | None
    location: str | None = None
    value: str | None = None
    state: str = "pending"
    source_name: str | None = None
    evidence: str | None = None
    owner_hint: str | None = None


@dataclass(slots=True)
class RenderOutput:
    document: bytes
    comparison_markdown: str
    unresolved: list[str] = field(default_factory=list)
    filled: int = 0
    gaps: int = 0


def _gap_text(slot: SlotFill, inline: bool = False) -> str:
    owner = (slot.owner_hint or DEFAULT_OWNER).strip() or DEFAULT_OWNER
    # 接在「品种名称：」后面时不重复冒号
    return f"待补充（{owner}）" if inline else f"{GAP_PREFIX}{owner}"


def _new_paragraph_like(source: Paragraph) -> Paragraph:
    """在 source 之后插入同格式空段落。"""
    new_p = OxmlElement("w:p")
    p_pr = source._p.pPr  # noqa: SLF001 - 需要复制段落属性（缩进/编号/间距）
    if p_pr is not None:
        new_p.append(deepcopy(p_pr))
    source._p.addnext(new_p)  # noqa: SLF001
    return Paragraph(new_p, source._parent)


def _set_paragraph_text(paragraph: Paragraph, value: str) -> None:
    """写入文本并保留段落与首个 run 的字体属性；多行按段落拆分。"""
    lines = value.split("\n")
    first_line = lines[0]
    runs = paragraph.runs
    if runs:
        template_run = runs[0]
        template_run.text = first_line
        for run in runs[1:]:
            run.text = ""
    else:
        template_run = paragraph.add_run(first_line)

    cursor = paragraph
    for line in lines[1:]:
        new_paragraph = _new_paragraph_like(cursor)
        new_run = new_paragraph.add_run(line)
        source_rpr = template_run._r.rPr  # noqa: SLF001
        if source_rpr is not None:
            new_run._r.insert(0, deepcopy(source_rpr))  # noqa: SLF001
        cursor = new_paragraph


def _fill_blank(paragraph: Paragraph, value: str) -> bool:
    """把值写进段落里的填空位，标签与首尾文字/字体原样保留；无填空位返回 False。

    实测母本行是「品种名称：____」，整段替换会把标签一起抹掉，成稿只剩一串裸值。
    """
    for run in paragraph.runs:
        text = run.text or ""
        match = _BLANK_RE.search(text)
        if match is None:
            continue
        first_line, *rest = value.split("\n")
        run.text = f"{text[: match.start()]}{first_line}{text[match.end() :]}"
        cursor = paragraph
        for line in rest:
            new_paragraph = _new_paragraph_like(cursor)
            new_run = new_paragraph.add_run(line)
            source_rpr = run._r.rPr  # noqa: SLF001
            if source_rpr is not None:
                new_run._r.insert(0, deepcopy(source_rpr))  # noqa: SLF001
            cursor = new_paragraph
        return True
    return False


def _paragraph_at(document: Any, anchor: dict[str, Any]) -> Paragraph | None:
    index = anchor.get("index")
    if not isinstance(index, int):
        return None
    paragraphs = document.paragraphs
    if 0 <= index < len(paragraphs):
        return cast(Paragraph, paragraphs[index])
    return None


def _cell_paragraph_at(document: Any, anchor: dict[str, Any]) -> Paragraph | None:
    try:
        table = document.tables[int(anchor["table_index"])]
        cell = table.rows[int(anchor["row"])].cells[int(anchor["col"])]
        paragraphs = cell.paragraphs
        para_index = int(anchor.get("para_index") or 0)
        if 0 <= para_index < len(paragraphs):
            return cast(Paragraph, paragraphs[para_index])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return None


def _locate(document: Any, anchor: dict[str, Any] | None) -> Paragraph | None:
    """按锚点定位目标段落；索引失效时用指纹在邻域与全文兜底。"""
    if not isinstance(anchor, dict):
        return None
    kind = anchor.get("kind")
    if kind == "table_cell":
        return _cell_paragraph_at(document, anchor)
    if kind != "paragraph":
        return None

    paragraph = _paragraph_at(document, anchor)
    expected_text = str(anchor.get("text") or "").strip()
    expected_fp = anchor.get("fingerprint")
    if paragraph is not None:
        current = (paragraph.text or "").strip()
        # 原文非空时校验指纹；空位（槽位本身为空）不校验，直接写入
        if not expected_text or fingerprint(current) == expected_fp:
            return paragraph

    paragraphs = document.paragraphs
    index = anchor.get("index")
    if isinstance(index, int):
        for offset in range(1, 4):
            for candidate_index in (index - offset, index + offset):
                if 0 <= candidate_index < len(paragraphs):
                    if fingerprint((paragraphs[candidate_index].text or "").strip()) == expected_fp:
                        return cast(Paragraph, paragraphs[candidate_index])

    if expected_fp:
        for candidate in paragraphs:
            if fingerprint((candidate.text or "").strip()) == expected_fp:
                return cast(Paragraph, candidate)
    return None


def _markdown_cell(text: str | None, limit: int = 200) -> str:
    if not text:
        return "-"
    cleaned = " ".join(text.split())
    if len(cleaned) > limit:
        cleaned = cleaned[:limit] + "…"
    return cleaned.replace("|", "／")


def _build_comparison(slots: list[SlotFill], unresolved: list[str], meta: dict[str, Any]) -> str:
    lines = [
        "# 槽位对照表",
        "",
        f"- 报告：{meta.get('title') or '-'}",
        f"- 受控编码：{meta.get('doc_code') or '-'}",
        f"- 品种名称：{meta.get('drug_name') or '-'}",
        f"- 模板：{meta.get('template_name') or '-'}",
        f"- 生成时间：{datetime.now(UTC).astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "| 槽位 | 位置 | 状态 | 填充值 | 来源 | 原文证据 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for slot in slots:
        state = STATE_LABELS.get(slot.state, slot.state)
        if slot.slot_key in unresolved and slot.state != "anchor_unresolved":
            state = STATE_LABELS["anchor_unresolved"]
        lines.append(
            "| {label} | {location} | {state} | {value} | {source} | {evidence} |".format(
                label=_markdown_cell(slot.label or slot.slot_key, 60),
                location=_markdown_cell(slot.location or str((slot.anchor or {}).get("location") or "-"), 60),
                state=state,
                value=_markdown_cell(slot.value),
                source=_markdown_cell(slot.source_name, 60),
                evidence=_markdown_cell(slot.evidence, 300),
            )
        )
    if unresolved:
        lines += ["", "## 未定位的槽位", ""]
        lines += [f"- {key}" for key in unresolved]
    lines.append("")
    return "\n".join(lines)


def render_document(
    template_bytes: bytes,
    slots: list[SlotFill],
    *,
    meta: dict[str, Any] | None = None,
) -> RenderOutput:
    """在母本上回写全部槽位，返回 docx 字节与对照表 markdown。"""
    document = open_document(template_bytes)
    unresolved: list[str] = []
    filled = 0
    gaps = 0

    for slot in slots:
        value = (slot.value or "").strip()
        needs_value = slot.state in ("filled", "conflict", "pending") and bool(value)
        text = value if needs_value else _gap_text(slot)

        target = _locate(document, slot.anchor)
        if target is None:
            unresolved.append(slot.slot_key)
            logger.warning(
                "report-gen slot anchor unresolved",
                extra={"slot_key": slot.slot_key, "kind": (slot.anchor or {}).get("kind")},
            )
            continue
        if not _fill_blank(target, value if needs_value else _gap_text(slot, inline=True)):
            _set_paragraph_text(target, text)
        if needs_value:
            filled += 1
        else:
            gaps += 1

    output = RenderOutput(
        document=_save(document),
        comparison_markdown=_build_comparison(slots, unresolved, meta or {}),
        unresolved=unresolved,
        filled=filled,
        gaps=gaps,
    )
    logger.info(
        "report-gen document rendered",
        extra={"slot_count": len(slots), "filled": filled, "gaps": gaps, "unresolved": len(unresolved)},
    )
    return output


def _save(document: Any) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


__all__ = ["GAP_PREFIX", "STATE_LABELS", "RenderOutput", "SlotFill", "render_document"]
