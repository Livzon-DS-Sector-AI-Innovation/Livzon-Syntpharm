"""人工在线编辑：在当前版本 docx 上原地增量改写。

为什么不走「改 slots 再整篇重渲」：

- 用户可能先下载改过再上传（``manual_upload``），整篇重渲会把这些手工修改冲掉；
- 重渲按母本回放，人工插在中间的内容没有母本锚点，重渲就丢。

所以改的是当前成品字节，改完落一个新版本（``manual_edit``），旧版随时可回滚。

定位与写入复用 ``render`` 的能力：``_locate``（下标 + 指纹双保险）、
``_set_paragraph_text``（保留 run 字体）、``_paragraph_element``（克隆 pPr/rPr）、
``_fill_row``（合并单元格只写一次）。

失败处理：一条操作被拒时不再整批回滚，而是把该位置还原成母本原样（文字与段落格式），
其余合法操作照常写入。被还原的位置同时产出一条 ``action="delete"`` 的槽位变更，
否则下次重渲会把旧值再写回去。只有一条都没生效时才不落版本。
"""

from __future__ import annotations

import logging
import re
from copy import deepcopy
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from docx.text.paragraph import Paragraph

from app.modules.research.report_gen.outline import TemplateOutline, WritablePosition, has_blank
from app.modules.research.report_gen.render import (
    _cell_at,
    _clear_paragraph,
    _fill_blank,
    _fill_row,
    _filled_text,
    _locate,
    _paragraph_element,
    _set_cell_text,
    _set_paragraph_text,
)
from app.modules.research.report_gen.schemas import ReportGenEditOperationRequest
from app.modules.research.report_gen.structure import open_document

logger = logging.getLogger(__name__)

KIND_PARAGRAPH = "paragraph"
KIND_TABLE_CELL = "table_cell"
KIND_APPEND_PARAGRAPH = "append_paragraph"
KIND_APPEND_TABLE_ROWS = "append_table_rows"

# 结构性操作放最后：插入/删除段落会让后面段落的下标漂移，
# 先把改值的做完，定位才都基于原始下标。
_OP_ORDER = {
    "update_text": 0,
    "update_cell": 0,
    "restore_position": 0,
    "append_table_row": 1,
    "delete_table_row": 1,
    "insert_paragraph": 2,
    "delete_paragraph": 3,
}

_MAX_TEXT_CHARS = 8000


@dataclass(slots=True)
class SlotChange:
    """编辑后要写回 slots 的一条变更（与 ORM 解耦，便于单测）。"""

    key: str
    label: str
    anchor: dict[str, Any]
    value: str | None
    action: str = "upsert"  # upsert / delete
    operation: str = "update_text"
    before: str | None = None


@dataclass(slots=True)
class Removal:
    """一条被丢弃的操作：为什么没改，以及该处有没有还原成母本原样。"""

    key: str | None
    op: str
    reason: str
    restored: bool = False


@dataclass(slots=True)
class EditRun:
    applied: int = 0
    removals: list[Removal] = field(default_factory=list)
    document: bytes | None = None
    slot_changes: list[SlotChange] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """有产出字节就算成功：部分操作被拒时其余修改仍然要落版本。"""
        return self.document is not None


def _table_ref(key: str | None) -> tuple[int | None, int | None]:
    """从 ``t2r3c1`` 里取表格与行下标，供删除/追加行定位。"""
    if not key:
        return None, None
    match = re.match(r"^t(\d+)r(\d+)", key)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _row_is_empty(row: Any) -> bool:
    return all(not (cell.text or "").strip() for cell in row.cells)


def _next_paragraph(paragraph: Paragraph) -> Paragraph | None:
    """取紧跟在后面的正文段落；跳过表格等非 ``w:p`` 节点。"""
    node = paragraph._p.getnext()  # noqa: SLF001 - python-docx 只暴露底层元素
    while node is not None:
        if node.tag.rsplit("}", 1)[-1] == "p":
            return Paragraph(node, paragraph._parent)
        node = node.getnext()
    return None


class _Editor:
    def __init__(
        self,
        document: Any,
        outline: TemplateOutline,
        rows: dict[str, Any],
    ) -> None:
        self.document = document
        self.outline = outline
        self.rows = rows
        self.positions: dict[str, WritablePosition] = outline.by_key()
        self.changes: list[SlotChange] = []
        self.removals: list[Removal] = []
        self.applied = 0
        # 同一批次里已经成功改过的位置：后续操作再失败时不能拿母本原文覆盖它
        self.touched: set[str] = set()

    # ---- 基础 ----

    def _reject(
        self,
        key: str | None,
        op: str,
        reason: str,
        *,
        position: WritablePosition | None = None,
        row: Any = None,
    ) -> None:
        """拒绝一条操作；能定位到母本位置时顺手还原，保证「报错处回到原始格式」."""
        restored = False
        if position is not None and position.key not in self.touched:
            restored = self._restore_to_template(position, row)
        self.removals.append(Removal(key=key, op=op, reason=reason, restored=restored))

    def _restore_to_template(self, position: WritablePosition, row: Any) -> bool:
        """把一处还原成母本原样：文字回原文、段落节点保留，并软删旧的写入记录."""
        original = position.text
        written = (getattr(row, "value", None) or "") if row is not None else ""
        if position.kind == KIND_TABLE_CELL:
            cell = _cell_at(self.document, position.anchor())
            if cell is None:
                return False
            self._drop_cell_tail(cell, written)
            _set_cell_text(cell, original)
        else:
            paragraph = _locate(self.document, position.anchor(), written=written)
            if paragraph is None:
                return False
            self._drop_value_tail(paragraph, written)
            if original:
                _set_paragraph_text(paragraph, original)
            else:
                _clear_paragraph(paragraph)

        if row is not None and written.strip():
            # 槽位行不软删，下次重渲会把被移除的旧值写回正文
            self.changes.append(
                SlotChange(
                    key=position.key,
                    label=position.label,
                    anchor={},
                    value=None,
                    action="delete",
                    operation="restore_position",
                    before=written,
                )
            )
        return True

    def _next_seq(self, prefix: str) -> int:
        used = [
            int(match.group(1))
            for key in list(self.rows.keys()) + [change.key for change in self.changes]
            if (match := re.match(rf"^{prefix}(\d+)$", key))
        ]
        return (max(used) + 1) if used else 1

    def _find_unique_paragraph(self, value: str | None) -> Paragraph | None:
        text = (value or "").strip()
        if not text:
            return None
        matches = [paragraph for paragraph in self.document.paragraphs if paragraph.text.strip() == text]
        return matches[0] if len(matches) == 1 else None

    def _appended_row_count(self, table_index: int) -> int:
        count = 0
        for row in self.rows.values():
            anchor = row.anchor if isinstance(row.anchor, dict) else {}
            if anchor.get("kind") != KIND_APPEND_TABLE_ROWS or anchor.get("table_index") != table_index:
                continue
            count += len(anchor.get("rows") or [])
        return count

    def _upsert_position(
        self, position: WritablePosition, value: str, *, before: str | None, operation: str
    ) -> None:
        self.changes.append(
            SlotChange(
                key=position.key,
                label=position.label,
                anchor={**position.anchor(), "manual": True},
                value=value,
                operation=operation,
                before=before,
            )
        )

    # ---- 七类操作 ----

    def _update_text(self, operation: ReportGenEditOperationRequest) -> None:
        position = self.positions.get(operation.key or "")
        if position is None:
            self._reject(operation.key, operation.op, "定位不到这个位置（母本可能换过版），请重新生成")
            return
        row = self.rows.get(position.key)
        text = (operation.text or "").strip()
        if not text:
            self._reject(
                operation.key,
                operation.op,
                "内容不能为空；要去掉这一段请用删除",
                position=position,
                row=row,
            )
            return
        if len(text) > _MAX_TEXT_CHARS:
            self._reject(
                operation.key,
                operation.op,
                f"内容超过 {_MAX_TEXT_CHARS} 字，这一处已还原为原文",
                position=position,
                row=row,
            )
            return
        paragraph = _locate(self.document, position.anchor(), written=row.value if row is not None else None)
        if paragraph is None:
            self._reject(
                operation.key,
                operation.op,
                "成品里找不到这个位置（母本可能换过版），请重新生成",
                position=position,
                row=row,
            )
            return
        before = paragraph.text
        if position.append:
            # 「标签：」段：只替换冒号后的值，标签本身不能动
            label = position.text.strip()
            value = text
            if value.startswith(label):
                value = value[len(label) :].lstrip(" ：:")
            _set_paragraph_text(paragraph, f"{label}{value}")
        elif not _fill_blank(paragraph, text):
            self._rewrite_filled_placeholder(paragraph, position, row, text)
        self.touched.add(position.key)
        self._upsert_position(position, text, before=before, operation=operation.op)

    def _rewrite_filled_placeholder(
        self,
        paragraph: Paragraph,
        position: WritablePosition,
        row: Any,
        value: str,
    ) -> None:
        """改已经填过的下划线占位段：先还原占位再重新填，保住「品种名称：」这类标签。

        占位段第一次写入后下划线就不在文本里了，直接整段覆盖会把标签一起冲掉。
        """
        original = position.text
        written = (getattr(row, "value", None) or "") if row is not None else ""
        expected = _filled_text(original, written).strip() if written else ""
        if has_blank(original) and expected and (paragraph.text or "").strip() == expected:
            self._drop_value_tail(paragraph, written)
            _set_paragraph_text(paragraph, original)
            if not _fill_blank(paragraph, value):
                _set_paragraph_text(paragraph, value)
            return
        _set_paragraph_text(paragraph, value)

    def _update_cell(self, operation: ReportGenEditOperationRequest) -> None:
        position = self.positions.get(operation.key or "")
        row = self.rows.get(position.key) if position is not None else None
        if position is None or position.kind != KIND_TABLE_CELL:
            self._reject(operation.key, operation.op, "定位不到这个单元格（母本可能换过版），请重新生成")
            return
        text = (operation.text or "").strip()
        if len(text) > _MAX_TEXT_CHARS:
            self._reject(
                operation.key,
                operation.op,
                f"内容超过 {_MAX_TEXT_CHARS} 字，这一格已还原为原文",
                position=position,
                row=row,
            )
            return
        cell = _cell_at(self.document, position.anchor())
        if cell is None:
            self._reject(
                operation.key,
                operation.op,
                "成品里找不到这一格（母本可能换过版），请重新生成",
                position=position,
                row=row,
            )
            return
        before = cell.text
        _set_cell_text(cell, text)
        self.touched.add(position.key)
        self._upsert_position(position, text, before=before, operation=operation.op)

    def _insert_paragraph(self, operation: ReportGenEditOperationRequest) -> None:
        key = operation.key or ""
        text = (operation.text or "").strip()
        if not text:
            self._reject(key, operation.op, "要插入的内容不能为空")
            return
        if len(text) > _MAX_TEXT_CHARS:
            self._reject(key, operation.op, f"内容超过 {_MAX_TEXT_CHARS} 字，请分多次保存")
            return

        position = self.positions.get(key)
        if position is not None:
            row = self.rows.get(key)
            anchor_paragraph = _locate(
                self.document, position.anchor(), written=row.value if row is not None else None
            )
            location = f"「{position.label}」之后"
        elif key.startswith("ap") and key in self.rows:
            anchor_paragraph = self._find_unique_paragraph(self.rows[key].value)
            location = f"「{self.rows[key].slot_label or key}」之后"
        else:
            self._reject(key, operation.op, "只能插在母本位置或已追加的内容之后")
            return
        if anchor_paragraph is None:
            self._reject(key, operation.op, "成品里找不到插入点，请刷新后重试")
            return

        cursor = anchor_paragraph
        for line in [item for item in text.split("\n") if item.strip()]:
            element = _paragraph_element(cursor, line.strip())
            cursor._p.addnext(element)  # noqa: SLF001 - 只在插入点之后追加，保持段落样式
            cursor = Paragraph(element, cursor._parent)

        seq = self._next_seq("ap")
        self.changes.append(
            SlotChange(
                key=f"ap{seq}",
                label=f"追加段 {seq}",
                anchor={
                    "kind": KIND_APPEND_PARAGRAPH,
                    "after": key,
                    "location": location,
                    "seq": seq,
                    "manual": True,
                },
                value=text,
                operation=operation.op,
            )
        )

    def _delete_paragraph(self, operation: ReportGenEditOperationRequest) -> None:
        key = operation.key or ""
        row = self.rows.get(key)
        if not key.startswith("ap") or row is None:
            self._reject(key, operation.op, "只能删除生成或编辑时追加的段落，母本原有段落不允许删")
            return
        paragraph = self._find_unique_paragraph(row.value)
        if paragraph is None:
            self._reject(key, operation.op, "成品里找不到这段文字（可能已被改过），请先改回原文再删")
            return
        paragraph._p.getparent().remove(paragraph._p)  # noqa: SLF001 - python-docx 只暴露底层元素
        self.changes.append(
            SlotChange(
                key=key,
                label=row.slot_label or key,
                anchor={},
                value=None,
                action="delete",
                operation=operation.op,
                before=row.value,
            )
        )

    def _restore_position(self, operation: ReportGenEditOperationRequest) -> None:
        """把已填写的位置还原成母本原样：空段仍为空，下划线占位恢复成 ``____``。

        只还原内容、不删段落/单元格节点：母本版式（缩进、间距、表格框线）全部保留，
        所以和「删除追加段落」是两件事，用独立操作表达。
        """
        key = operation.key or ""
        position = self.positions.get(key)
        row = self.rows.get(key)
        if position is None or position.kind not in (KIND_PARAGRAPH, KIND_TABLE_CELL):
            self._reject(key, operation.op, "只有母本里的正文段落和表格单元格可以还原")
            return
        if row is None or not (row.value or "").strip():
            self._reject(key, operation.op, "这一处没有写入记录，不需要还原")
            return

        # 改前内容取正文当前文字：人工可能已经改过，不能拿 row.value 当改前
        before: str | None
        if position.kind == KIND_TABLE_CELL:
            cell = _cell_at(self.document, position.anchor())
            before = cell.text if cell is not None else None
        else:
            paragraph = _locate(self.document, position.anchor(), written=row.value)
            before = paragraph.text if paragraph is not None else None

        if not self._restore_to_template(position, row):
            self._reject(key, operation.op, "成品里找不到这个位置（母本可能换过版），请重新生成")
            return
        self.touched.add(key)
        if self.changes:
            self.changes[-1].before = before or row.value

    def _drop_cell_tail(self, cell: Any, value: str | None) -> None:
        """多行写入给单元格插过段落；还原时按顺序删掉这些残留节点，避免留空段撑高行。

        只删「第 2 段起文本与写入值逐行一致」的段落，对不上就停手。
        """
        lines = [line.strip() for line in (value or "").split("\n") if line.strip()]
        for line in lines[1:]:
            paragraphs = cell.paragraphs
            if len(paragraphs) <= 1 or (paragraphs[1].text or "").strip() != line:
                return
            paragraphs[1]._p.getparent().remove(paragraphs[1]._p)  # noqa: SLF001

    def _drop_value_tail(self, paragraph: Paragraph, value: str | None) -> None:
        """多行写入会在首段后面插同款段落；还原时按顺序删掉这些残留。

        只删「紧跟在后面且文本与写入值第 2..n 行完全一致」的段落：不一致就停手，
        避免把人工后来插的正文误删。
        """
        lines = [line.strip() for line in (value or "").split("\n") if line.strip()]
        if len(lines) <= 1:
            return
        cursor = paragraph
        for line in lines[1:]:
            sibling = _next_paragraph(cursor)
            if sibling is None or (sibling.text or "").strip() != line:
                return
            sibling._p.getparent().remove(sibling._p)  # noqa: SLF001 - python-docx 只暴露底层元素

    def _append_table_row(self, operation: ReportGenEditOperationRequest) -> None:
        table_index, _ = _table_ref(operation.key)
        if operation.table_index is not None:
            table_index = operation.table_index
        if table_index is None or not (0 <= table_index < len(self.document.tables)):
            self._reject(operation.key, operation.op, "定位不到要加行的表格")
            return

        table = self.document.tables[table_index]
        cells = [item.strip() for item in (operation.cells or []) if item.strip()]
        if not cells:
            self._reject(operation.key, operation.op, "请填写新增行的内容")
            return
        if len(cells) > len(table.columns):
            self._reject(operation.key, operation.op, f"最多 {len(table.columns)} 列，收到 {len(cells)} 列")
            return

        clone_index = operation.clone_from_row if operation.clone_from_row is not None else len(table.rows) - 1
        if not (0 <= clone_index < len(table.rows)):
            self._reject(operation.key, operation.op, "要克隆格式的行不存在")
            return

        new_tr = deepcopy(table.rows[clone_index]._tr)
        table._tbl.append(new_tr)
        _fill_row(table.rows[-1], cells)

        seq = self._next_seq("at")
        self.changes.append(
            SlotChange(
                key=f"at{seq}",
                label=f"表{table_index + 1} 追加行",
                anchor={
                    "kind": KIND_APPEND_TABLE_ROWS,
                    "table_index": table_index,
                    "rows": [{"cells": cells}],
                    "clone_from_row": clone_index,
                    "location": f"表{table_index + 1} 末行",
                    "seq": seq,
                    "manual": True,
                },
                value="\n".join(cells),
                operation=operation.op,
            )
        )

    def _delete_table_row(self, operation: ReportGenEditOperationRequest) -> None:
        table_index, row_index = _table_ref(operation.key)
        if operation.table_index is not None:
            table_index = operation.table_index
        if operation.row is not None:
            row_index = operation.row
        if table_index is None or row_index is None:
            self._reject(operation.key, operation.op, "定位不到要删的行")
            return
        if not (0 <= table_index < len(self.document.tables)):
            self._reject(operation.key, operation.op, "表格不存在")
            return
        table = self.document.tables[table_index]
        if row_index == 0:
            self._reject(operation.key, operation.op, "表头不能删")
            return
        if not (0 <= row_index < len(table.rows)):
            self._reject(operation.key, operation.op, "行不存在")
            return

        row = table.rows[row_index]
        appended = self._appended_row_count(table_index)
        is_appended = appended > 0 and row_index >= len(table.rows) - appended
        if not _row_is_empty(row) and not is_appended:
            self._reject(operation.key, operation.op, "只能删空行或这次追加的行，母本里有内容的行不允许删")
            return

        table._tbl.remove(row._tr)
        if is_appended:
            self._consume_appended_row(table_index)

    def _consume_appended_row(self, table_index: int) -> None:
        """删掉一条追加行后同步 at 记录；最后一条删完就软删该 slot。"""
        candidates = [
            row
            for row in self.rows.values()
            if isinstance(row.anchor, dict)
            and row.anchor.get("kind") == KIND_APPEND_TABLE_ROWS
            and row.anchor.get("table_index") == table_index
        ]
        if not candidates:
            return
        target = max(candidates, key=lambda row: len(row.anchor.get("rows") or []))
        anchor = {**target.anchor, "manual": True}
        rows = list(anchor.get("rows") or [])
        if rows:
            rows.pop()
        if rows:
            anchor["rows"] = rows
            self.changes.append(
                SlotChange(
                    key=target.slot_key,
                    label=target.slot_label or target.slot_key,
                    anchor=anchor,
                    value="\n".join(str(cell) for cell in rows[-1].get("cells") or []),
                    operation="delete_table_row",
                    before="\n".join(str(cell) for cell in rows[-1].get("cells") or []),
                )
            )
        else:
            self.changes.append(
                SlotChange(
                    key=target.slot_key,
                    label=target.slot_label or target.slot_key,
                    anchor={},
                    value=None,
                    action="delete",
                    operation="delete_table_row",
                    before=target.value,
                )
            )


def apply_operations(
    document_bytes: bytes,
    outline: TemplateOutline,
    rows: dict[str, Any],
    operations: list[ReportGenEditOperationRequest],
) -> EditRun:
    """在内存文档上按顺序应用操作；被拒的操作逐条丢弃并还原，其余照常写入。"""
    document = open_document(document_bytes)
    editor = _Editor(document, outline, rows)
    handlers = {
        "update_text": editor._update_text,
        "update_cell": editor._update_cell,
        "restore_position": editor._restore_position,
        "insert_paragraph": editor._insert_paragraph,
        "delete_paragraph": editor._delete_paragraph,
        "append_table_row": editor._append_table_row,
        "delete_table_row": editor._delete_table_row,
    }

    for operation in sorted(operations, key=lambda item: _OP_ORDER.get(item.op, 99)):
        before = len(editor.removals)
        handlers[operation.op](operation)
        if len(editor.removals) == before:
            editor.applied += 1

    for removal in editor.removals:
        logger.info(
            "report-gen edit removed",
            extra={
                "slot_key": removal.key or "",
                "operation": removal.op,
                "reason": removal.reason,
                "restored": removal.restored,
            },
        )

    buffer = BytesIO()
    document.save(buffer)
    return EditRun(
        applied=editor.applied,
        removals=editor.removals,
        document=buffer.getvalue(),
        slot_changes=editor.changes,
    )


__all__ = ["EditRun", "Removal", "SlotChange", "apply_operations"]
