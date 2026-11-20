"""音色目录（voice catalog）。

**只登记已核实的音色**：模型仓库、许可证、声线 ID 均来自 Hugging Face 模型卡与仓库文件清单，
不凭记忆填写。新增音色前必须先在模型仓库里确认同名 `.pt` / voice 文件存在。

核实来源（2026-11 复核）：
- https://hf-mirror.com/hexgrad/Kokoro-82M          （Apache-2.0，英文，voices 见 VOICES.md）
- https://hf-mirror.com/hexgrad/Kokoro-82M-v1.1-zh （Apache-2.0，中英混排，voices/zf_*.pt、zm_*.pt）
"""

from dataclasses import dataclass
from typing import Literal

from app.modules.agent.tts_assets import (
    KOKORO_EN_REPO,
    KOKORO_EN_REVISION,
    KOKORO_LICENSE,
    KOKORO_ZH_REPO,
    KOKORO_ZH_REVISION,
)

Language = Literal["zh", "en"]

__all__ = [
    "KOKORO_EN_REPO",
    "KOKORO_EN_REVISION",
    "KOKORO_LICENSE",
    "KOKORO_SAMPLE_RATE",
    "KOKORO_ZH_REPO",
    "KOKORO_ZH_REVISION",
    "VOICES_BY_ID",
    "VOICE_CATALOG",
    "VoiceDef",
    "get_voice",
    "is_voice_in_language",
    "list_voices",
]

KOKORO_SAMPLE_RATE = 24000


@dataclass(frozen=True)
class VoiceDef:
    """一个可选音色。

    `voice_id` 是引擎内的声线名（Kokoro 即 voices 目录下的文件名去扩展名）。
    """

    voice_id: str
    language: Language
    #: 界面展示名：纯中文、语言内不重复（如「中文女声 · 一号」），不含内部 ID
    display_name: str
    gender: Literal["female", "male"]
    #: 一句中文听感说明，给不懂声线编号的用户看
    description: str
    source: str
    license: str
    version: str
    sample_rate: int = KOKORO_SAMPLE_RATE


#: 目录顺序即前端下拉顺序（zh 在前的，默认语言默认 zh）
VOICE_CATALOG: tuple[VoiceDef, ...] = (
    VoiceDef(
        "zf_001",
        "zh",
        "中文女声 · 一号",
        "female",
        "标准普通话，吐字清晰，适合正式汇报",
        KOKORO_ZH_REPO,
        KOKORO_LICENSE,
        "v1.1-zh",
    ),
    VoiceDef(
        "zf_002",
        "zh",
        "中文女声 · 二号",
        "female",
        "普通话自然，语气平稳，适合通篇讲解",
        KOKORO_ZH_REPO,
        KOKORO_LICENSE,
        "v1.1-zh",
    ),
    VoiceDef(
        "zf_003",
        "zh",
        "中文女声 · 三号",
        "female",
        "普通话柔和，节奏舒缓，适合说明类内容",
        KOKORO_ZH_REPO,
        KOKORO_LICENSE,
        "v1.1-zh",
    ),
    VoiceDef(
        "zf_017",
        "zh",
        "中文女声 · 四号",
        "female",
        "标准普通话，语速适中，适合长段落朗读",
        KOKORO_ZH_REPO,
        KOKORO_LICENSE,
        "v1.1-zh",
    ),
    VoiceDef(
        "zm_010",
        "zh",
        "中文男声 · 一号",
        "male",
        "标准普通话，语气稳重，适合正式场合",
        KOKORO_ZH_REPO,
        KOKORO_LICENSE,
        "v1.1-zh",
    ),
    VoiceDef(
        "af_bella",
        "en",
        "英文女声 · 一号",
        "female",
        "美式发音，语调自然，适合英文汇报",
        KOKORO_EN_REPO,
        KOKORO_LICENSE,
        "v1.0",
    ),
    VoiceDef(
        "bf_emma",
        "en",
        "英文女声 · 二号",
        "female",
        "英式发音，吐字清楚，适合英文讲解",
        KOKORO_EN_REPO,
        KOKORO_LICENSE,
        "v1.0",
    ),
    VoiceDef(
        "am_michael",
        "en",
        "英文男声 · 一号",
        "male",
        "美式发音，语气沉稳，适合英文汇报",
        KOKORO_EN_REPO,
        KOKORO_LICENSE,
        "v1.0",
    ),
    VoiceDef(
        "bm_george",
        "en",
        "英文男声 · 二号",
        "male",
        "英式发音，语气克制，适合英文讲解",
        KOKORO_EN_REPO,
        KOKORO_LICENSE,
        "v1.0",
    ),
)

VOICES_BY_ID: dict[str, VoiceDef] = {voice.voice_id: voice for voice in VOICE_CATALOG}


def list_voices(language: str | None = None) -> list[VoiceDef]:
    """按语言过滤音色；`language` 为空时返回全部。"""
    if not language:
        return list(VOICE_CATALOG)
    return [voice for voice in VOICE_CATALOG if voice.language == language]


def get_voice(voice_id: str) -> VoiceDef | None:
    return VOICES_BY_ID.get(voice_id)


def is_voice_in_language(voice_id: str, language: str) -> bool:
    """音色是否属于该语言（防止中英音色串用导致读音错误）。"""
    voice = VOICES_BY_ID.get(voice_id)
    return voice is not None and voice.language == language
