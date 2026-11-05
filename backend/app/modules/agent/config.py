"""智能体模块运行时配置。

优先级：数据库模块配置（`module-settings` 页面可改）> 本文件默认值。
默认值刻意写死在这里，保证 worker 在没有模块配置行时也能跑。
"""

import re
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
HIGHLIGHT_STYLE_TEXT_RECOLOR = "text_recolor"  # 讲到的文字变主色，背景不动；不画框（图片/图表只加淡色底）
HIGHLIGHT_STYLE_DIM_OUTLINE = "dim_outline"  # 其余区域压暗 + 目标描边
HIGHLIGHT_STYLE_DIM = "dim"  # 仅压暗
HIGHLIGHT_STYLE_OUTLINE = "outline"  # 仅描边
HIGHLIGHT_STYLES: tuple[str, ...] = (
    HIGHLIGHT_STYLE_TEXT_RECOLOR,
    HIGHLIGHT_STYLE_DIM_OUTLINE,
    HIGHLIGHT_STYLE_DIM,
    HIGHLIGHT_STYLE_OUTLINE,
)

#: 高亮主色：文字染色、描边、淡色底都用它
DEFAULT_HIGHLIGHT_COLOR = "#FF3B30"
_HEX_COLOR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")


def normalize_hex_color(value: str, default: str = DEFAULT_HIGHLIGHT_COLOR) -> str:
    """把用户输入归一成 `#RRGGBB`；不合法一律回落默认色，不让坏值进渲染。"""
    match = _HEX_COLOR_RE.match(str(value or "").strip())
    return f"#{match.group(1).upper()}" if match else default


def normalize_highlight_style(value: str, default: str = HIGHLIGHT_STYLE_TEXT_RECOLOR) -> str:
    """未知样式（手工写错、老版本遗留）回落默认档，避免渲染分支走到未定义状态。"""
    style = str(value or "").strip()
    return style if style in HIGHLIGHT_STYLES else default


def parse_hex_color(value: str, default: tuple[int, int, int] = (255, 59, 48)) -> tuple[int, int, int]:
    match = _HEX_COLOR_RE.match(str(value or "").strip())
    if not match:
        return default
    digits = match.group(1)
    return (int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16))


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
    #: 页级流水线并发（1-3）：本页出帧时先备好下一页的语音。默认 2，按「共用机器只吃 2-3 核」定
    page_concurrency: int
    #: 同页内多段语音合成并发（1-4）：TTS 是网络等待，不占本机 CPU
    tts_concurrency: int
    #: 拆图每批页数：一次 pdftoppm 出 N 页，兼顾进程次数与峰值内存
    pdf_split_batch: int
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
    #: 主色（#RRGGBB）：文字染色 / 描边 / 淡色底共用
    highlight_color: str
    #: 非命中区域压暗透明度（0 不压暗，255 全黑）
    highlight_dim_alpha: int
    highlight_outline_px: int
    #: 图片/图表命中时的淡色底透明度（不做染色，避免整块变红剪影）
    highlight_fill_alpha: int
    #: 文字染色强度（0 不染色，100 完全换成主色）
    highlight_recolor_strength: int
    highlight_max_steps: int
    #: 逐段合成旁白：高亮时间轴 = 各段音频实测时长；关掉则退回整页单段与估算
    segment_tts_enabled: bool
    segment_pause_ms: int
    highlight_min_dwell_ms: int
    highlight_text_match_coverage: float

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
    page_concurrency=2,
    tts_concurrency=2,
    pdf_split_batch=8,
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
    # 用户要的默认效果：讲到的文字变红，背景不动
    highlight_style=HIGHLIGHT_STYLE_TEXT_RECOLOR,
    highlight_color=DEFAULT_HIGHLIGHT_COLOR,
    highlight_dim_alpha=150,
    highlight_outline_px=4,
    highlight_fill_alpha=28,
    highlight_recolor_strength=100,
    highlight_max_steps=6,
    segment_tts_enabled=True,
    # 180ms 是「句间自然换气」的下限；再大就会显得旁白在卡顿
    segment_pause_ms=180,
    # 一段不足 0.7 秒观众来不及看清，直接并入相邻段，避免画面高频闪烁
    highlight_min_dwell_ms=700,
    highlight_text_match_coverage=0.6,
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

    coverage_raw = await _text("AGENT_PPT_VIDEO_HIGHLIGHT_TEXT_MATCH_COVERAGE", "")
    try:
        coverage = float(coverage_raw) if coverage_raw else DEFAULTS.highlight_text_match_coverage
    except ValueError:
        coverage = DEFAULTS.highlight_text_match_coverage

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
        # 上限夹到 3：本机是共用服务器，页级并发再高会抢掉别人的核
        page_concurrency=max(1, min(await _number("AGENT_PPT_VIDEO_PAGE_CONCURRENCY", DEFAULTS.page_concurrency), 3)),
        tts_concurrency=max(1, min(await _number("AGENT_PPT_VIDEO_TTS_CONCURRENCY", DEFAULTS.tts_concurrency), 4)),
        pdf_split_batch=max(1, min(await _number("AGENT_PPT_VIDEO_PDF_SPLIT_BATCH", DEFAULTS.pdf_split_batch), 32)),
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
        highlight_style=normalize_highlight_style(
            await _text("AGENT_PPT_VIDEO_HIGHLIGHT_STYLE", DEFAULTS.highlight_style), DEFAULTS.highlight_style
        ),
        highlight_color=normalize_hex_color(
            await _text("AGENT_PPT_VIDEO_HIGHLIGHT_COLOR", DEFAULTS.highlight_color), DEFAULTS.highlight_color
        ),
        highlight_dim_alpha=min(
            max(await _number("AGENT_PPT_VIDEO_HIGHLIGHT_DIM_ALPHA", DEFAULTS.highlight_dim_alpha), 0), 255
        ),
        highlight_outline_px=min(
            max(await _number("AGENT_PPT_VIDEO_HIGHLIGHT_OUTLINE_PX", DEFAULTS.highlight_outline_px), 0), 12
        ),
        highlight_fill_alpha=min(
            max(await _number("AGENT_PPT_VIDEO_HIGHLIGHT_FILL_ALPHA", DEFAULTS.highlight_fill_alpha), 0), 255
        ),
        highlight_recolor_strength=min(
            max(
                await _number("AGENT_PPT_VIDEO_HIGHLIGHT_RECOLOR_STRENGTH", DEFAULTS.highlight_recolor_strength),
                0,
            ),
            100,
        ),
        highlight_max_steps=max(
            1, min(await _number("AGENT_PPT_VIDEO_HIGHLIGHT_MAX_STEPS", DEFAULTS.highlight_max_steps), 12)
        ),
        segment_tts_enabled=await _flag("AGENT_PPT_VIDEO_SEGMENT_TTS_ENABLED", DEFAULTS.segment_tts_enabled),
        segment_pause_ms=max(
            0, min(await _number("AGENT_PPT_VIDEO_SEGMENT_PAUSE_MS", DEFAULTS.segment_pause_ms), 1000)
        ),
        highlight_min_dwell_ms=max(
            0,
            min(
                await _number("AGENT_PPT_VIDEO_HIGHLIGHT_MIN_DWELL_MS", DEFAULTS.highlight_min_dwell_ms),
                5000,
            ),
        ),
        highlight_text_match_coverage=min(max(coverage, 0.2), 1.0),
    )
