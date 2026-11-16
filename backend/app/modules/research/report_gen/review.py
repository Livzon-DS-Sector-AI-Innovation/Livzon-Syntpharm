"""详情页审阅清单：母本可写位置 + 本次写入记录 + 成品结构。

为什么要单独一层：``service.py`` 是任务状态机，``tools.py`` 是生成期运行时；详情页要的是
「读多写少」的视图数据，塞进这两处都会把生成链路拖进查询逻辑。

位置真源仍是 ``outline.build_outline``。``rd_report_gen_slots`` 只记录「写过的位置」，
未写位置根本没有行，所以清单必须是 outline 全量位置与 slots 的并集——这也是详情页
唯一能说清「哪里空着、为什么空着」的办法。

缓存：母本快照键不可变、成品每保存一版换新键，两者都按存储键做进程内 LRU——
解析结果与字节都缓存，所以清单接口不会每 5 秒重下一遍同样的 docx。
多 worker 各自一份没有一致性问题（内容只由键决定），容量按「同时打开几个任务」定。
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research.doc_template import store
from app.modules.research.models import RdDeliverableTemplate, RdReportGenJob, RdReportGenSlot
from app.modules.research.report_gen.cache import clear_bytes, load_bytes_cached, lru_get, lru_put
from app.modules.research.report_gen.outline import (
    TemplateOutline,
    WritablePosition,
    body_table_starts,
    build_outline,
)
from app.modules.research.report_gen.references import build_reference_groups
from app.modules.research.report_gen.schemas import (
    ReportGenFieldItemData,
    ReportGenOutlineData,
    ReportGenOutlineStatsData,
    ReportGenReferenceData,
    ReportGenReferenceLocationData,
    ReportGenSectionData,
)
from app.modules.research.report_gen.structure import open_document
from app.modules.research.report_gen.template_access import load_template_bytes, template_cache_key

logger = logging.getLogger(__name__)

KIND_PARAGRAPH = "paragraph"
KIND_TABLE_CELL = "table_cell"
KIND_APPEND_PARAGRAPH = "append_paragraph"
KIND_APPEND_TABLE_ROWS = "append_table_rows"
KIND_REFERENCES = "references"

# 追加内容排在所有母本位置之后
_APPEND_ORDER = 10**6

MAX_TEXT_CHARS = 200
MAX_VALUE_CHARS = 4000
MAX_EVIDENCE_CHARS = 300

_OUTLINE_CACHE: OrderedDict[str, tuple[TemplateOutline, list[int]]] = OrderedDict()
_DOC_STATS_CACHE: OrderedDict[str, tuple[int, int, list[str]]] = OrderedDict()


def clear_cache() -> None:
    """清空解析缓存与字节缓存：供测试隔离用。

    生产链路不需要它——缓存键取自不可变的存储键，模板换版会写新键，不会命中旧字节。
    """
    _OUTLINE_CACHE.clear()
    _DOC_STATS_CACHE.clear()
    clear_bytes()


def _outline_of(cache_key: str, data: bytes) -> tuple[TemplateOutline, list[int]]:
    cached = lru_get(_OUTLINE_CACHE, cache_key)
    if cached is not None:
        return cached
    document = open_document(data)
    computed = (build_outline(document), body_table_starts(document))
    lru_put(_OUTLINE_CACHE, cache_key, computed)
    return computed


def _document_stats(cache_key: str, data: bytes) -> tuple[int, int, list[str]]:
    """成品结构：段数、表数、段落文本。

    段落文本是给前端做「按内容对齐」用的：docx-preview 会把只含分页符的段落拆成两段，
    DOM 段数比这里多一段，按下标硬套就会把后面所有位置标错。
    """
    cached = lru_get(_DOC_STATS_CACHE, cache_key)
    if cached is not None:
        return cached
    document = open_document(data)
    stats = (
        len(document.paragraphs),
        len(document.tables),
        [_clip(paragraph.text, MAX_TEXT_CHARS) or "" for paragraph in document.paragraphs],
    )
    lru_put(_DOC_STATS_CACHE, cache_key, stats)
    return stats


def _clip(text: str | None, limit: int) -> str | None:
    """压成单行并截断：清单只用来辨认位置，不展示整段正文。"""
    value = " ".join((text or "").split())
    if not value:
        return None
    return value if len(value) <= limit else value[:limit] + "…"


def _clip_raw(text: str | None, limit: int) -> str | None:
    """保留换行的截断：当前内容要回填到编辑框，不能把多段压成一行。"""
    if not text:
        return None
    return text if len(text) <= limit else text[:limit] + "…"


def _state_of(row: RdReportGenSlot | None) -> tuple[str, str | None]:
    """把写入记录翻译成前端四种语义 + 空位。

    ``pending`` 是「写了但没关联到可引用来源」，不是「没写」：必须让人看一眼，
    否则详情页会把无依据内容当成已完成。
    """
    if row is None:
        return "blank", "这次没有填写：资料里没有可用依据，也可能是没有检索到"
    if not (row.value or "").strip():
        return "blank", "这次没有填写：位置仍然空着"
    if row.state == "anchor_unresolved":
        return "anchor_unresolved", "生成好的文档里找不到这一处（模板可能换过版本），内容没有写进去"
    if row.state == "conflict":
        return "conflict", "这一处资料互相矛盾，需要人工判断后再定稿"
    if row.state == "pending":
        # 出稿自检标出来的「内容与格子含义不符」：原因写在 anchor 里，优先展示它
        verify = (row.anchor or {}).get("verify_reason") if isinstance(row.anchor, dict) else None
        if isinstance(verify, str) and verify.strip():
            return "needs_verify", verify.strip()
        return "needs_verify", "已填写，但没有可引用的来源，需要人工确认"
    return "written", None


def _edit_source(row: RdReportGenSlot | None) -> str:
    """人工标记为空时一律按 AI 写入展示。"""
    if row is None:
        return "ai"
    return str(row.edit_source or "ai")


def _human_locked(row: RdReportGenSlot | None) -> bool:
    """人工锁定标记落在 anchor 里，不额外加列：只对「下一次生成必须沿用」的行有效。"""
    if row is None or not isinstance(row.anchor, dict):
        return False
    return row.anchor.get("human_locked") is True


def _order_of(position: WritablePosition, table_starts: list[int]) -> int:
    """文档阅读顺序：段落按下标 ×10 留出空档，表格落在「表前最后一段」与「表后第一段」之间。

    ``outline.positions`` 是「先所有段落、再所有表格」，直接按它排序会把表格全排到文末；
    若表格直接用「前面有多少段」当 order，会和表后那一段撞号，表格反而排到它后面。
    """
    if position.kind == KIND_TABLE_CELL and 0 <= position.index < len(table_starts):
        return table_starts[position.index] * 10 - 5
    return position.index * 10


def _section_anchor_of(position: WritablePosition, table_starts: list[int]) -> int:
    """判断章节归属用的段落下标：表格归到它前面那一段所属的章节。

    与 ``outline._table_section`` 同一口径（取表前最后一段的标题），否则表头附近的
    单元格会被算进下一个章节，清单分组与母本对不上。
    """
    if position.kind != KIND_TABLE_CELL:
        return position.index
    if not (0 <= position.index < len(table_starts)):
        return 0
    return max(table_starts[position.index] - 1, 0)


def _section_index_of(anchor_index: int, outline: TemplateOutline) -> int:
    """按段落下标找所属章节；同名标题出现多次时也不会把两章合并。"""
    found = -1
    for index, section in enumerate(outline.sections):
        if anchor_index >= section.start:
            found = index
        else:
            break
    return found


def _section_title_of(section_index: int, outline: TemplateOutline) -> str | None:
    if 0 <= section_index < len(outline.sections):
        return outline.sections[section_index].title or None
    return None


def _item_of_position(
    position: WritablePosition,
    row: RdReportGenSlot | None,
    *,
    order: int,
    section_index: int,
    outline: TemplateOutline,
) -> ReportGenFieldItemData:
    state, reason = _state_of(row)
    if not position.writable:
        # 不可写原因以母本判定为准（封面版式/标题/已有完整内容…），别用笼统一句话盖掉；
        # 已经写过的位置也要说明「这处本来就不该写」，否则人看不出为什么会被填。
        reason = position.reason or reason or "这是模板里固定的内容，需要时可以直接补写"
    return ReportGenFieldItemData(
        key=position.key,
        kind=position.kind,
        section=_section_title_of(section_index, outline),
        section_index=section_index,
        label=position.label,
        order=order,
        writable=position.writable,
        editable=True,
        human_locked=_human_locked(row),
        reason=reason,
        text=_clip(position.text, MAX_TEXT_CHARS),
        value=_clip_raw(row.value if row is not None else None, MAX_VALUE_CHARS),
        state=state,
        edit_source=_edit_source(row),
        source_name=(row.source_name if row is not None else None) or None,
        evidence=_clip(row.evidence if row is not None else None, MAX_EVIDENCE_CHARS),
        confidence=row.confidence if row is not None else None,
        context=_clip(position.context, MAX_TEXT_CHARS),
        column_hint=_clip(position.column_hint, MAX_TEXT_CHARS) or None,
        row_span=position.row_span,
        col_span=position.col_span,
        index=position.index,
        row=position.row,
        col=position.col,
    )


def _item_of_append(row: RdReportGenSlot, *, order: int) -> ReportGenFieldItemData:
    """生成期追加的内容：母本里没有位置，单独成条，方便人核对「这句是谁加的」。"""
    anchor = row.anchor if isinstance(row.anchor, dict) else {}
    kind = str(anchor.get("kind") or KIND_APPEND_PARAGRAPH)
    state, reason = _state_of(row)
    location = _clip(str(anchor.get("location") or row.slot_label or ""), MAX_TEXT_CHARS)
    return ReportGenFieldItemData(
        key=row.slot_key,
        kind=kind,
        section=None,
        section_index=-1,
        label=location or "追加内容",
        order=order,
        writable=True,
        editable=True,
        human_locked=_human_locked(row),
        reason=reason,
        text=None,
        value=_clip_raw(row.value, MAX_VALUE_CHARS),
        state=state,
        edit_source=_edit_source(row),
        source_name=row.source_name or None,
        evidence=_clip(row.evidence, MAX_EVIDENCE_CHARS),
        confidence=row.confidence,
        context=None,
        index=anchor.get("table_index") if isinstance(anchor.get("table_index"), int) else None,
        row=anchor.get("row") if isinstance(anchor.get("row"), int) else None,
        col=None,
    )


def _ordered(order: int, kind: str) -> int:
    """追加项的 order：表格追加行跟在同表后面，其余在文末。"""
    if kind == KIND_APPEND_TABLE_ROWS:
        return order
    return _APPEND_ORDER


async def _slot_rows(session: AsyncSession, job_id: UUID) -> dict[str, RdReportGenSlot]:
    result = await session.execute(
        select(RdReportGenSlot).where(
            RdReportGenSlot.job_id == job_id,
            RdReportGenSlot.is_deleted.is_(False),
        )
    )
    return {str(row.slot_key): row for row in result.scalars().all()}


async def load_outline(
    session: AsyncSession, job_id: UUID
) -> tuple[RdReportGenJob, TemplateOutline, list[int], dict[str, RdReportGenSlot]]:
    """清单与在线编辑共用的母本上下文：任务、母本 outline、表格位置、已有写入行。

    两个入口必须用同一份母本算位置，否则「清单里点的位置」和「编辑器改的位置」会分叉。
    """
    job = await session.get(RdReportGenJob, job_id)
    if job is None or job.is_deleted:
        raise NotFoundException("生成任务")

    template: RdDeliverableTemplate | None = None
    if job.deliverable_template_id:
        template = await session.get(RdDeliverableTemplate, job.deliverable_template_id)

    try:
        template_bytes = load_template_bytes(job, template)
    except RuntimeError as exc:
        raise BadRequestException(str(exc)) from exc

    outline, table_starts = _outline_of(template_cache_key(job, template), template_bytes)
    rows = await _slot_rows(session, job_id)
    return job, outline, table_starts, rows


async def build_review(session: AsyncSession, job_id: UUID) -> ReportGenOutlineData:
    """装配详情页清单：位置全量来自母本，写入值来自 slots，结构数字来自成品。"""
    job, outline, table_starts, rows = await load_outline(session, job_id)

    document_paragraph_count: int | None = None
    document_table_count: int | None = None
    document_paragraph_texts: list[str] = []
    if job.document_object_key:
        # 成品对象键每保存一版就换新键，缓存不会读到旧内容；命中即省一次全量下载
        document_bytes = load_bytes_cached(
            str(job.document_object_key),
            lambda: store.load_bytes(str(job.document_object_key)),
        )
        if document_bytes:
            try:
                document_paragraph_count, document_table_count, document_paragraph_texts = _document_stats(
                    str(job.document_object_key), document_bytes
                )
                # 成品结构可能被人工上传版改过；缓存的键随文件走，不需要额外失效
            except Exception:  # noqa: BLE001 - 自检数字失败只影响预览对齐提示，不应挡住清单
                logger.warning(
                    "report-gen review: 成品结构解析失败",
                    exc_info=True,
                    extra={"job_id": str(job_id)},
                )

    items: list[ReportGenFieldItemData] = []
    # 兼容字段：固定内容也进 items 了，locked_items 保持为空，老前端读它不会误判
    locked_items: list[ReportGenFieldItemData] = []
    section_stats: dict[int, dict[str, int]] = {}
    fixed_total = 0

    for position in outline.positions:
        row = rows.get(position.key)
        order = _order_of(position, table_starts)
        section_index = _section_index_of(_section_anchor_of(position, table_starts), outline)
        # 母本里的每一处都可人工编辑：固定内容只是「AI 不写」，不再是「人不能改」
        item = _item_of_position(position, row, order=order, section_index=section_index, outline=outline)
        items.append(item)
        if not item.writable:
            fixed_total += 1
            continue
        bucket = section_stats.setdefault(section_index, {"writable": 0, "written": 0, "blank": 0})
        bucket["writable"] += 1
        if item.state == "blank":
            bucket["blank"] += 1
        else:
            bucket["written"] += 1

    known_keys = {position.key for position in outline.positions}
    for key, row in rows.items():
        if key in known_keys:
            continue
        anchor = row.anchor if isinstance(row.anchor, dict) else {}
        kind = str(anchor.get("kind") or KIND_APPEND_PARAGRAPH)
        if kind == KIND_REFERENCES:
            # 参考资料不写进文档，只进右栏「参考资料」面板，不能混进位置清单
            continue
        table_index = anchor.get("table_index")
        order = (
            table_starts[table_index] * 10 - 5
            if kind == KIND_APPEND_TABLE_ROWS and isinstance(table_index, int) and 0 <= table_index < len(table_starts)
            else _APPEND_ORDER
        )
        items.append(_item_of_append(row, order=_ordered(order, kind)))

    items.sort(key=lambda item: item.order)
    locked_items.sort(key=lambda item: item.order)

    # 参考资料由写入记录现算：历史任务没有结构化分组也能直接展示
    references = [
        ReportGenReferenceData(
            index=group.index,
            name=group.name,
            total=group.total,
            locations=[
                ReportGenReferenceLocationData(key=location.key, label=location.label) for location in group.locations
            ],
        )
        for group in build_reference_groups(rows.values())
    ]

    written = sum(
        1
        for item in items
        if item.writable and item.kind in (KIND_PARAGRAPH, KIND_TABLE_CELL) and item.state not in ("blank", "locked")
    )
    writable_total = outline.writable_total
    stats = ReportGenOutlineStatsData(
        writable_total=writable_total,
        written=written,
        blank=max(writable_total - written, 0),
        needs_verify=sum(1 for item in items if item.state == "needs_verify"),
        conflict=sum(1 for item in items if item.state == "conflict"),
        anchor_unresolved=sum(1 for item in items if item.state == "anchor_unresolved"),
        manual=sum(1 for item in items if item.edit_source == "manual"),
        appended=sum(1 for item in items if item.kind in (KIND_APPEND_PARAGRAPH, KIND_APPEND_TABLE_ROWS)),
        references=len(references),
        locked=fixed_total,
        coverage_rate=round(written / writable_total, 4) if writable_total else None,
    )

    sections = _build_sections(outline, section_stats, items)
    return ReportGenOutlineData(
        job_id=job.id,
        status=job.status,
        has_document=bool(job.document_object_key),
        template_file_name=job.template_file_name,
        template_paragraph_count=outline.paragraph_count,
        template_table_count=outline.table_count,
        document_paragraph_count=document_paragraph_count,
        document_table_count=document_table_count,
        document_paragraph_texts=document_paragraph_texts,
        stats=stats,
        sections=sections,
        items=items,
        locked_items=locked_items,
        references=references,
    )


def _build_sections(
    outline: TemplateOutline,
    section_stats: dict[int, dict[str, int]],
    items: list[ReportGenFieldItemData],
) -> list[ReportGenSectionData]:
    """章节列表：第一个标题之前的内容补一个「正文开头」伪节，前端不用另写分支。"""
    sections: list[ReportGenSectionData] = []
    first_start = outline.sections[0].start if outline.sections else None
    has_leading = any(item.section_index == -1 and item.kind in (KIND_PARAGRAPH, KIND_TABLE_CELL) for item in items)
    if has_leading or not outline.sections:
        bucket = section_stats.get(-1, {"writable": 0, "written": 0, "blank": 0})
        sections.append(
            ReportGenSectionData(
                index=-1,
                title="",
                label="正文开头",
                level=0,
                start=0,
                end=(first_start - 1) if first_start is not None else outline.paragraph_count - 1,
                writable=bucket["writable"],
                written=bucket["written"],
                blank=bucket["blank"],
            )
        )
    for index, section in enumerate(outline.sections):
        bucket = section_stats.get(index, {"writable": 0, "written": 0, "blank": 0})
        sections.append(
            ReportGenSectionData(
                index=index,
                title=section.title,
                label=section.title or "正文开头",
                level=section.level,
                start=section.start,
                end=section.end,
                writable=bucket["writable"],
                written=bucket["written"],
                blank=bucket["blank"],
            )
        )
    return sections


__all__ = ["build_review", "clear_cache", "load_outline"]
