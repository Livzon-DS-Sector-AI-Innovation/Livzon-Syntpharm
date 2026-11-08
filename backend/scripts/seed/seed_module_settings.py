"""Seed initial module runtime settings into the database."""

import asyncio
import os
import sys

from sqlalchemy import select

# 本文件在 scripts/seed/ 下，需上溯三层到 backend/ 才能 import app.*
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# 导入模型确保表已注册（路径补丁必须在 app.* 之前执行）
from app.core.config_model import ModuleSetting  # noqa: E402
from app.core.database import async_session_factory  # noqa: E402
from app.platform.identity.models import User  # noqa: F401,E402

DEFAULT_SETTINGS = [
    # Research module — AI 报告生成（Agent 读母本 / 检索知识库 / 回写 docx）
    ("research", "REPORT_GEN_MODEL", "", "string", "报告生成主模型；可填配置名或模型名，留空用全局默认"),
    ("research", "REPORT_GEN_FALLBACK_MODEL", "", "string", "报告生成兜底模型；可填配置名或模型名，留空不切换"),
    ("research", "REPORT_GEN_STRUCTURE_MODEL", "", "string", "母本结构识别模型；可填配置名或模型名，留空复用主模型"),
    ("research", "REPORT_GEN_DISABLED_TOOLS", "", "string", "停用的 Agent 工具，逗号分隔，空=全启用"),
    ("research", "REPORT_GEN_TOOL_MODE", "auto", "string", "工具协议：auto=先试 tools 再降级 JSON / tools / json"),
    ("research", "REPORT_GEN_MAX_ROUNDS", "16", "int", "Agent 最大轮次上限"),
    ("research", "REPORT_GEN_LLM_TIMEOUT_SECONDS", "180", "int", "单次模型调用超时（秒）"),
    ("research", "REPORT_GEN_TOOL_TIMEOUT_SECONDS", "60", "int", "单个工具执行超时（秒）"),
    ("research", "REPORT_GEN_JOB_TIMEOUT_SECONDS", "2400", "int", "整个生成任务超时（秒）"),
    ("research", "REPORT_GEN_KB_TOP_K", "6", "int", "知识库检索默认返回条数"),
    ("research", "REPORT_GEN_MAX_STEPS", "400", "int", "执行过程步骤数上限（超限只记状态行）"),
    # Research module — 知识库后台富化（切片摸底 / 事实抽取）
    ("research", "DOC_GEN_LLM_CALL_TIMEOUT_SECONDS", "180", "int", "单次模型调用硬超时（秒），超时按降级处理"),
    (
        "research",
        "DOC_GEN_FALLBACK_MODEL",
        "Qwen3.8-27B",
        "string",
        "辅助兜底模型：主模型重试仍失败后切换（强模型兜底）",
    ),
    (
        "research",
        "DOC_GEN_EXTRACT_MODEL",
        "Local-DeepSeek-V4-Flash",
        "string",
        "提取模型：跑量主力（快模型），失败批次由兜底模型重试",
    ),
    # 性能优化配置
    # 模板分析 / 文件分析 / 交叉校验配置
    # 向量检索配置
    # 项目知识库（RAGFlow）：项目挂知识库后，提取阶段按槽位从知识库召回片段
    # 知识库摸底与事实抽取（把整个知识库先榨成结构化事实，填充更完整；增量、可跨任务复用）
    ("research", "DOC_GEN_KB_SURVEY_CONCURRENCY", "4", "int", "摸底并发数（>1 时多文档同时拉取远端切片，写库仍串行）"),
    (
        "research",
        "DOC_GEN_KB_BACKGROUND_ENRICH_ENABLED",
        "true",
        "bool",
        "知识库后台富化开关：空闲时持续补齐切片索引与事实（任务内只做小额增量）",
    ),
    ("research", "DOC_GEN_KB_BACKGROUND_ENRICH_INTERVAL_SECONDS", "30", "int", "后台富化无活可干时的休眠间隔（秒）"),
    (
        "research",
        "DOC_GEN_KB_BACKGROUND_ENRICH_MAX_CHUNKS",
        "200",
        "int",
        "后台单轮抽事实的切片数上限（多轮累计覆盖全库）",
    ),
    ("research", "DOC_GEN_FACT_EXTRACT_BATCH_SIZE", "4", "int", "事实抽取每批送入模型的切片数"),
    (
        "research",
        "DOC_GEN_FACT_EXTRACT_CONCURRENCY",
        "4",
        "int",
        "事实抽取并发批次数（>1 时多批同时调模型，写库仍串行）",
    ),
    # 缺口闭环：对没填上的填充项换一套检索口径定向重试（只跑缺口槽位、只收确有提升的结果）
    # 知识库覆盖预检：生成前算清「哪些填充项库里根本没料」，随 job.stats 落库供完成页/看板解释缺口
    # Identity / 平台账号：飞书首登自动建号时的本地用户名前缀
    # 最终用户名 = 前缀 + 6 位自增号（identity.user_username_seq），如 YTH000001
    (
        "identity",
        "USERNAME_PREFIX",
        "YTH",
        "string",
        "默认本地用户名前缀（飞书首登自动建号）",
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
    (
        "energy",
        "ENERGY_BITABLE_AUTO_SYNC_ENABLED",
        "false",
        "bool",
        "Enable daily Feishu bitable monthly sync",
    ),
    (
        "energy",
        "ENERGY_BITABLE_SYNC_HOUR",
        "17",
        "int",
        "Hour (0-23, CST) of daily Feishu bitable sync",
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
