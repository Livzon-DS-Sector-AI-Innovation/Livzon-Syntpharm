"""AI 报告生成的运行时配置（core.module_settings，模块 research）。

所有可调参数都走库里的 ``REPORT_GEN_*`` 键：模型档位、轮次与超时是运营参数，
改库即生效，不需要改代码或重启（每次任务开始时读一次）。

结构识别下线后，这里不再有「识别模型 / 识别提示词 / 示例注入」三组配置：识别本身没了，
保留这些键只会让配置页出现一个改了没用的开关。历史库里遗留的同名键不会被读取，
也不会报错（``get_module_setting`` 取不到就用默认值）。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.research.report_gen.model_binding import ModelBinding, resolve_binding
from app.modules.research.report_gen.prompts import (
    AGENT_SYSTEM_PROMPT,
    OPINION_DIGEST_PROMPT,
    resolve_prompt,
)
from app.shared.config_reader import (
    get_module_setting,
    get_module_setting_float,
    get_module_setting_int,
)

MODULE = "research"

# 工具协议：auto = 先试 tools，端点不支持再降级 JSON；tools / json 为强制
TOOL_MODE_VALUES = ("auto", "tools", "json")

# 一次写工具最多提交几处：太少会拖长轮次，太多会让单轮输出过长、模型开始编造
DEFAULT_WRITE_BATCH_LIMIT = 10
# 一轮检索最多几组关键词
DEFAULT_SEARCH_QUERY_LIMIT = 5
# 单任务目标时长（秒）：只用于日志与进度提示，真正的硬上限仍是 JOB_TIMEOUT_SECONDS
DEFAULT_JOB_TARGET_SECONDS = 600.0


@dataclass(slots=True, frozen=True)
class ReportGenConfig:
    """一次任务内固定使用的配置快照。"""

    model: ModelBinding
    fallback_model: ModelBinding
    tool_mode: str
    disabled_tools: frozenset[str]
    max_rounds: int
    llm_timeout_seconds: float
    tool_timeout_seconds: float
    job_timeout_seconds: float
    job_target_seconds: float
    kb_top_k: int
    max_steps: int
    write_batch_limit: int
    search_query_limit: int
    references_enabled: bool
    # 意见库：生成前把有效意见归并成写作要求；关闭后完全回到「只拼补充说明」的老链路
    opinion_digest_enabled: bool
    opinion_max_items: int
    # 提示词：库里配了就用库里的，留空用内置；变量渲染在任务内完成（要带品种/编码等）
    agent_prompt: str
    opinion_digest_prompt: str


async def load_config() -> ReportGenConfig:
    """读取运行时配置；缺省值保证开箱可用。

    两个模型档位在这里就解析成 ``ModelBinding``：可以填 LLM 配置名（整份切换端点与
    密钥）或模型名（只覆盖模型），解析一次后整条任务链路共用。
    """
    raw_model = (await get_module_setting(MODULE, "REPORT_GEN_MODEL", "")).strip()
    raw_fallback = (await get_module_setting(MODULE, "REPORT_GEN_FALLBACK_MODEL", "")).strip()
    model = await resolve_binding(raw_model)
    fallback_model = await resolve_binding(raw_fallback)

    tool_mode = (await get_module_setting(MODULE, "REPORT_GEN_TOOL_MODE", "auto")).strip().lower()
    if tool_mode not in TOOL_MODE_VALUES:
        tool_mode = "auto"

    raw_disabled = await get_module_setting(MODULE, "REPORT_GEN_DISABLED_TOOLS", "")
    # 空串 = 全开，天然向后兼容；工具名统一小写，过滤交给 tools.resolve_tool_specs
    disabled_tools = frozenset(item.strip().lower() for item in raw_disabled.split(",") if item.strip())

    return ReportGenConfig(
        model=model,
        fallback_model=fallback_model,
        tool_mode=tool_mode,
        disabled_tools=disabled_tools,
        max_rounds=max(1, await get_module_setting_int(MODULE, "REPORT_GEN_MAX_ROUNDS", 30)),
        llm_timeout_seconds=await get_module_setting_float(MODULE, "REPORT_GEN_LLM_TIMEOUT_SECONDS", 180.0),
        tool_timeout_seconds=await get_module_setting_float(MODULE, "REPORT_GEN_TOOL_TIMEOUT_SECONDS", 60.0),
        job_timeout_seconds=await get_module_setting_float(MODULE, "REPORT_GEN_JOB_TIMEOUT_SECONDS", 2400.0),
        job_target_seconds=await get_module_setting_float(
            MODULE, "REPORT_GEN_JOB_TARGET_SECONDS", DEFAULT_JOB_TARGET_SECONDS
        ),
        kb_top_k=await get_module_setting_int(MODULE, "REPORT_GEN_KB_TOP_K", 6),
        max_steps=await get_module_setting_int(MODULE, "REPORT_GEN_MAX_STEPS", 400),
        write_batch_limit=max(
            1, await get_module_setting_int(MODULE, "REPORT_GEN_WRITE_BATCH_LIMIT", DEFAULT_WRITE_BATCH_LIMIT)
        ),
        search_query_limit=max(
            1, await get_module_setting_int(MODULE, "REPORT_GEN_SEARCH_QUERY_LIMIT", DEFAULT_SEARCH_QUERY_LIMIT)
        ),
        references_enabled=(await get_module_setting(MODULE, "REPORT_GEN_REFERENCES_ENABLED", "true")).strip().lower()
        not in ("false", "0", "off", "no"),
        opinion_digest_enabled=(await get_module_setting(MODULE, "REPORT_GEN_OPINION_DIGEST_ENABLED", "true"))
        .strip()
        .lower()
        not in ("false", "0", "off", "no"),
        opinion_max_items=max(1, await get_module_setting_int(MODULE, "REPORT_GEN_OPINION_MAX_ITEMS", 40)),
        agent_prompt=resolve_prompt(
            await get_module_setting(MODULE, "REPORT_GEN_AGENT_PROMPT", ""),
            AGENT_SYSTEM_PROMPT,
        ),
        opinion_digest_prompt=resolve_prompt(
            await get_module_setting(MODULE, "REPORT_GEN_OPINION_DIGEST_PROMPT", ""),
            OPINION_DIGEST_PROMPT,
        ),
    )


__all__ = [
    "DEFAULT_JOB_TARGET_SECONDS",
    "DEFAULT_SEARCH_QUERY_LIMIT",
    "DEFAULT_WRITE_BATCH_LIMIT",
    "MODULE",
    "TOOL_MODE_VALUES",
    "ReportGenConfig",
    "load_config",
]
