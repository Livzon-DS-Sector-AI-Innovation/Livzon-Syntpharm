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
    # Agent module / 智能体 - PPT 配音视频
    (
        "agent",
        "AGENT_PPT_VIDEO_DEFAULT_LANGUAGE",
        "zh",
        "string",
        "PPT 配音默认旁白语言（zh/en）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_DEFAULT_VOICE_ZH",
        "zf_001",
        "string",
        "中文默认音色 voice_id",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_DEFAULT_VOICE_EN",
        "af_bella",
        "string",
        "英文默认音色 voice_id",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_DEFAULT_SPEED",
        "1.0",
        "string",
        "默认语速（0.5~2.0）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HEAD_PADDING_MS",
        "300",
        "int",
        "每页旁白前留白毫秒（呼吸间隙）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_TAIL_PADDING_MS",
        "500",
        "int",
        "每页旁白后留白毫秒（呼吸间隙）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_MAX_SLIDES",
        "60",
        "int",
        "单个项目允许的最大页数",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_JOB_TIMEOUT_SECONDS",
        "1800",
        "int",
        "单次渲染任务硬超时秒数",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_TTS_ENGINE",
        "kokoro",
        "string",
        "TTS 引擎（kokoro/melo）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_FFMPEG_THREADS",
        "2",
        "int",
        "ffmpeg 编码线程数（避免与 API 抢 CPU）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_RENDER_DPI",
        "120",
        "int",
        "PDF 转图片的 DPI（影响清晰度与耗时）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_MAX_ATTEMPTS",
        "3",
        "int",
        "渲染任务最大尝试次数",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SCRIPT_AI_ENABLED",
        "true",
        "bool",
        "上传 PPT 后是否自动生成逐页讲稿初稿",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SCRIPT_AI_BATCH_SIZE",
        "6",
        "int",
        "AI 讲稿生成每批页数（一次 LLM 调用）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SCRIPT_AI_TIMEOUT_SECONDS",
        "90",
        "int",
        "AI 讲稿单批调用硬超时秒数",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SCRIPT_AI_MAX_PAGE_TEXT_CHARS",
        "2000",
        "int",
        "喂给模型的单页文字截断长度",
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
