"""智能体模块 API 请求/响应模型。

字段与 DB、OpenAPI 严格一致：前端类型由 OpenAPI 生成，任何字段漂移都会在 CI 暴露。
所有响应都走 `DataResponse[具体模型]`，禁止 `dict` / `Any` 作为 `data`。
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

LanguageCode = Literal["zh", "en"]


class VoiceOption(BaseModel):
    """可选音色（含许可信息，TC-010 交付依据之一）。"""

    voice_id: str
    language: LanguageCode
    display_name: str
    gender: str
    license: str
    version: str
    source: str


class VoiceCatalogResponse(BaseModel):
    items: list[VoiceOption]


class JobState(BaseModel):
    """渲染任务状态（轮询端点）。"""

    job_id: UUID
    status: Literal["queued", "running", "succeeded", "failed", "canceled"]
    stage: str
    progress: int = Field(ge=0, le=100)
    attempts: int = 0
    error_message: str | None = None
    version_id: UUID | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class HighlightRect(BaseModel):
    """手绘矩形：相对整页的比例坐标，按像素存会随分辨率/版式一起偏。"""

    x: float = Field(ge=0.0, lt=1.0)
    y: float = Field(ge=0.0, lt=1.0)
    w: float = Field(gt=0.0, le=1.0)
    h: float = Field(gt=0.0, le=1.0)


class HighlightRegionItem(BaseModel):
    """一个区域的人工配置；`id` 是 layout 元素 id（`s0`、`s3.r2c1`）或 `rect:N`。"""

    id: str = Field(min_length=1, max_length=64)
    #: off=不参与高亮，text=只给文字变色，area=整块铺底色
    mode: Literal["off", "text", "area"]
    color: str | None = Field(default=None, max_length=16)
    fill_alpha: int | None = Field(default=None, ge=0, le=255)
    rect: HighlightRect | None = None
    shape_sha: str | None = Field(default=None, max_length=64)


class HighlightSentenceItem(BaseModel):
    """句级微调：这句讲哪些区域、这句哪些区域不亮。"""

    text: str = Field(min_length=1, max_length=500)
    targets: list[str] = Field(default_factory=list, max_length=12)
    mute: list[str] = Field(default_factory=list, max_length=12)


class HighlightRegionsPayload(BaseModel):
    """一页的区域级配置；空对象等价于未配置（走自动判定）。"""

    regions: list[HighlightRegionItem] = Field(default_factory=list, max_length=60)
    sentences: list[HighlightSentenceItem] = Field(default_factory=list, max_length=40)


class SlideRegionItem(BaseModel):
    """可被人工点选的区域（坐标来自 layout 解析，换分辨率不会偏）。"""

    element_id: str
    kind: str = ""
    label: str = ""
    text: str = ""
    left: int = 0
    top: int = 0
    width: int = 0
    height: int = 0


class SlideRegionsResponse(BaseModel):
    """区域设置面板的数据：页面尺寸 + 元素清单 + 可逐句微调的句子。"""

    page_width: int = 0
    page_height: int = 0
    items: list[SlideRegionItem] = Field(default_factory=list)
    #: 服务端切好的句子，前端逐句配置时直接用这份文本，避免两边切法不一致导致规则匹配不上
    sentences: list[str] = Field(default_factory=list)
    #: 当前页图指纹：手绘框记录的 shape_sha 与它不一致就说明页图变了，坐标要复核
    image_sha256: str | None = None


class SlideItem(BaseModel):
    """一页幻灯片（工作台时间轴与编辑区共用）。"""

    slide_no: int
    slide_uid: UUID
    script_text: str = ""
    script_source: Literal["", "upload", "ai", "manual"] = ""
    #: 画面已换、讲稿还没按新画面重写
    script_stale: bool = False
    has_page_text: bool = False
    language: LanguageCode | None = None
    voice_id: str | None = None
    speed: float | None = None
    #: 本页高亮样式/主色覆盖；None 表示跟随模块设置
    highlight_style: str | None = None
    highlight_color: str | None = None
    #: 区域级配置（区域三态 + 句级微调）；None 表示全部按讲稿自动判定
    highlight_regions: HighlightRegionsPayload | None = None
    page_text: str | None = None
    page_notes: str | None = None
    image_url: str | None = None
    #: 时间轴用的小图（宽 320 JPEG），没有时前端回退到 image_url
    thumb_url: str | None = None
    audio_url: str | None = None
    audio_sha256: str | None = None
    duration_ms: int = 0
    has_audio: bool = False


class ReuseSummary(BaseModel):
    total_slides: int = 0
    reused_slides: int = 0
    rendered_slides: int = 0
    body_reused_slides: int = 0
    body_rendered_slides: int = 0
    head_reused: int = 0


class VersionItem(BaseModel):
    """一个成片版本。"""

    id: UUID
    version_no: int
    file_name: str
    file_size: int
    duration_ms: int
    file_sha256: str
    head_key: str
    body_key: str
    reuse: ReuseSummary
    download_url: str
    created_at: datetime | None = None


class ProjectSummary(BaseModel):
    id: UUID
    name: str
    source_filename: str
    slide_count: int
    default_language: LanguageCode
    default_voice_id: str
    speed: float
    status: Literal["draft", "rendering", "ready", "failed"]
    version_count: int = 0
    latest_version_id: UUID | None = None
    latest_error: str | None = None
    thumbnail_url: str | None = None
    updated_at: datetime | None = None


class ProjectListResponse(BaseModel):
    items: list[ProjectSummary]


ModelSource = Literal["project", "global", "active", "env"]


class ScriptRuntime(BaseModel):
    """当前项目实际生效的模型与规则，用于页面回显。"""

    model_name: str
    provider: str
    source: ModelSource
    config_id: UUID | None = None
    project_config_id: UUID | None = None
    global_config_id: UUID | None = None
    global_guide: str = ""
    project_guide: str = ""
    effective_guide: str = ""
    guide_max_chars: int = 2000
    highlight_enabled: bool = True


class ScriptAiState(BaseModel):
    """AI 讲稿初稿状态（前端横幅与时间轴标记共用）。

    计数全部由 slides 现算，不额外存表：
    - `total`：有页内文字/备注的页数（送模型的基数）
    - `done`：其中有讲稿的页数（上传/AI/手工都算）
    - `pending`：其中仍无讲稿的页数
    - `skipped`：无页内文字且无讲稿的页数（「本页无文字」）
    - `failed`：任务已结束但仍 pending 的页数（partial/failed 时才有意义）
    """

    status: Literal["idle", "queued", "running", "done", "partial", "failed", "disabled"] = "idle"
    error: str | None = None
    progress: int = Field(default=0, ge=0, le=100)
    total: int = 0
    done: int = 0
    pending: int = 0
    skipped: int = 0
    failed: int = 0


class PageImagesState(BaseModel):
    """页图（编辑态底图）生成状态。

    与 `ScriptAiState` 同构：状态与进度取自项目列，前端左栏进度条轮询
    `GET /ppt-videos/{id}/page-images/status`，终态再回填一次整份详情。
    """

    status: Literal["idle", "queued", "running", "done", "failed"] = "idle"
    error: str | None = None
    progress: int = Field(default=0, ge=0, le=100)
    done: int = 0
    total: int = 0
    job_id: UUID | None = None


class PageImagesAccepted(BaseModel):
    """页图重生成受理结果（202）：前端拿到 job_id 后开始轮询状态。"""

    job_id: UUID
    status: Literal["queued", "running"] = "queued"


class ProjectDetail(BaseModel):
    id: UUID
    name: str
    source_filename: str
    slide_count: int
    default_language: LanguageCode
    default_voice_id: str
    speed: float
    status: Literal["draft", "rendering", "ready", "failed"]
    head_key: str | None = None
    body_key: str | None = None
    current_body_key: str = ""
    body_stale: bool = False
    slides: list[SlideItem] = Field(default_factory=list)
    versions: list[VersionItem] = Field(default_factory=list)
    latest_job: JobState | None = None
    script_ai: ScriptAiState = Field(default_factory=ScriptAiState)
    page_images: PageImagesState = Field(default_factory=PageImagesState)
    script_runtime: ScriptRuntime | None = None
    source_version: int = 1
    source_download_url: str = ""
    script_guide: str = ""
    llm_config_id: UUID | None = None
    updated_at: datetime | None = None


class ProjectCreateForm(BaseModel):
    """上传项目的表单字段说明（实际以 multipart 接收，此模型仅用于 OpenAPI 文档）。"""

    name: str
    default_language: LanguageCode = "zh"
    default_voice_id: str | None = None
    speed: float = 1.0


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    default_language: LanguageCode | None = None
    default_voice_id: str | None = None
    speed: float | None = Field(default=None, ge=0.5, le=2.0)


class SlideUpdateRequest(BaseModel):
    script_text: str | None = Field(default=None, max_length=2000)
    language: LanguageCode | None = None
    voice_id: str | None = None
    speed: float | None = Field(default=None, ge=0.5, le=2.0)
    #: 本页高亮样式（text_recolor/dim_outline/dim/outline）与主色 #RRGGBB
    highlight_style: str | None = Field(default=None, max_length=16)
    highlight_color: str | None = Field(default=None, max_length=16)
    #: 区域级配置：整份替换（不做增量合并，避免前后端各存一半对不上）
    highlight_regions: HighlightRegionsPayload | None = None
    clear_language: bool = False
    clear_voice: bool = False
    clear_speed: bool = False
    clear_highlight_style: bool = False
    clear_highlight_color: bool = False
    clear_highlight_regions: bool = False


class PreviewResponse(BaseModel):
    slide_no: int
    audio_url: str
    duration_ms: int
    audio_sha256: str


class RenderAccepted(BaseModel):
    job_id: UUID
    status: Literal["queued", "running"] = "queued"


class ManifestSlideItem(BaseModel):
    slide_no: int
    image_sha256: str
    audio_sha256: str
    segment_sha256: str
    duration_ms: int
    cache_hit: bool


class ManifestResponse(BaseModel):
    version_id: UUID
    head_key: str
    body_key: str
    encoder_key: str
    total_duration_ms: int
    reuse: ReuseSummary
    slides: list[ManifestSlideItem]


class MessageResult(BaseModel):
    """无数据返回的写操作回执。"""

    message: str


# ── AI 配置 ────────────────────────────────────────────────────────────────

RewriteMode = Literal["fill_blank", "rewrite_all", "rewrite_selected", "rewrite_one"]


class AiConfigItem(BaseModel):
    """下拉里的一项模型配置。永远不返回明文 Key。"""

    id: UUID
    config_name: str
    model_name: str
    api_base_url: str
    visibility: Literal["system", "personal"]
    is_active: bool = False
    masked_api_key: str = ""
    temperature: float = 0.7
    timeout_seconds: int = 60
    owned: bool = False


class AiConfigListResponse(BaseModel):
    items: list[AiConfigItem] = Field(default_factory=list)
    global_default_id: UUID | None = None
    can_manage_global: bool = False
    global_guide: str = ""
    script_guide_max_chars: int = 2000


class AiConfigCreateRequest(BaseModel):
    config_name: str = Field(min_length=1, max_length=100)
    api_base_url: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=128)
    api_key: str = Field(min_length=1, max_length=500)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    timeout_seconds: int = Field(default=60, ge=5, le=300)
    notes: str | None = Field(default=None, max_length=500)


class AiConfigUpdateRequest(BaseModel):
    config_name: str | None = Field(default=None, min_length=1, max_length=100)
    api_base_url: str | None = Field(default=None, min_length=1, max_length=500)
    model_name: str | None = Field(default=None, min_length=1, max_length=128)
    #: 留空表示不修改已保存的 Key
    api_key: str | None = Field(default=None, max_length=500)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    timeout_seconds: int | None = Field(default=None, ge=5, le=300)
    notes: str | None = Field(default=None, max_length=500)


class AiConfigTestRequest(BaseModel):
    """连通性测试：可直接测表单值，也可测已保存的配置。"""

    config_id: UUID | None = None
    api_base_url: str | None = Field(default=None, max_length=500)
    model_name: str | None = Field(default=None, max_length=128)
    api_key: str | None = Field(default=None, max_length=500)


class AiConfigTestResponse(BaseModel):
    ok: bool
    message: str


class GlobalAiSettingsRequest(BaseModel):
    """全局默认模型与全局风格指南（需模块配置管理权限）。"""

    global_config_id: UUID | None = None
    clear_global_config: bool = False
    global_guide: str | None = Field(default=None, max_length=4000)
    clear_global_guide: bool = False


class ProjectAiSettingsRequest(BaseModel):
    llm_config_id: UUID | None = None
    clear_config: bool = False
    script_guide: str | None = Field(default=None, max_length=4000)
    clear_guide: bool = False


# ── 讲稿改写 / 修订 ────────────────────────────────────────────────────────


class ScriptRewriteRequest(BaseModel):
    mode: RewriteMode = "rewrite_selected"
    slide_uids: list[UUID] = Field(default_factory=list)
    instruction: str | None = Field(default=None, max_length=2000)
    background: bool = True


class ScriptRewriteResult(BaseModel):
    revision_id: UUID | None = None
    status: Literal["queued", "running", "done", "partial", "failed"] = "done"
    total: int = 0
    done: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[str] = Field(default_factory=list)


class RevisionItem(BaseModel):
    id: UUID
    mode: Literal[
        "fill_blank",
        "rewrite_all",
        "rewrite_selected",
        "rewrite_one",
        "source_replace",
    ]
    instruction: str | None = None
    model_name: str | None = None
    provider: str | None = None
    status: Literal["queued", "running", "succeeded", "failed"] = "running"
    progress: int = 0
    scope_count: int = 0
    applied: bool = True
    error_message: str | None = None
    requested_by_name: str | None = None
    created_at: datetime | None = None


class RevisionListResponse(BaseModel):
    items: list[RevisionItem] = Field(default_factory=list)


# ── 换源 ──────────────────────────────────────────────────────────────────


class SourceDiffEntry(BaseModel):
    status: Literal["unchanged", "changed", "added", "removed"]
    old_index: int | None = None
    new_index: int | None = None
    title: str = ""
    similarity: float = 0.0


class SourceDiffSummary(BaseModel):
    old_count: int = 0
    new_count: int = 0
    unchanged: int = 0
    changed: int = 0
    added: int = 0
    removed: int = 0
    has_changes: bool = False
    entries: list[SourceDiffEntry] = Field(default_factory=list)


class SourceApplyResult(BaseModel):
    revision_id: UUID | None = None
    source_version: int
    slide_count: int
    rewrite_uids: list[UUID] = Field(default_factory=list)
    diff: SourceDiffSummary


# ── 页级编辑 ──────────────────────────────────────────────────────────────


class EditableShapeItem(BaseModel):
    index: int
    name: str
    kind: str = ""
    text: str = ""
    has_picture: bool = False
    editable_text: bool = False


class EditableShapeList(BaseModel):
    page_index: int
    items: list[EditableShapeItem] = Field(default_factory=list)


class SlideEditTextRequest(BaseModel):
    """把页面里某个文本形状的文字换掉，格式沿用第一个 run。"""

    shape_index: int = Field(ge=0)
    text: str = Field(max_length=2000)


class SlideEditImageRequest(BaseModel):
    """替换页面里某个图片形状（实际以 multipart 接收，此模型仅用于 OpenAPI 文档）。"""

    shape_index: int = Field(ge=0)


class SlideEditResult(BaseModel):
    revision_id: UUID | None = None
    source_version: int
    page_index: int
    rewrite_uids: list[UUID] = Field(default_factory=list)
    diff: SourceDiffSummary
