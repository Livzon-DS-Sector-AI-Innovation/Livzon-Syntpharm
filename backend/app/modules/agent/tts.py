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
import wave
from collections.abc import Callable
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
        logger.warning("misaki 英文 G2P 不可用，中文讲稿中的英文缩写将被跳过")
        return None
    try:
        g2p = misaki_en.G2P(trf=False)
    except Exception:  # noqa: BLE001 - 缺 spaCy 模型等运行期问题一律降级
        logger.warning("英文 G2P 初始化失败（多为缺 en_core_web_sm），中文讲稿中的英文缩写将被跳过")
        return None

    def _phonemes(text: str) -> str:
        phonemes = g2p(text)
        return phonemes[0] if isinstance(phonemes, tuple) else str(phonemes)

    return _phonemes


class KokoroEngine:
    """Kokoro-82M：中文用 v1.1-zh 仓库，英文用 v1.0 仓库。"""

    name = "kokoro"

    def __init__(self) -> None:
        self._pipelines: dict[str, object] = {}

    def version(self) -> str:
        try:
            from importlib.metadata import version

            return f"kokoro-{version('kokoro')}"
        except Exception:  # noqa: BLE001 - 版本读不到不影响合成，退化为固定标识
            return "kokoro-unknown"

    def _pipeline(self, language: str) -> object:
        if language in self._pipelines:
            return self._pipelines[language]
        try:
            from kokoro import KPipeline
        except ImportError as exc:
            raise TtsError(
                "当前进程缺少 Kokoro 运行时，无法合成旁白。"
                "试听由 API 进程同步合成，需让后端容器使用含 TTS 依赖的镜像"
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
        try:
            chunks = list(pipeline(text, voice=voice_id, speed=speed))  # type: ignore[operator]
        except Exception as exc:  # noqa: BLE001 - 引擎内部异常类型不稳定
            logger.exception("kokoro synthesize failed")
            raise TtsError(f"旁白合成失败：{exc}") from exc

        samples: list[float] = []
        for chunk in chunks:
            audio = getattr(chunk, "audio", None)
            if audio is None:
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
            logger.exception("melo synthesize failed")
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


def concat_wavs(parts: list[Path], out_path: Path, pause_ms: int = 0) -> tuple[Path, int]:
    """按序拼接 16bit 单声道 PCM WAV，段间插入静音，返回 (路径, 总时长ms)。

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

    silence = b"\x00\x00" * int(sample_rate * max(0, pause_ms) / 1000)
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
            if index and silence:
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
