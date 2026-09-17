"""生成说明：告诉使用者每一句话来自哪份资料第几页、哪些地方需要人工补。

在「下载后人工改」的模式下，这份说明是唯一能把 docx 里的文字追回到原始资料的载体，
因此它不是可选附件，而是每次生成的必产物。
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.extraction import SlotResult
from app.modules.research.doc_gen.renderer import RenderReport
from app.modules.research.doc_gen.sections import SectionInstance
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

_STATE_LABELS = {
    status.STATUS_OK: "已填充",
    status.STATUS_DRAFT: "AI草稿需确认",
    status.STATUS_PENDING: "待补充",
    status.STATUS_CONFLICT: "材料冲突",
    status.STATUS_MANUAL: "需人工填写",
    status.STATUS_FAILED: "AI未取得结果",
    status.STATUS_OVERFLOW: "版式待处理",
    status.STATUS_ANCHOR_UNRESOLVED: "未能定位",
    status.STATUS_NEEDS_VERIFY: "需人工核对",
}

_MAX_SHOWN = 80


def state_label(state: str) -> str:
    """状态中文说明。"""
    return _STATE_LABELS.get(state, state)


def _reason_of(result: SlotResult | None) -> str:
    """取填充项原因：优先显式 reason，其次待补充占位中的原因。"""
    if result is None:
        return "—"
    if result.reason:
        return result.reason
    return status.pending_reason(result.text) or "—"


def _where(slot: Slot) -> str:
    """填充项在模板原件中的位置描述。"""
    anchor = slot.anchors[0]
    for candidate in (anchor.heading, anchor.row_label, anchor.paragraph_label, anchor.header_contains):
        if candidate:
            return str(candidate)
    return "/".join(anchor.table_header) or "正文"


def _shown(result: SlotResult, slot: Slot) -> str:
    """值列展示：表格显示行数，其余显示截断文本。"""
    if slot.kind == "table":
        return f"{len(result.rows)} 行"
    return (result.text or "").replace("\n", " ")[:_MAX_SHOWN]


def _evidence_text(result: SlotResult, filenames: Mapping[str, str]) -> str:
    """依据列文本。"""
    if result.candidates:
        return "候选值：" + " / ".join(result.candidates[:4])
    if not result.evidence:
        return "—"
    parts: list[str] = []
    for evidence in result.evidence[:3]:
        name = filenames.get(evidence.file_id, evidence.file_id)
        parts.append(f"{name} 第{evidence.page}页“{evidence.quote[:60]}”")
    return "；".join(parts)


def summarize_states(results: Sequence[SlotResult]) -> dict[str, int]:
    """状态计数，供接口与统计使用。"""
    summary: dict[str, int] = {}
    for result in results:
        summary[result.state] = summary.get(result.state, 0) + 1
    return summary


def _pending_section(
    spec: TemplateSpec, results: Mapping[str, SlotResult], render_report: RenderReport
) -> list[str]:
    """待人工处理清单。"""
    lines = ["", "## 待人工处理清单", "", "| 填充项 | 名称 | 状态 | 原因 | 所在位置 |", "|---|---|---|---|---|"]
    for slot in spec.slots:
        result = results.get(slot.key)
        state = result.state if result else status.STATUS_PENDING
        if state == status.STATUS_OK:
            continue
        lines.append(f"| {slot.key} | {slot.label} | {state_label(state)} | {_reason_of(result)} | {_where(slot)} |")
    return lines


def _notes_section(
    spec: TemplateSpec, results: Mapping[str, SlotResult], render_report: RenderReport, filenames: Mapping[str, str]
) -> list[str]:
    """逐项填充结果与依据。"""
    lines = ["", "## 逐项填充结果与依据", "", "| 填充项 | 名称 | 状态 | 值/行数 | 依据 |", "|---|---|---|---|---|"]
    for slot in spec.slots:
        result = results.get(slot.key)
        if result is None:
            continue
        lines.append(
            f"| {slot.key} | {slot.label} | {state_label(result.state)} "
            f"| {_shown(result, slot)} | {_evidence_text(result, filenames)} |"
        )
    return lines


def _outline_section(sections: Sequence[SectionInstance], render_report: RenderReport) -> list[str]:
    """章节大纲与生成依据：每个动态章节为何出现、是否被人工禁用。"""
    if not sections:
        return []
    skipped = set(render_report.sections_skipped)
    lines = ["", "## 章节大纲与生成依据", ""]
    for section in sections:
        indent = "　" * max(0, section.level - 1)
        marks: list[str] = []
        if section.state != "enabled":
            marks.append("已禁用，未生成")
        elif section.section_key in skipped:
            marks.append("无实质内容，整节跳过")
        source = "人工新增" if section.source == "manual" else "数据判定"
        detail = str((section.trigger_trace or {}).get("detail") or "")
        suffix = f"　〔{source}〕{detail}" if detail else f"　〔{source}〕"
        tail = f"　（{'；'.join(marks)}）" if marks else ""
        lines.append(f"{indent}- **{section.title}**{suffix}{tail}")
    return lines


def build_report_markdown(
    spec: TemplateSpec,
    results: Mapping[str, SlotResult],
    render_report: RenderReport,
    *,
    filenames: Mapping[str, str],
    project_name: str = "",
    model_note: str = "",
    sections: Sequence[SectionInstance] = (),
) -> str:
    """产出 Markdown 生成说明。"""
    lines: list[str] = [f"# {spec.name} 生成说明", ""]
    lines.append(f"- 模板：{spec.code} v{spec.version}")
    if project_name:
        lines.append(f"- 项目：{project_name}")
    if model_note:
        lines.append(f"- 模型：{model_note}")
    # 统计口径与接口返回保持一致：占位符不计入「实质内容」，否则使用者会被「已写入」误导
    counts = summarize_states(list(results.values()))
    substantive = counts.get(status.STATUS_OK, 0)
    pending = counts.get(status.STATUS_PENDING, 0) + counts.get(status.STATUS_FAILED, 0)
    manual = counts.get(status.STATUS_MANUAL, 0)
    drafts = counts.get(status.STATUS_DRAFT, 0)
    needs_verify = counts.get(status.STATUS_NEEDS_VERIFY, 0)
    lines += [
        f"- 填充项总数：{len(spec.slots)}；实质内容：{substantive}；"
        f"待补充：{pending}；需人工：{manual}；AI 草稿：{drafts}；需人工核对：{needs_verify}",
        "",
        "本文档为初版。未填充或不确定处均以 `[待补充：原因]` 标出；"
        "带 `【AI草稿，需确认】` 前缀的段落由模型归纳，请逐条核对后删除前缀；"
        "「引用需核对」的值已写入但依据仅经模糊匹配核对，请重点确认。",
    ]
    lines += _outline_section(sections, render_report)
    lines += _pending_section(spec, results, render_report)
    if render_report.unresolved:
        lines += ["", "## 未能在模板原件中定位的填充项（需复核模板配置）", ""]
        lines += [f"- `{key}`：{reason}" for key, reason in render_report.unresolved.items()]
    if render_report.occupied:
        lines += ["", "## 模板原件已有内容、未覆盖的位置", ""]
        lines += [f"- `{key}`：该位置已有文字，需人工确认后再改" for key in render_report.occupied]
    if render_report.overflow:
        lines += ["", "## 版式待处理", ""]
        lines += [f"- {item}" for item in render_report.overflow]
    if render_report.toc_paragraphs:
        lines += ["", f"- 目录页码已移除（{render_report.toc_paragraphs} 条），请在 Word 中更新目录。"]
    if spec.unfilled_notes:
        lines += ["", "## 本版不自动填充的区域", ""]
        lines += [f"- {note}" for note in spec.unfilled_notes]
    lines += _notes_section(spec, results, render_report, filenames)
    if render_report.warnings:
        lines += ["", "## 过程告警", ""]
        lines += [f"- {warn}" for warn in render_report.warnings]
    return "\n".join(lines) + "\n"
