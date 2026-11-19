"""Seed initial module runtime settings into the database.

两部分职责：

1. ``DEFAULT_SETTINGS`` —— 首次部署时插入缺省配置行（只补缺，不覆盖已有值）；
2. ``SETTING_METADATA`` + ``backfill_metadata()`` —— 幂等回填展示元数据
   （中文名 / 功能域分组 / 是否密钥类 / 取值提示），只 UPDATE 已存在的行，
   不插行、不动 ``value`` 与 ``description``。

元数据放在数据库而不是前端映射表：新增配置项时在同一个地方维护，
界面缺元数据时回退显示 key 并归入「其他」，不会出现第二份业务字典。
"""

import asyncio
import os
import sys

# Add project root (backend/) to path：本文件位于 backend/scripts/seed/ 下，需上溯三层
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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

#: 展示元数据：(module, key) -> (中文名, 功能域分组, 是否密钥类, 取值提示)
#:
#: 分组名保持少而稳定（AI 模型 / 飞书集成 / 功能开关 / 调度任务 / 外部数据源 /
#: 文档生成 / 报告生成 / 通知与提醒 / 账号与身份），避免每个键自造一组。
SETTING_METADATA: dict[tuple[str, str], tuple[str, str, bool, str | None]] = {
    # ── 账号与身份 ──
    ("identity", "USERNAME_PREFIX"): (
        "本地用户名前缀",
        "账号与身份",
        False,
        "字母前缀，最终用户名 = 前缀 + 6 位自增号，如 YTH000001",
    ),
    ("identity", "AUTO_DISABLE_RESIGNED"): (
        "离职自动停用账号",
        "账号与身份",
        False,
        "启用后飞书同步发现离职即停用账号",
    ),
    # ── 安全管理 ──
    ("safety", "SAFETY_AI_TEXT_MODEL"): ("隐患文本分析模型", "AI 模型", False, "模型名或 LLM 配置名"),
    ("safety", "SAFETY_AI_VISION_MODEL"): ("隐患图片识别模型", "AI 模型", False, "需支持视觉输入的模型"),
    ("safety", "SAFETY_FEISHU_BITABLE_APP_TOKEN"): (
        "飞书多维表格 App Token",
        "飞书集成",
        True,
        "飞书多维表格 URL 中 base/ 之后的那段",
    ),
    ("safety", "SAFETY_FEISHU_BITABLE_HAZARD_TABLE_ID"): (
        "隐患台账表 ID",
        "飞书集成",
        False,
        "多维表格 URL 中 table= 之后的 table_id",
    ),
    # ── 设备管理 ──
    ("equipment", "EQUIPMENT_FEISHU_WS_ENABLED"): (
        "飞书长连接",
        "功能开关",
        False,
        "启用后设备模块通过长连接接收飞书事件",
    ),
    ("equipment", "MAINTENANCE_PLAN_AUTO_ENABLED"): (
        "自动生成维护计划",
        "功能开关",
        False,
        "按设备维保周期自动生成计划",
    ),
    # ── 能源管理 ──
    ("energy", "ENERGY_AUTO_COLLECT_ENABLED"): (
        "自动采集能耗数据",
        "功能开关",
        False,
        "启用后按计划从能耗平台拉取",
    ),
    ("energy", "ENERGY_BITABLE_AUTO_SYNC_ENABLED"): (
        "多维表格自动同步",
        "功能开关",
        False,
        "每日把能耗数据同步到飞书多维表格",
    ),
    ("energy", "ENERGY_BITABLE_SYNC_HOUR"): ("同步执行小时", "调度任务", False, "0–23 的整数（北京时间）"),
    # ── 人事管理 ──
    ("hr", "FEISHU_BOT_NAME"): ("人事助手 Bot 名称", "飞书集成", False, "展示在飞书会话与卡片上的名称"),
    ("hr", "AI_MODEL"): ("人事助手模型", "AI 模型", False, "模型名或 LLM 配置名"),
    ("hr", "AI_SYSTEM_PROMPT"): ("人事助手 System Prompt", "AI 模型", False, "整段覆盖，留空使用内置提示词"),
    # ── 法规追踪 ──
    ("regulatory_tracker", "DAILY_SYNC_CRON"): ("每日同步 Cron", "调度任务", False, "cron 表达式，如 0 2 * * *"),
    ("regulatory_tracker", "CRAWLER_HEADLESS"): ("采集器无头模式", "功能开关", False, "服务器上应保持启用"),
    ("regulatory_tracker", "NMPA_CRAWLER_HEADLESS"): ("NMPA 采集无头模式", "功能开关", False, "服务器上应保持启用"),
    ("regulatory_tracker", "NMPA_API_DISCOVERY_MODE"): (
        "NMPA 接口发现方式",
        "外部数据源",
        False,
        "auto / browser 等，留空用默认",
    ),
    ("regulatory_tracker", "CRAWLER_BROWSERS_PATH"): (
        "浏览器内核路径",
        "外部数据源",
        False,
        "Playwright 浏览器目录；留空用默认路径",
    ),
    ("regulatory_tracker", "CDE_GUIDELINE_URL"): ("CDE 指导原则列表页", "外部数据源", False, "需完整 http(s) 地址"),
    # ── 平台默认模型 ──
    ("core", "AI_VISION_MODEL"): ("默认视觉模型", "AI 模型", False, "未单独指定视觉模型时的兜底"),
    ("core", "LLM_MODEL"): ("默认文本模型", "AI 模型", False, "未单独指定文本模型时的兜底"),
    # ── 系统运维 ──
    ("system", "DISABLED_API_ROUTES"): (
        "已禁用的接口路由",
        "功能开关",
        False,
        "JSON 数组，元素为 {method, route, reason}",
    ),
    # ── 质量 · 偏差台账通知 ──
    ("quality-deviation", "NOTIFY"): (
        "偏差通知开关与接收群",
        "通知与提醒",
        False,
        "JSON：enabled / chat_id / events（flow、ai_done、overdue、weekly、gmp_group）",
    ),
    # ── 研发 · 文档生成 ──
    ("research", "DOC_GEN_EXTRACT_MODEL"): ("抽取主模型", "文档生成", False, "跑量用的快模型"),
    ("research", "DOC_GEN_FALLBACK_MODEL"): ("抽取兜底模型", "文档生成", False, "主模型重试仍失败后切换"),
    ("research", "DOC_GEN_FACT_EXTRACT_BATCH_SIZE"): ("事实抽取批大小", "文档生成", False, "每批切片数，≥1 的整数"),
    ("research", "DOC_GEN_FACT_EXTRACT_CONCURRENCY"): ("事实抽取并发", "文档生成", False, "并发批次数，≥1 的整数"),
    ("research", "DOC_GEN_KB_SURVEY_CONCURRENCY"): ("知识库摸底并发", "文档生成", False, "并发文档数，≥1 的整数"),
    ("research", "DOC_GEN_LLM_CALL_TIMEOUT_SECONDS"): ("模型调用超时", "文档生成", False, "秒；超时按降级处理"),
    ("research", "DOC_GEN_KB_BACKGROUND_ENRICH_ENABLED"): (
        "知识库后台富化",
        "文档生成",
        False,
        "空闲时补齐切片索引与事实",
    ),
    ("research", "DOC_GEN_KB_BACKGROUND_ENRICH_INTERVAL_SECONDS"): (
        "后台富化休眠间隔",
        "文档生成",
        False,
        "秒；无活可干时休眠多久",
    ),
    ("research", "DOC_GEN_KB_BACKGROUND_ENRICH_MAX_CHUNKS"): (
        "后台富化单轮切片数",
        "文档生成",
        False,
        "≥1 的整数",
    ),
    # ── 研发 · 报告生成 ──
    ("research", "REPORT_GEN_MODEL"): ("报告生成主模型", "报告生成", False, "配置名或模型名，留空用全局默认"),
    ("research", "REPORT_GEN_FALLBACK_MODEL"): ("报告生成兜底模型", "报告生成", False, "留空不切换"),
    ("research", "REPORT_GEN_STRUCTURE_MODEL"): ("母本结构识别模型", "报告生成", False, "留空复用主模型"),
    ("research", "REPORT_GEN_TOOL_MODE"): ("工具协议模式", "报告生成", False, "auto / tools / json"),
    ("research", "REPORT_GEN_DISABLED_TOOLS"): ("停用的工具", "报告生成", False, "逗号分隔，留空=全启用"),
    ("research", "REPORT_GEN_MAX_ROUNDS"): ("最大轮次", "报告生成", False, "≥1 的整数"),
    ("research", "REPORT_GEN_MAX_STEPS"): ("最大步骤数", "报告生成", False, "≥1 的整数"),
    ("research", "REPORT_GEN_KB_TOP_K"): ("知识库检索条数", "报告生成", False, "≥1 的整数"),
    ("research", "REPORT_GEN_LLM_TIMEOUT_SECONDS"): ("单次调用超时", "报告生成", False, "秒"),
    ("research", "REPORT_GEN_TOOL_TIMEOUT_SECONDS"): ("单工具执行超时", "报告生成", False, "秒"),
    ("research", "REPORT_GEN_JOB_TIMEOUT_SECONDS"): ("任务总超时", "报告生成", False, "秒；建议 600–3600"),
    ("research", "REPORT_GEN_EXAMPLES_ENABLED"): (
        "注入人工修正示例",
        "报告生成",
        False,
        "把人工改过的槽位当 few-shot 示例",
    ),
    ("research", "REPORT_GEN_EXAMPLES_LIMIT"): ("示例条数上限", "报告生成", False, "≥1 的整数"),
    ("research", "REPORT_GEN_AGENT_PROMPT"): (
        "正文生成 Prompt",
        "报告生成",
        False,
        "留空用内置；支持 $drug_name 等变量",
    ),
    ("research", "REPORT_GEN_STRUCTURE_PROMPT"): (
        "结构识别 Prompt",
        "报告生成",
        False,
        "留空用内置；支持 $template_name 等变量",
    ),
    # ── PPT 视频讲稿 ──
    ("agent", "AGENT_PPT_VIDEO_SCRIPT_AI_CONFIG_ID"): (
        "讲稿默认模型配置",
        "视频讲稿",
        False,
        "LLM 配置 id；留空用全局默认",
    ),
    ("agent", "AGENT_PPT_VIDEO_SCRIPT_AI_MODEL"): ("讲稿默认模型名", "视频讲稿", False, "模型名，留空用全局默认"),
    ("agent", "AGENT_PPT_VIDEO_SCRIPT_AI_GUIDE"): (
        "讲稿提示词指南",
        "视频讲稿",
        False,
        "整段覆盖，留空使用内置",
    ),
}

#: 键名后缀启发式：未登记元数据时，按后缀把明显的凭证类配置标为密钥
_SECRET_TOKENS = ("TOKEN", "SECRET", "PASSWORD", "API_KEY", "APP_KEY", "PRIVATE_KEY")


def _guess_secret(key: str) -> bool:
    upper = key.upper()
    return any(token in upper for token in _SECRET_TOKENS)


async def seed_settings():
    """Seed default module settings into the database (missing rows only)."""
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

            meta = SETTING_METADATA.get((module, key))
            setting = ModuleSetting(
                module=module,
                key=key,
                value=value,
                value_type=value_type,
                description=description,
                label=meta[0] if meta else None,
                group_name=meta[1] if meta else None,
                is_secret=meta[2] if meta else _guess_secret(key),
                value_hint=meta[3] if meta else None,
            )
            session.add(setting)
            added += 1

        await session.commit()

        print(f"✓ Seeded {added} new settings, skipped {skipped} existing settings")


async def backfill_metadata() -> None:
    """幂等回填展示元数据。

    只更新已登记的键，且只动 ``label / group_name / is_secret / value_hint``；
    不插行、不覆盖 ``value`` 与 ``description``，可反复执行。
    """
    async with async_session_factory() as session:
        result = await session.execute(select(ModuleSetting).where(~ModuleSetting.is_deleted))
        settings = result.scalars().all()

        updated = 0
        guessed_secret = 0
        for setting in settings:
            meta = SETTING_METADATA.get((setting.module, setting.key))
            if meta is not None:
                label, group_name, is_secret, value_hint = meta
                if (
                    setting.label != label
                    or setting.group_name != group_name
                    or setting.is_secret != is_secret
                    or setting.value_hint != value_hint
                ):
                    setting.label = label
                    setting.group_name = group_name
                    setting.is_secret = is_secret
                    setting.value_hint = value_hint
                    updated += 1
                continue

            # 未登记的键：只做「向更安全方向」的启发式标记，绝不把已标记的密钥改回 false
            if not setting.is_secret and _guess_secret(setting.key):
                setting.is_secret = True
                guessed_secret += 1

        await session.commit()
        print(
            f"✓ Backfilled metadata for {updated} settings, "
            f"guessed {guessed_secret} secret keys, {len(settings)} rows scanned"
        )


async def main() -> None:
    await seed_settings()
    await backfill_metadata()


if __name__ == "__main__":
    asyncio.run(main())
