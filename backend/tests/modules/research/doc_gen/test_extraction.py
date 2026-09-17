"""抽取层测试：「没有依据就不写」的落地验证（假模型，不打真实服务）。"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.extraction import SlotExtractor
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
    prompt = build_extract_prompt(
        [slot_payload], chunks, max_context_chars=120, scores=[0.0, 9.0, 1.0]
    )
    content = prompt[1]["content"]
    assert "高相关块" in content
    assert "低相关短块" not in content
