"""提取依据来源解析（file_id → 文件名/来源标签）的离线单测。

复核界面靠它告诉审核人「这个值来自哪份资料的哪一页哪句原文」，解析错了来源标记
就会误导人工核对，所以把各类 file_id（真实资料/知识库/登记数据/补充说明/人工填写/
上一版报告/未知）逐一钉死。
"""

from __future__ import annotations

import uuid
from typing import Any

from app.modules.research.doc_gen import service
from app.modules.research.doc_gen.models import DocGenSlotValue


def _row(evidence: Any) -> DocGenSlotValue:
    # id 显式给定：内存构造的 ORM 行不会触发 SQLAlchemy 的 uuid4 默认值，
    # 而 model_validate 要求 id 为合法 UUID（生产路径的行都来自 DB，必有 id）。
    return DocGenSlotValue(
        id=uuid.uuid4(),
        slot_key="route_1",
        label="工艺路线1",
        text="值",
        state="ok",
        evidence=evidence,
    )


def test_evidence_source_resolves_all_file_id_kinds() -> None:
    """六类 file_id 都要解析出可读文件名与来源类型标签。"""
    file_map = {
        "abcd1234abcd1234": "原料工艺资料.docx",
        "report-xyz123456789": "本报告已填内容.txt",
    }
    evidence = [
        {"file_id": "abcd1234abcd1234", "page": 3, "quote": "原文A"},
        {"file_id": "kb:项目知识库文档", "page": None, "quote": "原文B"},
        {"file_id": "db:proj-1", "page": None, "quote": "原文C"},
        {"file_id": "supplement", "page": None, "quote": "原文D"},
        {"file_id": "human", "page": None, "quote": "原文E"},
        {"file_id": "report-xyz123456789", "page": None, "quote": "原文F"},
    ]
    resp = service._slot_response(_row(evidence), file_map)
    assert resp.evidence is not None
    by_quote = {item.quote: item for item in resp.evidence}

    assert by_quote["原文A"].file_name == "原料工艺资料.docx"
    assert by_quote["原文A"].source_label == "资料文件"
    assert by_quote["原文A"].page == 3

    assert by_quote["原文B"].file_name == "项目知识库文档"
    assert by_quote["原文B"].source_label == "项目知识库"

    assert by_quote["原文C"].file_name == "项目登记数据"
    assert by_quote["原文C"].source_label == "项目登记数据"

    assert by_quote["原文D"].file_name == "人工补充说明"
    assert by_quote["原文D"].source_label == "补充说明"

    assert by_quote["原文E"].file_name == "人工填写"
    assert by_quote["原文E"].source_label == "人工填写"

    assert by_quote["原文F"].file_name == "本报告已填内容.txt"
    assert by_quote["原文F"].source_label == "上一版报告"


def test_resolve_evidence_handles_empty_and_unknown() -> None:
    """空依据返回 None；未知 file_id 退化为「其他来源」并保留原始 id 作名称。"""
    assert service._resolve_evidence(None, {}) is None
    assert service._resolve_evidence([], {}) is None

    items = service._resolve_evidence([{"file_id": "未知id", "quote": "x"}], {})
    assert items is not None
    assert items[0].source_label == "其他来源"
    assert items[0].file_name == "未知id"
    assert items[0].page is None


def test_resolve_evidence_skips_non_mapping_entries() -> None:
    """脏数据（非字典条目）不得让接口 500，跳过即可。"""
    items = service._resolve_evidence(["坏数据", {"file_id": "m1", "quote": "好数据"}], {"m1": "资料.docx"})
    assert items is not None
    assert len(items) == 1
    assert items[0].quote == "好数据"
    assert items[0].file_name == "资料.docx"
