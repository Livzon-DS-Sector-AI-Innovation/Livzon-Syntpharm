"""模板槽位配置：把 docx 母本中的可填位置声明为结构化槽位。

槽位定义随代码入库（而非数据库），好处是新增模板与字段约束可被 mypy/单测覆盖；
代价是新增模板需要发版。第一版按此取舍。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AnchorType = Literal[
    "global_variable",  # 全文替换占位关键词（如 XXXX）
    "table_cell",  # 表格内单个单元格
    "table_rows",  # 表格数据区（按需克隆行）
    "paragraph_after_label",  # 「名称：」冒号之后
    "replace_paragraph",  # 整段替换（母本中给人看的提示语段落）
    "section_body",  # 章节标题下的正文段
    "section_relative",  # 写在本章节（动态章节实例）标题之后，母本中不存在该标题
    "header_field",  # 页眉中的受控元数据
    "image_placeholder",  # 图片占位
]

SourceRole = Literal["material", "literature"]


class Anchor(BaseModel):
    """一个槽位在母本中的定位规则。解析失败必须显式报错，不允许退化为「猜位置」。"""

    type: AnchorType
    table_header: list[str] = Field(default_factory=list)  # 用表头单元格文本定位表格
    row_label: str | None = None
    row_match: Literal["exact", "contains"] = "contains"
    column_header: str | None = None
    row_index: int | None = None
    col_index: int | None = None
    guard: str | None = None  # 使用坐标锚点时必须声明的校验文本，防模板变更后填错格子
    paragraph_label: str | None = None
    paragraph_match: Literal["exact", "prefix", "contains"] = "exact"
    heading: str | None = None
    heading_level: int | None = None
    after_heading: int = 0
    keyword: str | None = None
    header_contains: str | None = None
    color: str | None = None  # 按字体颜色识别提示语段落（母本用 00B0F0 标记）


class ColumnSpec(BaseModel):
    """table_rows 槽位的列定义。"""

    key: str
    label: str = ""
    max_chars: int = 80
    expects: Literal["text", "number", "date", "percent"] = "text"
    compute: Literal["none", "product", "ratio"] = "none"
    operands: list[str] = Field(default_factory=list)


class TableSpec(BaseModel):
    """数据表槽位的结构约束。"""

    header_rows: int = 1
    row_limit: int = 60
    sequence_column: str | None = None  # 由代码写入的连续序号列 key
    total_row_label: str | None = None  # 合计行标签，如「1kg总价」「合计」
    keep_existing_rows: bool = True  # 母本预留空行不足时克隆，超出时删除多余空行


def _default_source_roles() -> list[SourceRole]:
    """槽位默认可取值来源：仅项目材料，不含文献。"""
    return ["material"]


class Slot(BaseModel):
    """模板中一个可填位置。"""

    key: str
    label: str
    kind: Literal["field", "paragraph", "table", "image"] = "field"
    required: bool = False
    overwrite_cell: bool = False  # 母本该格已有内容时是否允许覆盖（默认不允许）
    from_meta: bool = False  # 值取自任务元数据（受控编码/版本号等），不问模型也不标待补充
    draft_allowed: bool = False  # 允许 AI 出草稿（正文加【AI草稿，需确认】前缀）
    manual_only: bool = False  # 完全不问模型，直接标待补充
    max_chars: int = 600
    source_roles: list[SourceRole] = Field(default_factory=_default_source_roles)
    query_hint: str = ""
    # 检索同义词/别名（如「登记号」→「受理号」）：并入关键词检索，解决槽位用语与资料用语脱节
    search_terms: list[str] = Field(default_factory=list)
    expects: Literal["text", "number", "date", "percent"] = "text"
    table: TableSpec | None = None
    columns: list[ColumnSpec] = Field(default_factory=list)
    anchors: list[Anchor] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_anchors(self) -> Slot:
        if not self.anchors:
            raise ValueError(f"槽位 {self.key} 缺少锚点定义")
        if self.kind == "table":
            table_anchor = next((a for a in self.anchors if a.type == "table_rows"), None)
            if table_anchor is None:
                raise ValueError(f"表格槽位 {self.key} 必须包含 table_rows 锚点")
            if not self.columns:
                raise ValueError(f"表格槽位 {self.key} 必须声明列定义")
        return self


# ---------------------------------------------------------------------------
# 动态章节：触发规则 / 扩展点 / 章节片段
#
# 设计要点：
# 1. 触发规则是**受限声明式原语**，不是表达式求值——必须可解释、可测试、可落库。
# 2. 扩展点只声明「此处可以长出章节」；具体长出几节由数据判定 + 人工复核决定。
# 3. 章节标题一律取自预设标题池且**禁止含编号**：编号由 Word 标题样式的多级列表生成，
#    标题文字里再写一遍会变成「1. 1. 路线研究」。
# ---------------------------------------------------------------------------

TriggerOp = Literal[
    "slot_filled",  # 某槽位有实质值（非待补充/失败）
    "table_rows_at_least",  # 表格槽位有效行数 >= count
    "keyword_found",  # 解析文本中命中任一关键词
    "role_present",  # 存在某来源角色的资料文件
    "meta_equals",  # 任务元数据等于指定值
    "all_of",  # 子规则全部成立
    "any_of",  # 子规则任一成立
    "not",  # 子规则不成立
]

# 标题禁止以编号开头：阿拉伯「1. / 1、/ (1)」、中文「一、」、以及「第X章/节」
_NUMBERING_PREFIX_RE = re.compile(
    r"^\s*(?:\d+(?:\.\d+)*\s*[.、)]"
    r"|[（(]\d+[）)]"
    r"|第\s*[一二三四五六七八九十百零\d]+\s*[章节条]"
    r"|[一二三四五六七八九十]+\s*[、.])"
)

# 标题变量白名单：{index} / {meta:xxx} / {slot:xxx} / {repeat:xxx}
_TITLE_VAR_RE = re.compile(r"\{([a-z_]+)(?::([^{}]*))?\}")
_TITLE_VAR_PREFIXES = ("index", "meta", "slot", "repeat")

# 章节实例 key 与槽位 key 的前缀分隔符（展开后槽位 key = "{section_key}.{slot_key}"）
SECTION_SLOT_SEP = "."
# 实例 key 的后缀分隔符（"{fragment_key}__{index}"）
SECTION_INSTANCE_SEP = "__"


def expand_slot_key(section_key: str, slot_key: str) -> str:
    """章节实例内的槽位 key：加实例前缀，保证在重复章节中仍然唯一。"""
    return f"{section_key}{SECTION_SLOT_SEP}{slot_key}"


def split_slot_key(qualified: str) -> tuple[str | None, str]:
    """拆分展开后的槽位 key，返回 (章节实例 key, 原始槽位 key)。骨架槽位返回 (None, key)。"""
    if SECTION_INSTANCE_SEP not in qualified:
        return None, qualified
    section_key, _, raw = qualified.partition(SECTION_SLOT_SEP)
    if not raw:
        return None, qualified
    return section_key, raw


class Trigger(BaseModel):
    """章节触发条件：由数据判定的受限声明式原语。"""

    op: TriggerOp
    key: str | None = None  # slot_filled / table_rows_at_least / meta_equals 的目标槽位
    count: int = 1  # table_rows_at_least 的行数阈值
    keywords: list[str] = Field(default_factory=list)  # keyword_found
    role: str | None = None  # role_present
    value: str | None = None  # meta_equals
    of: list[Trigger] = Field(default_factory=list)  # 组合原语

    @model_validator(mode="after")
    def _check(self) -> Trigger:
        if self.op in {"slot_filled", "table_rows_at_least"} and not self.key:
            raise ValueError(f"触发规则 {self.op} 必须声明 key")
        if self.op == "keyword_found" and not self.keywords:
            raise ValueError("触发规则 keyword_found 必须声明 keywords")
        if self.op == "role_present" and not self.role:
            raise ValueError("触发规则 role_present 必须声明 role")
        if self.op == "meta_equals" and not self.key:
            raise ValueError("触发规则 meta_equals 必须声明 key")
        if self.op in {"all_of", "any_of"} and not self.of:
            raise ValueError(f"触发规则 {self.op} 必须声明子规则")
        if self.op == "not" and len(self.of) != 1:
            raise ValueError("触发规则 not 只接受一个子规则")
        return self


Trigger.model_rebuild()


class ExtensionPoint(BaseModel):
    """母本骨架中的章节扩展点：声明「此处可以长出章节」。

    heading 与 fragment 二选一：
    - heading：挂在骨架标题之后（顶层扩展点）；
    - fragment：挂在某片段的每个实例之下（多层级）。
    """

    key: str
    label: str = ""
    heading: str | None = None  # 骨架标题文本，如「工艺研究」
    fragment: str | None = None  # 父片段 key（多层级）
    level: int = 1  # 允许插入的标题层级
    fragments: list[str] = Field(default_factory=list)  # 允许出现的片段白名单
    max_instances: int = 5  # 实例数上限，防失控
    sequence: int = 0  # 同级自动排序位次

    @model_validator(mode="after")
    def _check(self) -> ExtensionPoint:
        if bool(self.heading) == bool(self.fragment):
            raise ValueError(f"扩展点 {self.key} 必须且只能声明 heading 或 fragment 之一")
        if self.level < 1:
            raise ValueError(f"扩展点 {self.key} 的 level 必须 >= 1")
        if self.max_instances < 1:
            raise ValueError(f"扩展点 {self.key} 的 max_instances 必须 >= 1")
        return self


class SectionFragment(BaseModel):
    """可动态出现的章节片段：标题池 + 局部槽位 + 触发规则。"""

    key: str
    label: str = ""
    level: int = 1
    title_pool: list[str] = Field(default_factory=list)  # 预设标题池，自动生成默认取第一项
    trigger: Trigger | None = None  # 为空表示无条件出现（仍需人工复核）
    repeat_over: str | None = None  # 表格槽位 key：每行生成一个实例
    repeat_field: str = ""  # 参与标题变量的行字段（如 route_name）
    slots: list[Slot] = Field(default_factory=list)  # 局部槽位，定义方式与骨架完全一致
    on_empty: Literal["keep_title", "skip_section"] = "keep_title"
    extension_points: list[ExtensionPoint] = Field(default_factory=list)  # 子扩展点（多层级）

    @model_validator(mode="after")
    def _check(self) -> SectionFragment:
        if not self.title_pool:
            raise ValueError(f"章节片段 {self.key} 必须声明 title_pool")
        for title in self.title_pool:
            if _NUMBERING_PREFIX_RE.match(title):
                raise ValueError(
                    f"章节片段 {self.key} 的标题池含编号前缀：{title!r}（编号应由 Word 标题样式生成，不写进标题文字）"
                )
            for prefix, _arg in _TITLE_VAR_RE.findall(title):
                if prefix not in _TITLE_VAR_PREFIXES:
                    raise ValueError(
                        f"章节片段 {self.key} 的标题变量 {{{prefix}}} 不在白名单 {_TITLE_VAR_PREFIXES} 内"
                    )
        if self.repeat_over and not self.repeat_field:
            raise ValueError(f"章节片段 {self.key} 声明了 repeat_over，必须同时声明 repeat_field")
        slot_keys = [s.key for s in self.slots]
        dup = {k for k in slot_keys if slot_keys.count(k) > 1}
        if dup:
            raise ValueError(f"章节片段 {self.key} 存在重复槽位: {sorted(dup)}")
        for point in self.extension_points:
            if point.fragment != self.key:
                raise ValueError(f"片段 {self.key} 的子扩展点 {point.key} 的 fragment 必须指向自身")
            if point.level != self.level + 1:
                raise ValueError(f"片段 {self.key} 的子扩展点 {point.key} 层级必须为 {self.level + 1}")
        return self

    @property
    def default_title(self) -> str:
        """自动生成时的默认标题：标题池第一项。"""
        return self.title_pool[0] if self.title_pool else self.key


class TemplateSpec(BaseModel):
    """一份固定模板（母本 docx + 槽位清单）。"""

    code: str
    name: str
    version: str
    stage: str = ""
    master_asset: str  # assets/templates 下的母本文件名
    description: str = ""
    hint_colors: list[str] = Field(default_factory=lambda: ["00B0F0"])
    toc_notice: str = "[目录：请在 Word 中更新页码]"
    unfilled_notes: list[str] = Field(default_factory=list)  # 本版明确不填充的区域，写进生成说明
    slots: list[Slot] = Field(default_factory=list)
    extension_points: list[ExtensionPoint] = Field(default_factory=list)  # 骨架上的顶层扩展点
    fragments: list[SectionFragment] = Field(default_factory=list)  # 可动态出现的章节片段

    @model_validator(mode="after")
    def _check_unique_keys(self) -> TemplateSpec:
        keys = [s.key for s in self.slots]
        dup = {k for k in keys if keys.count(k) > 1}
        if dup:
            raise ValueError(f"模板 {self.code} 存在重复槽位: {sorted(dup)}")
        return self

    @model_validator(mode="after")
    def _check_sections(self) -> TemplateSpec:
        """校验扩展点与章节片段的引用关系，防止配置漂移在渲染期才炸。"""
        fragment_keys = [f.key for f in self.fragments]
        dup = {k for k in fragment_keys if fragment_keys.count(k) > 1}
        if dup:
            raise ValueError(f"模板 {self.code} 存在重复章节片段: {sorted(dup)}")
        fragments = {f.key: f for f in self.fragments}

        points: list[ExtensionPoint] = list(self.extension_points)
        for fragment in self.fragments:
            points.extend(fragment.extension_points)
        point_keys = [p.key for p in points]
        dup_points = {k for k in point_keys if point_keys.count(k) > 1}
        if dup_points:
            raise ValueError(f"模板 {self.code} 存在重复扩展点: {sorted(dup_points)}")

        for point in points:
            if point.fragment and point.fragment not in fragments:
                raise ValueError(f"扩展点 {point.key} 引用了不存在的父片段 {point.fragment}")
            for key in point.fragments:
                target = fragments.get(key)
                if target is None:
                    raise ValueError(f"扩展点 {point.key} 引用了不存在的章节片段 {key}")
                if target.level != point.level:
                    raise ValueError(
                        f"扩展点 {point.key}(L{point.level}) 引用的片段 {key} 层级为 L{target.level}，不一致"
                    )
            if not point.fragments:
                raise ValueError(f"扩展点 {point.key} 未声明任何允许的章节片段")

        # 片段之间通过子扩展点形成有向图，必须无环（A 的扩展点里再放 A 会无限递归）
        graph = {
            fragment.key: [child for point in fragment.extension_points for child in point.fragments]
            for fragment in self.fragments
        }
        self._assert_acyclic(graph)
        return self

    @staticmethod
    def _assert_acyclic(graph: dict[str, list[str]]) -> None:
        """DFS 三色标记检测环。"""
        white, gray, black = 0, 1, 2
        color: dict[str, int] = {node: white for node in graph}

        def visit(node: str) -> None:
            color[node] = gray
            for nxt in graph.get(node, []):
                if color.get(nxt, white) == gray:
                    raise ValueError(f"章节片段存在循环引用：{node} → {nxt}")
                if color.get(nxt, white) == white:
                    visit(nxt)
            color[node] = black

        for node in graph:
            if color[node] == white:
                visit(node)

    @property
    def slot_keys(self) -> list[str]:
        """全部骨架槽位 key。"""
        return [s.key for s in self.slots]

    def slot(self, key: str) -> Slot | None:
        """按 key 取骨架槽位（不接受展开后的带前缀 key）。"""
        return next((s for s in self.slots if s.key == key), None)

    def slots_of_kind(self, kind: str) -> list[Slot]:
        """按类型取骨架槽位列表。"""
        return [s for s in self.slots if s.kind == kind]

    # --- 动态章节相关查询 ---

    @property
    def has_sections(self) -> bool:
        """本模板是否声明了动态章节能力。"""
        return bool(self.extension_points)

    def fragment(self, key: str) -> SectionFragment | None:
        """按 key 取章节片段。"""
        return next((f for f in self.fragments if f.key == key), None)

    def extension_point(self, key: str) -> ExtensionPoint | None:
        """按 key 取扩展点（含片段内的子扩展点）。"""
        for point in self.extension_points:
            if point.key == key:
                return point
        for fragment in self.fragments:
            for point in fragment.extension_points:
                if point.key == key:
                    return point
        return None

    def fragment_slot(self, fragment_key: str, slot_key: str) -> Slot | None:
        """按片段 key + 原始槽位 key 取片段局部槽位定义。"""
        fragment = self.fragment(fragment_key)
        if fragment is None:
            return None
        return next((s for s in fragment.slots if s.key == slot_key), None)


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
TEMPLATE_DIR = ASSETS_DIR / "templates"


def master_path(spec: TemplateSpec) -> Path:
    """母本文件的仓库内路径。"""
    return TEMPLATE_DIR / spec.master_asset
