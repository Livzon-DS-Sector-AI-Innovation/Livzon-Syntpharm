"""智能体模块运行时配置。

优先级：数据库模块配置（`module-settings` 页面可改）> 本文件默认值。
默认值刻意写死在这里，保证 worker 在没有模块配置行时也能跑。
"""

from dataclasses import dataclass

from app.shared.config_reader import (
    get_module_setting,
    get_module_setting_bool,
    get_module_setting_int,
)

MODULE_CODE = "agent"

#: 支持的语言码（与 TTS 引擎的 lang_code 无关，后者在 tts.py 内部映射）
SUPPORTED_LANGUAGES: tuple[str, ...] = ("zh", "en")

#: 单页讲稿长度上限（字符），防止误贴整篇文档把 TTS 拖死
MAX_SCRIPT_CHARS = 2000

#: 上传 PPT 大小上限（字节），默认 100MB
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

#: 渲染画布固定 1920×1080，页片段编码参数必须完全一致，才能 `-c copy` 拼接
CANVAS_WIDTH = 1920
CANVAS_HEIGHT = 1080
FRAME_RATE = 30

#: 编码参数指纹：改了任何一项都必须改这个值，否则旧缓存片段会被错误复用。
#: v2：画面从「单张静帧」变为「按句分段的静帧序列」，旧片段必须全部失效。
ENCODER_KEY = "v2-h264-1920x1080-30-yuv420p-aac48000-128k"

#: 讲稿风格指南正文上限（字符），超长会挤占单批 90 秒预算
SCRIPT_GUIDE_MAX_CHARS = 2000

#: 页内视觉引导样式
HIGHLIGHT_STYLE_DIM_OUTLINE = "dim_outline"  # 其余区域压暗 + 目标描边
HIGHLIGHT_STYLE_DIM = "dim"  # 仅压暗
HIGHLIGHT_STYLE_OUTLINE = "outline"  # 仅描边
HIGHLIGHT_STYLES: tuple[str, ...] = (HIGHLIGHT_STYLE_DIM_OUTLINE, HIGHLIGHT_STYLE_DIM, HIGHLIGHT_STYLE_OUTLINE)


@dataclass(frozen=True)
class PptVideoSettings:
    """一次渲染任务用到的全部可调参数。"""

    default_language: str
    default_voice_zh: str
    default_voice_en: str
    default_speed: float
    head_padding_ms: int
    tail_padding_ms: int
    max_slides: int
    job_timeout_seconds: int
    tts_engine: str
    ffmpeg_threads: int
    render_dpi: int
    max_attempts: int
    script_ai_enabled: bool
    script_ai_batch_size: int
    script_ai_timeout_seconds: int
    script_ai_max_page_text_chars: int
    script_ai_config_id: str
    script_ai_global_guide: str
    script_guide_max_chars: int
    highlight_enabled: bool
    highlight_style: str
    highlight_max_steps: int

    def default_voice(self, language: str) -> str:
        return self.default_voice_zh if language == "zh" else self.default_voice_en


DEFAULTS = PptVideoSettings(
    default_language="zh",
    default_voice_zh="zf_001",
    default_voice_en="af_bella",
    default_speed=1.0,
    head_padding_ms=300,
    tail_padding_ms=500,
    max_slides=60,
    job_timeout_seconds=1800,
    tts_engine="kokoro",
    ffmpeg_threads=2,
    render_dpi=150,
    max_attempts=3,
    script_ai_enabled=True,
    # 单批 6 页 + 风格指南容易撞 90 秒硬超时，默认降到 3 页，失败面也更小
    script_ai_batch_size=3,
    script_ai_timeout_seconds=90,
    script_ai_max_page_text_chars=2000,
    script_ai_config_id="",
    script_ai_global_guide="",
    script_guide_max_chars=SCRIPT_GUIDE_MAX_CHARS,
    highlight_enabled=True,
    highlight_style=HIGHLIGHT_STYLE_DIM_OUTLINE,
    highlight_max_steps=6,
)


async def _text(key: str, default: str) -> str:
    return await get_module_setting(MODULE_CODE, key, default)


async def _number(key: str, default: int) -> int:
    return await get_module_setting_int(MODULE_CODE, key, default)


async def _flag(key: str, default: bool) -> bool:
    return await get_module_setting_bool(MODULE_CODE, key, default)


async def load_settings() -> PptVideoSettings:
    """从数据库读取运行时配置，缺省回落到 `DEFAULTS`。"""
    speed_raw = await _text("AGENT_PPT_VIDEO_DEFAULT_SPEED", "")
    try:
        speed = float(speed_raw) if speed_raw else DEFAULTS.default_speed
    except ValueError:
        speed = DEFAULTS.default_speed

    return PptVideoSettings(
        default_language=await _text("AGENT_PPT_VIDEO_DEFAULT_LANGUAGE", DEFAULTS.default_language),
        default_voice_zh=await _text("AGENT_PPT_VIDEO_DEFAULT_VOICE_ZH", DEFAULTS.default_voice_zh),
        default_voice_en=await _text("AGENT_PPT_VIDEO_DEFAULT_VOICE_EN", DEFAULTS.default_voice_en),
        default_speed=min(max(speed, 0.5), 2.0),
        head_padding_ms=await _number("AGENT_PPT_VIDEO_HEAD_PADDING_MS", DEFAULTS.head_padding_ms),
        tail_padding_ms=await _number("AGENT_PPT_VIDEO_TAIL_PADDING_MS", DEFAULTS.tail_padding_ms),
        max_slides=await _number("AGENT_PPT_VIDEO_MAX_SLIDES", DEFAULTS.max_slides),
        job_timeout_seconds=await _number("AGENT_PPT_VIDEO_JOB_TIMEOUT_SECONDS", DEFAULTS.job_timeout_seconds),
        tts_engine=await _text("AGENT_PPT_VIDEO_TTS_ENGINE", DEFAULTS.tts_engine),
        ffmpeg_threads=await _number("AGENT_PPT_VIDEO_FFMPEG_THREADS", DEFAULTS.ffmpeg_threads),
        render_dpi=await _number("AGENT_PPT_VIDEO_RENDER_DPI", DEFAULTS.render_dpi),
        max_attempts=await _number("AGENT_PPT_VIDEO_MAX_ATTEMPTS", DEFAULTS.max_attempts),
        script_ai_enabled=await _flag("AGENT_PPT_VIDEO_SCRIPT_AI_ENABLED", DEFAULTS.script_ai_enabled),
        script_ai_batch_size=max(
            1, min(await _number("AGENT_PPT_VIDEO_SCRIPT_AI_BATCH_SIZE", DEFAULTS.script_ai_batch_size), 20)
        ),
        script_ai_timeout_seconds=max(
            10, await _number("AGENT_PPT_VIDEO_SCRIPT_AI_TIMEOUT_SECONDS", DEFAULTS.script_ai_timeout_seconds)
        ),
        script_ai_max_page_text_chars=max(
            200,
            await _number("AGENT_PPT_VIDEO_SCRIPT_AI_MAX_PAGE_TEXT_CHARS", DEFAULTS.script_ai_max_page_text_chars),
        ),
        script_ai_config_id=await _text("AGENT_PPT_VIDEO_SCRIPT_AI_CONFIG_ID", DEFAULTS.script_ai_config_id),
        script_ai_global_guide=await _text("AGENT_PPT_VIDEO_SCRIPT_AI_GUIDE", DEFAULTS.script_ai_global_guide),
        script_guide_max_chars=max(
            200,
            await _number("AGENT_PPT_VIDEO_SCRIPT_GUIDE_MAX_CHARS", DEFAULTS.script_guide_max_chars),
        ),
        highlight_enabled=await _flag("AGENT_PPT_VIDEO_HIGHLIGHT_ENABLED", DEFAULTS.highlight_enabled),
        highlight_style=await _text("AGENT_PPT_VIDEO_HIGHLIGHT_STYLE", DEFAULTS.highlight_style),
        highlight_max_steps=max(
            1, min(await _number("AGENT_PPT_VIDEO_HIGHLIGHT_MAX_STEPS", DEFAULTS.highlight_max_steps), 12)
        ),
    )
