"""从 Word 母本自动草拟槽位定义（上传时不要求用户选择任何配置）。

能自动推断的是**定位**（anchor）：表头+待填数据行（真空行或 ``/`` ``—`` 类占位符行）、
空值标签段落、彩色提示语段落、章节标题后的空白正文、页眉受控字段。母本里不存在的是**语义**，一律取保守默认：

- `source_roles` 只允许 material（不引用文献）；
- 表格列不做 `compute`（不猜合计/占比）；
- 字段与表格不允许 AI 草稿；只有「提示语段落 / 空章节正文」这类明显是「此处请撰写正文」
  的位置才允许草稿（前缀会被标成【AI草稿，需确认】）；
- `required` 一律 False，取不到就写 `[待补充：原因]`。

这样自动识别出来的配置可以直接用，且不违反「没有依据就不写」与「样式零改动」。
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from docx.document import Document as DocxDocument
from docx.table import Table, _Row
from docx.text.paragraph import Paragraph

from app.modules.research.doc_gen.anchors import header_paragraphs, run_color
from app.modules.research.doc_gen.grid import cell_text, distinct_row_cells, normalize
from app.modules.research.doc_gen.renderer import open_document
from app.modules.research.doc_gen.template_spec import (
    Anchor,
    ColumnSpec,
    Slot,
    TableSpec,
    TemplateSpec,
)

logger = logging.getLogger(__name__)

DEFAULT_HINT_COLORS: tuple[str, ...] = ("00B0F0",)
# 页眉受控字段：key 必须与 job.meta 的键一致，否则渲染阶段取不到值
_HEADER_FIELDS: tuple[tuple[str, str, str], ...] = (
    ("doc_code", "受控编码", "编码"),
    ("doc_version", "版本号", "版本号"),
)
_TOTAL_LABELS = ("总价", "合计", "总计")
# 序号列同义词：母本里这一列常叫「编号/No.」而非「序号」，只认「序号」会整表漏识别
_SEQ_HEADERS = frozenset({"序号", "编号", "序次", "次序", "no", "n0", "№"})
# 单元格占位符：母本用「/」「—」「待定」等标记「这里要填」，旧「严格全空」规则会把
# 这类表格整体漏掉——占位符视同空白（纯符号串或约定词即命中）。
_PLACEHOLDER_WORDS = frozenset({"TBD", "N/A", "NA", "NULL", "待定", "待补充", "待填写", "待填"})
_PLACEHOLDER_CHARS = frozenset("/／＼\\—–―-－_＿?？*…·.。")
# 母本里最常见的「此处待填」记号其实是重复字母（XXX / xxxx / ×××），比「/」用得还多，
# 旧集合不含 X 会把整表判成「无待填迹象」而漏掉。要求 ≥2 个同类符号，
# 避免把单格「X」（勾选语义）误判成空位。
_REPEAT_MARK_RE = re.compile(r"^[Xx×＊]{2,}$")
_LABEL_TAILS = ("：", ":")
_IMAGE_LABELS = ("结构式", "图片", "图谱")
_HEADING_HINTS = ("heading", "标题")
_TOC_HINTS = ("toc",)
_MAX_SLOTS = 120
# 键值/签署型表格逐格建槽的每表上限：再多的空格多半是版式留白，拆成槽位只会淹没人工核对
_MAX_KV_CELLS_PER_TABLE = 8


def _is_seq_header(text: str) -> bool:
    """序号列判定：归一化 + 去尾点 + 忽略大小写（No./NO./编号 都算）。"""
    return normalize(text).lower().rstrip(".。") in _SEQ_HEADERS


def _is_placeholder(text: str) -> bool:
    """单元格是否「等同一格空白」：空串、纯占位符号串、重复待填记号、或约定占位词。"""
    token = normalize(text)
    if not token:
        return True
    if token.upper() in _PLACEHOLDER_WORDS or all(ch in _PLACEHOLDER_CHARS for ch in token):
        return True
    return bool(_REPEAT_MARK_RE.match(token))


def _is_heading(para: Paragraph) -> bool:
    """按样式名判断标题（兼容中英文 Word 样式）。"""
    name = str(getattr(para.style, "name", "") or "").lower()
    return any(hint in name for hint in _HEADING_HINTS)


def _is_toc(para: Paragraph) -> bool:
    """目录条目（样式名含 toc），既不是标题也不该当正文。"""
    name = str(getattr(para.style, "name", "") or "").lower()
    return any(hint in name for hint in _TOC_HINTS)


def _short(text: str, limit: int = 100) -> str:
    """压缩空白并截断，用于 label / key 生成。"""
    joined = " ".join(text.split())
    return joined[:limit]


def _spec_code(data: bytes) -> str:
    """按母本内容生成稳定 code：同一份文件重复上传会命中同一套定义。"""
    return f"auto_{hashlib.sha1(data).hexdigest()[:10]}"


def _scan_header_fields(doc: DocxDocument) -> list[Slot]:
    """页眉里的受控字段（编码/版本号），值来自表单而非资料。"""
    slots: list[Slot] = []
    for key, label, needle in _HEADER_FIELDS:
        if not header_paragraphs(doc, needle):
            continue
        slots.append(
            Slot(
                key=key,
                label=label,
                from_meta=True,
                max_chars=40,
                anchors=[Anchor(type="header_field", header_contains=needle)],
            )
        )
    return slots


def _pick_header(table: Table) -> tuple[list[str], int, frozenset[int], bool, bool] | None:
    """为表格选出表头行：(列文本, header_rows, 补位格下标, 需人工核对, 键值型网格)。

    三级放宽（每降一级都把槽位标 ``needs_review``，识别得出但不装作可信）：
    1. 首行全部非空 → 直接采用（与旧规则一致，``auto``）；
    2. 首行**恰有一格为空**且总列数 ≥3（合并表头常见形态）→ 空位补「列N」，
       补出来的列名不进锚点关键词，渲染期按声明顺序对齐；
    3. 首行不可用但第二行全部非空（双行表头）→ 用第二行做列语义，``header_rows=2``。

    第 2 级再放宽到「空格不超过半数」：起草人/审核人签署表这类**键值网格**首行是
    「起草人 | 空 | 空 | 年月日」，旧规则直接选不出表头 → 整表漏识别。空格 ≥2 时
    不再按整表 ``table_rows`` 生成（会破坏版式），改由 :func:`_scan_key_value_tables`
    逐格建单元格槽位，故用末位 ``grid_like`` 标记交回调用方分流。
    """
    rows = list(table.rows)
    if len(rows) < 2:
        return None
    first = [cell_text(c) for c in distinct_row_cells(rows[0])]
    if len(first) >= 2:
        blanks = frozenset(i for i, text in enumerate(first) if not text)
        if not blanks:
            return first, 1, frozenset(), False, False
        if len(first) >= 3 and len(blanks) <= max(1, len(first) // 2):
            filled = list(first)
            for pos in blanks:
                filled[pos] = f"列{pos + 1}"
            grid_like = len(blanks) >= 2
            return filled, 1, blanks, True, grid_like
    if len(rows) >= 3:
        second = [cell_text(c) for c in distinct_row_cells(rows[1])]
        if len(second) >= 2 and all(second):
            return second, 2, frozenset(), True, False
    return None


def _scan_key_value_tables(doc: DocxDocument, claimed: set[int]) -> list[Slot]:
    """键值/签署型表格逐格建槽：每行「固定标签格 + 紧跟的空白格」= 一个单元格槽位。

    这类表（起草人/审核人签署表、两列「项目 | 内容」表）没有规整表头，按整表
    ``table_rows`` 生成会让模型编造行、破坏版式；按格定位（坐标锚点 + guard 校验
    行标签）才既填得进去又追得到出处。只取每行**第一个真空格**，不覆盖
    「姓名（职务）」这类提示文字；每表限量，避免把大表逐格拆爆。
    """
    slots: list[Slot] = []
    index = 0
    for table_pos, table in enumerate(doc.tables):
        if table_pos in claimed:
            continue
        rows = list(table.rows)
        if len(rows) < 2:
            continue
        picked = _pick_header(table)
        if picked is None:
            # 连表头都选不出来（首行大量空格/整行合并）：拿首行第一个有文本的格做定位关键词
            header_kw = [text for text in (cell_text(c) for c in distinct_row_cells(rows[0])) if text][:1]
        else:
            # 补位的「列N」不存在于原文，写进关键词会让 find_table 永远匹配失败
            header_kw = [h for pos, h in enumerate(picked[0]) if h and pos not in picked[2]]
        if not header_kw:
            continue
        emitted = 0
        seen_labels: dict[str, int] = {}
        for row_idx, row in enumerate(rows):
            if emitted >= _MAX_KV_CELLS_PER_TABLE:
                break
            cells = [cell_text(c) for c in distinct_row_cells(row)]
            if len(cells) < 2 or sum(1 for text in cells if text) > 2:
                continue  # 数据行（≥3 格有文本）交给整表规则，不逐格拆
            label_pos = next((pos for pos, text in enumerate(cells) if text), None)
            if label_pos is None:
                continue
            empty_pos = next(
                (pos for pos in range(label_pos + 1, len(cells)) if not cells[pos]),
                None,
            )
            if empty_pos is None:
                continue
            label = _short(cells[label_pos], 40)
            # 「（姓名）」「【职务】」这类是格内提示文字，不是行标签，不配当槽位名
            if not label or label[0] in "（(【[":
                continue
            seen_labels[label] = seen_labels.get(label, 0) + 1
            if seen_labels[label] > 1:
                label = f"{label}（第{row_idx + 1}行）"
            index += 1
            emitted += 1
            slots.append(
                Slot(
                    key=f"cell_{index}",
                    label=label,
                    kind="field",
                    max_chars=120,
                    review_state="needs_review",
                    draft_allowed=False,
                    anchors=[
                        Anchor(
                            type="table_cell",
                            table_header=header_kw,
                            row_index=row_idx,
                            col_index=empty_pos,
                            guard=label.split("（")[0],
                        )
                    ],
                )
            )
    return slots


def pending_rows(
    rows: list[_Row], headers: list[str], header_rows: int, seq_key: str | None
) -> tuple[bool, bool, bool, str | None]:
    """数据行「待填」状态：(存在全空行, 存在全占位符行, 存在多数格待填的行, 合计行标签)。

    除序号列外全空 = 全空行；全为 ``/`` ``—`` ``XXX`` 类占位符 = 全占位符行；首列含
    总价/合计的行记为合计行不参与判定。草拟与候选补扫共用，保证口径一致。

    第三项 ``has_partial`` 救的是**行标签型表格**：每行首格是固定标签（「技术难度」
    「考察起始原料…」），其余格全空——旧规则要求「整行除序号列外全空」，这类表
    永远不成立而整表漏掉，是表格槽位漏识别最集中的一类。命中 partial 的表格一律
    标 ``needs_review``（识别得出但不装作可信）。
    """
    has_empty = False
    has_placeholder = False
    has_partial = False
    total_label: str | None = None
    for row in rows[header_rows:]:
        texts = [cell_text(c) for c in distinct_row_cells(row)]
        first = texts[0] if texts else ""
        if first and any(label in first for label in _TOTAL_LABELS):
            total_label = first
            continue
        pending = [text for pos, text in enumerate(texts) if f"c{pos + 1}" != seq_key]
        if not pending:
            continue
        blanks = sum(1 for text in pending if _is_placeholder(text))
        if not blanks:
            continue
        if blanks == len(pending):
            if all(not text for text in pending):
                has_empty = True
            else:
                has_placeholder = True
        elif blanks >= len(pending) - 1 or (len(pending) >= 3 and blanks * 2 >= len(pending)):
            # 至多一格是固定文本，或过半格子待填 → 这张表在等内容
            has_partial = True
    return has_empty, has_placeholder, has_partial, total_label


def _scan_tables(doc: DocxDocument) -> tuple[list[Slot], set[int]]:
    """识别「表头 + 待填数据行」的可填表格，返回 (槽位, 已占用的表格下标)。

    待填判定三档（见 :func:`pending_rows`）：整行全空 / 整行全占位符（``/`` ``—``
    ``XXX`` 等）/ 多数格待填的**行标签型**表格。后两档一律标 ``needs_review``。
    首行空格过半的键值网格（签署表）不在此建整表槽位——按整表生成会让模型编造行、
    破坏版式，交给 :func:`_scan_key_value_tables` 逐格建槽，因此也不计入「已占用」。
    """
    slots: list[Slot] = []
    claimed: set[int] = set()
    index = 0
    for table_pos, table in enumerate(doc.tables):
        picked = _pick_header(table)
        if picked is None:
            continue
        headers, header_rows, filled_positions, header_review, grid_like = picked
        if grid_like:
            continue
        rows = list(table.rows)
        columns: list[ColumnSpec] = []
        seq_key: str | None = None
        for pos, text in enumerate(headers):
            key = f"c{pos + 1}"
            columns.append(ColumnSpec(key=key, label=text, max_chars=200))
            if _is_seq_header(text):
                seq_key = key
        has_empty_row, has_placeholder_row, has_partial_row, total_label = pending_rows(
            rows, headers, header_rows, seq_key
        )
        if not (has_empty_row or has_placeholder_row or has_partial_row):
            continue
        claimed.add(table_pos)
        index += 1
        slots.append(
            Slot(
                key=f"table_{index}",
                label=_short(" / ".join(headers), 150),
                kind="table",
                review_state="needs_review" if (header_review or not has_empty_row) else "auto",
                table=TableSpec(
                    header_rows=header_rows,
                    row_limit=60,
                    sequence_column=seq_key,
                    total_row_label=total_label,
                ),
                columns=columns,
                # 锚点关键词只取母本真实存在的表头文本：补位的「列N」不存在于原文，
                # 写进去会让 find_table 永远匹配失败
                anchors=[
                    Anchor(
                        type="table_rows",
                        table_header=[h for pos, h in enumerate(headers) if h and pos not in filled_positions],
                    )
                ],
            )
        )
    return slots, claimed


def _scan_label_paragraphs(doc: DocxDocument) -> list[Slot]:
    """正文里「标签：」且冒号后为空的位置（如「制剂/规格：」）。"""
    slots: list[Slot] = []
    index = 0
    for para in doc.paragraphs:
        text = normalize(para.text)
        if not text or len(text) > 60 or not text.endswith(_LABEL_TAILS):
            continue
        if _is_heading(para) or _is_toc(para):
            continue
        index += 1
        raw = para.text.strip()
        if any(hint in raw for hint in _IMAGE_LABELS):
            # 结构式/图片这类位置只留文字占位，人工贴图
            slots.append(
                Slot(
                    key=f"image_{index}",
                    label=_short(raw),
                    kind="image",
                    anchors=[Anchor(type="image_placeholder", paragraph_label=raw)],
                )
            )
            continue
        slots.append(
            Slot(
                key=f"label_{index}",
                label=_short(raw),
                kind="field",
                max_chars=300,
                anchors=[Anchor(type="paragraph_after_label", paragraph_label=raw, paragraph_match="exact")],
            )
        )
    return slots


def _scan_hint_paragraphs(doc: DocxDocument, colors: tuple[str, ...]) -> list[Slot]:
    """彩色提示语段落（母本用蓝字告诉人「这里要写什么」）→ 整段替换。"""
    wanted = {c.upper() for c in colors}
    slots: list[Slot] = []
    index = 0
    for para in doc.paragraphs:
        text = normalize(para.text)
        if not text or _is_heading(para) or _is_toc(para):
            continue
        if not any(run_color(run).upper() in wanted for run in para.runs):
            continue
        index += 1
        raw = para.text.strip()
        slots.append(
            Slot(
                key=f"paragraph_{index}",
                label=_short(raw),
                kind="paragraph",
                draft_allowed=True,
                max_chars=2000,
                anchors=[Anchor(type="replace_paragraph", paragraph_label=raw, paragraph_match="contains")],
            )
        )
    return slots


def _scan_section_bodies(doc: DocxDocument) -> list[Slot]:
    """章节标题下没有预留正文的位置 → 在标题后补写正文。"""
    paras = list(doc.paragraphs)
    slots: list[Slot] = []
    index = 0
    for pos, para in enumerate(paras):
        if not _is_heading(para):
            continue
        raw = para.text.strip()
        if not raw or normalize(raw) == "目录":
            continue
        following = next((p for p in paras[pos + 1 :] if p.text.strip()), None)
        if following is None or not _is_heading(following):
            continue  # 标题下已有正文，交给其他规则处理
        index += 1
        slots.append(
            Slot(
                key=f"section_{index}",
                label=_short(raw),
                kind="paragraph",
                draft_allowed=True,
                max_chars=2000,
                anchors=[Anchor(type="section_body", heading=raw)],
            )
        )
    return slots


def draft_spec_from_bytes(
    data: bytes,
    *,
    name: str = "",
    code: str | None = None,
    version: str = "01",
    stage: str = "",
    hint_colors: tuple[str, ...] | None = None,
) -> TemplateSpec:
    """扫描一份 Word 母本，产出可直接使用的槽位定义。

    打开失败会抛出异常（调用方需捕获并给出「文件损坏」类提示），
    其余情况即使一个槽位都没识别到也返回合法但为空的规格——由调用方决定是否拒绝。
    """
    doc = open_document(data)
    colors = tuple(hint_colors or DEFAULT_HINT_COLORS)
    slots: list[Slot] = []
    slots += _scan_header_fields(doc)
    table_slots, claimed_tables = _scan_tables(doc)
    slots += table_slots
    # 整表规则没占用的表格（签署表、行标签型表）再按格扫一遍，别整表漏掉
    slots += _scan_key_value_tables(doc, claimed_tables)
    slots += _scan_label_paragraphs(doc)
    slots += _scan_hint_paragraphs(doc, colors)
    slots += _scan_section_bodies(doc)

    deduped: list[Slot] = []
    seen: set[tuple[str, str]] = set()
    for slot in slots:
        marker = (slot.kind, slot.label)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(slot)
        if len(deduped) >= _MAX_SLOTS:
            break

    spec = TemplateSpec(
        code=code or _spec_code(data),
        name=name or "自动识别的文档模板",
        version=version,
        stage=stage,
        master_asset="",
        description="由上传的 Word 母本自动识别填充项生成",
        hint_colors=list(colors),
        unfilled_notes=[
            "填充项由母本结构自动识别，语义为保守默认：不引用文献、不做表格计算、取不到依据一律标 [待补充]",
        ],
        slots=deduped,
    )
    logger.info(
        "母本槽位自动识别完成",
        extra={"code": spec.code, "slots": len(deduped), "module_code": "research"},
    )
    return spec


def summarize_spec(spec: TemplateSpec) -> dict[str, Any]:
    """概况（用于日志与接口回显）。"""
    kinds: dict[str, int] = {}
    for slot in spec.slots:
        kinds[slot.kind] = kinds.get(slot.kind, 0) + 1
    return {
        "code": spec.code,
        "name": spec.name,
        "version": spec.version,
        "slot_count": len(spec.slots),
        "kinds": kinds,
    }


__all__ = ["DEFAULT_HINT_COLORS", "draft_spec_from_bytes", "summarize_spec"]
