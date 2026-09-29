"""模板 Markdown 识别版：把模板槽位结构渲染为**接近母本内容**的 Markdown 页面。

定位（P1 只读展示）：交付物模板页「模板 Markdown」弹窗——渲染视图就是模板内容本身，
只展示章节、填写项名称与待填区，不展示类型/检索词/定位等识别元信息。
视图由 ``template_structure`` 现渲染、不落库，与唯一事实源永不漂移。

每个填写项的**内容区**用 ``<!--slot:key-->`` 标记包裹：渲染视图里注释不可见，
源码里稳定可寻，为 P2「编辑 Markdown → 按 key 解析回槽位值」预留结构。
渲染安全不受此视图影响：docx 仍由锚点回填母本，本文件永不反向转 Word。
"""

from __future__ import annotations

import re

from app.modules.research.doc_gen.template_spec import SectionFragment, Slot, TemplateSpec

# 内容区标记：key 允许字母数字下划线、点（章节实例前缀）与短横线
_SLOT_BLOCK_RE = re.compile(r"<!--slot:([A-Za-z0-9_.\-]+)-->(.*?)<!--/slot-->", re.DOTALL)


def _slot_group(slot: Slot) -> tuple[str, str | None]:
    """槽位按锚点语境分组：章节标题 > 表格 > 段落标签 > 其他，让视图接近母本内容页。

    返回 (分组 id, 分组标题)；标题为 None 时不输出标题行——段落标签本身就是母本里的
    文字，再打一行「段落 · xx」反而偏离内容页形态。
    """
    for anchor in slot.anchors:
        if anchor.heading:
            return (f"h:{anchor.heading}", anchor.heading)
    for anchor in slot.anchors:
        if anchor.table_header:
            return (f"t:{anchor.table_header[0]}", f"表格 · {anchor.table_header[0]}")
        if anchor.paragraph_label:
            return (f"p:{anchor.paragraph_label}", None)
    return ("other", None)


def _content_block(slot: Slot) -> list[str]:
    """内容区（被 slot 标记包裹）：P2 在此解析编辑值，表格槽位渲染列头占位行。"""
    if slot.kind == "table":
        headers = [c.label or c.key for c in slot.columns]
        return [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---"] * len(headers)) + " |",
            "| " + " | ".join(["{{待填}}"] * len(headers)) + " |",
        ]
    if slot.kind == "image":
        return ["> 【图片占位：{{待填}}】"]
    return ["> {{待填}}"]


def _slot_lines(slot: Slot) -> list[str]:
    """一个填写项 = 名称 + 待填内容区，不展示类型/检索词/定位等识别元信息。"""
    lines = [f"**{slot.label}**", ""]
    lines.append(f"<!--slot:{slot.key}-->")
    lines.append("")
    lines.extend(_content_block(slot))
    lines.append("")
    lines.append("<!--/slot-->")
    lines.append("")
    return lines


def _fragment_lines(fragment: SectionFragment) -> list[str]:
    title = fragment.label or fragment.default_title
    lines = [f"## {title}", ""]
    for slot in fragment.slots:
        lines.extend(_slot_lines(slot))
    return lines


def render_spec_markdown(spec: TemplateSpec) -> str:
    """把模板槽位结构渲染为 Markdown 内容页（只读展示；不落库，现渲染现返回）。"""
    lines = [f"# {spec.name}", ""]

    # 骨架槽位按锚点语境分组展示，保持 spec 内的原始顺序
    groups: dict[tuple[str, str | None], list[Slot]] = {}
    for slot in spec.slots:
        groups.setdefault(_slot_group(slot), []).append(slot)
    for (_, heading), slots in groups.items():
        if heading:
            lines.append(f"## {heading}")
            lines.append("")
        for slot in slots:
            lines.extend(_slot_lines(slot))

    for fragment in spec.fragments:
        lines.extend(_fragment_lines(fragment))

    return "\n".join(lines) + "\n"


def extract_slot_blocks(markdown: str) -> dict[str, str]:
    """按 ``<!--slot:key-->`` 标记提取各填写项的内容区原文。

    P1 仅用于单测验证标记完整性；P2 将在此基础上把人工编辑解析回槽位值。
    """
    return {match.group(1): match.group(2).strip() for match in _SLOT_BLOCK_RE.finditer(markdown)}


__all__ = ["extract_slot_blocks", "render_spec_markdown"]
