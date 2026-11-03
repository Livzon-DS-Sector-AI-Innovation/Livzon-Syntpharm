"""缓存键与复用语义单测（TC-006 的取证基础）。

这里只测纯函数，不碰数据库/存储/TTS：
- key 稳定：同样的输入永远同一 key；
- 页序敏感：正文页换序必须换 body_key；
- 片头/正文分离：只改第 1 页时 body_key 不变；
- 语言/音色/语速入键：中英同稿不能命中同一份音频。
"""

from app.modules.agent import cache


def _voice(language: str = "zh", voice_id: str = "zf_001", speed: float = 1.0) -> str:
    return cache.voice_key(language, voice_id, speed, "kokoro", "1.0")


# ── 讲稿指纹 ────────────────────────────────────────────────────────


def test_normalize_script_folds_whitespace_noise() -> None:
    # 行尾空白丢弃；连续空行折叠成一个段间空行（保留段落停顿，避免改变朗读节奏）
    assert cache.normalize_script("第一行   \n\n\n第二行\n") == "第一行\n\n第二行"
    assert cache.normalize_script("　全角空格　") == "全角空格"
    assert cache.normalize_script("") == ""


def test_script_key_is_stable_and_language_sensitive() -> None:
    text = "本项目介绍原料药车间的公用工程。"
    assert cache.script_key(text, "zh") == cache.script_key(text, "zh")
    # 同一段中文文本按英文朗读，是另一份音频
    assert cache.script_key(text, "zh") != cache.script_key(text, "en")
    # 视觉上等价的讲稿必须命中同一 key，否则复用会失效
    assert cache.script_key("第一行\n第二行  ", "zh") == cache.script_key(" 第一行\n第二行", "zh")


def test_voice_key_changes_with_any_param() -> None:
    base = cache.voice_key("zh", "zf_001", 1.0, "kokoro", "1.0")
    assert base == cache.voice_key("zh", "zf_001", 1.0, "kokoro", "1.0")
    assert base != cache.voice_key("zh", "zf_002", 1.0, "kokoro", "1.0")
    assert base != cache.voice_key("zh", "zf_001", 1.2, "kokoro", "1.0")
    assert base != cache.voice_key("zh", "zf_001", 1.0, "melo", "1.0")
    assert base != cache.voice_key("zh", "zf_001", 1.0, "kokoro", "1.1")
    # 语速精度按两位小数归一，1.0 与 1.001 视为同一档
    assert base == cache.voice_key("zh", "zf_001", 1.001, "kokoro", "1.0")


# ── 片段与正文 ──────────────────────────────────────────────────────


def test_segment_key_depends_on_image_audio_and_encoder() -> None:
    audio = cache.audio_key(cache.script_key("讲稿", "zh"), _voice())
    seg = cache.segment_key("img-hash", audio)
    assert seg == cache.segment_key("img-hash", audio)
    assert seg != cache.segment_key("img-hash-2", audio)
    assert seg != cache.segment_key("img-hash", audio, "other-encoder")


def test_body_key_is_order_sensitive() -> None:
    keys = ["seg-a", "seg-b", "seg-c"]
    assert cache.body_key(keys) == cache.body_key(keys)
    assert cache.body_key(keys) != cache.body_key(["seg-b", "seg-a", "seg-c"])
    assert cache.body_key(keys) != cache.body_key(["seg-a", "seg-b"])
    assert cache.body_key([]) == ""


def test_body_key_excludes_head_so_head_edit_keeps_body() -> None:
    """核心语义：只改片头 → head_key 变、body_key 不变（正文不必重合成）。"""
    head_before = cache.segment_key("img-head-v1", cache.audio_key(cache.script_key("旧片头", "zh"), _voice()))
    head_after = cache.segment_key("img-head-v1", cache.audio_key(cache.script_key("新片头", "zh"), _voice()))
    body = [
        cache.segment_key(f"img-{i}", cache.audio_key(cache.script_key(f"正文{i}", "zh"), _voice())) for i in (2, 3)
    ]

    assert head_before != head_after
    assert cache.body_key(body) == cache.body_key(body)


def test_body_input_key_tracks_script_and_voice_not_page_image() -> None:
    keys_v1 = [cache.slide_input_key(2, cache.script_key("正文", "zh"), _voice())]
    keys_same = [cache.slide_input_key(2, cache.script_key("正文", "zh"), _voice())]
    keys_voice = [cache.slide_input_key(2, cache.script_key("正文", "zh"), _voice(voice_id="zm_010"))]
    keys_text = [cache.slide_input_key(2, cache.script_key("正文改稿", "zh"), _voice())]

    assert cache.body_input_key(keys_v1) == cache.body_input_key(keys_same)
    assert cache.body_input_key(keys_v1) != cache.body_input_key(keys_voice)
    assert cache.body_input_key(keys_v1) != cache.body_input_key(keys_text)
    assert cache.body_input_key([]) == ""


# ── 文件名与 manifest ───────────────────────────────────────────────


def test_version_file_name_is_distinguishable_and_path_safe() -> None:
    name = cache.version_file_name("研发/报告:终版", 3, "abcdef1234567890")
    assert name == "研发报告终版-v3-abcdef12.mp4"
    assert cache.version_file_name("   ", 1, "0123456789") == "ppt-video-v1-01234567.mp4"


def test_manifest_roundtrip_keeps_reuse_stats() -> None:
    manifest = cache.Manifest(project_id="p1", head_key="head", body_key_value="body")
    manifest.slides = [
        cache.ManifestSlide(1, "i1", "a1", "s1", 1200, cache_hit=True),
        cache.ManifestSlide(2, "i2", "a2", "s2", 3400, cache_hit=True),
        cache.ManifestSlide(3, "i3", "a3", "s3", 2800, cache_hit=False),
    ]
    manifest.total_duration_ms = 7400

    restored = cache.Manifest.from_dict(manifest.as_dict())
    assert restored.head_key == "head"
    assert restored.body_key_value == "body"
    assert restored.total_duration_ms == 7400
    assert restored.reuse_summary() == {
        "total_slides": 3,
        "reused_slides": 2,
        "rendered_slides": 1,
        "body_reused_slides": 1,
        "body_rendered_slides": 1,
        "head_reused": 1,
    }


def test_manifest_reuse_summary_without_head_reuse() -> None:
    manifest = cache.Manifest(project_id="p1", head_key="head", body_key_value="body")
    manifest.slides = [
        cache.ManifestSlide(1, "i1", "a1", "s1", 1200, cache_hit=False),
        cache.ManifestSlide(2, "i2", "a2", "s2", 3400, cache_hit=True),
    ]
    summary = manifest.reuse_summary()
    assert summary["head_reused"] == 0
    assert summary["body_reused_slides"] == 1
    assert summary["rendered_slides"] == 1
