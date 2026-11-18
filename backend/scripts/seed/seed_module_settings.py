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
    ("research", "REPORT_GEN_DISABLED_TOOLS", "", "string", "停用的 Agent 工具，逗号分隔，空=全启用"),
    ("research", "REPORT_GEN_TOOL_MODE", "auto", "string", "工具协议：auto=先试 tools 再降级 JSON / tools / json"),
    ("research", "REPORT_GEN_MAX_ROUNDS", "30", "int", "Agent 最大轮次上限；可写位置多时 16 轮不够"),
    ("research", "REPORT_GEN_LLM_TIMEOUT_SECONDS", "180", "int", "单次模型调用超时（秒）"),
    ("research", "REPORT_GEN_TOOL_TIMEOUT_SECONDS", "60", "int", "单个工具执行超时（秒）"),
    ("research", "REPORT_GEN_JOB_TIMEOUT_SECONDS", "2400", "int", "整个生成任务超时（秒）"),
    ("research", "REPORT_GEN_KB_TOP_K", "6", "int", "知识库检索默认返回条数"),
    ("research", "REPORT_GEN_MAX_STEPS", "400", "int", "执行过程步骤数上限（超限只记状态行）"),
    ("research", "REPORT_GEN_WRITE_BATCH_LIMIT", "10", "int", "单个写工具一次最多提交几处（10 处/次较平衡）"),
    ("research", "REPORT_GEN_SEARCH_QUERY_LIMIT", "5", "int", "一轮检索最多几组关键词"),
    ("research", "REPORT_GEN_REFERENCES_ENABLED", "true", "bool", "是否在文末自动生成引用源章节"),
    ("research", "REPORT_GEN_JOB_TARGET_SECONDS", "600", "int", "单任务目标时长（秒）；超出只留告警，不中止任务"),
    (
        "research",
        "REPORT_GEN_AGENT_PROMPT",
        "",
        "string",
        "正文生成 system prompt 整段覆盖；留空用内置。变量见 report_gen/prompts.py",
    ),
    (
        "research",
        "REPORT_GEN_OPINION_DIGEST_ENABLED",
        "true",
        "bool",
        "生成前是否把意见库里的历史意见汇总成写作要求（关=回到只拼补充说明）",
    ),
    (
        "research",
        "REPORT_GEN_OPINION_MAX_ITEMS",
        "40",
        "int",
        "生成前汇总最多取几条意见（按被提出次数排序）",
    ),
    (
        "research",
        "REPORT_GEN_OPINION_DIGEST_PROMPT",
        "",
        "string",
        "意见汇总提示词整段覆盖；留空用内置，需保留 {items} 占位符",
    ),
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
        "300",
        "int",
        "每页旁白后留白毫秒（呼吸间隙）；与页内分级停顿量级协调，避免翻页突然停一下",
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
        "1",
        "int",
        "AI 讲稿生成每批页数（一次 LLM 调用）；1 页/批覆盖最全，调大会压缩长页",
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
        "4000",
        "int",
        "喂给模型的单页文字截断长度；太短会让长页后半部分完全没进 prompt",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_ENABLED",
        "true",
        "bool",
        "是否开启页内视觉引导（讲到哪、画面就亮到哪）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_STYLE",
        "text_recolor",
        "string",
        "视觉引导样式（text_recolor 仅文字变色、不画框/dim_outline/dim/outline）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_COLOR",
        "#FF3B30",
        "string",
        "高亮主色 #RRGGBB（文字染色、描边、图片淡色底共用）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_DIM_ALPHA",
        "150",
        "int",
        "非命中区域压暗透明度 0~255（text_recolor 档不压暗）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_OUTLINE_PX",
        "4",
        "int",
        "命中区域描边粗细 0~12 像素，0 表示不描边",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_FILL_ALPHA",
        "28",
        "int",
        "图片/图表命中时的淡色底透明度 0~255（这类元素不做染色）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_RECOLOR_STRENGTH",
        "100",
        "int",
        "文字染色强度 0~100（0 只描边，100 文字完全变主色）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_MAX_STEPS",
        "6",
        "int",
        "单页最多高亮段数（也是单页最多帧数，1~12）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_AUDIO_MAX_SEGMENTS",
        "12",
        "int",
        "单页最多旁白段数（1~20）：比画面帧数多，避免合并后两句连读变快",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SEGMENT_TTS_ENABLED",
        "true",
        "bool",
        "旁白是否逐段合成（关闭后退回整页合成长音频）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SEGMENT_PAUSE_MS",
        "180",
        "int",
        "逐段旁白之间的默认停顿毫秒（未识别标点时用，0~1000）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SEGMENT_PAUSE_COMMA_MS",
        "120",
        "int",
        "逗号/顿号/冒号后的停顿毫秒（0~1000）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SEGMENT_PAUSE_PERIOD_MS",
        "300",
        "int",
        "句号/问号/叹号/分号后的停顿毫秒（0~2000）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_SILENCE_TRIM_MS",
        "60",
        "int",
        "每段合成音频首尾保留的静音毫秒（0~500）；其余静音裁掉，段间停顿改由标点决定",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_MIN_DWELL_MS",
        "700",
        "int",
        "单段高亮最短停留毫秒，过短会并入相邻段（0~5000）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_HIGHLIGHT_TEXT_MATCH_COVERAGE",
        "0.6",
        "string",
        "讲稿未绑定元素时，文字重合度达到多少才高亮（0.2~1.0）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_COVERAGE_ELEMENT_THRESHOLD",
        "0.6",
        "string",
        "覆盖度自检：单个页面元素判为「已讲到」的字面重合率门槛（0.2~1.0）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_COVERAGE_MIN_SCORE",
        "0.75",
        "string",
        "覆盖度自检：页级达标阈值，低于它标记「可能漏讲」（0.1~1.0）",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_PRONUNCIATION_DICT",
        "",
        "string",
        '模块级发音词典 JSON（{"原文": "合成替代文本"}），项目级词条优先；只影响语音合成',
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_PAGE_CONCURRENCY",
        "2",
        "int",
        "渲染时同时处理的页数（1~3）；上调提速但会占用更多 CPU",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_TTS_CONCURRENCY",
        "2",
        "int",
        "同一页内并发合成的旁白段数（1~4）；失败会自动回退整页合成",
    ),
    (
        "agent",
        "AGENT_PPT_VIDEO_PDF_SPLIT_BATCH",
        "8",
        "int",
        "页图拆图每批页数（1~32）；越大进程越少、内存占用越高",
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
