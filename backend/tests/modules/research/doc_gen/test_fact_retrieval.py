"""本地事实库召回的适配层测试（不打数据库、不打外部服务）。

覆盖点：事实库为空时的降级、核心域与引用域的匹配差异、人工锁定优先、
top_k 截断、同文档内编号、重复引用去重、短检索词忽略。
"""

from __future__ import annotations

from app.modules.research.doc_gen.fact_retrieval import FactRetriever
from app.modules.research.doc_gen.kb_retrieval import KB_FILE_PREFIX


class FakeFact:
    """最小事实替身：只暴露召回器真正读取的字段。"""

    def __init__(
        self,
        *,
        subject: str = "",
        predicate: str = "",
        value: str = "",
        unit: str | None = None,
        quote: str = "",
        confidence: float = 0.8,
        document_name: str = "报告.docx",
        locked: bool = False,
    ) -> None:
        self.subject = subject
        self.predicate = predicate
        self.value = value
        self.unit = unit
        self.quote = quote
        self.confidence = confidence
        self.document_name = document_name
        self.locked = locked


async def test_empty_facts_is_disabled() -> None:
    retriever = FactRetriever([])
    assert not retriever.enabled
    assert await retriever.retrieve(["米诺地尔"]) == []


async def test_matches_core_field_and_returns_quote_as_text() -> None:
    fact = FakeFact(
        subject="米诺地尔",
        predicate="CAS号",
        value="38304-91-5",
        quote="米诺地尔 CAS 号 38304-91-5。",
        document_name="调研报告.docx",
    )
    retriever = FactRetriever([fact])
    blocks = await retriever.retrieve(["CAS号"])

    assert len(blocks) == 1
    block = blocks[0]
    assert block.file_id == f"{KB_FILE_PREFIX}调研报告.docx"
    # 正文即 quote：与证据回检语料登记同源，引用不会被误判成「无依据」
    assert block.text == "米诺地尔 CAS 号 38304-91-5。"
    assert retriever.stats.hits == 1
    assert retriever.stats.sources == {block.file_id: "调研报告.docx"}


async def test_no_match_returns_empty_for_live_fallback() -> None:
    retriever = FactRetriever([FakeFact(subject="适应症", value="高血压", quote="适应症为高血压。")])
    assert await retriever.retrieve(["分子式"]) == []


async def test_core_match_outranks_quote_only_match() -> None:
    quote_only = FakeFact(subject="其他", value="无关", quote="纯度相关资料附录见 99.5%。", document_name="b.docx")
    core = FakeFact(subject="纯度", value="99.5%", quote="纯度为 99.5%。", document_name="a.docx")
    retriever = FactRetriever([quote_only, core], top_k=1)

    blocks = await retriever.retrieve(["纯度"])
    assert len(blocks) == 1
    assert blocks[0].file_id == f"{KB_FILE_PREFIX}a.docx"


async def test_locked_fact_wins_tie() -> None:
    auto = FakeFact(subject="纯度", value="99.0%", quote="纯度为 99.0%。", document_name="auto.docx")
    locked = FakeFact(subject="纯度", value="99.9%", quote="纯度为 99.9%。", document_name="locked.docx", locked=True)
    retriever = FactRetriever([auto, locked], top_k=1)

    blocks = await retriever.retrieve(["纯度"])
    assert blocks[0].file_id == f"{KB_FILE_PREFIX}locked.docx"


async def test_top_k_limits_blocks() -> None:
    facts = [
        FakeFact(subject="米诺地尔", value=str(i), quote=f"米诺地尔记录 {i}。", document_name="x.docx")
        for i in range(5)
    ]
    blocks = await FactRetriever(facts, top_k=2).retrieve(["米诺地尔"])
    assert len(blocks) == 2


async def test_index_increments_within_document() -> None:
    facts = [
        FakeFact(subject="米诺地尔", value="1", quote="米诺地尔记录 1。", document_name="x.docx"),
        FakeFact(subject="米诺地尔", value="2", quote="米诺地尔记录 2。", document_name="x.docx"),
    ]
    blocks = await FactRetriever(facts, top_k=10).retrieve(["米诺地尔"])
    assert [block.index for block in blocks] == [0, 1]


async def test_dedupes_identical_quotes() -> None:
    facts = [
        FakeFact(subject="米诺地尔", value="a", quote="米诺地尔记录。", document_name="x.docx"),
        FakeFact(subject="米诺地尔", value="b", quote="米诺地尔记录。", document_name="x.docx"),
    ]
    blocks = await FactRetriever(facts, top_k=10).retrieve(["米诺地尔"])
    assert len(blocks) == 1


async def test_short_keywords_are_ignored() -> None:
    """单字检索词无区分度，不参与匹配（避免命中满库噪声）。"""
    retriever = FactRetriever([FakeFact(subject="的", value="x", quote="的的的的。")])
    assert await retriever.retrieve(["的"]) == []


async def test_missing_document_name_falls_back() -> None:
    retriever = FactRetriever([FakeFact(subject="米诺地尔", value="x", quote="米诺地尔记录。", document_name="")])
    blocks = await retriever.retrieve(["米诺地尔"])
    assert blocks[0].file_id == f"{KB_FILE_PREFIX}知识库事实"
