"""
DOCX 翻译器 - 核心数据模型
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextUnit:
    """一个待翻译的文本单元（通常是一个段落）"""

    id: str
    text: str
    location_type: str  # 'body', 'header', 'footer', 'table_cell', 'nested_table_cell'
    section_index: int  # section序号（页眉页脚用到）
    table_path: str  # 表格路径描述，如 "table[0].row[1].cell[2]"
    paragraph_element: Any  # lxml element: <w:p>
    parent_element: Any  # 父容器 element（如 <w:tc>, <w:hdr>, <w:ftr>, <w:body>）
    paragraph_index: int  # 在同容器内的段落序号
    original_text_hash: str = field(default="")
    translated_text: str = field(default="")
    is_translated: bool = field(default=False)
    is_empty: bool = field(default=False)
    inline_formats: list[str] = field(default_factory=list)  # ['u', 'b', 'i'] 等内联格式标记
    sub_index: int = 0  # 当段落按 w:br 拆分时，子段序号（从0开始）
    sub_count: int = 1  # 拆分后子段总数（1 = 未拆分）

    def __post_init__(self) -> None:
        if not self.original_text_hash:
            self.original_text_hash = hashlib.md5(self.text.encode("utf-8")).hexdigest()[:12]
        self.is_empty = not self.text or not self.text.strip()


@dataclass
class TranslationBatch:
    """一批待翻译的文本单元"""

    batch_id: int
    units: list[TextUnit]
    combined_text: str = field(default="")

    def prepare_combined_text(self) -> str:
        """将所有单元文本合并为带ID标记的文本，用于批量翻译"""
        lines = []
        for unit in self.units:
            if not unit.is_empty:
                # 使用不可见的特殊格式，但为保险起见用显式标记
                lines.append(f"[ID:{unit.id}] {unit.text}")
        self.combined_text = "\n".join(lines)
        return self.combined_text


@dataclass
class TranslationResult:
    """单条翻译结果"""

    unit_id: str
    original_text: str
    translated_text: str
    success: bool
    error_message: str = ""


@dataclass
class TranslateJob:
    """一次翻译任务"""

    input_path: str
    output_path: str
    source_lang: str  # 'en', 'zh'
    target_lang: str  # 'en', 'zh'
    units: list[TextUnit] = field(default_factory=list)
    results: list[TranslationResult] = field(default_factory=list)
    glossary_path: str | None = None
