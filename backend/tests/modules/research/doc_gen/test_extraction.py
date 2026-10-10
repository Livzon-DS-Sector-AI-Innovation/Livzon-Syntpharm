"""抽取层测试：「没有依据就不写」的落地验证（假模型，不打真实服务）。"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen import gap, status
from app.modules.research.doc_gen.extraction import RETRIEVAL_DEFAULT, RETRIEVAL_RECALL, SlotExtractor, SlotResult
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.prompts import build_extract_prompt
from app.modules.research.doc_gen.templates import get_template_spec

BLOCKS = [
    TextBlock(file_id="m1", page=2, index=0, text="原研企业：AstraZeneca AB", kind="paragraph"),
    TextBlock(file_id="m1", page=2, index=1, text="商品名：洛赛克 制剂规格：肠溶胶囊 20mg", kind="paragraph"),
    TextBlock(file_id="l1", page=1, index=0, text="文献报道该路线总收率为 85%", kind="paragraph"),
    TextBlock(file_id="m1", page=4, index=2, text="工艺路线 1：以吡啶环缩合，再氧化成亚磺酰基", kind="paragraph"),
    TextBlock(
        file_id="m1",
        page=5,
        index=3,
        text="方案 物料名称 CAS号 参考供应商 | 方案1 溶剂B 110-82-7 某溶剂有限公司",
        kind="table_row",
    ),
]

ALL_SLOTS = {s.key: s for s in get_template_spec("tech_research_report").slots}

# 需求描述（template_structure v2）校验专用语料：覆盖量纲与枚举两类取值
REQ_BLOCKS = [
    TextBlock(file_id="m1", page=1, index=0, text="含量：20 mg/mL", kind="paragraph"),
    TextBlock(file_id="m1", page=1, index=1, text="剂型：肠溶胶囊", kind="paragraph"),
]


class FakeLLM:
    """按脚本返回预设响应，并可模拟失败次数。"""

    def __init__(self, responses: list[dict[str, Any]], failures: int = 0) -> None:
        self._responses = responses
        self._failures = failures
        self.calls = 0
        self.prompts: list[str] = []

    async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        self.prompts.append(messages[-1]["content"])
        if self._failures > 0:
            self._failures -= 1
            raise RuntimeError("模型不可用")
        return self._responses[min(self.calls - 1, len(self._responses) - 1)]


def _extractor(llm: Any, slots: list[str], **kwargs: Any) -> SlotExtractor:
    spec = get_template_spec("tech_research_report").model_copy(update={"slots": [ALL_SLOTS[k] for k in slots]})
    return SlotExtractor(spec, BLOCKS, roles_by_file={"m1": ["material"], "l1": ["literature"]}, llm=llm, **kwargs)


async def test_valid_quote_is_accepted() -> None:
    """引用能在原文命中的值正常落地。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "confidence": 0.95,
                        "evidence": [{"file_id": "m1", "page": 2, "quote": "原研企业：AstraZeneca AB"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"]).run()
    result = results["originator"]
    assert result.state == status.STATUS_OK
    assert result.text == "AstraZeneca AB"
    assert result.evidence[0].page == 2


async def test_fabricated_quote_downgrades_to_pending() -> None:
    """编造引用（原文里没有）必须降级为待补充，而不是写进正文；AI 值保留进候选供人工参考。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "Bristol-Myers",
                        "found": True,
                        "evidence": [{"file_id": "m1", "page": 9, "quote": "原研企业：Bristol-Myers"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"]).run()
    result = results["originator"]
    assert result.state == status.STATUS_PENDING
    assert status.is_pending(result.text)
    assert result.candidates == ["Bristol-Myers"]
    assert result.evidence  # 原始引用保留，供人工判断


async def test_fullwidth_quote_is_normalized() -> None:
    """引用的全半角/空白差异经归一化后仍可精确核对，不再误判为编造。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "confidence": 0.95,
                        "evidence": [{"file_id": "m1", "page": 2, "quote": "原研企业:AstraZeneca AB"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"]).run()
    assert results["originator"].state == status.STATUS_OK


async def test_fuzzy_quote_is_flagged_for_review() -> None:
    """引用仅有个别字符差异（OCR 级）时模糊核对通过：值照写但标「引用需核对」。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "route_1",
                        "value": "以吡啶环缩合后氧化",
                        "found": True,
                        "evidence": [
                            {"file_id": "m1", "page": 4, "quote": "工艺路线1:以吡啶环缩合，再氧化成亚磺酰基。"}
                        ],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["route_1"], batch_size=1).run()
    result = results["route_1"]
    assert result.state == status.STATUS_NEEDS_VERIFY
    assert result.text == "以吡啶环缩合后氧化"
    assert result.evidence


async def test_wide_retrieval_recovers_zero_hit_slot() -> None:
    """主关键词 0 命中时用二字片段宽检索兜底，槽位仍能进入模型抽取而不是直接跳过。"""
    llm = FakeLLM([{"slots": [{"key": "custom", "value": "x", "found": False}]}])
    base = ALL_SLOTS["originator"].model_copy(
        update={"key": "custom", "label": "物料供应商清单", "required": False, "search_terms": []}
    )
    spec = get_template_spec("tech_research_report").model_copy(update={"slots": [base]})
    extractor = SlotExtractor(spec, BLOCKS, roles_by_file={"m1": ["material"], "l1": ["literature"]}, llm=llm)
    results = await extractor.run()
    assert llm.calls == 1
    assert results["custom"].state == status.STATUS_PENDING
    assert extractor.stats.retrieval_misses == 0


async def test_retrieval_misses_are_counted() -> None:
    """主检索与宽检索均 0 命中：不调模型直接判待补充，并计入 stats。"""
    llm = FakeLLM([{"slots": []}])
    base = ALL_SLOTS["originator"].model_copy(
        update={"key": "custom", "label": "地球化学勘探数据", "required": False, "search_terms": []}
    )
    spec = get_template_spec("tech_research_report").model_copy(update={"slots": [base]})
    extractor = SlotExtractor(spec, BLOCKS, roles_by_file={"m1": ["material"], "l1": ["literature"]}, llm=llm)
    results = await extractor.run()
    assert llm.calls == 0
    assert extractor.stats.retrieval_misses == 1
    assert status.is_pending(results["custom"].text)


async def test_evidence_from_wrong_file_is_rejected() -> None:
    """引用声称来自 m1，但文字其实只在文献里 → 视为不可核对。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "85%",
                        "found": True,
                        "evidence": [{"file_id": "m1", "page": 1, "quote": "文献报道该路线总收率为 85%"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"]).run()
    assert results["originator"].state == status.STATUS_PENDING


async def test_draft_slot_keeps_text_with_prefix() -> None:
    """允许草稿的槽位：引用不可核对时保留草稿但加显式前缀。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "route_1",
                        "value": "该路线收率较高，适合放大。",
                        "found": True,
                        "evidence": [{"file_id": "m1", "page": 1, "quote": "根本没有这句话"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["route_1"], batch_size=1).run()
    result = results["route_1"]
    assert result.state == status.STATUS_DRAFT
    assert result.text.startswith(status.DRAFT_PREFIX)


async def test_conflicting_candidates_are_not_decided() -> None:
    """冲突值不自动裁决，写入冲突标记并保留候选。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "candidates": ["AstraZeneca AB", "海正药业"],
                        "evidence": [{"file_id": "m1", "page": 2, "quote": "原研企业：AstraZeneca AB"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"]).run()
    result = results["originator"]
    assert result.state == status.STATUS_CONFLICT
    assert result.text == status.CONFLICT_MARK
    assert len(result.candidates) == 2


async def test_literature_cannot_feed_material_only_slot() -> None:
    """只允许项目材料的槽位不会拿到文献内容（连候选都不给模型看）。"""
    llm = FakeLLM([{"slots": []}])
    await _extractor(llm, ["originator"]).run()
    assert "文献报道" not in llm.prompts[0]


async def test_model_failure_degrades_without_crashing() -> None:
    """模型不可用时降级：槽位标待补充，任务不抛异常。"""
    llm = FakeLLM([{"slots": []}], failures=5)
    results = await _extractor(llm, ["originator"], max_retries=2).run()
    result = results["originator"]
    assert status.is_pending(result.text)
    assert llm.calls >= 2


async def test_manual_only_slot_never_reaches_prompt() -> None:
    """manual_only 槽位不问模型，直接标需人工填写。"""
    llm = FakeLLM([{"slots": []}])
    results = await _extractor(llm, ["tech_opinion"]).run()
    assert results["tech_opinion"].state == status.STATUS_MANUAL
    assert llm.calls == 0


async def test_table_rows_drop_computed_columns_from_model() -> None:
    """表格槽位：模型只给原始列，计算列与序号由程序负责。"""
    evidence = [{"file_id": "m1", "page": 5, "quote": "方案1 溶剂B 110-82-7 某溶剂有限公司"}]
    response = {
        "rows": [
            {"values": {"material": "溶剂B", "cas": "110-82-7", "supplier": "某溶剂有限公司"}, "evidence": evidence}
        ]
    }
    llm = FakeLLM([response])
    results = await _extractor(llm, ["supplier_rows"]).run()
    rows = results["supplier_rows"].rows
    assert rows and rows[0].get("material") == "溶剂B"
    assert set(rows[0]) <= {"plan", "material", "cas", "supplier"}


async def test_low_confidence_downgrades_to_needs_verify() -> None:
    """模型自报置信度低于中阈值：值照写但降级为需人工核对，理由注明置信度。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "confidence": 0.3,
                        "evidence": [{"file_id": "m1", "page": 2, "quote": "原研企业：AstraZeneca AB"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"], confidence_high=0.85, confidence_mid=0.6).run()
    result = results["originator"]
    assert result.state == status.STATUS_NEEDS_VERIFY
    assert result.text == "AstraZeneca AB"
    assert "置信度" in (result.reason or "")


async def test_mid_confidence_stays_ok_but_counted() -> None:
    """置信度介于中/高阈值之间：保持已填充，计入低置信度统计供抽查。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "confidence": 0.7,
                        "evidence": [{"file_id": "m1", "page": 2, "quote": "原研企业：AstraZeneca AB"}],
                    }
                ]
            }
        ]
    )
    extractor = _extractor(llm, ["originator"], confidence_high=0.85, confidence_mid=0.6)
    results = await extractor.run()
    assert results["originator"].state == status.STATUS_OK
    assert extractor.stats.low_confidence == 1


async def test_database_evidence_is_trusted_without_quote_check() -> None:
    """项目登记数据（db: 前缀虚拟文件）是数据库权威事实：引用不查语料直接核对通过。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "confidence": 0.95,
                        "evidence": [{"file_id": "db:1", "page": 1, "quote": "语料里根本没有这句话"}],
                    }
                ]
            }
        ]
    )
    results = await _extractor(llm, ["originator"]).run()
    result = results["originator"]
    assert result.state == status.STATUS_OK
    assert result.evidence[0].file_id == "db:1"


def test_context_prefers_high_score_chunks_within_budget() -> None:
    """上下文预算内按相关性贪心挑选：高分块优先保留，放不下的低分块让位。"""
    chunks = [
        {"file_id": "f1", "page": 1, "text": "低相关短块"},
        {"file_id": "f2", "page": 1, "text": "高相关块" * 20},
        {"file_id": "f3", "page": 1, "text": "另一个低相关块"},
    ]
    slot_payload = {"key": "k", "label": "测试槽位"}
    prompt = build_extract_prompt([slot_payload], chunks, max_context_chars=120, scores=[0.0, 9.0, 1.0])
    content = prompt[1]["content"]
    assert "高相关块" in content
    assert "低相关短块" not in content


def _single_slot_extractor(llm: Any, **slot_update: Any) -> Any:
    """只取一个自造槽位、并按需求描述覆写的抽取器（用于 template_structure v2 校验）。

    槽位的检索词固定为「含量」，与 ``REQ_BLOCKS`` 对齐，保证候选块能召回。
    """
    slot = ALL_SLOTS["originator"].model_copy(
        update={"key": "custom", "label": "含量", "required": False, "search_terms": ["含量"]}
    )
    slot = slot.model_copy(update=slot_update)
    spec = get_template_spec("tech_research_report").model_copy(update={"slots": [slot]})
    return SlotExtractor(spec, REQ_BLOCKS, roles_by_file={"m1": ["material"], "l1": ["literature"]}, llm=llm)


def _single_slot_response(value: str, quote: str) -> dict[str, Any]:
    return {
        "slots": [
            {
                "key": "custom",
                "value": value,
                "found": True,
                "confidence": 0.95,
                "evidence": [{"file_id": "m1", "page": 1, "quote": quote}],
            }
        ]
    }


async def test_requirement_unit_mismatch_downgrades_to_needs_verify() -> None:
    """需求描述声明量纲：取值缺量纲时值照写，但降级为需人工核对并计入统计。"""
    llm = FakeLLM([_single_slot_response("肠溶胶囊", "剂型：肠溶胶囊")])
    extractor = _single_slot_extractor(llm, unit="mg")
    results = await extractor.run()
    result = results["custom"]
    assert result.state == status.STATUS_NEEDS_VERIFY
    assert result.text == "肠溶胶囊"
    assert "量纲" in (result.reason or "")
    assert extractor.stats.requirement_mismatches == 1


async def test_requirement_unit_accepts_equivalent_writing() -> None:
    """量纲按归一化核对：``mg/ml`` 与 ``mg/mL`` 视为一致，不误判。"""
    llm = FakeLLM([_single_slot_response("20 mg/mL", "含量：20 mg/mL")])
    results = await _single_slot_extractor(llm, unit="mg/ml").run()
    assert results["custom"].state == status.STATUS_OK


async def test_requirement_enum_outside_range_downgrades() -> None:
    """需求描述声明允许取值：取值不在集合内时降级为需人工核对。"""
    llm = FakeLLM([_single_slot_response("20 mg/mL", "含量：20 mg/mL")])
    results = await _single_slot_extractor(llm, enum_values=["肠溶胶囊"]).run()
    result = results["custom"]
    assert result.state == status.STATUS_NEEDS_VERIFY
    assert "允许范围" in (result.reason or "")


async def test_requirement_prompt_exposes_unit_and_scope() -> None:
    """需求描述必须进入提取 prompt，否则模型无从遵守。"""
    llm = FakeLLM([_single_slot_response("20 mg/mL", "含量：20 mg/mL")])
    results = await _single_slot_extractor(llm, unit="mg", enum_values=["肠溶胶囊"], cardinality="one_or_more").run()
    assert results
    prompt = llm.prompts[0]
    assert "量纲要求：mg" in prompt
    assert "允许取值：肠溶胶囊" in prompt
    assert "允许多个值" in prompt


async def test_project_kb_scope_excludes_local_material() -> None:
    """source_scope=project_kb：本地项目材料不进候选，未配知识库时直接判待补充。"""
    llm = FakeLLM([{"slots": []}])
    extractor = _single_slot_extractor(llm, source_scope="project_kb")
    results = await extractor.run()
    assert llm.calls == 0
    assert extractor.stats.retrieval_misses == 1
    assert status.is_pending(results["custom"].text)


# ---- 缺口重试口径：换的是「问法」而不是「更多预算」 ------------------------------

RECALL_KB_FILE = "kb:工艺调研报告.docx"
RECALL_KB_QUOTE = "催化体系筛选以 Pd/C 为催化剂，收率提升至 88%"


class FragmentKbRetriever:
    """只认指定二字片段的假知识库：模拟「同一套槽位用词查不到、换个问法就查得到」。"""

    marker = "筛选"

    def __init__(self) -> None:
        self.queries: list[list[str]] = []

    async def retrieve(self, keywords: list[str]) -> list[TextBlock]:
        self.queries.append(list(keywords))
        if self.marker not in keywords:
            return []
        return [TextBlock(file_id=RECALL_KB_FILE, page=1, index=0, text=RECALL_KB_QUOTE, kind="paragraph")]


def _recall_extractor(profile: str, kb: Any, llm: Any) -> SlotExtractor:
    """同一槽位、同一份本地资料与知识库，只有检索口径不同。"""
    base = ALL_SLOTS["originator"].model_copy(
        update={"key": "custom", "label": "催化体系筛选数据", "required": False, "search_terms": []}
    )
    spec = get_template_spec("tech_research_report").model_copy(update={"slots": [base]})
    return SlotExtractor(
        spec,
        BLOCKS,
        roles_by_file={"m1": ["material"], "l1": ["literature"]},
        llm=llm,
        kb_retriever=kb,
        retrieval_profile=profile,
    )


async def test_default_profile_misses_kb_with_slot_wording() -> None:
    """默认口径：知识库与本地资料都按槽位用词检索、双双 0 命中 → 判待补充且不调模型。"""
    llm = FakeLLM([{"slots": []}])
    kb = FragmentKbRetriever()
    extractor = _recall_extractor(RETRIEVAL_DEFAULT, kb, llm)

    results = await extractor.run()

    assert "催化体系筛选数据" in kb.queries[0]
    assert llm.calls == 0
    assert extractor.stats.retrieval_misses == 1
    assert results["custom"].gap_reason == gap.GAP_NO_MATERIAL


async def test_recall_profile_queries_kb_with_widened_terms() -> None:
    """重试口径：把二字片段当主口径，知识库收到的是另一套词，于是捞到措辞不同的片段并填上。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "custom",
                        "value": "Pd/C",
                        "found": True,
                        "confidence": 0.95,
                        "evidence": [{"file_id": RECALL_KB_FILE, "page": 1, "quote": RECALL_KB_QUOTE}],
                    }
                ]
            }
        ]
    )
    kb = FragmentKbRetriever()
    extractor = _recall_extractor(RETRIEVAL_RECALL, kb, llm)

    results = await extractor.run()

    assert "催化体系筛选数据" not in kb.queries[0]
    assert FragmentKbRetriever.marker in kb.queries[0]
    assert results["custom"].state == status.STATUS_OK
    assert results["custom"].text == "Pd/C"
    assert extractor.stats.kb_hits == 1
    assert llm.calls == 1


# ---- 引用编号复核（refs）：引用抄写不可靠时，按模型自报的资料编号救回取值 ----------------


def test_value_in_refs_requires_valid_index_and_locatable_value() -> None:
    """编号复核的三个边界：越界不认、空编号不认、值不在被引片段里不认。"""
    extractor = _extractor(FakeLLM([{"slots": []}]), ["originator"])
    pool = [{"file_id": "m1", "page": 2, "text": "原研企业：AstraZeneca AB"}]
    assert extractor._value_in_refs(pool, [1], "AstraZeneca AB") is True
    assert extractor._value_in_refs(pool, [2], "AstraZeneca AB") is False  # 越界
    assert extractor._value_in_refs(pool, [], "AstraZeneca AB") is False  # 无编号
    assert extractor._value_in_refs(pool, [1], "Bristol-Myers") is False  # 值不在被引片段
    assert extractor._value_in_refs(None, [1], "AstraZeneca AB") is False  # 无候选池


async def test_refs_rescue_keeps_value_when_quote_missed() -> None:
    """引用文本编造（无法核对），但 refs 指向的候选里含该取值：保留取值并标需人工核对。

    引用抄写不可靠 ≠ 值编造：模型明确指向了依据的资料编号，程序在被引片段内复核取值，
    命中则降级 needs_verify 交人工，而不是整条打回「待补充」。
    """
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "refs": list(range(1, 10)),  # 覆盖全部候选：只看编号有效性，与检索排序无关
                        "evidence": [{"file_id": "m1", "page": 9, "quote": "原研企业：Bristol-Myers"}],
                    }
                ]
            }
        ]
    )
    extractor = _extractor(llm, ["originator"])
    results = await extractor.run()

    result = results["originator"]
    assert result.state == status.STATUS_NEEDS_VERIFY
    assert result.text == "AstraZeneca AB"
    assert "所引资料" in result.reason
    assert extractor.stats.refs_rescued == 1


async def test_refs_out_of_range_does_not_rescue_fabricated_value() -> None:
    """编号越界 + 取值在全语料中也找不到：仍按「无依据」处理，不因 refs 字段松绑。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "Bristol-Myers",
                        "found": True,
                        "refs": [99],
                        "evidence": [{"file_id": "m1", "page": 9, "quote": "原研企业：Bristol-Myers"}],
                    }
                ]
            }
        ]
    )
    extractor = _extractor(llm, ["originator"])
    results = await extractor.run()

    assert results["originator"].state == status.STATUS_PENDING
    assert extractor.stats.refs_rescued == 0


# ---- 跨任务持久缓存（DB 版）：命中即跳过模型调用 --------------------------------------


async def test_persist_cache_hit_skips_model_call() -> None:
    """持久缓存命中：模型一次都不调，结果直接复用（跨任务/重跑提速的关键）。"""
    cached = SlotResult(key="originator", text="AstraZeneca AB", state=status.STATUS_OK)

    class _StubCache:
        def __init__(self) -> None:
            self.puts: list[tuple[str, SlotResult]] = []

        def key(self, slot_key: str, content_hash: str) -> str:
            return f"{slot_key}:{content_hash}"

        async def get(self, cache_key: str) -> SlotResult | None:
            return cached

        async def put(self, cache_key: str, result: SlotResult) -> None:
            self.puts.append((cache_key, result))

    stub = _StubCache()
    llm = FakeLLM([{"slots": []}])
    extractor = _extractor(llm, ["originator"], persist_cache=stub)
    results = await extractor.run()

    assert results["originator"] is cached
    assert llm.calls == 0
    assert extractor.stats.calls == 0
    assert extractor._cache_hits == 1


# ---- 定向补问（probe）：把槽位与它自己的候选单独再问一次 ------------------------------


async def test_probe_recovers_value_from_own_candidates() -> None:
    """补问用「槽位 + 自己的候选」单独问一次，模型给出可核对取值即补上。"""
    llm = FakeLLM(
        [
            {
                "slots": [
                    {
                        "key": "originator",
                        "value": "AstraZeneca AB",
                        "found": True,
                        "confidence": 0.95,
                        "refs": list(range(1, 10)),
                        "evidence": [{"file_id": "m1", "page": 2, "quote": "原研企业：AstraZeneca AB"}],
                    }
                ]
            }
        ]
    )
    extractor = _extractor(llm, ["originator"])
    results = await extractor.probe(list(extractor._spec.slots))

    assert results["originator"].state == status.STATUS_OK
    assert results["originator"].text == "AstraZeneca AB"
    assert llm.calls == 1


async def test_table_rows_without_any_evidence_downgrade_to_needs_verify() -> None:
    """表格行既无可核对引用也无资料编号：数据照写，但整表降级为需人工核对并计数。"""
    response = {
        "rows": [
            {
                "values": {"material": "溶剂C", "cas": "999-99-9", "supplier": "某厂"},
                "evidence": [{"file_id": "m1", "page": 5, "quote": "这段引用并不存在于资料中"}],
            }
        ]
    }
    llm = FakeLLM([response])
    extractor = _extractor(llm, ["supplier_rows"])
    results = await extractor.run()

    result = results["supplier_rows"]
    assert result.state == status.STATUS_NEEDS_VERIFY
    assert "未能核对" in result.reason
    assert result.rows and result.rows[0]["material"] == "溶剂C"  # 行不丢，只是降级
    assert extractor.stats.table_rows_unverified == 1


async def test_table_row_refs_can_verify_row() -> None:
    """行只带资料编号（refs）：所引片段内能定位行值即算核对通过，保持 OK。"""
    response = {
        "rows": [
            {
                "values": {"material": "溶剂B", "cas": "110-82-7", "supplier": "某溶剂有限公司"},
                "refs": list(range(1, 9)),  # 覆盖全部候选：只看编号有效性与定位结果
            }
        ]
    }
    llm = FakeLLM([response])
    extractor = _extractor(llm, ["supplier_rows"])
    results = await extractor.run()

    assert results["supplier_rows"].state == status.STATUS_OK
    assert extractor.stats.table_rows_unverified == 0


async def test_probe_ignores_manual_only_slots() -> None:
    """人工填写项不进补问：一个模型调用都不该发生。"""
    llm = FakeLLM([{"slots": []}])
    spec = get_template_spec("tech_research_report")
    manual = [slot for slot in spec.slots if slot.manual_only]
    assert manual  # 模板自带人工填写项，测试前提成立
    extractor = SlotExtractor(spec.model_copy(update={"slots": manual}), BLOCKS, llm=llm)

    assert await extractor.probe(manual) == {}
    assert llm.calls == 0
