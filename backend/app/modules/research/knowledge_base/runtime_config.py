"""运行时配置：运营参数走 core.module_settings（Web UI 可改），代码里只留默认值。

从原 doc_gen 迁入后只服务知识库富化（切片摸底、事实抽取、模型选择）。报告生成的可调参数
已迁到 ``report_gen/config.py``（``REPORT_GEN_*``），两边不要混用。

配置键沿用 ``DOC_GEN_`` 前缀：库中已按该前缀存过值，改名会让存量配置全部失效。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.llm import get_named_config
from app.shared.config_reader import (
    get_module_setting,
    get_module_setting_bool,
    get_module_setting_int,
)

logger = logging.getLogger(__name__)

MODULE = "research"


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """知识库富化（后台摸底 + 事实抽取）可调参数。"""

    # 摸底并发数：>1 时多文档同时拉取远端切片（写库仍串行）
    kb_survey_concurrency: int = 4
    # 后台富化 worker：把「摸底 + 事实抽取」从任务链路移到后台持续增量
    kb_background_enrich_enabled: bool = True
    kb_background_enrich_interval_seconds: int = 30
    # 后台单轮抽事实的切片数上限（多轮累计覆盖全库；0=不限，不建议）
    kb_background_enrich_max_chunks: int = 200
    # 事实抽取每批送入模型的切片数
    fact_extract_batch_size: int = 4
    # 事实抽取并发批次数：>1 时多批同时调模型（写库仍串行）；有代码硬顶保护
    fact_extract_concurrency: int = 4
    # 单次模型调用硬超时（秒），超时按降级处理
    llm_call_timeout_seconds: int = 180
    # 富化用的模型名（留空=沿用当前活跃配置）
    extract_model_name: str = ""


@dataclass(frozen=True, slots=True)
class ModelChoice:
    """一次调用该用哪份模型配置（两者都为空即沿用当前活跃配置）。"""

    config_name: str | None = None
    model_override: str | None = None


async def resolve_model(name: str, purpose: str = "text") -> ModelChoice:
    """把运行时配置里的模型名解析成调用参数。

    - 命中 ``core.llm_configs``（按 config_name 或 model_name）→ 整份配置切过去，
      端点与密钥跟着换，适用于两个模型不在同一网关的情况；
    - 没命中 → 只覆盖 model 字段，适用于同一网关下换模型；
    - 名字留空 → 完全沿用活跃配置，改造前后行为一致。
    """
    wanted = (name or "").strip()
    if not wanted:
        return ModelChoice()
    config = await get_named_config(wanted, purpose)
    if config is not None:
        return ModelChoice(config_name=config.config_name)
    logger.warning(
        "运行时配置的模型未登记为 LLM 配置，按同名模型覆盖活跃配置",
        extra={"requested_model": wanted},
    )
    return ModelChoice(model_override=wanted)


async def load_runtime_config() -> RuntimeConfig:
    """读取运行时配置（缺省即用默认值，未播种也能工作）。"""
    get = get_module_setting_int
    return RuntimeConfig(
        kb_survey_concurrency=await get(MODULE, "DOC_GEN_KB_SURVEY_CONCURRENCY", 4),
        kb_background_enrich_enabled=await get_module_setting_bool(
            MODULE, "DOC_GEN_KB_BACKGROUND_ENRICH_ENABLED", True
        ),
        kb_background_enrich_interval_seconds=await get(MODULE, "DOC_GEN_KB_BACKGROUND_ENRICH_INTERVAL_SECONDS", 30),
        kb_background_enrich_max_chunks=await get(MODULE, "DOC_GEN_KB_BACKGROUND_ENRICH_MAX_CHUNKS", 200),
        fact_extract_batch_size=await get(MODULE, "DOC_GEN_FACT_EXTRACT_BATCH_SIZE", 4),
        fact_extract_concurrency=await get(MODULE, "DOC_GEN_FACT_EXTRACT_CONCURRENCY", 4),
        llm_call_timeout_seconds=await get(MODULE, "DOC_GEN_LLM_CALL_TIMEOUT_SECONDS", 180),
        extract_model_name=await get_module_setting(MODULE, "DOC_GEN_EXTRACT_MODEL", ""),
    )
