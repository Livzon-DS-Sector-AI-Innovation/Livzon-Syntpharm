"""提示词集中管理：内置常量 + ``$变量`` 渲染 + 运行时覆盖。

为什么集中：提示词是最常被调的一段文字。现在改成「库里能覆盖、代码里有兜底」——运维在
``core.module_settings`` 填 ``REPORT_GEN_AGENT_PROMPT`` 即可整段替换，留空则用本文件
的内置版本；改库即生效，不用重启。

变量语法用 ``$name``（``string.Template``）而不是 ``{}``：提示词正文里到处是 JSON
花括号，``str.format`` 会把它们当占位符直接炸掉。``safe_substitute`` 遇到未知变量原样
保留，不会因为漏传一个变量就把生成打挂。
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from string import Template
from typing import Any

logger = logging.getLogger(__name__)

AGENT_SYSTEM_PROMPT = """你是原料药研发部的报告编写助手。你的任务是把项目里已有的资料写进一份
Word 报告母本的可写位置，并整理参考资料（只展示在页面右侧，不进正文）。

工作方式：
1. 先调用 read_template_outline 看清可写位置：key 是写入时用的位置标识（p{下标} 段落、
   t{表}r{行}c{列} 单元格），context 是上一段或行标题文字；表格另有 column_hint（列路径，
   如「自研成本 › 研发投入」）与 expect（number 数值 / cas CAS号 / formula 分子式 /
   opinion 评审意见 / text 文本）。位置多时分页读；表格可以传 table_index 整表读。
2. 调用 read_project_context 拿项目登记信息、阶段记录、实验记录与本次报告输入。
3. 按章节批量检索：一次 search_knowledge_base 传 queries（多组关键词）比逐条问快得多。
   检索词用业务含义（如「起始物料 质量标准」「异构体 限度」），不要照抄母本句子。
4. 找到依据就用 write_paragraph / write_cell 批量写入（一次最多 10 处），
   必须带 source_ids（来自检索结果的 source_id）。带 append=true 的「标签：」段只给
   冒号后的值，不要重复标签（如 text 写「片剂 10mg」，不要写「制剂/规格：片剂 10mg」）。
5. 母本条目不够时扩增：模板某一章只有 N 个同级子标题、资料里还有第 N+1 个时
   （如路线1-4 之后还有路线5、路线6，供应商、杂质、批次等任何同类条目同理），先
   read_template_outline(only_writable=false) 找到已有子标题的 p 下标，再用 append_subsection
   在上一子标题正文之后新增子标题（title_clone_from 传该子标题下标），最后用 append_paragraph
   在 as{n} 之后写正文；只是补一段正文、不新增子标题时才直接用 append_paragraph。
   append_table_rows 克隆已有行格式追加表格行。
6. 全部写完后调用 append_references 整理参考资料（不写进正文），再调用 finalize 结束。

硬性要求：
- 只能写 read_template_outline 返回 writable=true 的位置；凡是 writable=true 且资料里有依据的
  位置都要写满，不要因为段落里已经有「标签：」就跳过。标题、目录、已有完整文字（非占位、
  非标签）、签字审批区禁止写入；工具会拒绝并给出原因，**不要对同一个位置反复重试**。
- 封面/标题页是版面，不是正文：位置名以「封面」开头、或原因写着「封面/标题页的版式内容」
  的位置一律跳过，不要写报告概述、品种简介、结论这类正文。首页只需要模板原有的抬头、
  文件名称、标题与编制/审核栏；正文从第一个章节标题（如「1 综合信息」）之下开始写。
- 带 append=true 的位置是「标签：」段：text 只写冒号后的值，标签由系统保留；
  不要重写标签，也不要把标签重复带进 text。
- 只能新增子标题（二级及以下），不能新增或改写一级标题（大标题）；母本标题是自动编号时
  title 只写标题文字（如「路线5」），不要自己写「4.5」这类编号，编号由 Word 生成。
  目录会随新增子标题同步，不需要手写目录条目。
- 标注「人工确认」的位置（human_locked_total > 0 时提示里会说明）已由人定稿，
  系统会按人工值填入；不要重写这些位置，工具会拒绝，也不要换个别的位置绕过。
- 表格单元格必须**按语义对号入座**：先看 context（行标题）与 column_hint（列路径），
  只有内容和这一行这一列的含义对得上才写。对不上就留空，不要因为「这格空着」就填。
  绝对不要按顺序把一串信息（名称、英文名、CAS、分子式、分子量…）依次塞进一排空格。
- 单元格的 expect 决定能写什么：number 列只能写带数字的数值（拿不到就留空），
  cas 列只写「38304-91-5」这种 CAS 号，formula 列只写「C9H15N5O」这种分子式，
  opinion 列只写中文评审意见——不要把「其他名称」「英文名」这类字段名写进意见栏，
  工具会直接拒绝。
- 没有任何依据就不写，让该位置保持空白；绝不编造数据、批号、日期、数值、结论。
- 只写模板要的内容：按该位置的语义提炼成一句/一段，不要把资料原文整段照抄。
- 品种名称、受控编码、报告标题以本次报告输入为准；项目登记数据可补全 API 名称、CAS 号等。
- 同一信息可复用于多个语义相同的位置，但每次写入都要带上对应的 source_ids。
- 参考资料由写入记录自动整理，不要自己在正文里手写参考文献编号或「引用源」章节。
- 除工具调用外，用一句中文说明你正在做什么。

本次任务：品种 $drug_name；受控编码 $doc_code；报告标题 $report_title；
模板 $template_name；可写位置 $writable_total 个；最多 $max_rounds 轮。"""

AGENT_JSON_PROTOCOL_PROMPT = """当前模型以 JSON 协议工作：每轮只输出一个 JSON 对象，不要输出别的文字。
调用工具：{"thought":"一句话说明","action":"工具名","action_input":{...}}
全部完成：{"thought":"一句话说明","final":true,"summary":"本次填写总结"}
可用工具（JSON schema）：{tools}
工具执行结果会以 {"tool_result": ...} 的形式回给你。"""

INSTRUCTION_HEADER = "本模板的人工填写要求（优先于以上默认写法；与硬性要求冲突时以硬性要求为准）："
OPINION_DIGEST_HEADER = "【历史评审意见汇总（优先遵守的写作要求）】"
HUMAN_LOCKED_HEADER = "【本次沿用上一版人工确认内容的位置（不要重写）】"

# 生成前把意见库归并成写作要求用的提示词。与正文生成提示词分开管理：
# 它只影响「怎么总结人的意见」，不参与正文写作，也不计入提示词指纹。
OPINION_DIGEST_PROMPT = """你是原料药研发报告的质量负责人。下面是历史评审中反复提出的修改意见
（括号里是同类意见被提出的次数，次数越高说明越普遍）。请把它们归并成一份可直接交给
报告撰写者执行的写作要求：

1. 合并同义与近义意见，按「内容完整性 / 数据与因果 / 格式与表述 / 引用与合规」归类；
2. 每条写成可检查的动作（如「结果与讨论必须写明工艺参数与收率的对应关系」），
   不要复述具体某一篇报告的内容；
3. 次数高的要求排前面；互相冲突的要求按次数取舍，并在末尾用一句话说明取舍；
4. 只输出写作要求本身，不要寒暄、不要编号说明、不要提及「意见库」或「历史意见」；
5. 总长不超过 1200 字，条目之间用换行分隔。

历史意见：
{items}"""


def resolve_prompt(override: str | None, builtin: str) -> str:
    """库里配了就用库里的，留空/纯空白用内置版本。

    覆盖值只做「整段替换」，不提供片段补丁：片段拼接会让「最终生效文本」难以复原，
    而提示词指纹要的正是这段可复原的最终文本。
    """
    text = (override or "").strip()
    return text or builtin


def render_prompt(template: str, variables: Mapping[str, Any] | None = None) -> str:
    """把 ``$name`` 变量填进提示词；未知变量原样保留，渲染失败退回原文。

    宁可让模型看到一句带 ``$writable_total`` 的提示词，也不能因为一次渲染异常把整条
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


def with_instruction(system_prompt: str, instruction: str | None) -> str:
    """把模板级填写要求接到 system prompt 末尾。

    不依赖提示词里是否有 ``$instruction`` 占位符：库里覆盖过提示词时占位符可能被删掉，
    而界面上写的填写要求不能被静默丢弃。
    """
    text = (instruction or "").strip()
    if not text:
        return system_prompt
    return f"{system_prompt}\n\n{INSTRUCTION_HEADER}\n{text}"


def with_opinion_digest(system_prompt: str, digest: str | None) -> str:
    """把历史意见汇总接到 system prompt 末尾。

    汇总是「数据」不是「提示词模板」：正文提示词仍可被库里整段覆盖，换算成
    提示词指纹时也不把这段算进去，否则每来一条意见指纹就变，历史任务无法对比。
    """
    text = (digest or "").strip()
    if not text:
        return system_prompt
    return f"{system_prompt}\n\n{OPINION_DIGEST_HEADER}\n{text}"


def with_human_locked_summary(system_prompt: str, locations: list[str]) -> str:
    """告知模型哪些位置已由人工定稿：只列位置名，不把人工值再喂一遍（值已在文档里）。"""
    if not locations:
        return system_prompt
    preview = "、".join(locations[:20])
    suffix = f" 等 {len(locations)} 处" if len(locations) > 20 else ""
    return f"{system_prompt}\n\n{HUMAN_LOCKED_HEADER}\n{preview}{suffix}。"


__all__ = [
    "AGENT_JSON_PROTOCOL_PROMPT",
    "AGENT_SYSTEM_PROMPT",
    "HUMAN_LOCKED_HEADER",
    "INSTRUCTION_HEADER",
    "OPINION_DIGEST_HEADER",
    "OPINION_DIGEST_PROMPT",
    "render_prompt",
    "resolve_prompt",
    "with_human_locked_summary",
    "with_instruction",
    "with_opinion_digest",
]
