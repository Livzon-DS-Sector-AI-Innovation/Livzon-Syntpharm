"""提示词集中管理：内置常量 + ``$变量`` 渲染 + 运行时覆盖。

为什么集中：提示词是最常被调的一段文字，原来散在 ``agent.py`` / ``structure.py`` 里，
改一句话就得改代码发版。现在改成「库里能覆盖、代码里有兜底」——运维在
``core.module_settings`` 填 ``REPORT_GEN_AGENT_PROMPT`` / ``REPORT_GEN_STRUCTURE_PROMPT``
即可整段替换，留空则用本文件的内置版本；改库即生效，不用重启。

变量语法用 ``$name``（``string.Template``）而不是 ``{}``：提示词正文里到处是 JSON
花括号（``{"slots": [...]}``），``str.format`` 会把它们当占位符直接炸掉。
``safe_substitute`` 遇到未知变量原样保留，不会因为漏传一个变量就把生成打挂。
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from string import Template
from typing import Any

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是原料药研发部的报告编写助手。你要基于**项目已有资料**填写一份 Word 报告模板。

工作方式：
1. 先调用 read_template_outline 看清要填哪些槽位（可分页读取）；
2. 调用 read_project_context 拿项目登记信息、阶段记录、实验记录；
3. 针对每个槽位，用 search_knowledge_base 找资料（检索词用槽位含义，不要照抄槽位名）；
4. 找到依据就 fill_slot，必须带 source_name 与 evidence（原文摘录，不得改写）；
5. 确实找不到就 mark_gap，并给出应补充的部门；
6. 所有槽位都处理完后调用 finalize。

硬性要求：
- 绝不编造数据、批号、日期、数值；没有依据一律 mark_gap。
- 品种名称、受控编码、报告标题以本次报告输入为准，项目登记数据可补全 API 名称、CAS 号等。
- 同一信息可复用于多个语义相同的槽位。
- 一次可以并行发起多个工具调用；不要重复检索同样的内容。
- 相近槽位（如同一表格的同一行）先合并检索，不要为每个槽位重复搜同一个词。
- 除工具调用外，用一句中文说明你正在做什么。

本次任务：品种 $drug_name；受控编码 $doc_code；报告标题 $report_title；
模板 $template_name；共 $slot_total 个槽位，最多 $max_rounds 轮。"""

AGENT_JSON_PROTOCOL_PROMPT = """当前模型以 JSON 协议工作：每轮只输出一个 JSON 对象，不要输出别的文字。
调用工具：{"thought":"一句话说明","action":"工具名","action_input":{...}}
全部完成：{"thought":"一句话说明","final":true,"summary":"本次填写总结"}
可用工具（JSON schema）：{tools}
工具执行结果会以 {"tool_result": ...} 的形式回给你。"""

STRUCTURE_SYSTEM_PROMPT = """你是医药研发报告模板的结构分析专家。
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


def resolve_prompt(override: str | None, builtin: str) -> str:
    """库里配了就用库里的，留空/纯空白用内置版本。

    覆盖值只做「整段替换」，不提供片段补丁：片段拼接会让「最终生效文本」难以复原，
    而提示词指纹要的正是这段可复原的最终文本。
    """
    text = (override or "").strip()
    return text or builtin


def render_prompt(template: str, variables: Mapping[str, Any] | None = None) -> str:
    """把 ``$name`` 变量填进提示词；未知变量原样保留，渲染失败退回原文。

    宁可让模型看到一句带 ``$slot_total`` 的提示词，也不能因为一次渲染异常把整条
    生成任务打挂——提示词是软约束，任务可用性优先。
    """
    if not variables:
        return template
    safe = {key: "" if value is None else str(value) for key, value in variables.items()}
    try:
        return Template(template).safe_substitute(safe)
    except (ValueError, TypeError):  # 极端情况：正文里有孤立的 ``$``
        logger.warning("report-gen prompt rendering failed, fallback to raw text")
        return template


__all__ = [
    "AGENT_JSON_PROTOCOL_PROMPT",
    "AGENT_SYSTEM_PROMPT",
    "STRUCTURE_SYSTEM_PROMPT",
    "render_prompt",
    "resolve_prompt",
]
