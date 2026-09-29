"""Seed initial module runtime settings into the database."""

import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import models to ensure tables are registered
from sqlalchemy import select

from app.core.config_model import ModuleSetting
from app.core.database import async_session_factory
from app.platform.identity.models import User  # noqa: F401

DEFAULT_SETTINGS = [
    # Research module — 文档生成（资料 → 模板 → 初版文档）
    ("research", "DOC_GEN_ENABLED", "true", "bool", "文档生成任务开关"),
    ("research", "DOC_GEN_MAX_FILES", "20", "int", "单次任务最多上传资料文件数"),
    ("research", "DOC_GEN_MAX_TOTAL_PAGES", "150", "int", "单次任务资料总页数上限"),
    ("research", "DOC_GEN_MAX_FILE_MB", "30", "int", "单个资料文件大小上限（MB）"),
    ("research", "DOC_GEN_MAX_TOTAL_MB", "150", "int", "单次任务资料文件合计上限（MB，须 ≤ 前端代理请求体上限）"),
    ("research", "DOC_GEN_BATCH_SIZE", "3", "int", "每次模型调用批量处理的槽位数"),
    ("research", "DOC_GEN_CANDIDATE_LIMIT", "10", "int", "每个槽位送入模型的候选资料块数量"),
    ("research", "DOC_GEN_MAX_CONTEXT_CHARS", "12000", "int", "单次模型调用的资料上下文字符上限"),
    ("research", "DOC_GEN_CONFIDENCE_HIGH", "0.85", "float", "模型置信度高阈值，低于该值的已填充槽位计入低置信度统计"),
    ("research", "DOC_GEN_CONFIDENCE_MID", "0.6", "float", "模型置信度中阈值，低于该值的已填充槽位降级为需人工核对"),
    ("research", "DOC_GEN_MAX_PAGES_PER_FILE", "80", "int", "单个文档最多解析页数"),
    ("research", "DOC_GEN_MAX_OCR_PAGES_PER_FILE", "30", "int", "单个 PDF 最多 OCR 页数（扫描件耗时主要来源）"),
    ("research", "DOC_GEN_MAX_CONCURRENCY", "1", "int", "同时执行的生成任务数（内网模型吞吐有限）"),
    ("research", "DOC_GEN_LEASE_SECONDS", "1800", "int", "任务租约时长，超时后可被重新领取"),
    ("research", "DOC_GEN_MAX_ATTEMPTS", "3", "int", "单个任务的尝试次数上限"),
    ("research", "DOC_GEN_SCAN_INTERVAL_SECONDS", "30", "int", "后台队列扫描间隔"),
    ("research", "DOC_GEN_PARSE_TIMEOUT_SECONDS", "180", "int", "单个资料文件解析硬超时（秒），超时强制终止该文件解析"),
    ("research", "DOC_GEN_LLM_CALL_TIMEOUT_SECONDS", "180", "int", "单次模型调用硬超时（秒），超时按降级处理"),
    ("research", "DOC_GEN_JOB_TIMEOUT_SECONDS", "2400", "int", "单个任务整体硬超时（秒），超时强制终止并标记失败"),
    ("research", "DOC_GEN_HEARTBEAT_SECONDS", "60", "int", "任务租约续租心跳间隔（秒），防止长任务被重复领取"),
    (
        "research",
        "DOC_GEN_CHAT_ENABLED",
        "false",
        "bool",
        "对话复核开关：关（默认）=新建报告即直达生成（提取→成文→渲染）；开=初抽后停待确认并自动建会话",
    ),
    ("research", "DOC_GEN_CHAT_MAX_ROUNDS", "3", "int", "对话补全轮数上限，超过后提示转确认页逐项编辑"),
    ("research", "DOC_GEN_FALLBACK_MODEL", "", "string", "主模型重试仍失败后的备用模型名（为空则不启用）"),
    (
        "research",
        "DOC_GEN_TEMPLATE_MODEL",
        "Qwen3.8-27B",
        "string",
        "模板模型：读模板结构、标注槽位检索词（命中配置即整份切换）",
    ),
    ("research", "DOC_GEN_EXTRACT_MODEL", "Qwen3.8-27B", "string", "提取模型：逐文件提炼 + 按槽位取证"),
    ("research", "DOC_GEN_WRITE_MODEL", "Local-DeepSeek-V4-Flash", "string", "成文模型：确认后润色正文（AI 报告生成）"),
    ("research", "DOC_GEN_COMPOSE_ENABLED", "true", "bool", "成文开关：关闭时渲染直接用人工确认值"),
    ("research", "DOC_GEN_MODEL_MAX_INPUT_TOKENS", "0", "int", "模型输入 token 上限（0=使用固定字符预算）"),
    ("research", "DOC_GEN_OUTPUT_RESERVE_TOKENS", "2048", "int", "模型输出预留 token（从输入预算中扣除）"),
    ("research", "DOC_GEN_CHAR_PER_TOKEN", "1.6", "float", "每 token 对应字符数（中英混合经验值）"),
    ("research", "DOC_GEN_CONTEXT_WATER_LEVEL", "0.6", "float", "上下文水位线（占可用输入比例）"),
    # 性能优化配置
    (
        "research",
        "DOC_GEN_EXTRACT_CONCURRENCY",
        "1",
        "int",
        "提取阶段并发批次数（>1 时多批同时调 LLM，加速但增加网关压力）",
    ),
    ("research", "DOC_GEN_COMPOSE_CONCURRENCY", "1", "int", "成文阶段并发批次数"),
    ("research", "DOC_GEN_PARSE_CONCURRENCY", "1", "int", "解析阶段文件并发数（多文件场景提速）"),
    ("research", "DOC_GEN_EXTRACT_CACHE_ENABLED", "false", "bool", "提取结果缓存开关（重跑时内容未变的槽位直接复用）"),
    ("research", "DOC_GEN_OCR_STRUCTURED_ENABLED", "false", "bool", "解析兜底第二级：快速 OCR 无结果时改用结构化 OCR"),
    ("research", "DOC_GEN_VISION_FALLBACK_ENABLED", "true", "bool", "解析兜底第三级：OCR 无结果时转图交给视觉模型"),
    ("research", "DOC_GEN_VISION_MAX_PAGES", "5", "int", "单文件走视觉模型的最大页数"),
    # 模板分析 / 文件分析 / 交叉校验配置
    (
        "research",
        "DOC_GEN_TEMPLATE_ANALYSIS_ENABLED",
        "true",
        "bool",
        "模板分析开关：用 LLM 解析模板结构，为提取阶段提供槽位指引",
    ),
    (
        "research",
        "DOC_GEN_FILE_ANALYSIS_ENABLED",
        "true",
        "bool",
        "文件分析开关：用 LLM 异步逐文件分析，提取与模板匹配的结构化摘要",
    ),
    ("research", "DOC_GEN_FILE_ANALYSIS_CONCURRENCY", "4", "int", "文件分析并发数（同时分析的文件数）"),
    (
        "research",
        "DOC_GEN_CROSS_VALIDATION_ENABLED",
        "true",
        "bool",
        "交叉校验开关：提取完成后对比文件分析与槽位结果，标记不一致",
    ),
    # 向量检索配置
    ("research", "DOC_GEN_EMBEDDING_MODEL", "", "string", "Embedding 模型名（留空则不启用向量检索）"),
    (
        "research",
        "DOC_GEN_VECTOR_ALPHA",
        "0.6",
        "float",
        "向量检索融合权重（0=纯向量，1=纯关键词，0.6=关键词为主+向量辅助）",
    ),
    (
        "research",
        "DOC_GEN_VECTOR_RETRIEVAL_ENABLED",
        "false",
        "bool",
        "向量检索开关（需同时配置 embedding 模型才生效）",
    ),
    # 项目知识库（RAGFlow）：项目挂知识库后，提取阶段按槽位从知识库召回片段
    (
        "research",
        "DOC_GEN_KB_ENABLED",
        "true",
        "bool",
        "项目知识库检索开关（项目未挂知识库或服务不可用时自动退回本地资料）",
    ),
    ("research", "DOC_GEN_KB_TOP_K", "6", "int", "单个填充项从知识库召回的片段数上限"),
    (
        "research",
        "DOC_GEN_KB_SIMILARITY_THRESHOLD",
        "0.2",
        "float",
        "知识库召回相似度下限，低于该值的片段不进入 prompt",
    ),
    ("research", "DOC_GEN_KB_VECTOR_WEIGHT", "0.3", "float", "知识库混合检索的向量路权重（0=纯关键词，1=纯向量）"),
    ("research", "DOC_GEN_KB_TIMEOUT_SECONDS", "30", "int", "单次知识库召回超时（秒），超时降级为本次不含知识库资料"),
    # 知识库摸底与事实抽取（把整个知识库先榨成结构化事实，填充更完整；增量、可跨任务复用）
    (
        "research",
        "DOC_GEN_KB_SURVEY_ENABLED",
        "true",
        "bool",
        "知识库摸底开关：镜像全库已解析切片到本地索引（增量，为事实抽取打底）",
    ),
    ("research", "DOC_GEN_KB_SURVEY_MAX_CHUNKS", "2000", "int", "单任务镜像切片数硬上限（0=不限，大库分多次任务覆盖）"),
    (
        "research",
        "DOC_GEN_FACT_EXTRACT_ENABLED",
        "true",
        "bool",
        "事实抽取开关：对未抽过的切片批量抽结构化事实（增量，多轮累计覆盖全库）",
    ),
    ("research", "DOC_GEN_FACT_EXTRACT_MAX_CHUNKS", "200", "int", "单任务抽事实的切片数硬上限（0=不限）"),
    ("research", "DOC_GEN_FACT_EXTRACT_BATCH_SIZE", "4", "int", "事实抽取每批送入模型的切片数"),
    (
        "research",
        "DOC_GEN_FACT_RETRIEVAL_ENABLED",
        "true",
        "bool",
        "事实召回开关：填充项优先从本地事实库匹配，无命中再回落实时检索",
    ),
    ("research", "DOC_GEN_FACT_TOP_K", "8", "int", "单个填充项从事实库召回的事实条数上限"),
    ("research", "DOC_GEN_FACT_MIN_CONFIDENCE", "0.4", "float", "事实召回置信度下限，低于该值的事实不参与匹配"),
    # 缺口闭环：对没填上的填充项换一套检索口径定向重试（只跑缺口槽位、只收确有提升的结果）
    (
        "research",
        "DOC_GEN_GAP_RETRY_ENABLED",
        "true",
        "bool",
        "缺口闭环开关：提取完成后对可重试缺口换检索口径再取一次（冲突项与不符合需求描述的取值不重试）",
    ),
    (
        "research",
        "DOC_GEN_GAP_RETRY_ROUNDS",
        "2",
        "int",
        "缺口闭环最大轮数（0=关闭；某轮零提升会提前收手，不会跑满）",
    ),
    (
        "research",
        "DOC_GEN_GAP_RETRY_CANDIDATE_MULTIPLIER",
        "2",
        "int",
        "缺口重试轮的候选块上限倍数（放宽候选才有机会捞到首轮漏掉的资料）",
    ),
    (
        "research",
        "DOC_GEN_GAP_RETRY_CONTEXT_MULTIPLIER",
        "1.5",
        "float",
        "缺口重试轮的上下文预算倍数（缺口槽位少，预算给足才能看到新捞到的候选）",
    ),
    # 知识库覆盖预检：生成前算清「哪些填充项库里根本没料」，随 job.stats 落库供完成页/看板解释缺口
    (
        "research",
        "DOC_GEN_KB_COVERAGE_ENABLED",
        "true",
        "bool",
        "知识库覆盖预检开关：索引刷到最新后离线匹配，输出可填/部分可填/无资料（不调模型、不压知识库）",
    ),
    (
        "research",
        "DOC_GEN_KB_COVERAGE_MAX_CHUNKS",
        "3000",
        "int",
        "覆盖预检参与匹配的索引文本条数上限（结构化事实优先，其次原始切片）",
    ),
    (
        "research",
        "DOC_GEN_KB_COVERAGE_MAX_SLOTS",
        "60",
        "int",
        "覆盖预检实时检索兜底的槽位上限（仅知识库尚无本地索引时生效，避免长尾拖慢接口）",
    ),
    # Safety module
    (
        "safety",
        "SAFETY_AI_TEXT_MODEL",
        "deepseek-v4-flash",
        "string",
        "AI model for text analysis",
    ),
    (
        "safety",
        "SAFETY_AI_VISION_MODEL",
        "qwen-vl-max",
        "string",
        "AI model for image analysis",
    ),
    (
        "safety",
        "SAFETY_FEISHU_BITABLE_APP_TOKEN",
        "",
        "string",
        "Feishu bitable app token for safety module",
    ),
    (
        "safety",
        "SAFETY_FEISHU_BITABLE_HAZARD_TABLE_ID",
        "",
        "string",
        "Feishu bitable hazard table ID",
    ),
    # Equipment module
    (
        "equipment",
        "EQUIPMENT_FEISHU_WS_ENABLED",
        "false",
        "bool",
        "Enable Feishu WebSocket for equipment module",
    ),
    (
        "equipment",
        "MAINTENANCE_PLAN_AUTO_ENABLED",
        "true",
        "bool",
        "Auto-generate maintenance plans",
    ),
    # Energy module
    (
        "energy",
        "ENERGY_AUTO_COLLECT_ENABLED",
        "false",
        "bool",
        "Enable automatic energy data collection",
    ),
    # HR module
    ("hr", "FEISHU_BOT_NAME", "", "string", "Feishu bot name for HR module"),
    ("hr", "AI_MODEL", "kimi-k2.5", "string", "AI model for HR analysis"),
    (
        "hr",
        "AI_SYSTEM_PROMPT",
        "你是「小H」，原料药工厂人事管理助手。只基于查询结果回答人事问题，禁止编造。回答极其简洁，只陈述事实，不分析、不解释、不推理。",
        "string",
        "System prompt for HR AI assistant",
    ),
    # Regulatory tracker module
    (
        "regulatory_tracker",
        "DAILY_SYNC_CRON",
        "0 2 * * *",
        "string",
        "Cron schedule for daily regulatory sync",
    ),
    (
        "regulatory_tracker",
        "CRAWLER_HEADLESS",
        "true",
        "bool",
        "Run crawler in headless mode",
    ),
    (
        "regulatory_tracker",
        "CRAWLER_BROWSERS_PATH",
        "",
        "string",
        "Playwright browsers path (empty = default)",
    ),
    (
        "regulatory_tracker",
        "CDE_GUIDELINE_URL",
        "https://www.cde.org.cn/zdyz/listpage/9cd8db3b7530c6fa0c86485e563f93c7",
        "string",
        "CDE guideline URL to track",
    ),
    # Platform-level AI settings
    (
        "core",
        "AI_VISION_MODEL",
        "gpt-4o",
        "string",
        "Default model for vision tasks",
    ),
    (
        "core",
        "LLM_MODEL",
        "deepseek-chat",
        "string",
        "Default model for LLM text tasks",
    ),
]


async def seed_settings():
    """Seed default module settings into the database."""
    async with async_session_factory() as session:
        # Check which settings already exist
        result = await session.execute(select(ModuleSetting.module, ModuleSetting.key))
        existing = set((row.module, row.key) for row in result.fetchall())

        added = 0
        skipped = 0

        for module, key, value, value_type, description in DEFAULT_SETTINGS:
            if (module, key) in existing:
                skipped += 1
                continue

            setting = ModuleSetting(
                module=module,
                key=key,
                value=value,
                value_type=value_type,
                description=description,
            )
            session.add(setting)
            added += 1

        await session.commit()

        print(f"✓ Seeded {added} new settings, skipped {skipped} existing settings")


if __name__ == "__main__":
    asyncio.run(seed_settings())
