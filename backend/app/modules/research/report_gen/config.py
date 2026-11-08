"""AI 报告生成的运行时配置（core.module_settings，模块 research）。

所有可调参数都走库里的 ``REPORT_GEN_*`` 键：模型档位、轮次与超时是运营参数，
改库即生效，不需要改代码或重启（每次任务开始时读一次）。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.research.report_gen.model_binding import ModelBinding, resolve_bindings
from app.shared.config_reader import (
    get_module_setting,
    get_module_setting_float,
    get_module_setting_int,
)

MODULE = "research"

# 工具协议：auto = 先试 tools，端点不支持再降级 JSON；tools / json 为强制
TOOL_MODE_VALUES = ("auto", "tools", "json")


@dataclass(slots=True, frozen=True)
class ReportGenConfig:
    """一次任务内固定使用的配置快照。"""

    model: ModelBinding
    fallback_model: ModelBinding
    structure_model: ModelBinding
    tool_mode: str
    disabled_tools: frozenset[str]
    max_rounds: int
    llm_timeout_seconds: float
    tool_timeout_seconds: float
    job_timeout_seconds: float
    kb_top_k: int
    max_steps: int


async def load_config() -> ReportGenConfig:
    """读取运行时配置；缺省值保证开箱可用。

    三个模型档位在这里就解析成 ``ModelBinding``：可以填 LLM 配置名（整份切换端点与
    密钥）或模型名（只覆盖模型），解析一次后整条任务链路共用。
    """
    raw_model = (await get_module_setting(MODULE, "REPORT_GEN_MODEL", "")).strip()
    raw_fallback = (await get_module_setting(MODULE, "REPORT_GEN_FALLBACK_MODEL", "")).strip()
    # 结构识别是「读母本、判空位」，用同档模型即可；未单独配置时复用主模型
    raw_structure = (await get_module_setting(MODULE, "REPORT_GEN_STRUCTURE_MODEL", "")).strip()
    model, structure_model, fallback_model = await resolve_bindings(raw_model, raw_structure, raw_fallback)

    tool_mode = (await get_module_setting(MODULE, "REPORT_GEN_TOOL_MODE", "auto")).strip().lower()
    if tool_mode not in TOOL_MODE_VALUES:
        tool_mode = "auto"

    raw_disabled = await get_module_setting(MODULE, "REPORT_GEN_DISABLED_TOOLS", "")
    # 空串 = 全开，天然向后兼容；工具名统一小写，过滤交给 tools.resolve_tool_specs
    disabled_tools = frozenset(item.strip().lower() for item in raw_disabled.split(",") if item.strip())

    return ReportGenConfig(
        model=model,
        fallback_model=fallback_model,
        structure_model=structure_model,
        tool_mode=tool_mode,
        disabled_tools=disabled_tools,
        max_rounds=await get_module_setting_int(MODULE, "REPORT_GEN_MAX_ROUNDS", 16),
        llm_timeout_seconds=await get_module_setting_float(MODULE, "REPORT_GEN_LLM_TIMEOUT_SECONDS", 180.0),
        tool_timeout_seconds=await get_module_setting_float(MODULE, "REPORT_GEN_TOOL_TIMEOUT_SECONDS", 60.0),
        job_timeout_seconds=await get_module_setting_float(MODULE, "REPORT_GEN_JOB_TIMEOUT_SECONDS", 2400.0),
        kb_top_k=await get_module_setting_int(MODULE, "REPORT_GEN_KB_TOP_K", 6),
        max_steps=await get_module_setting_int(MODULE, "REPORT_GEN_MAX_STEPS", 400),
    )


__all__ = ["MODULE", "TOOL_MODE_VALUES", "ReportGenConfig", "load_config"]
