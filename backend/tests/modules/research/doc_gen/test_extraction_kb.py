"""项目知识库接入提取链路的测试：召回片段要能被引用并核对通过。

对照组是关键——同一个引用，接入知识库时核对通过、不接入时判为「依据无法定位」，
证明结论确实来自知识库片段，而不是回检逻辑放水。
"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.extraction import SlotExtractor
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.templates import get_template_spec

KB_DOC_NAME = "米诺地尔项目调研报告.docx"
KB_QUOTE = "原研企业为 Kaken Pharmaceutical Co., Ltd."
KB_FILE_ID = f"kb:{KB_DOC_NAME}"

LOCAL_BLOCKS = [
    TextBlock(file_id="m1", page=1, index=0, text="商品名：洛赛克 制剂规格：肠溶胶囊 20mg", kind="paragraph"),
    # 命中 originator 槽位关键词，保证「不接知识库」的对照组仍会调用模型
    TextBlock(file_id="m1", page=2, index=1, text="原研企业：AstraZeneca AB，商品名洛赛克", kind="paragraph"),
]
ALL_SLOTS = {s.key: s for s in get_template_spec("tech_research_report").slots}


class FakeLLM:
    """固定返回原研企业取值，依据指向知识库文档。"""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        self.prompts.append(messages[-1]["content"])
        return {
            "slots": [
                {
                    "key": "originator",
                    "value": "Kaken Pharmaceutical Co., Ltd.",
                    "found": True,
                    "confidence": 0.95,
                    "evidence": [{"file_id": KB_FILE_ID, "page": 1, "quote": KB_QUOTE}],
                    "candidates": [],
                }
            ]
        }


class FakeKbRetriever:
    """假知识库召回器：固定返回一条命中片段。"""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error
        self.queries: list[list[str]] = []

    async def retrieve(self, keywords: list[str]) -> list[TextBlock]:
        self.queries.append(list(keywords))
        if self._error is not None:
            raise self._error
        return [TextBlock(file_id=KB_FILE_ID, page=1, index=0, text=KB_QUOTE, kind="paragraph")]


class FakeFactRetriever:
    """假事实召回器：默认命中一条事实；传空列表模拟「无命中」以触发回落。"""

    def __init__(self, blocks: list[TextBlock] | None = None, error: Exception | None = None) -> None:
        self._blocks = (
            blocks
            if blocks is not None
            else [TextBlock(file_id=KB_FILE_ID, page=1, index=0, text=KB_QUOTE, kind="paragraph")]
        )
        self._error = error
        self.queries: list[list[str]] = []

    async def retrieve(self, keywords: list[str]) -> list[TextBlock]:
        self.queries.append(list(keywords))
        if self._error is not None:
            raise self._error
        return list(self._blocks)


def _extractor(kb_retriever: Any = None, fact_retriever: Any = None) -> SlotExtractor:
    spec = get_template_spec("tech_research_report").model_copy(update={"slots": [ALL_SLOTS["originator"]]})
    return SlotExtractor(
        spec,
        LOCAL_BLOCKS,
        roles_by_file={"m1": ["material"]},
        llm=FakeLLM(),
        kb_retriever=kb_retriever,
        fact_retriever=fact_retriever,
    )


async def test_kb_evidence_is_verified_and_slot_filled() -> None:
    extractor = _extractor(FakeKbRetriever())
    results = await extractor.run()

    result = results["originator"]
    assert result.state == status.STATUS_OK
    assert result.text == "Kaken Pharmaceutical Co., Ltd."
    assert [e.file_id for e in result.evidence] == [KB_FILE_ID]
    assert extractor.stats.kb_hits == 1


async def test_same_evidence_fails_without_kb() -> None:
    """不接知识库时同一引用无法核对：槽位退化为待补充（对照实验）。"""
    extractor = _extractor()
    results = await extractor.run()

    result = results["originator"]
    assert result.state == status.STATUS_PENDING
    assert "依据无法在原文中定位" in result.text
    # 值保留在候选里供人工参考，但不写入正文
    assert result.candidates == ["Kaken Pharmaceutical Co., Ltd."]
    assert extractor.stats.kb_hits == 0


async def test_kb_failure_does_not_break_extraction() -> None:
    """知识库异常不能让任务失败，只是退回本地资料。"""
    extractor = _extractor(FakeKbRetriever(error=RuntimeError("连接被拒绝")))
    results = await extractor.run()

    assert results["originator"].state == status.STATUS_PENDING
    assert extractor.stats.kb_hits == 0


async def test_kb_candidates_are_merged_first() -> None:
    extractor = _extractor(FakeKbRetriever())
    chunks, payload, wide = await extractor._candidates(ALL_SLOTS["originator"])

    assert wide is False
    assert chunks[0].file_id == KB_FILE_ID
    assert payload[0]["file_id"] == KB_FILE_ID
    assert KB_FILE_ID in extractor._kb_files
    # 知识库片段必须进入回检语料，否则引用核对会被判为无依据
    assert KB_QUOTE.replace(" ", "").lower() in extractor._corpus_of(KB_FILE_ID)


async def test_kb_query_uses_slot_keywords() -> None:
    retriever = FakeKbRetriever()
    extractor = _extractor(retriever)
    await extractor._candidates(ALL_SLOTS["originator"])

    assert retriever.queries, "知识库召回必须按槽位检索词发起"
    assert "originator" in retriever.queries[0]


async def test_fact_retriever_is_preferred_over_live_kb() -> None:
    """事实库命中时不再打实时检索：它是零外部调用的第一级来源。"""
    facts = FakeFactRetriever()
    live = FakeKbRetriever()
    extractor = _extractor(live, facts)
    chunks, payload, _ = await extractor._candidates(ALL_SLOTS["originator"])

    assert facts.queries and not live.queries
    assert chunks[0].file_id == KB_FILE_ID
    assert payload[0]["file_id"] == KB_FILE_ID
    assert KB_FILE_ID in extractor._kb_files
    # 事实正文也要进回检语料，否则模型引用它会被判成「无依据」
    assert KB_QUOTE.replace(" ", "").lower() in extractor._corpus_of(KB_FILE_ID)


async def test_live_kb_used_when_facts_miss() -> None:
    """事实库无命中时回落实时检索（覆盖该槽位事实尚未抽到的场景）。"""
    facts = FakeFactRetriever(blocks=[])
    live = FakeKbRetriever()
    extractor = _extractor(live, facts)
    chunks, _, _ = await extractor._candidates(ALL_SLOTS["originator"])

    assert facts.queries and live.queries
    assert chunks[0].file_id == KB_FILE_ID


async def test_fact_failure_falls_back_to_live_kb() -> None:
    """事实库异常不能让提取失败，直接回落实时检索。"""
    facts = FakeFactRetriever(error=RuntimeError("事实库不可用"))
    live = FakeKbRetriever()
    extractor = _extractor(live, facts)
    results = await extractor.run()

    assert results["originator"].state == status.STATUS_OK
    assert live.queries, "事实库异常后必须回落实时检索"


async def test_fact_evidence_is_verified_and_slot_filled() -> None:
    """仅接事实库（不接实时检索）时，引用同样要能核对通过。"""
    extractor = _extractor(None, FakeFactRetriever())
    results = await extractor.run()

    assert results["originator"].state == status.STATUS_OK
    assert [e.file_id for e in results["originator"].evidence] == [KB_FILE_ID]
    assert extractor.stats.kb_hits == 1
