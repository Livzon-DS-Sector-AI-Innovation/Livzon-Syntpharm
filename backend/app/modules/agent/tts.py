"""本地开源 TTS 适配层（中/英双语）。

选型：默认 **Kokoro-82M**（Apache-2.0）
- 中文：`hexgrad/Kokoro-82M-v1.1-zh`（voices/zf_*.pt、zm_*.pt）
- 英文：`hexgrad/Kokoro-82M`（voices 见模型卡 VOICES.md）
- 均允许商用；纯 CPU 可跑，24kHz 单声道 WAV。

备选：**MeloTTS**（MIT），需 torch，音色数量远少于 Kokoro，仅作为兜底实现保留；
其声线名与 Kokoro 不同，因此二者共用音色目录时按语言映射到该语言的默认说话人。

所有重量级依赖（torch / kokoro / misaki / melo）都在函数内**惰性导入**：通用 API 镜像不装
TTS 依赖也能正常启动（试听接口会返回明确提示），需要用 `backend/Dockerfile.worker`
（依赖清单 `backend/requirements-tts.txt`）构建的镜像才具备合成能力。
"""

import logging
import sys
import wave
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from app.modules.agent.cache import sha256_file
from app.modules.agent.voices import KOKORO_EN_REPO, KOKORO_ZH_REPO, get_voice, is_voice_in_language

logger = logging.getLogger(__name__)


class TtsError(RuntimeError):
    """合成失败，message 直接给用户看。"""


@dataclass(frozen=True)
class SynthResult:
    path: Path
    duration_ms: int
    sample_rate: int
    sha256: str


class TtsEngine(Protocol):
    """引擎契约：给定文本/语言/音色/语速，产出一个 WAV。"""

    name: str

    def version(self) -> str: ...

    def synthesize(self, text: str, language: str, voice_id: str, speed: float, out_path: Path) -> SynthResult: ...


def _write_wav(path: Path, samples: list[float], sample_rate: int) -> int:
    """float32 [-1,1] → 16bit PCM WAV，返回时长(ms)。用标准库写，避免额外音频依赖。"""
    import numpy as np

    array = np.clip(np.asarray(samples, dtype=np.float32), -1.0, 1.0)
    pcm = (array * 32767).astype("<i2")
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm.tobytes())
    return int(len(pcm) / sample_rate * 1000)


def _english_g2p() -> Callable[[str], str] | None:
    """中文讲稿里的英文缩写（GMP/HPLC/API）必须交给英文 G2P，否则会被丢成占位符。

    实测：不加 en_callable 时「本次 GMP 认证涉及 HPLC」里的英文全部变成 `❓`；
    加上之后才会转成 IPA 音素。英文 G2P 依赖 spaCy 的 en_core_web_sm（见
    scripts/ci/install_spacy_en_model.py），拿不到就降级为「跳过英文」，不阻塞中文合成。
    """
    try:
        from misaki import en as misaki_en
    except ImportError:
        logger.warning(
            "misaki 英文 G2P 不可用，中文讲稿中的英文缩写将被跳过",
            extra={"biz_module": "agent", "tts_engine": "kokoro"},
        )
        return None
    try:
        g2p = misaki_en.G2P(trf=False)
    except Exception:  # noqa: BLE001 - 缺 spaCy 模型等运行期问题一律降级
        logger.warning(
            "英文 G2P 初始化失败（多为缺 en_core_web_sm），中文讲稿中的英文缩写将被跳过",
            exc_info=True,
            extra={"biz_module": "agent", "tts_engine": "kokoro"},
        )
        return None

    def _phonemes(text: str) -> str:
        phonemes = g2p(text)
        return phonemes[0] if isinstance(phonemes, tuple) else str(phonemes)

    return _phonemes


#: 单块最大字符数。中文音素约是字数的 2~3 倍（含数字/英文时更高），kokoro 中文分支
#: 对单个 chunk 超过 510 音素会**静默截断**（`ps = ps[:510]`，只打一条 warning 日志），
#: 表现为「旁白只念一半、无任何报错」。120 字 ≈ 300 音素以内，同时给英文 G2P 的
#: 音素膨胀留出余量。
TTS_CHUNK_MAX_CHARS = 120

#: 切块口径版本。它进 `KokoroEngine.version()` → 音频指纹，改了切块逻辑必须同步改这里，
#: 否则旧缓存里被截断的 wav 会继续命中，改了也听不出变化。
KOKORO_CHUNKING_VERSION = "split2"

_SENTENCE_BOUNDARY = "。！？；!?;"
_CLAUSE_BOUNDARY = "，、：,:"


def _split_after(text: str, boundaries: str) -> list[str]:
    """按标点切分并保留标点（标点跟随前一段，避免句末语气丢失）。

    连续标点（`！！！`、`？！`）会并入前一段而不是各自成块：单送一个「！」给 TTS
    既浪费一次推理，也容易被念成怪声。
    """
    parts: list[str] = []
    start = 0
    for index, char in enumerate(text):
        if char not in boundaries:
            continue
        segment = text[start : index + 1]
        if parts and not segment.strip(_SENTENCE_BOUNDARY + _CLAUSE_BOUNDARY):
            parts[-1] += segment
        else:
            parts.append(segment)
        start = index + 1
    if start < len(text):
        parts.append(text[start:])
    return [part for part in parts if part.strip()]


def split_text_for_tts(text: str, max_chars: int = TTS_CHUNK_MAX_CHARS) -> list[str]:
    """把讲稿切成适合逐块送 TTS 的片段（纯函数，结果只取决于入参）。

    优先级：句末标点 → 逗号/顿号等句内标点 → 按 `max_chars` 硬切。
    这样绝大多数切点落在自然停顿上，听感与整段合成一致；硬切只在「整句无标点且
    超长」时发生（人工讲稿极少见），代价是个别字可能被切开，但好过被静默截断。
    """
    limit = max(1, max_chars)
    chunks: list[str] = []
    for sentence in _split_after(text, _SENTENCE_BOUNDARY):
        if len(sentence) <= limit:
            chunks.append(sentence)
            continue
        buffer = ""
        for clause in _split_after(sentence, _CLAUSE_BOUNDARY):
            if len(clause) > limit:
                if buffer:
                    chunks.append(buffer)
                    buffer = ""
                chunks.extend(clause[offset : offset + limit] for offset in range(0, len(clause), limit))
                continue
            if len(buffer) + len(clause) > limit:
                chunks.append(buffer)
                buffer = clause
            else:
                buffer += clause
        if buffer:
            chunks.append(buffer)
    return [chunk.strip() for chunk in chunks if chunk.strip()]


class KokoroEngine:
    """Kokoro-82M：中文用 v1.1-zh 仓库，英文用 v1.0 仓库。"""

    name = "kokoro"

    def __init__(self) -> None:
        self._pipelines: dict[str, object] = {}

    def version(self) -> str:
        try:
            from importlib.metadata import version

            return f"kokoro-{version('kokoro')}-{KOKORO_CHUNKING_VERSION}"
        except Exception:  # noqa: BLE001 - 版本读不到不影响合成，退化为固定标识
            # 版本串进音频指纹：静默降级会让「缓存为何全量失效」无从排查，必须留日志
            logger.warning(
                "读取 kokoro 版本失败，退化为固定标识: %s",
                KOKORO_CHUNKING_VERSION,
                exc_info=True,
                extra={"biz_module": "agent", "tts_engine": "kokoro"},
            )
            return f"kokoro-unknown-{KOKORO_CHUNKING_VERSION}"

    def _pipeline(self, language: str) -> object:
        if language in self._pipelines:
            return self._pipelines[language]
        try:
            from kokoro import KPipeline
        except ImportError as exc:
            raise TtsError(
                "当前进程缺少 Kokoro 运行时，无法合成旁白。"
                "试听与成片均由 worker 容器合成，需让 worker 使用含 TTS 依赖的镜像"
                "（backend/Dockerfile.worker，依赖见 backend/requirements-tts.txt，"
                "本机可直接用 docker-compose.dev.yml 覆盖，它会复用 worker 镜像），改后重试。"
            ) from exc

        if language == "zh":
            pipeline = KPipeline(lang_code="z", repo_id=KOKORO_ZH_REPO, en_callable=_english_g2p())
        else:
            pipeline = KPipeline(lang_code="a", repo_id=KOKORO_EN_REPO)
        self._pipelines[language] = pipeline
        return pipeline

    def synthesize(self, text: str, language: str, voice_id: str, speed: float, out_path: Path) -> SynthResult:
        voice = get_voice(voice_id)
        if voice is None or not is_voice_in_language(voice_id, language):
            raise TtsError(f"音色 {voice_id} 不属于语言 {language}，请重新选择")
        pipeline = self._pipeline(language)
        # 必须自己切块：KPipeline 默认只按换行切（`split_pattern="\n+"`），中文讲稿通常
        # 一整段没有换行，189 字就会成为单个 chunk（≈572 音素）并被静默截断到 510。
        blocks = split_text_for_tts(text)
        samples: list[float] = []
        for index, block in enumerate(blocks, start=1):
            try:
                chunks = list(pipeline(block, voice=voice_id, speed=speed))  # type: ignore[operator]
            except Exception as exc:  # noqa: BLE001 - 引擎内部异常类型不稳定
                logger.exception(
                    "kokoro synthesize failed: block %s/%s",
                    index,
                    len(blocks),
                    extra={
                        "biz_module": "agent",
                        "tts_engine": "kokoro",
                        "language": language,
                        "voice_id": voice_id,
                        "block_index": index,
                        "block_total": len(blocks),
                    },
                )
                raise TtsError(f"旁白合成失败（第 {index}/{len(blocks)} 块）：{exc}") from exc
            for chunk in chunks:
                audio = getattr(chunk, "audio", None)
                if audio is None:
                    # 空块静默跳过会让该段讲稿无声消失（与 #244 同症状），必须留痕
                    logger.warning(
                        "引擎返回空音频块，已跳过: block=%s/%s",
                        index,
                        len(blocks),
                        extra={
                            "biz_module": "agent",
                            "tts_engine": "kokoro",
                            "language": language,
                            "voice_id": voice_id,
                            "block_index": index,
                        },
                    )
                    continue
                samples.extend(audio.detach().cpu().numpy().tolist() if hasattr(audio, "detach") else list(audio))
        if not samples:
            raise TtsError("旁白合成失败：引擎未返回音频，请检查讲稿是否为空")

        duration_ms = _write_wav(out_path, samples, voice.sample_rate)
        return SynthResult(out_path, duration_ms, voice.sample_rate, sha256_file(out_path))


class MeloEngine:
    """MeloTTS（MIT）兜底实现：按语言取默认说话人。"""

    name = "melo"

    _DEFAULT_SPEAKER = {"zh": "ZH", "en": "EN-US"}

    def __init__(self) -> None:
        self._models: dict[str, object] = {}

    def version(self) -> str:
        try:
            from importlib.metadata import version

            return f"melo-{version('melotts')}"
        except Exception:  # noqa: BLE001
            logger.warning(
                "读取 melotts 版本失败，退化为固定标识",
                exc_info=True,
                extra={"biz_module": "agent", "tts_engine": "melo"},
            )
            return "melo-unknown"

    def _model(self, language: str) -> object:
        if language in self._models:
            return self._models[language]
        try:
            from melo.api import TTS
        except ImportError as exc:
            raise TtsError("服务器未安装 MeloTTS 运行时，无法合成旁白") from exc
        model = TTS(language="ZH" if language == "zh" else "EN", device="cpu")
        self._models[language] = model
        return model

    def synthesize(self, text: str, language: str, voice_id: str, speed: float, out_path: Path) -> SynthResult:
        model = self._model(language)
        speaker_key = self._DEFAULT_SPEAKER.get(language, "EN-US")
        try:
            speaker_id = model.hps.data.spk2id[speaker_key]  # type: ignore[attr-defined]
            model.tts_to_file(text, speaker_id, str(out_path), speed=speed)  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "melo synthesize failed",
                extra={
                    "biz_module": "agent",
                    "tts_engine": "melo",
                    "language": language,
                    "voice_id": voice_id,
                },
            )
            raise TtsError(f"旁白合成失败：{exc}") from exc

        rate = 44100
        with wave.open(str(out_path), "rb") as handle:
            rate = handle.getframerate()
            frames = handle.getnframes()
        duration_ms = int(frames / rate * 1000)
        return SynthResult(out_path, duration_ms, rate, sha256_file(out_path))


_ENGINES: dict[str, TtsEngine] = {}


def get_engine(name: str = "kokoro") -> TtsEngine:
    """按名称取引擎单例（进程内缓存，模型只加载一次）。"""
    key = (name or "kokoro").lower()
    if key not in _ENGINES:
        if key == "melo":
            _ENGINES[key] = MeloEngine()
        elif key == "kokoro":
            _ENGINES[key] = KokoroEngine()
        else:
            raise TtsError(f"未知的 TTS 引擎：{name}")
    return _ENGINES[key]


def synthesize_to_wav(
    text: str,
    language: str,
    voice_id: str,
    speed: float,
    out_path: Path,
    engine_name: str = "kokoro",
) -> SynthResult:
    """合成一段旁白到 WAV。`text` 为空时抛 TtsError（调用方应提前跳过空页）。"""
    if not (text or "").strip():
        raise TtsError("讲稿为空，无法合成旁白")
    if not 0.5 <= speed <= 2.0:
        raise TtsError("语速需在 0.5~2.0 之间")
    return get_engine(engine_name).synthesize(text.strip(), language, voice_id, speed, out_path)


#: 判定为静音的采样绝对值阈值（16bit）：低于它的样本视为底噪
SILENCE_THRESHOLD = 200


def trim_silence(path: str | Path, keep_ms: int = 60, threshold: int = SILENCE_THRESHOLD) -> int:
    """裁掉一段 WAV 的首尾静音，两端各保留 `keep_ms`，返回裁剪后时长(ms)。

    引擎每段输出的首尾静音长度不一，直接拼会让段间停顿忽长忽短；
    先裁到统一余量，再由 `concat_wavs` 按标点补停顿，节奏才可控。
    """
    import array

    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sampwidth = handle.getsampwidth()
        rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if sampwidth != 2 or not frames:
        return int(len(frames) / (rate * max(1, sampwidth) * max(1, channels)) * 1000)

    samples = array.array("h")
    samples.frombytes(frames[: len(frames) - (len(frames) % 2)])
    if sys.byteorder == "big":
        samples.byteswap()

    total = len(samples)
    first = 0
    while first < total and abs(samples[first]) <= threshold:
        first += 1
    if first >= total:
        # 全静音：保留一帧，避免产出 0 长度 WAV
        first, last = 0, 1
    else:
        last = total
        while last > first and abs(samples[last - 1]) <= threshold:
            last -= 1

    keep = int(rate * max(0, keep_ms) / 1000)
    start = max(0, first - keep)
    end = min(total, last + keep)
    trimmed = samples[start:end]

    if sys.byteorder == "big":
        trimmed.byteswap()
    with wave.open(str(path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sampwidth)
        out.setframerate(rate)
        out.writeframes(trimmed.tobytes())
    return int(len(trimmed) / rate * 1000)


def concat_wavs(
    parts: list[Path],
    out_path: Path,
    pause_ms: int = 0,
    pauses: Sequence[int] | None = None,
) -> tuple[Path, int]:
    """按序拼接 16bit 单声道 PCM WAV，段间插入静音，返回 (路径, 总时长ms)。

    `pauses` 给出每条边界的静音长度（按上一段尾标点分级），优先于统一的 `pause_ms`；
    缺省或长度不足的位置回落到 `pause_ms`。

    格式不一致（换过引擎/采样率不同）直接抛 `TtsError`，由上层退回整页合成；
    宁可多合成一次，也不能拼出一段采样率错乱的音频把整条视频带坏。
    """
    if not parts:
        raise TtsError("没有可拼接的音频片段")
    with wave.open(str(parts[0]), "rb") as first:
        sample_rate = first.getframerate()
        channels = first.getnchannels()
        sampwidth = first.getsampwidth()
    if channels != 1 or sampwidth != 2:
        raise TtsError(f"不支持的音频格式：{channels} 声道 / {sampwidth * 8} bit")

    boundaries = len(parts) - 1
    if pauses is None:
        gaps = [max(0, int(pause_ms))] * boundaries
    else:
        gaps = [
            max(0, int(pauses[index])) if index < len(pauses) else max(0, int(pause_ms)) for index in range(boundaries)
        ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    total_frames = 0
    with wave.open(str(out_path), "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        for index, part in enumerate(parts):
            with wave.open(str(part), "rb") as source:
                if source.getnchannels() != 1 or source.getsampwidth() != 2 or source.getframerate() != sample_rate:
                    raise TtsError("音频片段格式不一致，无法拼接")
                data = source.readframes(source.getnframes())
            if index and gaps[index - 1]:
                silence = b"\x00\x00" * int(sample_rate * gaps[index - 1] / 1000)
                target.writeframes(silence)
                total_frames += len(silence) // 2
            target.writeframes(data)
            total_frames += len(data) // 2
    return out_path, int(total_frames / sample_rate * 1000)


def wav_duration_ms(path: Path) -> int:
    """读 WAV 头算时长（不加载音频数据）。"""
    with wave.open(str(path), "rb") as handle:
        frames = handle.getnframes()
        rate = handle.getframerate() or 1
    return int(frames / rate * 1000)
