"""母本基础工具：打开 docx、读段落/单元格、文本指纹、模板级填写要求。

历史上这里还负责「把母本交给模型识别填充项」（``ensure_structure`` 一族）。填充项识别
已下线：现在由智能体在生成时调用 ``read_template_outline`` 自己读母本、自己决定写哪，
判定逻辑收敛到 ``report_gen/outline.py``。本模块只保留与「识别」无关的、渲染与解析
都要用的底层能力，避免同一份 docx 打开/指纹逻辑复制两份。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from docx import Document

from app.core.exceptions import BadRequestException

# 模板级填写要求的上限：它会拼进智能体的 system prompt，太长会把可写位置总览挤掉
MAX_INSTRUCTION_CHARS = 2000


@dataclass(slots=True)
class ParagraphRef:
    index: int
    text: str
    style: str


@dataclass(slots=True)
class CellRef:
    table_index: int
    row: int
    col: int
    para_index: int
    text: str
    style: str
    label: str


def fingerprint(text: str) -> str:
    """文本指纹：忽略空白差异，用于回写时校验锚点是否漂移。"""
    normalized = re.sub(r"\s+", "", text or "")
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def open_document(data: bytes) -> Any:
    """打开 docx；损坏或不是 Word 文件时给出可读错误。"""
    try:
        return Document(BytesIO(data))
    except Exception as exc:  # noqa: BLE001 - python-docx 抛的异常类型不稳定
        raise BadRequestException("Word 模板无法解析，请确认上传的是有效的 docx 文件") from exc


def paragraph_refs(document: Any) -> list[ParagraphRef]:
    refs: list[ParagraphRef] = []
    for index, paragraph in enumerate(document.paragraphs):
        try:
            style = paragraph.style.name or ""
        except AttributeError:  # 样式表缺失的极端文档
            style = ""
        refs.append(ParagraphRef(index=index, text=(paragraph.text or "").strip(), style=style))
    return refs


def cell_refs(document: Any) -> list[CellRef]:
    """按 (表, 行, 列, 段) 展开单元格；合并单元格只取第一次出现。

    去重标识用底层节点的树内路径而不是 ``id()``：python-docx 每次访问
    ``row.cells`` 都会新建包装对象，底层 lxml 元素代理也会被回收后重建，
    ``id()`` 会被后续单元格复用，导致正常单元格被误判成「合并单元格已出现」
    而整格漏收（大表格会静默缺位）。
    """
    refs: list[CellRef] = []
    for table_index, table in enumerate(document.tables):
        seen: set[str] = set()
        for row_index, row in enumerate(table.rows):
            for col_index, cell in enumerate(row.cells):
                tc = cell._tc  # noqa: SLF001 - 识别合并单元格需要底层 w:tc 节点
                marker = tc.getroottree().getpath(tc)  # 同一节点路径恒定，不受对象回收影响
                if marker in seen:
                    continue
                seen.add(marker)
                for para_index, paragraph in enumerate(cell.paragraphs):
                    try:
                        style = paragraph.style.name or ""
                    except AttributeError:
                        style = ""
                    refs.append(
                        CellRef(
                            table_index=table_index,
                            row=row_index,
                            col=col_index,
                            para_index=para_index,
                            text=(paragraph.text or "").strip(),
                            style=style,
                            label=f"表格{table_index + 1} 第{row_index + 1}行第{col_index + 1}列",
                        )
                    )
    return refs


def structure_instruction(structure: Any) -> str:
    """模板级「填写要求」（存在 ``template_structure.instruction``，不新增列）。

    识别下线后这段文字不再给结构识别用，改为在生成时下发智能体，约束文风与写法。
    """
    data = structure if isinstance(structure, dict) else {}
    return str(data.get("instruction") or "").strip()[:MAX_INSTRUCTION_CHARS]


def with_instruction(structure: Any, instruction: str | None) -> dict[str, Any]:
    """把人工填写要求合并进既有 ``template_structure``，其余键（历史槽位等）原样保留。

    不删历史键：老模板里的 ``slots`` 仍供历史任务查阅与追溯，只是生成链路不再读它。
    """
    data = dict(structure) if isinstance(structure, dict) else {}
    text = (instruction or "").strip()[:MAX_INSTRUCTION_CHARS]
    if text:
        data["instruction"] = text
    else:
        data.pop("instruction", None)
    return data


__all__ = [
    "MAX_INSTRUCTION_CHARS",
    "CellRef",
    "ParagraphRef",
    "cell_refs",
    "fingerprint",
    "open_document",
    "paragraph_refs",
    "structure_instruction",
    "with_instruction",
]
