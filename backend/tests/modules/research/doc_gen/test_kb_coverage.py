"""知识库覆盖预检测试：生成之前先算清「这些填充项库里到底有没有料」。

预检的口径直接决定用户看到的那句「预计 N 项无资料」，所以这里钉死三件事：
主口径与别名的分界、三档状态的判定、以及「查不到」时的降级行为（不挂库/无索引/检索失败/超时）。
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.doc_gen import kb_coverage
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.template_spec import Anchor, ColumnSpec, Slot, TableSpec, TemplateSpec
from app.modules.research.knowledge_base.models import RdKnowledgeBase


def _slot(key: str, label: str | None = None, **kwargs: Any) -> Slot:
    return Slot(key=key, label=label or key, anchors=[Anchor(type="section_relative")], **kwargs)


def _table_slot(key: str, label: str, columns: list[str]) -> Slot:
    """表格槽位：列名才是真正的填充位置，理应并入别名参与覆盖判断。"""
    return Slot(
        key=key,
        label=label,
        kind="table",
        anchors=[Anchor(type="table_rows")],
        columns=[ColumnSpec(key=f"c{index}", label=column) for index, column in enumerate(columns)],
        table=TableSpec(),
    )


def _spec(*slots: Slot) -> TemplateSpec:
    return TemplateSpec(code="t", name="测试模板", version="1", master_asset="x.docx", slots=list(slots))


def _kb(*, dataset_id: str | None = "ds-1", deleted: bool = False) -> Any:
    return cast(
        RdKnowledgeBase,
        SimpleNamespace(
            id=uuid.uuid4(),
            name="某项目知识库",
            is_deleted=deleted,
            ragflow_dataset_id=dataset_id,
            document_count=3,
        ),
    )


def _session() -> AsyncSession:
    """预检只读索引，测试里把 load_index_texts 换成离线替身，会话不必是真的。"""
    return cast(AsyncSession, SimpleNamespace())


def _norm(text: str) -> str:
    """替身内部沿用与实现一致的归一化（去空白 + 小写），中文用例无需 NFKC 处理。"""
    return text.replace(" ", "").lower()


def _patch_index(
    monkeypatch: pytest.MonkeyPatch,
    texts: list[str],
    *,
    facts: int = 0,
    truncated: bool = False,
) -> None:
    """把本地索引载入替换成给定文本集合。"""

    async def _fake(session: Any, kb_id: Any, *, max_chunks: int) -> kb_coverage.IndexedMaterial:
        return kb_coverage.IndexedMaterial(
            texts=[_norm(text) for text in texts],
            chunks=len(texts),
            facts=facts,
            truncated=truncated,
        )

    monkeypatch.setattr(kb_coverage, "load_index_texts", _fake)


class StubRetriever:
    """实时检索兜底替身：记录每次查询的关键词，按关键词返回命中文本。"""

    def __init__(
        self,
        mapping: dict[str, list[str]] | None = None,
        *,
        delay: float = 0.0,
        error: bool = False,
    ) -> None:
        self.calls: list[list[str]] = []
        self._mapping = mapping or {}
        self._delay = delay
        self._error = error

    async def retrieve(self, keywords: list[str]) -> list[TextBlock]:
        self.calls.append(list(keywords))
        if self._error:
            raise RuntimeError("知识库不可用")
        if self._delay:
            await asyncio.sleep(self._delay)
        texts = [text for keyword in keywords for text in self._mapping.get(keyword, [])]
        return [
            TextBlock(file_id="kb:doc", page=1, index=index, text=text, kind="paragraph")
            for index, text in enumerate(dict.fromkeys(texts))
        ]


# ---- 口径：主口径 vs 别名 ---------------------------------------------------


def test_probe_terms_splits_primary_and_aliases() -> None:
    """槽位名与检索提示是主口径，同义词是别名——这决定「可填」还是「部分可填」。"""
    slot = _slot("reg_no", "登记号", query_hint="药品注册受理编号", search_terms=["受理号", "注册号"])
    primary, alternates = kb_coverage.probe_terms(slot)
    assert primary == ["登记号", "药品注册受理编号"]
    assert alternates == ["受理号", "注册号"]


def test_probe_terms_includes_table_column_labels() -> None:
    """表格槽位一行多列，列名同样是「能不能填上」的口径。"""
    primary, alternates = kb_coverage.probe_terms(_table_slot("stability", "稳定性数据", ["批号", "考察月", "含量"]))

    assert primary == ["稳定性数据"]
    assert alternates == ["批号", "考察月", "含量"]


def test_probe_terms_drops_short_duplicates_and_overlapping_aliases() -> None:
    """单字词噪声太大直接丢；与主口径重复的别名不再重复计分。"""
    slot = _slot("x", "含量", search_terms=["含", "含量", "纯度", "纯度"])
    primary, alternates = kb_coverage.probe_terms(slot)
    assert primary == ["含量"]
    assert alternates == ["纯度"]


def test_is_checkable_skips_meta_manual_and_image_slots() -> None:
    """元数据槽位不问库、人工槽位本来就该留白、图片槽位没有文字可检索。"""
    assert kb_coverage.is_checkable(_slot("a"))
    assert kb_coverage.is_checkable(_table_slot("t", "稳定性数据", ["批号"]))
    assert not kb_coverage.is_checkable(_slot("b", from_meta=True))
    assert not kb_coverage.is_checkable(_slot("c", manual_only=True))
    assert not kb_coverage.is_checkable(_slot("d", kind="image"))


def test_classify_prefers_primary_over_alias() -> None:
    """三档判定：主口径命中 → 可填；只有别名有料 → 部分可填；完全没料 → 无资料。"""
    assert kb_coverage.classify(primary_hits=1, alternate_hits=0, material_hits=1) == kb_coverage.COVERAGE_FILLABLE
    assert kb_coverage.classify(primary_hits=0, alternate_hits=2, material_hits=1) == kb_coverage.COVERAGE_PARTIAL
    assert kb_coverage.classify(primary_hits=0, alternate_hits=0, material_hits=3) == kb_coverage.COVERAGE_PARTIAL
    assert kb_coverage.classify(primary_hits=0, alternate_hits=0, material_hits=0) == kb_coverage.COVERAGE_NO_MATERIAL


# ---- 离线匹配（本地索引） ---------------------------------------------------


async def test_offline_marks_each_slot_by_evidence_strength(monkeypatch: pytest.MonkeyPatch) -> None:
    """同一份索引里三种槽位各归各档，且人工资质/元数据槽位不参与统计。"""
    _patch_index(
        monkeypatch,
        [
            "本项目登记号为 H2024001234，受理号为 CXHS2400012。",
            "制剂规格为 25mg，稳定性考察 6 个月。",
        ],
    )
    spec = _spec(
        _slot("reg_no", "登记号", search_terms=["受理号"]),  # 主口径命中 → 可填
        _slot("impurity", "有关物质", search_terms=["杂质谱"]),  # 一条都没命中 → 无资料
        _slot("version", "版本号", from_meta=True),  # 不适用
        _slot("opinion", "技术审评意见", manual_only=True),  # 不适用
    )

    coverage = await kb_coverage.evaluate_coverage(_session(), spec, kb=_kb())

    assert coverage.source == kb_coverage.SOURCE_INDEX
    assert coverage.as_payload()["kb_name"] == "某项目知识库"
    statuses = {entry.key: entry.status for entry in coverage.entries}
    assert statuses == {
        "reg_no": kb_coverage.COVERAGE_FILLABLE,
        "impurity": kb_coverage.COVERAGE_NO_MATERIAL,
        "version": kb_coverage.COVERAGE_SKIPPED,
        "opinion": kb_coverage.COVERAGE_SKIPPED,
    }
    assert (coverage.total, coverage.checked, coverage.fillable, coverage.missing, coverage.skipped) == (4, 2, 1, 1, 2)


async def test_offline_partial_when_only_alias_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    """只有别名（如「受理号」）出现时算部分可填：值可能对得上，但需要人工确认。"""
    _patch_index(monkeypatch, ["受理号：CXHS2400012，注册分类：1 类。"])

    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(_slot("reg_no", "登记号", search_terms=["受理号"])),
        kb=_kb(),
    )

    entry = coverage.entries[0]
    assert entry.status == kb_coverage.COVERAGE_PARTIAL
    assert entry.status_label == "部分可填"
    assert entry.matched_terms == 1
    assert entry.material_hits == 1
    # 部分可填只算半分：加权覆盖率比严格覆盖率更能反映「其实还差一点」
    assert coverage.fillable_ratio == 0.0
    assert coverage.weighted_ratio == 0.5


async def test_offline_records_index_shape_in_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """切片/事实条数与截断标记要如实回报，否则用户看不懂「为什么判成无资料」。"""
    _patch_index(monkeypatch, ["含量为 99.5%。"], facts=4, truncated=True)

    coverage = await kb_coverage.evaluate_coverage(_session(), _spec(_slot("assay", "含量")), kb=_kb())

    assert (coverage.chunks, coverage.facts, coverage.truncated) == (1, 4, True)
    assert coverage.entries[0].status == kb_coverage.COVERAGE_FILLABLE


async def test_skipped_slots_do_not_dilute_ratios(monkeypatch: pytest.MonkeyPatch) -> None:
    """分母只算「需要检索的槽位」：人工/元数据槽位一旦进分母，覆盖率会被无意义地拉低。"""
    _patch_index(monkeypatch, ["规格为 25mg。"])
    spec = _spec(
        _slot("spec", "规格"),
        *[_slot(f"manual_{index}", manual_only=True) for index in range(5)],
    )

    coverage = await kb_coverage.evaluate_coverage(_session(), spec, kb=_kb())

    assert coverage.total == 6
    assert coverage.checked == 1
    assert coverage.fillable_ratio == 1.0
    assert coverage.weighted_ratio == 1.0


# ---- 降级：不挂库 / 无索引 / 检索失败 / 超时 ---------------------------------


async def test_without_knowledge_base_everything_is_no_material(monkeypatch: pytest.MonkeyPatch) -> None:
    """项目没挂知识库时全部判无资料并给出告警，前端据此提示「只用登记数据与补充说明」。"""
    _patch_index(monkeypatch, ["不该被读到"])

    coverage = await kb_coverage.evaluate_coverage(_session(), _spec(_slot("spec", "规格")), kb=None)

    assert coverage.source == kb_coverage.SOURCE_NONE
    assert coverage.entries[0].status == kb_coverage.COVERAGE_NO_MATERIAL
    assert coverage.warnings
    assert coverage.as_payload()["source_label"] == "无可用资料"


async def test_knowledge_base_without_dataset_is_treated_as_missing() -> None:
    """知识库还没绑定 RAGFlow 数据集时同样不算资料源。"""
    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(_slot("spec", "规格")),
        kb=_kb(dataset_id=None),
    )

    assert coverage.source == kb_coverage.SOURCE_NONE
    assert coverage.missing == 1


async def test_empty_index_without_live_fallback_reports_no_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """索引为空且关闭实时兜底时，必须说清「尚未建立索引」，而不是含糊地判无资料。"""
    _patch_index(monkeypatch, [])
    retriever = StubRetriever()

    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(_slot("spec", "规格")),
        kb=_kb(),
        live_retriever=retriever,
        live_fallback=False,
    )

    assert coverage.source == kb_coverage.SOURCE_NONE
    assert retriever.calls == []
    assert any("索引" in warning for warning in coverage.warnings)


# ---- 实时检索兜底 -----------------------------------------------------------


async def test_live_fallback_probes_each_slot_with_its_terms(monkeypatch: pytest.MonkeyPatch) -> None:
    """索引为空时退化为实时检索：每个槽位一次查询（多查询），关键词带主口径与别名。"""
    _patch_index(monkeypatch, [])
    retriever = StubRetriever({"规格": ["本品规格为 25mg。"], "受理号": ["受理号 CXHS2400012。"]})

    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(
            _slot("spec", "规格"),
            _slot("reg_no", "登记号", search_terms=["受理号"]),
        ),
        kb=_kb(),
        live_retriever=retriever,
    )

    assert coverage.source == kb_coverage.SOURCE_LIVE
    assert len(retriever.calls) == 2
    assert retriever.calls[0][0] == "规格"
    assert set(retriever.calls[1]) == {"登记号", "受理号"}
    statuses = {entry.key: entry.status for entry in coverage.entries}
    assert statuses == {"spec": kb_coverage.COVERAGE_FILLABLE, "reg_no": kb_coverage.COVERAGE_PARTIAL}


async def test_live_fallback_respects_slot_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """实时检索会压知识库，必须有槽位上限：超出的槽位保持无资料并告警。"""
    _patch_index(monkeypatch, [])
    retriever = StubRetriever({"规格": ["本品规格为 25mg。"]})

    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(*[_slot(f"slot_{index}", "规格") for index in range(5)]),
        kb=_kb(),
        live_retriever=retriever,
        max_slots=2,
    )

    assert len(retriever.calls) == 2
    assert coverage.fillable == 2
    assert coverage.missing == 3
    assert any("上限" in warning for warning in coverage.warnings)


async def test_live_retriever_failure_degrades_to_no_material(monkeypatch: pytest.MonkeyPatch) -> None:
    """单个槽位检索失败只降级成无资料，不能让整个预检接口 500。"""
    _patch_index(monkeypatch, [])
    retriever = StubRetriever(error=True)

    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(_slot("spec", "规格")),
        kb=_kb(),
        live_retriever=retriever,
    )

    assert coverage.entries[0].status == kb_coverage.COVERAGE_NO_MATERIAL
    assert len(retriever.calls) == 1


async def test_live_timeout_keeps_partial_result_and_warns(monkeypatch: pytest.MonkeyPatch) -> None:
    """实时检索超时必须如实告警：结果只覆盖已完成的槽位，不能假装查完了。"""
    _patch_index(monkeypatch, [])
    retriever = StubRetriever({"规格": ["本品规格为 25mg。"]}, delay=0.5)

    coverage = await kb_coverage.evaluate_coverage(
        _session(),
        _spec(_slot("spec", "规格")),
        kb=_kb(),
        live_retriever=retriever,
        live_timeout_seconds=0.01,
    )

    assert coverage.source == kb_coverage.SOURCE_LIVE
    assert any("超时" in warning for warning in coverage.warnings)


# ---- 结果落库与接口载荷 ------------------------------------------------------


async def test_job_stats_expose_counts_and_capped_missing_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    """job.stats 只放扁平计数与少量无资料槽位名，避免 stats 被长列表撑爆。"""
    _patch_index(monkeypatch, ["规格为 25mg。"])
    spec = _spec(_slot("spec", "规格"), *[_slot(f"missing_{index}", f"缺料项{index}") for index in range(10)])

    coverage = await kb_coverage.evaluate_coverage(_session(), spec, kb=_kb())
    stats = coverage.as_job_stats()

    assert stats["kb_coverage_source"] == kb_coverage.SOURCE_INDEX
    assert stats["kb_coverage_checked"] == 11
    assert stats["kb_coverage_fillable"] == 1
    assert stats["kb_coverage_missing"] == 10
    assert stats["kb_coverage_ratio"] == round(1 / 11, 3)
    assert len(cast(list[str], stats["kb_coverage_missing_labels"])) == 8


async def test_payload_carries_labels_for_every_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    """接口载荷必须自带中文标签，前端不做状态文案映射。"""
    _patch_index(monkeypatch, ["规格为 25mg。"])

    payload = (
        await kb_coverage.evaluate_coverage(
            _session(),
            _spec(_slot("spec", "规格"), _slot("version", "版本号", from_meta=True)),
            kb=_kb(),
        )
    ).as_payload()

    assert payload["fillable_ratio"] == 1.0
    slots = {slot["key"]: slot for slot in payload["slots"]}
    assert slots["spec"]["status_label"] == "可填"
    assert slots["version"]["status_label"] == "不适用"


def test_load_index_texts_skips_database_when_budget_is_zero() -> None:
    """上限为 0 时直接返回空索引并标记截断，不去打数据库。"""
    material = asyncio.run(kb_coverage.load_index_texts(_session(), uuid.uuid4(), max_chunks=0))
    assert material.texts == []
    assert material.truncated is True
