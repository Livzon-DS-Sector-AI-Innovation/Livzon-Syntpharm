"""AI 报告生成的请求与响应模型。

响应统一用 ``DataResponse[T]``（``app/shared/schemas.py``）：``data`` 类型具体，
前端通过 OpenAPI 生成类型时能直接拿到字段，避免 ``response_model=dict``。

填充项识别下线后，这里不再有「槽位清单 / 结构分析记录 / 槽位示例」三类模型：
生成详情页只展示执行过程、写入覆盖率与版本，不再有可编辑的填充项对照表。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ReportGenJobCreateRequest(BaseModel):
    """提交一次 AI 生成。"""

    report_id: uuid.UUID
    project_id: uuid.UUID
    deliverable_template_id: uuid.UUID = Field(..., description="Word 母本对应的交付物模板")
    doc_code: str | None = Field(None, max_length=100, description="受控编码")
    drug_name: str | None = Field(None, max_length=200, description="品种名称")
    supplement_text: str | None = Field(None, description="补充说明")


class ReportGenFeedbackBrief(BaseModel):
    """本次生成带走的评审意见摘要。

    ``supplement_text`` 里混着「人自己写的补充说明」和「系统按意见自动拼进去的段落」，
    两者在出参里长得一样，详情页因此说不清这一版到底按哪几条意见改的；
    这个列表把「带入的意见」单独列出来，与补充说明区分开。
    """

    id: uuid.UUID
    slot_key: str | None = Field(None, description="针对的位置（p12 / t2r3c1）；空=整篇意见")
    content: str


class ReportGenOpinionDigestBrief(BaseModel):
    """本次生成套用的意见汇总：只带摘要，全文留给意见库页。"""

    id: uuid.UUID
    item_count: int = Field(0, description="归并了多少条有效意见")
    status: str = Field("ok", description="ok=模型归并 / fallback=模型不可用退回原文清单")
    digest_preview: str = Field("", description="汇总全文前 300 字")
    model_name: str | None = None
    created_at: datetime


class ReportGenJobData(BaseModel):
    """任务详情：详情页头部与列表进度列都用它。

    ``slot_total / slot_filled / slot_gap`` 是沿用下来的列名，语义为
    「母本可写位置总数 / 已写位置数 / 未写空位数」，不建迁移也能表达覆盖率。
    """

    id: uuid.UUID
    report_id: uuid.UUID
    project_id: uuid.UUID
    report_title: str | None = None
    template_file_name: str | None = None
    deliverable_template_id: uuid.UUID | None = None
    status: str
    progress: int
    current_step: str | None = None
    error_message: str | None = None
    doc_code: str | None = None
    drug_name: str | None = None
    supplement_text: str | None = None
    feedback_applied: list[ReportGenFeedbackBrief] = Field(
        default_factory=list, description="本次生成带走的评审意见（已拼入补充说明）"
    )
    opinion_digest: ReportGenOpinionDigestBrief | None = Field(
        None, description="本次生成套用的历史意见汇总快照；空=当时意见库为空或汇总未生成"
    )
    document_file_name: str | None = None
    slot_total: int = Field(0, description="母本可写位置总数")
    slot_filled: int = Field(0, description="本次实际写入的位置数")
    slot_gap: int = Field(0, description="仍为空的可写位置数")
    rounds: int
    tool_mode: str | None = None
    model_config_name: str | None = None
    model_name: str | None = None
    structure_model_name: str | None = Field(None, description="结构识别时代的遗留字段，新任务恒为空")
    fallback_model_name: str | None = None
    used_fallback: bool = False
    can_cancel: bool = False
    has_document: bool = False
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime


class ReportGenJobListData(BaseModel):
    items: list[ReportGenJobData]
    active_count: int = 0


class ReportGenStepData(BaseModel):
    id: uuid.UUID
    seq: int
    kind: str
    title: str
    tool_name: str | None = None
    args_summary: dict[str, Any] | None = None
    result_summary: str | None = None
    status: str
    duration_ms: int | None = None
    created_at: datetime


class ReportGenStepListData(BaseModel):
    items: list[ReportGenStepData]
    last_seq: int = 0


class ReportGenDocumentVersionData(BaseModel):
    """一版成品文档：AI 初稿 / 人工重渲 / 人工上传。

    ``is_current`` 表示当前生效版本——交付物附件、列表页预览与下载都取它。
    """

    id: uuid.UUID
    job_id: uuid.UUID
    version_no: int
    kind: str = Field(..., description="ai_draft / manual_render / manual_upload")
    file_name: str | None = None
    file_size: int | None = None
    note: str | None = None
    is_current: bool = False
    created_at: datetime


class ReportGenDocumentVersionListData(BaseModel):
    items: list[ReportGenDocumentVersionData]
    total: int = 0


class ReportGenRenderData(BaseModel):
    """成品版本落库后的结果：版本信息 + 任务当前写入统计（人工改稿上传用）。"""

    version: ReportGenDocumentVersionData
    filled: int = 0
    gaps: int = 0
    unresolved: list[str] = Field(default_factory=list, description="母本里没找到锚点的写入记录")
    synced_deliverable: bool = Field(False, description="是否已同步回写阶段交付物附件")


class ReportGenFieldItemData(BaseModel):
    """一处可写位置：母本里的段落/单元格，或生成时追加的段落/表格行。

    ``key`` 与 ``rd_report_gen_slots.slot_key`` 同一套命名：
    ``p{下标}`` / ``t{表}r{行}c{列}`` / ``ap{n}`` / ``at{n}`` / ``ref``。
    前端用它把预览 DOM 上的标记、右侧清单行与编辑卡串成同一条记录。
    """

    key: str
    kind: str = Field(..., description="paragraph / table_cell / append_paragraph / append_table_rows / references")
    section: str | None = Field(None, description="所属章节标题；空=正文开头或追加内容")
    section_index: int = Field(-1, description="所属章节在 sections 里的下标；-1=第一个标题之前")
    label: str = Field(..., description="可读位置名，如「正文第 12 段」「表 2 第 3 行第 1 列」")
    order: int = Field(0, description="文档内阅读顺序：正文段落为段落下标，表格为其前段落数")
    writable: bool = Field(True, description="母本判定为 AI 可写；固定内容为 False，但人工仍可改")
    editable: bool = Field(True, description="人工是否可改；固定内容放开后恒为 True")
    reason: str | None = Field(None, description="不可写原因，或未写原因")
    text: str | None = Field(None, description="母本原文（写入前）")
    value: str | None = Field(None, description="当前内容（AI 写入或人工修改后的值）")
    state: str = Field(..., description="written / needs_verify / conflict / anchor_unresolved / blank / locked")
    edit_source: str = Field("ai", description="ai=生成写入 / manual=人工修改")
    human_locked: bool = Field(
        False, description="人工确认过的值：下一次生成沿用，AI 不得覆盖"
    )
    source_name: str | None = Field(None, description="来源文件或数据表")
    evidence: str | None = Field(None, description="原文证据（引文）")
    confidence: float | None = None
    context: str | None = Field(None, description="上一段或表头提示，帮助判断该处写什么")
    index: int | None = Field(None, description="段落下标；表格位置为 table_index")
    row: int | None = None
    col: int | None = None


class ReportGenSectionData(BaseModel):
    """章节树的一节：详情页按它分组展示位置清单。"""

    index: int = 0
    title: str = ""
    label: str = Field(..., description="展示名；没有标题的正文开头用「正文开头」")
    level: int = 0
    start: int = 0
    end: int = 0
    writable: int = 0
    written: int = 0
    blank: int = 0


class ReportGenReferenceLocationData(BaseModel):
    """参考资料里的一处引用位置。"""

    key: str | None = Field(None, description="可点击定位的位置 key（p12 / t2r3c1）；空=正文里没有锚点")
    label: str = Field("", description="位置名，如「正文第 12 段」「表 2 第 3 行第 1 列」")


class ReportGenReferenceData(BaseModel):
    """一条参考资料：来源名 + 它在正文里的落点（不写进 Word 文档）。"""

    index: int = Field(0, description="序号，与页面上的 [n] 一致")
    name: str = Field(..., description="来源文件名或数据表名")
    total: int = Field(0, description="该来源在正文里的引用处数（locations 是截断后的展示样本）")
    locations: list[ReportGenReferenceLocationData] = Field(
        default_factory=list, description="前若干处落点，点一条跳到正文对应位置"
    )


class ReportGenOutlineStatsData(BaseModel):
    """清单统计：口径与生成期 coverage 一致，另加人工修改与锁定数。"""

    writable_total: int = Field(0, description="母本可写位置总数")
    written: int = Field(0, description="有内容的位置数（含需核对/失效）")
    blank: int = Field(0, description="仍空着的可写位置数")
    needs_verify: int = Field(0, description="已写但没有可引用来源，需人工核对")
    conflict: int = Field(0, description="信息冲突，需人工判断")
    anchor_unresolved: int = Field(0, description="成品里找不到位置，写入没落到位")
    manual: int = Field(0, description="人工改过的位置数")
    appended: int = Field(0, description="AI 追加的段落/表格行条数（不含参考资料）")
    references: int = Field(0, description="参考资料条数（按来源去重）")
    locked: int = Field(0, description="母本里不可写的段落与单元格数（标题、固定章节等）")
    coverage_rate: float | None = Field(None, description="written ÷ writable_total")


class ReportGenOutlineData(BaseModel):
    """详情页审阅工作台的一次性数据：清单 + 统计 + 两侧结构自检数字。"""

    job_id: uuid.UUID
    status: str
    has_document: bool = False
    template_file_name: str | None = None
    template_paragraph_count: int = Field(0, description="母本正文段落数")
    template_table_count: int = Field(0, description="母本表格数")
    document_paragraph_count: int | None = Field(None, description="成品正文段落数，供预览映射自检")
    document_table_count: int | None = Field(None, description="成品表格数，供预览映射自检")
    document_paragraph_texts: list[str] = Field(
        default_factory=list,
        description=(
            "成品正文段落文本（截断），预览按内容对齐用。docx-preview 会把只含分页符的段落拆成两段，"
            "段落数与母本对不上时不能按下标硬套"
        ),
    )
    stats: ReportGenOutlineStatsData = Field(default_factory=ReportGenOutlineStatsData)
    sections: list[ReportGenSectionData] = Field(default_factory=list)
    items: list[ReportGenFieldItemData] = Field(default_factory=list)
    locked_items: list[ReportGenFieldItemData] = Field(
        default_factory=list, description="不可写位置（只带位置名与原因），用于预览点击时提示锁定"
    )
    references: list[ReportGenReferenceData] = Field(
        default_factory=list, description="参考资料（引用源）：只展示在页面右侧，不写进 Word 文档"
    )


class ReportGenEditOperationRequest(BaseModel):
    """一条编辑动作。白名单外的操作直接被模型层拒绝，不在这里兜。

    ``key`` 语义按 op 不同：改值/删段落指向目标位置；插段落指向「插在谁后面」。
    """

    op: Literal[
        "update_text",
        "update_cell",
        "restore_position",
        "insert_paragraph",
        "delete_paragraph",
        "append_table_row",
        "delete_table_row",
    ]
    key: str | None = Field(None, max_length=100, description="目标位置：p12 / t2r3c1 / ap1 / at1")
    # 单处上限 8000 字由 editor 逐条判定：超长只丢这一处并还原，不能让整个请求 422
    text: str | None = Field(None, max_length=80000, description="改后的内容（多行按段落拆分）")
    cells: list[str] | None = Field(None, description="追加表格行的各列内容")
    clone_from_row: int | None = Field(None, ge=0, description="克隆哪一行的格式；默认最后一行")
    table_index: int | None = Field(None, ge=0, description="表格下标；key 不是单元格时用它定位")
    row: int | None = Field(None, ge=0, description="行下标；key 不是单元格时用它定位")


class ReportGenEditRequest(BaseModel):
    """一次保存的整批改动：任一条不合法则整批不生效。"""

    base_version_id: uuid.UUID | None = Field(
        None, description="基于哪一版改；与当前版本不一致时返回 409，避免覆盖别人的改动"
    )
    operations: list[ReportGenEditOperationRequest] = Field(..., min_length=1, max_length=50)


class ReportGenEditRejection(BaseModel):
    key: str | None = None
    op: str
    reason: str


class ReportGenEditRemoval(BaseModel):
    """一条校验未通过、已被丢弃并还原的位置。

    与 ``rejected`` 的区别：``rejected`` 是旧的「整批失败」语义，保留只为兼容老前端；
    现在批量保存允许多条里只失败几条，失败项由这里逐条说明「为什么没改、有没有还原」。
    """

    key: str | None = None
    op: str
    reason: str
    restored: bool = Field(False, description="该位置是否已还原成母本原始文字与格式")


class ReportGenEditResultData(BaseModel):
    applied: int = Field(0, description="实际生效的操作数")
    removed: list[ReportGenEditRemoval] = Field(
        default_factory=list, description="校验未通过、已丢弃并还原的操作"
    )
    restored: int = Field(0, description="其中已还原为母本原样的条数")
    rejected: list[ReportGenEditRejection] = Field(
        default_factory=list, description="兼容字段：与 removed 同源，旧前端按整批失败展示"
    )
    version: ReportGenDocumentVersionData | None = Field(None, description="保存成功后的新版本")
    synced_deliverable: bool = Field(False, description="是否已同步回写阶段交付物附件")


class ReportGenVersionRestoreRequest(BaseModel):
    base_version_id: uuid.UUID | None = Field(None, description="并发校验：与当前版本不一致时拒绝")


class ReportGenModelTestRequest(BaseModel):
    """配置页的「测试连通」：只验证某一档能不能出字，不改任何配置。"""

    slot: Literal["main", "fallback"] = Field(description="要测试的模型档位")


class ReportGenModelTestData(BaseModel):
    ok: bool
    slot: str
    model: str | None = Field(None, description="实际使用的模型名；不含密钥与端点")
    latency_ms: int | None = Field(None, description="一次往返耗时（毫秒）")
    detail: str | None = Field(None, description="成功提示或失败原因摘要")


class ReportGenFeedbackSlotStat(BaseModel):
    """意见集中在哪些位置：同一位置反复被提，说明那里需要的不是改一次，而是改模板或写清要求。"""

    slot_key: str = Field(description="位置标识")
    count: int = Field(description="窗口内该位置被提意见的条数")


class ReportGenMetricsData(BaseModel):
    """配置页「Agent 运行情况」：窗口内**已终态**任务的聚合口径。

    比率类字段在样本为 0 时返回 ``None``，前端显示「—」而不是假的 0%，
    避免「刚上线没跑过任务」被误读成「成功率 0%」。
    评审意见部分按意见的提出时间落窗口，与任务窗口各算各的：意见是人对成品的判断，
    不依赖任务是否在窗口内开始。
    """

    window_days: int = Field(description="统计窗口天数")
    total: int = Field(0, description="窗口内终态任务数（completed + failed + cancelled）")
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    success_rate: float | None = Field(None, description="completed ÷ 终态任务数")
    avg_rounds: float | None = Field(None, description="仅统计 completed 的平均轮次")
    avg_duration_seconds: float | None = Field(None, description="仅统计 completed 的平均耗时（秒）")
    gap_rate: float | None = Field(None, description="Σ未写空位 ÷ Σ可写位置（仅 completed）")
    fallback_rate: float | None = Field(None, description="completed 中触发兜底降级的比例")
    feedback_total: int = Field(0, description="窗口内提出的意见总数")
    feedback_open: int = Field(0, description="其中仍未落实的条数（下次生成会带上）")
    feedback_applied: int = Field(0, description="其中已被后续生成落实的条数")
    feedback_ignored: int = Field(0, description="其中被判不采纳的条数")
    feedback_adoption_rate: float | None = Field(
        None, description="applied ÷ (applied + ignored)：有人处置过的意见里被采纳的比例"
    )
    feedback_slot_top: list[ReportGenFeedbackSlotStat] = Field(
        default_factory=list, description="被提意见最多的位置（最多 5 个，整篇意见不计入）"
    )
    agent_prompt_version: str = Field(description="正文生成提示词指纹（sha256 前 8 位）")
    generated_at: datetime = Field(description="本次统计时间，用于判断面板数据新鲜度")


class ReportGenFeedbackCreateRequest(BaseModel):
    """提一条评审意见：要么针对整篇，要么针对某个位置。"""

    slot_key: str | None = Field(None, max_length=100, description="针对的位置；留空=整篇意见")
    content: str = Field(..., min_length=1, max_length=1000, description="意见内容")


class ReportGenFeedbackUpdateRequest(BaseModel):
    """人工处置意见：不采纳标 ignored，需要重新打开标 open。"""

    status: Literal["open", "ignored"] = Field(description="open=重新待落实 / ignored=不采纳")


class ReportGenFeedbackData(BaseModel):
    id: str
    job_id: str
    slot_key: str | None = Field(None, description="针对的位置；空=整篇意见")
    content: str
    status: str = Field(description="open / applied / ignored")
    applied_job_id: str | None = Field(None, description="落实该意见的重生成任务")
    created_at: datetime


class ReportGenFeedbackListData(BaseModel):
    total: int = 0
    open_count: int = Field(0, description="待落实条数：下次生成会被自动带上")
    items: list[ReportGenFeedbackData] = Field(default_factory=list)


class ReportGenOpinionData(BaseModel):
    """意见库的一条：跨报告归并后的可复用写作要求。"""

    id: str
    content: str
    hit_count: int = Field(1, description="被提出次数；次数越高越普遍")
    status: str = Field(description="active=参与汇总 / disabled=人工停用")
    last_seen_at: datetime | None = None
    created_at: datetime


class ReportGenOpinionListData(BaseModel):
    total: int = 0
    active_count: int = 0
    items: list[ReportGenOpinionData] = Field(default_factory=list)


class ReportGenOpinionUpdateRequest(BaseModel):
    """人工停用/启用一条意见：停用后不再进入生成前的汇总。"""

    status: Literal["active", "disabled"] = Field(description="active=恢复参与 / disabled=停用")


class ReportGenOpinionDigestData(BaseModel):
    id: str
    item_count: int = 0
    status: str = Field(description="ok=模型归并 / fallback=模型不可用退回原文清单")
    digest_text: str
    model_name: str | None = None
    created_at: datetime


class ReportGenOpinionDigestListData(BaseModel):
    total: int = 0
    items: list[ReportGenOpinionDigestData] = Field(default_factory=list)


__all__ = [
    "ReportGenDocumentVersionData",
    "ReportGenDocumentVersionListData",
    "ReportGenEditOperationRequest",
    "ReportGenEditRejection",
    "ReportGenEditRemoval",
    "ReportGenEditRequest",
    "ReportGenEditResultData",
    "ReportGenFeedbackBrief",
    "ReportGenFeedbackCreateRequest",
    "ReportGenFeedbackData",
    "ReportGenFeedbackListData",
    "ReportGenFeedbackSlotStat",
    "ReportGenFeedbackUpdateRequest",
    "ReportGenFieldItemData",
    "ReportGenJobCreateRequest",
    "ReportGenJobData",
    "ReportGenJobListData",
    "ReportGenMetricsData",
    "ReportGenModelTestData",
    "ReportGenModelTestRequest",
    "ReportGenOpinionData",
    "ReportGenOpinionDigestBrief",
    "ReportGenOpinionDigestData",
    "ReportGenOpinionDigestListData",
    "ReportGenOpinionListData",
    "ReportGenOpinionUpdateRequest",
    "ReportGenOutlineData",
    "ReportGenOutlineStatsData",
    "ReportGenRenderData",
    "ReportGenSectionData",
    "ReportGenStepData",
    "ReportGenStepListData",
]
