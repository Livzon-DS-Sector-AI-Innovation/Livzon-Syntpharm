"""翻译引擎：批次切分、响应解析、后处理与失败重试（LLM 全部 mock）。"""

from __future__ import annotations

from typing import Any

import pytest

from app.modules.registration.docx_translator import translator as translator_module
from app.modules.registration.docx_translator.config import TranslateConfig
from app.modules.registration.docx_translator.engine_models import TextUnit
from app.modules.registration.docx_translator.glossary import Glossary
from app.modules.registration.docx_translator.translator import TranslationEngineError, Translator


def _unit(uid: str, text: str) -> TextUnit:
    return TextUnit(
        id=uid,
        text=text,
        location_type="body",
        section_index=0,
        table_path="",
        paragraph_element=None,
        parent_element=None,
        paragraph_index=0,
    )


class _FakeLLM:
    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    async def chat(self, **_kwargs: Any) -> str:
        self.calls += 1
        if not self.responses:
            raise RuntimeError("no response")
        return self.responses.pop(0)


def _config(**kwargs: Any) -> TranslateConfig:
    base: dict[str, Any] = {"source_lang": "en", "target_lang": "zh", "mode": "bilingual", "batch_size": 2}
    base.update(kwargs)
    return TranslateConfig(**base)


def test_split_into_batches_respects_size() -> None:
    translator = Translator(_config(batch_size=2))
    units = [_unit(f"u{i:05d}", f"text {i}") for i in range(1, 6)]
    batches = translator._split_into_batches(units)
    assert [len(batch.units) for batch in batches] == [2, 2, 1]


def test_parse_response_tolerates_markdown_and_continuation() -> None:
    translator = Translator(_config())
    batches = translator._split_into_batches([_unit("u00001", "hello"), _unit("u00002", "world")])
    parsed = translator._parse_response("- [ID:u00001] 你好\n[ID: u00002] 世界\n续行", batches[0])
    assert parsed["u00001"] == "你好"
    assert parsed["u00002"] == "世界\n续行"


def test_post_process_fixes_duplicated_unit() -> None:
    translator = Translator(_config())
    assert translator._post_process_translation("500 克 (g)g", "500 克 (g)g") == "500 g"


async def test_translate_all_uses_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeLLM(["[ID:u00001] 你好\n[ID:u00002] 世界"])
    monkeypatch.setattr(translator_module, "llm_client", fake)
    translator = Translator(_config(batch_size=5))
    units = [_unit("u00001", "hello"), _unit("u00002", "world"), _unit("u00003", "")]
    results = await translator.translate_all(units)
    assert fake.calls == 1
    by_id = {item.unit_id: item for item in results}
    assert by_id["u00001"].translated_text == "你好"
    assert by_id["u00002"].success is True
    assert by_id["u00003"].success is True


async def test_translate_all_marks_batch_failed_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeLLM([])
    monkeypatch.setattr(translator_module, "llm_client", fake)
    monkeypatch.setattr(Translator, "_request_retries", 1)
    monkeypatch.setattr(Translator, "_max_batch_retries", 1)
    monkeypatch.setattr(Translator, "_retry_delay", (0.0, 0.0))
    translator = Translator(_config(batch_size=5))
    results = await translator.translate_all([_unit("u00001", "hello")])
    assert results[0].success is False
    assert "失败" in (results[0].error_message or "")


async def test_call_api_raises_after_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeLLM([])
    monkeypatch.setattr(translator_module, "llm_client", fake)
    monkeypatch.setattr(Translator, "_request_retries", 2)
    translator = Translator(_config())
    with pytest.raises(TranslationEngineError):
        await translator._call_api("system", "user")


def test_glossary_terms_injected_into_prompt() -> None:
    glossary = Glossary()
    glossary.load_from_terms({"批生产记录": "Batch Production Record"})
    translator = Translator(_config(), glossary)
    batches = translator._split_into_batches([_unit("u00001", "Batch Production Record shall be kept")])
    terms = translator._extract_batch_terms(batches[0])
    assert terms == {"Batch Production Record": "批生产记录"}
    prompt = translator._build_system_prompt(terms)
    assert "Batch Production Record → 批生产记录" in prompt
