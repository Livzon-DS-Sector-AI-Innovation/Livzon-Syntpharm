"""运行时配置：运营参数走 core.module_settings（Web UI 可改），代码里只留默认值。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.llm import get_named_config
from app.shared.config_reader import (
    get_module_setting,
    get_module_setting_bool,
    get_module_setting_float,
    get_module_setting_int,
)

logger = logging.getLogger(__name__)

MODULE = "research"


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """文档生成可调参数。"""

    enabled: bool = True
    max_files: int = 20
    max_total_pages: int = 150
    max_file_mb: int = 30
    # 单次任务资料合计上限：必须 ≤ 前端代理的请求体上限（next.config.ts proxyClientMaxBodySize），
    # 否则请求会在 Next 层被截断成不完整的 multipart，浏览器侧收不到任何响应
    max_total_mb: int = 150
    max_pages_per_file: int = 80
    max_ocr_pages_per_file: int = 30
    batch_size: int = 3
    candidate_limit: int = 10
    max_context_chars: int = 12000
    # 置信度分级：模型自报 confidence < mid 的已填充槽位降级为「需人工核对」，
    # [mid, high) 区间保持写入但计入 low_confidence 统计供抽查
    confidence_high: float = 0.85
    confidence_mid: float = 0.6
    max_concurrency: int = 1
    # 提取/成文阶段 LLM 并发批次数（>1 时多批同时调 LLM，加速但增加网关压力）
    extract_concurrency: int = 1
    compose_concurrency: int = 1
    # 解析阶段文件并发数（>1 时多文件同时解析，OCR 场景提速明显）
    parse_concurrency: int = 1
    # 提取结果缓存：重跑时内容未变的槽位直接复用，跳过 LLM 调用
    extract_cache_enabled: bool = False
    # 解析兜底链第二级：快速 OCR（PP-OCR）无结果时，改用 PP-StructureV3 输出 Markdown
    # （保留表格/标题层级/阅读顺序），比 PP-OCR 慢数倍，按需开启
    ocr_structured_enabled: bool = False
    # 解析兜底链第三级：OCR 仍无结果时把页面转图交给视觉模型（需已登记 vision 类型 LLM 配置）
    vision_fallback_enabled: bool = True
    # 单文件走视觉模型的最大页数（视觉调用最贵，只兜底前面几页）
    vision_max_pages: int = 5
    # 视觉模型图片压缩：JPEG 质量（1-100），越低体积越小但清晰度下降
    vision_image_quality: int = 60
    # 视觉模型图片最大宽度（像素），超过会等比缩放
    vision_max_width: int = 1600
    # 向量检索：embedding 模型名（留空则不启用向量检索，纯关键词）
    embedding_model_name: str = ""
    # 向量检索融合权重：0.0=纯向量，1.0=纯关键词，0.6=关键词为主+向量辅助
    vector_alpha: float = 0.6
    # 向量检索开关（即使配了 embedding_model_name，也可临时关闭）
    vector_retrieval_enabled: bool = False
    lease_seconds: int = 1800
    max_attempts: int = 3
    scan_interval_seconds: int = 30
    # 稳定性护栏：解析/模型调用/整任务三级硬超时 + 租约心跳，卡住能被强制终止
    parse_timeout_seconds: int = 180
    llm_call_timeout_seconds: int = 180
    job_timeout_seconds: int = 2400
    heartbeat_seconds: int = 60
    # 对话补全：初抽完成后与用户多轮对话补值（工具调用走 JSON 模拟模式）
    # 默认开启：提取完成后停在 review 阶段，等用户点击「AI 创建报告」按钮才生成报告
    chat_enabled: bool = True
    chat_max_rounds: int = 3
    # 主模型重试仍失败后的备用模型名（同一网关下的备模型）；为空则不启用备模型
    fallback_model_name: str = ""
    # 三档分工模型名（命中 core.llm_configs 的 config_name/model_name 即整份配置切过去，
    # 端点与密钥随之改变；未命中则只覆盖 model 字段；留空=沿用当前活跃配置）
    template_model_name: str = ""  # 读模板结构、标注槽位检索词
    extract_model_name: str = ""  # 逐文件提炼 + 按槽位取证
    write_model_name: str = ""  # 确认后的成文（AI 报告生成）
    # 成文开关：关闭时渲染直接用人工确认值，等价改造前行为
    compose_enabled: bool = True
    # 直接生成模式：跳过逐槽位提取+成文，一次性把全部资料塞进 context 让模型直接生成报告内容
    # 开启后 LLM 调用从 30+ 次降到 1-2 次，速度大幅提升，但失去逐槽位证据追溯能力
    direct_generation_enabled: bool = False
    # 直接生成模式下的资料来源最大字符数（控制进 prompt 的资料文本量，适配 128K 输入模型）
    direct_gen_max_chars: int = 180000
    # 模板分析开关：用 LLM 解析模板结构，为提取阶段提供槽位指引
    template_analysis_enabled: bool = True
    # 文件分析开关：用 LLM 异步逐文件分析，提取与模板匹配的结构化摘要
    file_analysis_enabled: bool = True
    # 文件分析并发数（同时分析的文件数）
    file_analysis_concurrency: int = 4
    # 交叉校验开关：提取完成后对比文件分析与槽位结果，标记不一致
    cross_validation_enabled: bool = True
    # 每批上下文字符预算：三层上限里的「模型层」。
    # 配了 model_max_input_tokens 就按 (输入上限 - 输出预留) × 水位 ÷ 字符系数 派生，
    # 未配（0）则沿用 max_context_chars 固定值。
    model_max_input_tokens: int = 0
    output_reserve_tokens: int = 2048
    char_per_token: float = 1.6
    context_water_level: float = 0.6


    @property
    def context_chars(self) -> int:
        """模型层预算：单批能进 prompt 的字符上限。

        上传体积（传输层）、解析字符数（解析层）与这里是三层独立上限：模型只吃解析后的
        文本，MB 与 token 之间没有固定换算，所以模型上限换算成「每批字符预算」来配，
        而不是放大上传体积。未配 token 上限时沿用固定字符值（改造前行为）。
        """
        if self.model_max_input_tokens <= 0:
            return self.max_context_chars
        usable = max(1000, self.model_max_input_tokens - self.output_reserve_tokens)
        chars = int(usable * self.context_water_level / max(0.4, self.char_per_token))
        return max(2000, min(chars, 200_000))


@dataclass(frozen=True, slots=True)
class ModelChoice:
    """一次调用该用哪份模型配置（两者都为空即沿用当前活跃配置）。"""

    config_name: str | None = None
    model_override: str | None = None


async def resolve_model(name: str, purpose: str = "text") -> ModelChoice:
    """把运行时配置里的模型名解析成调用参数。

    - 命中 ``core.llm_configs``（按 config_name 或 model_name）→ 整份配置切过去，
      端点与密钥跟着换，适用于两个模型不在同一网关的情况；
    - 没命中 → 只覆盖 model 字段，与 ``DOC_GEN_FALLBACK_MODEL`` 同语义，
      适用于同一网关下换模型；
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
    enabled = await get_module_setting_bool(MODULE, "DOC_GEN_ENABLED", True)
    return RuntimeConfig(
        enabled=enabled,
        max_files=await get(MODULE, "DOC_GEN_MAX_FILES", 20),
        max_total_pages=await get(MODULE, "DOC_GEN_MAX_TOTAL_PAGES", 150),
        max_file_mb=await get(MODULE, "DOC_GEN_MAX_FILE_MB", 30),
        max_total_mb=await get(MODULE, "DOC_GEN_MAX_TOTAL_MB", 150),
        max_pages_per_file=await get(MODULE, "DOC_GEN_MAX_PAGES_PER_FILE", 80),
        max_ocr_pages_per_file=await get(MODULE, "DOC_GEN_MAX_OCR_PAGES_PER_FILE", 30),
        batch_size=await get(MODULE, "DOC_GEN_BATCH_SIZE", 3),
        candidate_limit=await get(MODULE, "DOC_GEN_CANDIDATE_LIMIT", 10),
        max_context_chars=await get(MODULE, "DOC_GEN_MAX_CONTEXT_CHARS", 12000),
        confidence_high=await get_module_setting_float(MODULE, "DOC_GEN_CONFIDENCE_HIGH", 0.85),
        confidence_mid=await get_module_setting_float(MODULE, "DOC_GEN_CONFIDENCE_MID", 0.6),
        max_concurrency=await get(MODULE, "DOC_GEN_MAX_CONCURRENCY", 1),
        extract_concurrency=await get(MODULE, "DOC_GEN_EXTRACT_CONCURRENCY", 1),
        compose_concurrency=await get(MODULE, "DOC_GEN_COMPOSE_CONCURRENCY", 1),
        parse_concurrency=await get(MODULE, "DOC_GEN_PARSE_CONCURRENCY", 1),
        extract_cache_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_EXTRACT_CACHE_ENABLED", False),
        ocr_structured_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_OCR_STRUCTURED_ENABLED", False),
        vision_fallback_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_VISION_FALLBACK_ENABLED", True),
        vision_max_pages=await get(MODULE, "DOC_GEN_VISION_MAX_PAGES", 5),
        vision_image_quality=await get(MODULE, "DOC_GEN_VISION_IMAGE_QUALITY", 60),
        vision_max_width=await get(MODULE, "DOC_GEN_VISION_MAX_WIDTH", 1600),
        embedding_model_name=await get_module_setting(MODULE, "DOC_GEN_EMBEDDING_MODEL", ""),
        vector_alpha=await get_module_setting_float(MODULE, "DOC_GEN_VECTOR_ALPHA", 0.6),
        vector_retrieval_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_VECTOR_RETRIEVAL_ENABLED", False),
        lease_seconds=await get(MODULE, "DOC_GEN_LEASE_SECONDS", 1800),
        max_attempts=await get(MODULE, "DOC_GEN_MAX_ATTEMPTS", 3),
        scan_interval_seconds=await get(MODULE, "DOC_GEN_SCAN_INTERVAL_SECONDS", 30),
        parse_timeout_seconds=await get(MODULE, "DOC_GEN_PARSE_TIMEOUT_SECONDS", 180),
        llm_call_timeout_seconds=await get(MODULE, "DOC_GEN_LLM_CALL_TIMEOUT_SECONDS", 180),
        job_timeout_seconds=await get(MODULE, "DOC_GEN_JOB_TIMEOUT_SECONDS", 2400),
        heartbeat_seconds=await get(MODULE, "DOC_GEN_HEARTBEAT_SECONDS", 60),
        chat_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_CHAT_ENABLED", True),
        chat_max_rounds=await get(MODULE, "DOC_GEN_CHAT_MAX_ROUNDS", 3),
        fallback_model_name=await get_module_setting(MODULE, "DOC_GEN_FALLBACK_MODEL", ""),
        template_model_name=await get_module_setting(MODULE, "DOC_GEN_TEMPLATE_MODEL", ""),
        extract_model_name=await get_module_setting(MODULE, "DOC_GEN_EXTRACT_MODEL", ""),
        write_model_name=await get_module_setting(MODULE, "DOC_GEN_WRITE_MODEL", ""),
        compose_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_COMPOSE_ENABLED", True),
        direct_generation_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_DIRECT_GENERATION_ENABLED", False),
        direct_gen_max_chars=await get(MODULE, "DOC_GEN_DIRECT_GEN_MAX_CHARS", 200000),
        template_analysis_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_TEMPLATE_ANALYSIS_ENABLED", True),
        file_analysis_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_FILE_ANALYSIS_ENABLED", True),
        file_analysis_concurrency=await get(MODULE, "DOC_GEN_FILE_ANALYSIS_CONCURRENCY", 4),
        cross_validation_enabled=await get_module_setting_bool(MODULE, "DOC_GEN_CROSS_VALIDATION_ENABLED", True),
        model_max_input_tokens=await get(MODULE, "DOC_GEN_MODEL_MAX_INPUT_TOKENS", 0),
        output_reserve_tokens=await get(MODULE, "DOC_GEN_OUTPUT_RESERVE_TOKENS", 2048),
        char_per_token=await get_module_setting_float(MODULE, "DOC_GEN_CHAR_PER_TOKEN", 1.6),
        context_water_level=await get_module_setting_float(MODULE, "DOC_GEN_CONTEXT_WATER_LEVEL", 0.6),
    )
