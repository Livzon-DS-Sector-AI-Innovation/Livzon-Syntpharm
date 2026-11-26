"""TTS 切块与逐块合成的单测（#244）。

不加载真实模型：把 `KokoroEngine._pipelines[...]` 换成假 pipeline，只验证切块口径、
调用顺序与样本拼接；真实音质由人工听感验收（见 issue #244 的实例页）。
"""

from pathlib import Path

import pytest

from app.modules.agent import tts

#: 假 pipeline 每块产出的样本数（2400 @ 24kHz = 100ms，便于断言时长）
SAMPLES_PER_BLOCK = 2400


class _Voice:
    sample_rate = 24000


class _Chunk:
    def __init__(self, audio: list[float]) -> None:
        self.audio = audio


def _install_fake_pipeline(monkeypatch: pytest.MonkeyPatch, engine: tts.KokoroEngine) -> list[str]:
    """替换 pipeline / 音色查询 / 写盘，返回记录调用入参的列表。"""
    calls: list[str] = []

    def _pipeline(text: str, voice: str = "", speed: float = 1.0) -> list[_Chunk]:
        calls.append(text)
        # 用「第几次调用」当样本值，方便断言拼接顺序
        return [_Chunk([float(len(calls))] * SAMPLES_PER_BLOCK)]

    engine._pipelines["zh"] = _pipeline
    monkeypatch.setattr(tts, "get_voice", lambda voice_id: _Voice())
    monkeypatch.setattr(tts, "is_voice_in_language", lambda voice_id, language: True)
    return calls


def _install_writer(monkeypatch: pytest.MonkeyPatch, captured: dict[str, list[float]]) -> None:
    def _write(path: Path, samples: list[float], sample_rate: int) -> int:
        captured["samples"] = list(samples)
        Path(path).write_bytes(b"RIFF")  # sha256_file 需要文件真实存在
        return int(len(samples) / sample_rate * 1000)

    monkeypatch.setattr(tts, "_write_wav", _write)


# ── 切块口径 ────────────────────────────────────────────────────────────────


def test_split_keeps_short_text_in_one_block() -> None:
    assert tts.split_text_for_tts("丽珠集团简介。") == ["丽珠集团简介。"]


def test_split_prefers_sentence_boundaries() -> None:
    assert tts.split_text_for_tts("第一句。第二句！第三句？") == ["第一句。", "第二句！", "第三句？"]


def test_split_merges_repeated_punctuation() -> None:
    """`！！！` 不能各自成块：单独送一个「！」既浪费推理也容易念怪。"""
    blocks = tts.split_text_for_tts("真的很好！！！下一句。")

    assert blocks == ["真的很好！！！", "下一句。"]


def test_split_breaks_long_sentence_on_clauses() -> None:
    clause = "这是一段没有句号的很长的说明文字，"
    text = (clause * 10).rstrip("，") + "。"

    blocks = tts.split_text_for_tts(text)

    assert len(blocks) > 1
    assert all(len(block) <= tts.TTS_CHUNK_MAX_CHARS for block in blocks)
    assert "".join(blocks) == text


def test_split_hard_breaks_unpunctuated_text() -> None:
    text = "无标点" * 100  # 300 字，无任何标点

    blocks = tts.split_text_for_tts(text)

    assert len(blocks) == 3
    assert all(len(block) <= tts.TTS_CHUNK_MAX_CHARS for block in blocks)
    assert "".join(blocks) == text


def test_split_handles_mixed_language() -> None:
    text = "本次 GMP 认证涉及 HPLC 与 API。下一句。"

    blocks = tts.split_text_for_tts(text)

    assert "".join(blocks) == text
    assert blocks[0] == "本次 GMP 认证涉及 HPLC 与 API。"


# ── 逐块合成 ────────────────────────────────────────────────────────────────


def test_synthesize_calls_pipeline_per_block(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = tts.KokoroEngine()
    calls = _install_fake_pipeline(monkeypatch, engine)
    captured: dict[str, list[float]] = {}
    _install_writer(monkeypatch, captured)
    # 20 句 × 11 字 = 220 字，超过 510 音素的经验阈值
    text = "第一句话讲清楚了背景。" * 20

    result = engine.synthesize(text, "zh", "zf_001", 1.0, tmp_path / "out.wav")

    assert len(calls) > 1
    assert "".join(calls) == text
    assert all(len(call) <= tts.TTS_CHUNK_MAX_CHARS for call in calls)

    samples = captured["samples"]
    assert len(samples) == SAMPLES_PER_BLOCK * len(calls)
    for index in range(len(calls)):
        assert samples[index * SAMPLES_PER_BLOCK] == float(index + 1)
    assert result.duration_ms == int(len(samples) / 24000 * 1000)


def test_synthesize_short_text_calls_pipeline_once(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = tts.KokoroEngine()
    calls = _install_fake_pipeline(monkeypatch, engine)
    _install_writer(monkeypatch, {})

    result = engine.synthesize("短句。", "zh", "zf_001", 1.0, tmp_path / "short.wav")

    assert calls == ["短句。"]
    assert result.duration_ms == int(SAMPLES_PER_BLOCK / 24000 * 1000)


def test_version_carries_chunking_suffix() -> None:
    """切块口径必须进引擎版本，否则旧截断缓存会继续命中。"""
    assert tts.KokoroEngine().version().endswith("-split2")
