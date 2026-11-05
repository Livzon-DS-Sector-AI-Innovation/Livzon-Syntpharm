/**
 * 智能体 - PPT 配音视频：前端类型薄封装。
 *
 * 契约模型一律来自 `@/types/generated/schema`（后端已声明具名 response_model），
 * 这里只做重命名与少量 UI 专用联合类型，避免各组件重复写 `components['schemas'][...]`。
 */
import type { components } from '@/types/generated/schema'

export type VoiceOption = components['schemas']['VoiceOption']
export type JobState = components['schemas']['JobState']
export type SlideItem = components['schemas']['SlideItem']
export type ScriptAiState = components['schemas']['ScriptAiState']
export type PageImagesState = components['schemas']['PageImagesState']
export type PageImagesAccepted = components['schemas']['PageImagesAccepted']
export type ReuseSummary = components['schemas']['ReuseSummary']
export type VersionItem = components['schemas']['VersionItem']
export type ProjectSummary = components['schemas']['ProjectSummary']
export type ProjectDetail = components['schemas']['ProjectDetail']
export type PreviewResult = components['schemas']['PreviewResponse']
export type RenderAccepted = components['schemas']['RenderAccepted']
export type ManifestSlideItem = components['schemas']['ManifestSlideItem']
export type VersionManifest = components['schemas']['ManifestResponse']
export type AiConfigItem = components['schemas']['AiConfigItem']
export type AiConfigListResponse = components['schemas']['AiConfigListResponse']
export type AiConfigTestResponse = components['schemas']['AiConfigTestResponse']
export type AiModelsDiscoverResponse = components['schemas']['AiModelsDiscoverResponse']
export type ScriptRuntime = components['schemas']['ScriptRuntime']
export type ScriptRewriteResult = components['schemas']['ScriptRewriteResult']
export type RevisionItem = components['schemas']['RevisionItem']
export type SourceDiffEntry = components['schemas']['SourceDiffEntry']
export type SourceDiffSummary = components['schemas']['SourceDiffSummary']
export type SourceApplyResult = components['schemas']['SourceApplyResult']
export type EditableShapeItem = components['schemas']['EditableShapeItem']
export type EditableShapeList = components['schemas']['EditableShapeList']
export type SlideEditResult = components['schemas']['SlideEditResult']
export type HighlightRect = components['schemas']['HighlightRect']
export type HighlightRegionItem = components['schemas']['HighlightRegionItem']
export type HighlightSentenceItem = components['schemas']['HighlightSentenceItem']
export type HighlightRegionsPayload = components['schemas']['HighlightRegionsPayload']
export type SlideRegionItem = components['schemas']['SlideRegionItem']
export type SlideRegionsResponse = components['schemas']['SlideRegionsResponse']
/** 后端算出的「这句会亮什么」，含兜底来源标记；仅用于面板标注，不参与渲染 */
export type SlideSentenceHint = components['schemas']['SlideSentenceHint']

/** 区域三态：不亮 / 只给文字变色 / 整块铺底色（与后端 REGION_MODES 对齐） */
export type RegionMode = 'off' | 'text' | 'area'

export const REGION_MODE_OPTIONS: { value: RegionMode; label: string }[] = [
  { value: 'off', label: '不亮' },
  { value: 'text', label: '文字变色' },
  { value: 'area', label: '区域铺底色' },
]

/** 区域类型标签：元素来自 layout 解析，手绘框是解析不出时的兜底 */
export const REGION_SOURCE_LABEL = { element: '页内元素', manual: '手绘区域' } as const

/** 改写语义（与后端 RewriteMode 对齐） */
export type RewriteMode = 'fill_blank' | 'rewrite_all' | 'rewrite_selected' | 'rewrite_one'

/** 模型来源：项目覆盖 / 全局默认 / 系统活跃配置 / 环境变量兜底 */
export type ModelSource = 'project' | 'global' | 'active' | 'env'

/** 页序列差异状态 */
export type DiffStatus = 'unchanged' | 'changed' | 'added' | 'removed'

export const MODEL_SOURCE_LABEL: Record<ModelSource, string> = {
  project: '项目覆盖',
  global: '全局默认',
  active: '系统配置',
  env: '环境变量',
}

export const MODEL_SOURCE_HINT: Record<ModelSource, string> = {
  project: '本项目单独指定，优先于全局设置',
  global: '在「AI 配置」里设定的全局默认模型',
  active: '沿用平台管理后台启用的文本模型',
  env: '尚未配置任何模型，暂时读取部署环境变量',
}

export const REWRITE_MODE_LABEL: Record<RewriteMode, string> = {
  fill_blank: '只补空页',
  rewrite_all: '全部重写',
  rewrite_selected: '按指令改写',
  rewrite_one: 'AI 改写本页',
}

export const REWRITE_MODE_HINT: Record<RewriteMode, string> = {
  fill_blank: '只给还没有讲稿的页面生成初稿，已有内容不动',
  rewrite_all: '按页面顺序重写全部讲稿，覆盖前自动存快照',
  rewrite_selected: '用一句指令改写勾选的页面，覆盖前自动存快照',
  rewrite_one: '只改当前这一页，直接把结果写回编辑框',
}

export const DIFF_STATUS_LABEL: Record<DiffStatus, string> = {
  unchanged: '未变',
  changed: '内容变更',
  added: '新增',
  removed: '删除',
}

/** 修订记录里的模式文案（比 RewriteMode 多一个换源重写） */
export const REVISION_MODE_LABEL: Record<string, string> = {
  fill_blank: '只补空页',
  rewrite_all: '全部重写',
  rewrite_selected: '按指令改写',
  rewrite_one: 'AI 改写单页',
  source_replace: '换源重写',
}

export const REVISION_STATUS_LABEL: Record<string, string> = {
  queued: '排队中',
  running: '进行中',
  succeeded: '已完成',
  failed: '失败',
}

/** AI 配置抽屉里的自定义模型表单（新建/编辑共用） */
export interface AiConfigFormValue {
  config_name: string
  api_base_url: string
  /** 勾选后的模型清单，首项作为默认模型 */
  available_models: string[]
  /** 兼容旧调用：只传单个模型名时后端会并入清单 */
  model_name?: string
  api_key?: string
  temperature?: number
  timeout_seconds?: number
}

/** 讲稿改写提交体（与后端 ScriptRewriteRequest 对齐） */
export interface ScriptRewritePayload {
  mode: RewriteMode
  slide_uids?: string[]
  instruction?: string | null
  background?: boolean
}

/** 项目默认语言；页级可覆盖，同一项目允许中英混排 */
export type LanguageCode = 'zh' | 'en'

export const LANGUAGE_LABEL: Record<LanguageCode, string> = { zh: '中文', en: '英文' }

/** 性别统一说「女声 / 男声」，不要露 female/male */
export function genderLabel(gender?: string | null): string {
  return gender === 'male' ? '男声' : '女声'
}

/** 音色展示名：后端已给纯中文名，这里只兜底空值，绝不回退到 voice_id */
export function voiceLabel(displayName?: string | null): string {
  return displayName?.trim() || '未选择'
}

/** 高亮样式中文名：列表、摘要、页签预览共用同一套说法 */
export const HIGHLIGHT_STYLE_LABEL: Record<string, string> = {
  text_recolor: '文字变色',
  dim_outline: '压暗 + 描边',
  dim: '仅压暗',
  outline: '仅描边',
}

export function highlightStyleLabel(value?: string | null): string {
  if (!value) return '跟随系统默认'
  return HIGHLIGHT_STYLE_LABEL[value] ?? '跟随系统默认'
}

/** 项目列表接口返回：items 在 data 内，total 在 meta 内 */
export interface ProjectPage {
  items: ProjectSummary[]
  total: number
}

/** Server Action 统一回执（不抛异常给客户端） */
export interface ActionResult<T> {
  success: boolean
  message: string
  data?: T
}

/** 单页编辑提交体（与后端 SlideUpdateRequest 对齐） */
export interface SlideUpdatePayload {
  script_text: string
  language?: LanguageCode | null
  voice_id?: string | null
  speed?: number | null
  /** 本页高亮样式覆盖；null 表示跟随项目设置 */
  highlight_style?: string | null
  /** 本页高亮主色 #RRGGBB；null 表示跟随项目设置 */
  highlight_color?: string | null
  /** 本页自定义高亮是否启用；关闭只让上面两项不生效，不清值 */
  highlight_override_enabled?: boolean | null
  /** 区域级配置；整份替换语义，传空数组对象即清空（后端不区分「未传」和「传空」） */
  highlight_regions?: HighlightRegionsPayload | null
  clear_language?: boolean
  clear_voice?: boolean
  clear_speed?: boolean
  clear_highlight_style?: boolean
  clear_highlight_color?: boolean
  clear_highlight_regions?: boolean
}

/** 页级可选的视觉引导样式（与后端 HIGHLIGHT_STYLES 对齐） */
export const HIGHLIGHT_STYLE_OPTIONS: { value: string; label: string }[] = [
  { value: 'text_recolor', label: '文字变色（不画框，背景不动）' },
  { value: 'dim_outline', label: '压暗 + 描边' },
  { value: 'dim', label: '仅压暗' },
  { value: 'outline', label: '仅描边' },
]

/** 项目全局设置提交体（与后端 ProjectUpdateRequest 对齐） */
export interface ProjectUpdatePayload {
  name?: string
  default_language?: LanguageCode
  default_voice_id?: string
  speed?: number
  /** 项目高亮样式；空串表示清除覆盖、回到跟随模块默认 */
  highlight_style?: string
  /** 项目高亮主色 #RRGGBB；空串表示清除覆盖 */
  highlight_color?: string
  /** 项目级自定义高亮是否启用；关闭只让上面两项不生效，不清值 */
  highlight_override_enabled?: boolean
  clear_highlight_style?: boolean
  clear_highlight_color?: boolean
}

/** 渲染阶段文案：后端返回机器码，界面显示中文 */
export const STAGE_LABEL: Record<string, string> = {
  queued: '排队中',
  parse: '解析页面',
  render: '渲染页面',
  tts: '合成旁白',
  concat: '拼接视频',
  upload: '上传成片',
  done: '已完成',
  failed: '失败',
}

/**
 * 页图生成阶段文案：后端只给一个 0~100 的百分比，阶段由区间反推，
 * 与 `page_images.py` 的 `PROGRESS_CONVERT_END` / `PROGRESS_UPLOAD_END` 保持一致。
 */
export function pageImagesStageLabel(progress: number): string {
  if (progress >= 100) return '已完成'
  if (progress >= 85) return '编码上传'
  if (progress >= 40) return '拆图'
  return '转换'
}

export const PROJECT_STATUS_LABEL: Record<string, string> = {
  draft: '草稿',
  rendering: '渲染中',
  ready: '已完成',
  failed: '失败',
}

/** 毫秒 → `mm:ss`，用于版本时长与旁白时长展示 */
export function formatDuration(ms: number): string {
  if (!ms || ms <= 0) return '00:00'
  const total = Math.round(ms / 1000)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

/** 文件大小 → 人类可读 */
export function formatFileSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index === 0 ? 0 : 1)} ${units[index]}`
}