"""发音词典单测：清洗、合并优先级、单遍替换与缓存指纹。"""

from app.modules.agent import cache, pronunciation


def test_normalize_entries_drops_blank_and_identical() -> None:
    entries = pronunciation.normalize_entries(
        {
            " 重楼 ": " 崇楼 ",
            "空值": "",
            "  ": "无原文",
            "相同": "相同",
            "过长" * 20: "目标",
        }
    )

    assert entries == {"重楼": "崇楼"}


def test_normalize_entries_caps_count() -> None:
    raw = {f"词{i}": f"替换{i}" for i in range(pronunciation.MAX_ENTRIES + 20)}

    assert len(pronunciation.normalize_entries(raw)) == pronunciation.MAX_ENTRIES


def test_parse_module_dict_ignores_bad_json() -> None:
    assert pronunciation.parse_module_dict("{not json") == {}
    assert pronunciation.parse_module_dict('["a"]') == {}
    assert pronunciation.parse_module_dict('{"重楼": "崇楼"}') == {"重楼": "崇楼"}


def test_build_prefers_project_entries() -> None:
    lexicon = pronunciation.build('{"重楼": "崇楼", "阿胶": "阿交"}', {"阿胶": "阿胶粉"})

    assert lexicon.entries == {"重楼": "崇楼", "阿胶": "阿胶粉"}


def test_apply_uses_longest_key_and_single_pass() -> None:
    lexicon = pronunciation.build(None, {"阿胶": "阿交", "阿胶口服液": "阿交口服液", "阿交": "别动"})

    replaced, hits = lexicon.apply("本页讲阿胶口服液与阿胶。")

    # 长词优先命中；替换产物「阿交」不能再次被替换（单遍）
    assert replaced == "本页讲阿交口服液与阿交。"
    assert hits == 2


def test_apply_without_entries_returns_original() -> None:
    text, hits = pronunciation.build().apply("原样返回")

    assert (text, hits) == ("原样返回", 0)


def test_fingerprint_changes_with_entries() -> None:
    first = pronunciation.build(None, {"重楼": "崇楼"})
    second = pronunciation.build(None, {"重楼": "重楼2"})
    empty = pronunciation.build()

    assert first.fingerprint and second.fingerprint
    assert first.fingerprint != second.fingerprint
    assert empty.fingerprint == ""


def test_voice_key_includes_dict_fingerprint() -> None:
    """词条变化必须让音频指纹变化，否则改完词典听起来毫无变化。"""
    base = cache.voice_key("zh", "zf_001", 1.0, "kokoro", "kokoro-0.9.4")
    with_dict = cache.voice_key("zh", "zf_001", 1.0, "kokoro", "kokoro-0.9.4", "dict-sha")

    assert base != with_dict
