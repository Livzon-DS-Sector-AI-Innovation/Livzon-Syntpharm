"""交付物模板「填充示例稿」的单元测试。

不连数据库、不连 MinIO：用 python-docx 现造母本，用脚本化的假 session 提供
模板 / 示例 / 版本号查询，断言示例文本规则、跳过规则、留档语义（kind=sample、
is_current=false、主表母本不变）以及错误路径。
"""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from docx import Document

from app.core.exceptions import BadRequestException
from app.modules.research.doc_template import service
from app.modules.research.report_gen.render import SlotFill, render_document
from app.modules.research.report_gen.structure import fingerprint, open_document


class _Result:
    """够用的假查询结果：被测代码只用到这几个收敛方法。"""

    def __init__(self, *, one: Any = None, rows: list[Any] | None = None) -> None:
        self._one = one
        self._rows = rows or []

    def scalar_one_or_none(self) -> Any:
        return self._one

    def scalar_one(self) -> Any:
        return self._one

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


class _ScriptedSession:
    """按调用顺序吐出预置结果，并记录新增对象与 flush 次数。"""

    def __init__(self, results: list[_Result]) -> None:
        self._results = list(results)
        self.added: list[Any] = []
        self.flushes = 0

    async def execute(self, _stmt: Any) -> _Result:
        return self._results.pop(0)

    async def get(self, _model: Any, _pk: Any) -> Any:
        raise AssertionError("示例稿生成不应按主键取行")

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1


def _template_bytes() -> bytes:
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("品种名称：").bold = True
    paragraph.add_run("____")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    table.cell(1, 1).text = ""
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _paragraph_anchor(index: int, text: str) -> dict[str, Any]:
    return {"kind": "paragraph", "index": index, "text": text, "fingerprint": fingerprint(text)}


def _template(**overrides: Any) -> SimpleNamespace:
    template = SimpleNamespace(
        id=uuid4(),
        name="研发报告模板",
        file_object_key="local:doc-gen/abc/sample.docx",
        file_ext=".docx",
        file_name="研发报告模板.docx",
        template_code=None,
        template_structure={"version": 2, "slots": []},
        is_deleted=False,
    )
    for key, value in overrides.items():
        setattr(template, key, value)
    return template


# ---------------------------------------------------------------- 示例文本规则


def test_sample_text_uses_example_without_repeating_label() -> None:
    """母本已含标签时只写标记，避免出现「品种名称：【品种名称｜…】」。"""
    slot = {
        "slot_key": "drug_name",
        "label": "品种名称",
        "anchor": {"kind": "paragraph", "text": "品种名称：____"},
    }

    assert service._sample_text(slot, "化合物A") == "【示例：化合物A】"


def test_sample_text_keeps_label_when_anchor_has_none() -> None:
    slot = {"slot_key": "conclusion", "label": "结论", "anchor": {"kind": "table_cell", "text": ""}}

    assert service._sample_text(slot, "工艺稳定") == "【结论｜示例：工艺稳定】"


def test_sample_text_falls_back_to_hint_and_owner() -> None:
    slot = {
        "slot_key": "stability",
        "label": "稳定性",
        "hint": "写明考察周期与条件",
        "owner_hint": "分析部",
        "anchor": {"kind": "table_cell", "text": ""},
    }

    assert service._sample_text(slot, None) == "【稳定性｜必填：写明考察周期与条件（责任：分析部）】"


def test_sample_text_uses_value_type_format_when_hint_missing() -> None:
    slot = {"slot_key": "due_date", "label": "完成日期", "value_type": "date", "anchor": {"text": ""}}

    assert service._sample_text(slot, None) == "【完成日期｜必填：YYYY-MM-DD】"


def test_sample_text_flattens_multiline_example() -> None:
    """多行示例折成一行：多行值会触发渲染器插段，改掉母本版式。"""
    slot = {"slot_key": "note", "label": "备注", "anchor": {"text": ""}}

    assert service._sample_text(slot, "第一行\n第二行") == "【备注｜示例：第一行；第二行】"


# ---------------------------------------------------------------- 槽位筛选


def test_sample_fills_skips_disabled_and_unbound_slots() -> None:
    slots = [
        {"slot_key": "a", "label": "A", "anchor": _paragraph_anchor(0, "品种名称：____")},
        {"slot_key": "b", "label": "B", "anchor": _paragraph_anchor(0, "x"), "is_enabled": False},
        {"slot_key": "c", "label": "C", "anchor": None},
        {"slot_key": "", "label": "无键", "anchor": _paragraph_anchor(0, "y")},
    ]

    fills = service._sample_fills(slots, {"a": "值A"})

    assert [fill.slot_key for fill in fills] == ["a"]
    assert fills[0].state == "filled"
    assert fills[0].value == "【A｜示例：值A】"


# ---------------------------------------------------------------- 生成与留档


def _capture_bytes(sink: dict[str, bytes]) -> Any:
    """替掉 store.save_bytes：把渲染出的 docx 留下来断言，返回一个假存储键。"""

    def _save(_name: str, data: bytes, _mime: str = "") -> str:
        sink["data"] = data
        return "local:doc-gen/new/sample.docx"

    return _save


def _generate_session(template: SimpleNamespace, examples: list[tuple[str, str]]) -> _ScriptedSession:
    """按 generate_sample_document 的实际查询顺序预置结果。"""
    return _ScriptedSession(
        [
            _Result(one=template),  # _load_template_or_404
            _Result(rows=examples),  # load_all_examples
            _Result(one=template.id),  # 行锁
            _Result(one=None),  # max(version_no)
            _Result(),  # 旧当前版本退位（make_current=False 时不执行，占位无副作用）
        ]
    )


async def test_generate_sample_document_marks_parent_and_keeps_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = _template(
        template_structure={
            "slots": [
                {
                    "slot_key": "drug_name",
                    "label": "品种名称",
                    "anchor": _paragraph_anchor(0, "品种名称：____"),
                    "is_enabled": True,
                },
                {
                    "slot_key": "conclusion",
                    "label": "结论",
                    "value_type": "long_text",
                    "anchor": {
                        "kind": "table_cell",
                        "table_index": 0,
                        "row": 1,
                        "col": 1,
                        "para_index": 0,
                        "text": "",
                    },
                },
            ]
        }
    )
    session = _generate_session(template, [("drug_name", "化合物A")])
    captured: dict[str, bytes] = {}
    original_key = template.file_object_key

    monkeypatch.setattr(service.store, "load_bytes", lambda _key: _template_bytes())
    monkeypatch.setattr(service.store, "save_bytes", _capture_bytes(captured))

    data = await service.generate_sample_document(session, template.id, None)

    assert data["version_no"] == 1
    assert data["slot_count"] == 2
    assert data["skipped_count"] == 0
    assert data["unresolved_count"] == 0
    version = session.added[-1]
    assert version.kind == service.VERSION_KIND_SAMPLE
    assert version.is_current is False
    assert version.file_name == "研发报告模板-填充示例.docx"
    # 主表必须一字节不动：示例稿不能顶替母本
    assert template.file_object_key == original_key

    document = open_document(captured["data"])
    assert document.paragraphs[0].text == "品种名称：【示例：化合物A】"
    assert document.tables[0].cell(1, 1).text == "【结论｜必填：填写段落说明】"


async def test_generate_sample_document_reports_unresolved_without_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = _template(
        template_structure={
            "slots": [
                {
                    "slot_key": "ghost",
                    "label": "失效项",
                    "anchor": {
                        "kind": "paragraph",
                        "index": 99,
                        "text": "模板里没有这句",
                        "fingerprint": fingerprint("模板里没有这句"),
                    },
                }
            ]
        }
    )
    session = _generate_session(template, [])
    monkeypatch.setattr(service.store, "load_bytes", lambda _key: _template_bytes())
    monkeypatch.setattr(service.store, "save_bytes", lambda _n, data, _m="": "local:doc-gen/new/sample.docx")

    data = await service.generate_sample_document(session, template.id, None)

    assert data["unresolved_count"] == 1
    assert data["slot_count"] == 1


async def test_generate_sample_document_rejects_missing_template_file() -> None:
    template = _template(file_object_key=None)
    session = _ScriptedSession([_Result(one=template)])

    with pytest.raises(BadRequestException):
        await service.generate_sample_document(session, template.id, None)


async def test_generate_sample_document_rejects_when_no_usable_slots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = _template(template_structure={"slots": [{"slot_key": "x", "label": "X", "anchor": None}]})
    session = _generate_session(template, [])
    monkeypatch.setattr(service.store, "load_bytes", lambda _key: _template_bytes())
    monkeypatch.setattr(service.store, "save_bytes", lambda _n, data, _m="": "local:doc-gen/new/sample.docx")

    with pytest.raises(BadRequestException):
        await service.generate_sample_document(session, template.id, None)


# ---------------------------------------------------------------- 版本护栏


async def test_restore_rejects_sample_version() -> None:
    template = _template()
    version = SimpleNamespace(
        id=uuid4(),
        template_id=template.id,
        is_deleted=False,
        is_current=False,
        kind=service.VERSION_KIND_SAMPLE,
        version_no=4,
    )
    session = _ScriptedSession([_Result(one=template)])
    session.get = _async_return(version)  # type: ignore[method-assign]

    with pytest.raises(BadRequestException):
        await service.restore_template_version(session, template.id, version.id, None)


async def test_delete_allows_sample_even_when_only_one_template_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = _template()
    version = SimpleNamespace(
        id=uuid4(),
        template_id=template.id,
        is_deleted=False,
        is_current=False,
        kind=service.VERSION_KIND_SAMPLE,
        version_no=4,
        updated_by=None,
    )
    session = _ScriptedSession([_Result(one=template), _Result(one=1)])
    session.get = _async_return(version)  # type: ignore[method-assign]

    await service.delete_template_version(session, template.id, version.id, None)

    assert version.is_deleted is True


def _async_return(value: Any) -> Any:
    async def _inner(*_args: Any, **_kwargs: Any) -> Any:
        return value

    return _inner


# ---------------------------------------------------------------- 渲染器配合


def test_render_placeholder_keeps_label_when_value_carries_marker() -> None:
    """示例稿最终形态：标签在左、标记在右，不重复也不丢格式。"""
    output = render_document(
        _template_bytes(),
        [
            SlotFill(
                slot_key="drug_name",
                label="品种名称",
                anchor=_paragraph_anchor(0, "品种名称：____"),
                value="【示例：化合物A】",
                state="filled",
            )
        ],
    )

    document = open_document(output.document)
    assert document.paragraphs[0].text == "品种名称：【示例：化合物A】"
    assert document.paragraphs[0].runs[0].bold is True
