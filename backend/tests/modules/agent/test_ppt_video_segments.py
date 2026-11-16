"""逐段旁白合成相关单测：WAV 拼接、段级缓存指纹、段落排期。

纯函数与本地文件用例，不连数据库、不连对象存储、不跑真实 TTS。
守两件事：
1. 段间停顿与各段音频时长相加必须等于页面音频时长（否则音画会漂）；
2. 段边界或停顿一变，页音频指纹就必须变，不然会复用旧音频、时间轴对不上。
"""

import uuid
import wave
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core import storage
from app.modules.agent import cache, service, tts
from app.modules.agent.config import DEFAULTS
from app.modules.agent.highlight import ScriptSegment
from app.modules.agent.models import PptVideoSlide

SAMPLE_RATE = 24000


def _write_wav(path: Path, duration_ms: int, sample_rate: int = SAMPLE_RATE) -> Path:
    frames = int(sample_rate * duration_ms / 1000)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        handle.writeframes(b"\x00\x00" * frames)
    return path


# ── WAV 拼接 ──────────────────────────────────────────────────────────────


def test_concat_wavs_inserts_pause_and_reports_duration(tmp_path: Path) -> None:
    first = _write_wav(tmp_path / "a.wav", 500)
    second = _write_wav(tmp_path / "b.wav", 250)

    out, duration_ms = tts.concat_wavs([first, second], tmp_path / "out.wav", pause_ms=200)

    assert duration_ms == pytest.approx(950, abs=2)
    assert tts.wav_duration_ms(out) == pytest.approx(950, abs=2)
    with wave.open(str(out), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getframerate() == SAMPLE_RATE
        assert handle.getnframes() == int(SAMPLE_RATE * 0.95)


def test_concat_wavs_without_pause_keeps_length(tmp_path: Path) -> None:
    first = _write_wav(tmp_path / "a.wav", 400)
    second = _write_wav(tmp_path / "b.wav", 100)

    _, duration_ms = tts.concat_wavs([first, second], tmp_path / "out.wav", pause_ms=0)

    assert duration_ms == pytest.approx(500, abs=2)


def test_concat_wavs_accepts_per_boundary_pauses(tmp_path: Path) -> None:
    """标点分级停顿：每条边界可以用各自的静音长度。"""
    first = _write_wav(tmp_path / "a.wav", 400)
    second = _write_wav(tmp_path / "b.wav", 300)
    third = _write_wav(tmp_path / "c.wav", 200)

    out, duration_ms = tts.concat_wavs([first, second, third], tmp_path / "out.wav", pauses=[120, 300])

    assert duration_ms == pytest.approx(400 + 120 + 300 + 300 + 200, abs=2)
    assert tts.wav_duration_ms(out) == pytest.approx(1320, abs=2)


def test_trim_silence_removes_edges_and_keeps_tone(tmp_path: Path) -> None:
    """各段合成音频自带首尾静音，长度不一；裁剪后段间停顿才可控。"""
    path = tmp_path / "tone.wav"
    sample_rate = SAMPLE_RATE
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        silence = b"\x00\x00" * int(sample_rate * 0.2)
        tone = (1000).to_bytes(2, "little", signed=True) * int(sample_rate * 0.3)
        handle.writeframes(silence + tone + silence)

    duration_ms = tts.trim_silence(path, keep_ms=20)

    # 300ms 有效音频 + 两端各保留 20ms
    assert duration_ms == pytest.approx(340, abs=15)
    assert tts.wav_duration_ms(path) == pytest.approx(duration_ms, abs=2)


def test_concat_wavs_rejects_format_mismatch(tmp_path: Path) -> None:
    first = _write_wav(tmp_path / "a.wav", 300)
    worse = _write_wav(tmp_path / "b.wav", 300, sample_rate=16000)

    with pytest.raises(tts.TtsError):
        tts.concat_wavs([first, worse], tmp_path / "out.wav", pause_ms=100)


def test_concat_wavs_rejects_empty_parts(tmp_path: Path) -> None:
    with pytest.raises(tts.TtsError):
        tts.concat_wavs([], tmp_path / "out.wav", pause_ms=100)


# ── 段级缓存指纹 ──────────────────────────────────────────────────────────


def test_audio_key_variant_separates_segment_variants() -> None:
    base = cache.audio_key("script-sha", "voice-fp")

    assert cache.audio_key("script-sha", "voice-fp", "") == base
    assert cache.audio_key("script-sha", "voice-fp", "segabc") != base


def test_segment_audio_key_ignores_trailing_whitespace_only() -> None:
    same = cache.segment_audio_key("收率提升。\n", "zh", "voice-fp")
    assert same == cache.segment_audio_key("收率提升。", "zh", "voice-fp")
    assert same != cache.segment_audio_key("收率下降。", "zh", "voice-fp")


# ── 段落排期 ──────────────────────────────────────────────────────────────


def test_segment_slots_add_pause_except_last() -> None:
    page_audio = service.PageAudio(
        path=Path("ignored.wav"),
        duration_ms=2200,
        sha256="sha",
        audio_key="key",
        segments=[ScriptSegment("一。"), ScriptSegment("二。"), ScriptSegment("三。")],
        segment_durations_ms=[700, 800, 700],
        pause_ms=180,
    )

    # 段后停顿计入该段占用时长，末段不补停顿
    assert page_audio.segment_slots_ms == [880, 980, 700]
    # 排期总长 = 各段音频 + 段间停顿（末段后没有停顿）
    assert sum(page_audio.segment_slots_ms) == sum(page_audio.segment_durations_ms) + 2 * page_audio.pause_ms
    assert page_audio.segmented is True


def test_page_audio_plan_uses_per_punctuation_pauses() -> None:
    """句末标点决定停顿：逗号短、句号长，未识别标点回落默认值。"""
    settings = replace(DEFAULTS, segment_pause_ms=180, segment_pause_comma_ms=120, segment_pause_period_ms=300)

    assert service.pause_after_segment("第一句，", settings) == 120
    assert service.pause_after_segment("第一句、", settings) == 120
    assert service.pause_after_segment("第一句。", settings) == 300
    assert service.pause_after_segment("第一句？", settings) == 300
    assert service.pause_after_segment("第一句", settings) == 180


def test_page_audio_plan_changes_with_graded_pause() -> None:
    script = "第一句讲收率。第二句讲产线。"
    slide = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout={"width": 12192000, "height": 6858000, "shapes": []},
        script_text=script,
    )
    effective = _effective(script)
    project_on: Any = SimpleNamespace(highlight_override_enabled=True)
    fast = replace(DEFAULTS, segment_pause_period_ms=200)
    slow = replace(DEFAULTS, segment_pause_period_ms=400)

    _, _, fast_key = service.page_audio_plan(slide, effective, fast, project_on)
    _, _, slow_key = service.page_audio_plan(slide, effective, slow, project_on)

    assert fast_key != slow_key


def test_segment_slots_use_graded_pauses() -> None:
    """画面时间轴必须用分级停顿：否则高亮会和实际旁白错位。"""
    page_audio = service.PageAudio(
        path=Path("ignored.wav"),
        duration_ms=2200,
        sha256="sha",
        audio_key="key",
        segments=[ScriptSegment("一，"), ScriptSegment("二。"), ScriptSegment("三")],
        segment_durations_ms=[700, 800, 700],
        segment_pauses_ms=[120, 300],
        pause_ms=180,
    )

    assert page_audio.segment_slots_ms == [820, 1100, 700]


def test_page_audio_plan_uses_segments_when_bound() -> None:
    script = "第一句讲收率。第二句讲产线。"
    slide = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout={
            "width": 12192000,
            "height": 6858000,
            "shapes": [{"text": "收率", "left": 0, "top": 0, "width": 900000, "height": 400000}],
        },
        script_text=script,
        script_segments=[
            {"text": "第一句讲收率。", "targets": ["s0"]},
            {"text": "第二句讲产线。", "targets": []},
        ],
        # 高亮改为项目级为准后，必须至少有一层开关放行才会逐段合成
        highlight_override_enabled=True,
    )
    effective = _effective(script)

    # 音频分段只看项目开关（本页开关只管画面）
    project_on: Any = SimpleNamespace(highlight_override_enabled=True)
    segments, pause_ms, audio_key = service.page_audio_plan(slide, effective, DEFAULTS, project_on)

    assert len(segments) == 2
    assert segments[0].targets == ("s0",)
    assert pause_ms == DEFAULTS.segment_pause_ms
    assert audio_key != cache.audio_key(effective.script_sha256, effective.voice_fingerprint)


def test_page_audio_plan_falls_back_when_disabled_or_single_segment() -> None:
    script = "只有一句话。"
    slide = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout={"width": 12192000, "height": 6858000, "shapes": []},
        script_text=script,
        highlight_override_enabled=True,
    )
    effective = _effective(script)
    base_key = cache.audio_key(effective.script_sha256, effective.voice_fingerprint)

    assert service.page_audio_plan(slide, effective, DEFAULTS) == ([], 0, base_key)
    disabled = replace(DEFAULTS, segment_tts_enabled=False)
    assert service.page_audio_plan(slide, effective, disabled) == ([], 0, base_key)


def test_page_audio_plan_changes_with_pause() -> None:
    script = "第一句讲收率。第二句讲产线。"
    slide = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout={"width": 12192000, "height": 6858000, "shapes": []},
        script_text=script,
        highlight_override_enabled=True,
    )
    effective = _effective(script)
    slower = replace(DEFAULTS, segment_pause_ms=400)
    project_on: Any = SimpleNamespace(highlight_override_enabled=True)

    _, _, fast_key = service.page_audio_plan(slide, effective, DEFAULTS, project_on)
    _, _, slow_key = service.page_audio_plan(slide, effective, slower, project_on)

    assert fast_key != slow_key


def test_page_audio_plan_requires_some_level_enabled() -> None:
    """音频是否分段只看模块总闸与项目开关。

    单页开关只影响画面，不再影响音频：否则同一项目会出现「部分页分段、部分页整页」
    两种合成方式，听感在页与页之间跳变。
    """
    script = "第一句讲收率。第二句讲产线。"
    layout = {"width": 12192000, "height": 6858000, "shapes": []}
    stored_segments = [
        {"text": "第一句讲收率。", "targets": []},
        {"text": "第二句讲产线。", "targets": []},
    ]
    effective = _effective(script)
    base_key = cache.audio_key(effective.script_sha256, effective.voice_fingerprint)
    slide_off = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout=layout,
        script_text=script,
        script_segments=stored_segments,
    )
    slide_on = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout=layout,
        script_text=script,
        script_segments=stored_segments,
        highlight_override_enabled=True,
    )

    project_on: Any = SimpleNamespace(highlight_override_enabled=True)
    project_off: Any = SimpleNamespace(highlight_override_enabled=False)

    # 项目开：本页开关不影响音频，两页都分段
    assert len(service.page_audio_plan(slide_off, effective, DEFAULTS, project_on)[0]) == 2
    assert len(service.page_audio_plan(slide_on, effective, DEFAULTS, project_on)[0]) == 2
    # 项目关：本页单独开也不再分段，指纹与整页口径一致（老缓存继续命中）
    assert service.page_audio_plan(slide_off, effective, DEFAULTS, project_off) == ([], 0, base_key)
    assert service.page_audio_plan(slide_on, effective, DEFAULTS, project_off) == ([], 0, base_key)
    # 模块总闸关 → 即使项目开也不分段
    module_off = replace(DEFAULTS, highlight_enabled=False)
    assert service.page_audio_plan(slide_off, effective, module_off, project_on) == ([], 0, base_key)


def test_page_audio_plan_caps_audio_segments_independently_of_frames() -> None:
    """音频段上限与画面帧上限解耦：帧数保持 6，音频仍按 3 段合成。"""
    script = "".join(f"第{i}句话讲一个要点。" for i in range(1, 9))
    layout = {"width": 12192000, "height": 6858000, "shapes": []}
    stored = [{"text": f"第{i}句话讲一个要点。", "targets": []} for i in range(1, 9)]
    slide = PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout=layout,
        script_text=script,
        script_segments=stored,
    )
    effective = _effective(script)
    project_on: Any = SimpleNamespace(highlight_override_enabled=True)
    tight = replace(DEFAULTS, audio_max_segments=3, highlight_max_steps=6)
    loose = replace(DEFAULTS, audio_max_segments=12, highlight_max_steps=3)

    tight_segments, _, _ = service.page_audio_plan(slide, effective, tight, project_on)
    loose_segments, _, _ = service.page_audio_plan(slide, effective, loose, project_on)

    assert len(tight_segments) == 3
    # 放宽音频段数不受 highlight_max_steps=3 影响
    assert len(loose_segments) == 8


def _effective(script: str) -> service.EffectiveVoice:
    return service.EffectiveVoice(
        language="zh",
        voice_id="zf_xiaoxiao",
        speed=1.0,
        script=script,
        script_sha256="script-sha",
        voice_fingerprint="voice-fp",
        input_key="input-key",
    )


# ── 页音频合成：缓存命中与降级 ──────────────────────────────────────────────


def _page_slide(script: str) -> PptVideoSlide:
    return PptVideoSlide(
        project_id=uuid.uuid4(),
        slide_no=1,
        layout={"width": 12192000, "height": 6858000, "shapes": []},
        script_text=script,
        script_segments=[
            {"text": "第一句讲收率。", "targets": []},
            {"text": "第二句讲产线。", "targets": []},
        ],
        # 逐段合成的前置条件：高亮至少有一层开关放行
        highlight_override_enabled=True,
    )


def _page_project() -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        default_language="zh",
        default_voice_id=DEFAULTS.default_voice_zh,
        speed=1.0,
        tts_engine="kokoro",
        highlight_override_enabled=True,
    )


async def test_prepare_page_audio_reuses_cached_page_audio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """页音频与段时长都命中缓存时不能再调 TTS，否则改一句就重跑整页。"""
    slide = _page_slide("第一句讲收率。第二句讲产线。")
    cached = _write_wav(tmp_path / "merged.wav", 1300)

    def fake_download(object_key: str, target: Path) -> bool:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(cached.read_bytes())
        return True

    def boom(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("命中缓存时不应再调 TTS")

    monkeypatch.setattr(service, "_download_object", fake_download)
    monkeypatch.setattr(service, "_load_segment_durations", lambda key: [600, 700])
    monkeypatch.setattr(tts, "synthesize_to_wav", boom)

    audio = await service.prepare_page_audio(slide, _page_project(), DEFAULTS, "kokoro", "test", tmp_path)

    assert audio.segmented is True
    assert audio.segment_durations_ms == [600, 700]
    assert audio.duration_ms == 1300


async def test_prepare_page_audio_falls_back_when_segment_synthesis_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """段级合成炸了要退回整页单段合成：单页旁白不该把整条视频带崩。"""
    slide = _page_slide("第一句讲收率。第二句讲产线。")
    calls = {"synth": 0}

    def flaky(
        text: str,
        language: str,
        voice_id: str,
        speed: float,
        out_path: Path,
        engine_name: str = "kokoro",
    ) -> tts.SynthResult:
        calls["synth"] += 1
        if calls["synth"] == 1:
            raise tts.TtsError("段级合成失败")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        _write_wav(out_path, 900)
        return tts.SynthResult(path=out_path, duration_ms=900, sample_rate=SAMPLE_RATE, sha256="sha")

    monkeypatch.setattr(service, "_download_object", lambda key, target: False)
    monkeypatch.setattr(service, "_load_segment_durations", lambda key: [])
    monkeypatch.setattr(tts, "synthesize_to_wav", flaky)
    monkeypatch.setattr(storage, "upload_object", lambda *args, **kwargs: "ok")

    audio = await service.prepare_page_audio(slide, _page_project(), DEFAULTS, "kokoro", "test", tmp_path)

    # 段级并发后不再保证「失败即停」：另一段可能已经发出去（次数随并发度变化），
    # 只要求至少跑过段级一次、并且整页兜底确实又合成了一次
    assert calls["synth"] >= 2
    assert audio.segmented is False
    assert audio.segments == []
    assert audio.duration_ms == 900
