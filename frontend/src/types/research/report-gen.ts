/**
 * AI 报告生成前端类型
 *
 * 结构类型全部从 OpenAPI 生成文件派生，手写部分只有「展示口径」：
 * 状态标签、色板与终态判断，避免在多处组件里重复写字符串。
 */

import type { components } from '@/types/generated/schema'

export type ReportGenJob = components['schemas']['ReportGenJobData']
export type ReportGenJobList = components['schemas']['ReportGenJobListData']
export type ReportGenStep = components['schemas']['ReportGenStepData']
export type ReportGenStepList = components['schemas']['ReportGenStepListData']
export type ReportGenJobCreate = components['schemas']['ReportGenJobCreateRequest']
export type ReportGenFeedback = components['schemas']['ReportGenFeedbackData']
export type ReportGenFeedbackList = components['schemas']['ReportGenFeedbackListData']
export type ReportGenFeedbackCreate = components['schemas']['ReportGenFeedbackCreateRequest']

export type ReportGenJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type ReportGenStepKind = 'think' | 'tool_call' | 'tool_result' | 'error' | 'status'

interface StatusMeta {
  label: string
  color: string
  /** 进度条颜色，与标签保持同一色系 */
  stroke: string
}

export const REPORT_GEN_STATUS_META: Record<ReportGenJobStatus, StatusMeta> = {
  queued: { label: '等待开始', color: 'default', stroke: '#8C8C8C' },
  running: { label: '生成中', color: 'processing', stroke: '#1677FF' },
  completed: { label: '已完成', color: 'success', stroke: '#52C41A' },
  failed: { label: '生成失败', color: 'error', stroke: '#FF4D4F' },
  cancelled: { label: '已停止', color: 'warning', stroke: '#FAAD14' },
}

export const REPORT_GEN_STEP_KIND_META: Record<ReportGenStepKind, { label: string; color: string }> = {
  think: { label: '思考', color: '#1677FF' },
  tool_call: { label: '执行动作', color: '#13C2C2' },
  tool_result: { label: '动作结果', color: '#52C41A' },
  error: { label: '出错', color: '#FF4D4F' },
  status: { label: '状态变化', color: '#8C8C8C' },
}

const TERMINAL: ReportGenJobStatus[] = ['completed', 'failed', 'cancelled']

export function isTerminal(status: string): boolean {
  return TERMINAL.includes(status as ReportGenJobStatus)
}

export function statusMeta(status: string): StatusMeta {
  return REPORT_GEN_STATUS_META[status as ReportGenJobStatus] ?? REPORT_GEN_STATUS_META.queued
}

export function stepKindMeta(kind: string): { label: string; color: string } {
  return REPORT_GEN_STEP_KIND_META[kind as ReportGenStepKind] ?? { label: kind, color: '#8C8C8C' }
}

/** 毫秒转「1m 20s」这类可读耗时；空值返回占位。 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || ms < 0) return '-'
  if (ms < 1000) return `${ms}ms`
  const totalSeconds = Math.round(ms / 1000)
  if (totalSeconds < 60) return `${totalSeconds}s`
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes < 60) return `${minutes}m ${seconds}s`
  const hours = Math.floor(minutes / 60)
  return `${hours}h ${minutes % 60}m`
}

/** 任务耗时：优先用真实起止时间，未结束则按当前时间算到当下。 */
export function jobElapsedMs(job: ReportGenJob): number | null {
  if (!job.started_at) return null
  const start = new Date(job.started_at).getTime()
  const end = job.finished_at ? new Date(job.finished_at).getTime() : Date.now()
  if (Number.isNaN(start) || Number.isNaN(end)) return null
  return Math.max(0, end - start)
}

/** 列表页判断是否需要继续轮询：有非终态任务就刷新。 */
export function hasActiveJob(jobs: ReportGenJob[]): boolean {
  return jobs.some((job) => !isTerminal(job.status))
}

/** 同一报告取最近一次任务（列表按 created_at 倒序返回）。 */
export function latestJobByReport(jobs: ReportGenJob[]): Map<string, ReportGenJob> {
  const map = new Map<string, ReportGenJob>()
  for (const job of jobs) {
    if (!map.has(job.report_id)) map.set(job.report_id, job)
  }
  return map
}

export type ReportGenOutline = components['schemas']['ReportGenOutlineData']
export type ReportGenOutlineStats = components['schemas']['ReportGenOutlineStatsData']
export type ReportGenOutlineSection = components['schemas']['ReportGenSectionData']
export type ReportGenFieldItem = components['schemas']['ReportGenFieldItemData']
export type ReportGenReference = components['schemas']['ReportGenReferenceData']
export type ReportGenReferenceLocation = components['schemas']['ReportGenReferenceLocationData']

/** AI 追加内容：预览按 DOM 标记、清单单独分组；参考资料不写进文档，不在此列 */
export const APPENDED_ITEM_KINDS: readonly string[] = ['append_paragraph', 'append_table_rows']
export type ReportGenDocumentVersion = components['schemas']['ReportGenDocumentVersionData']
export type ReportGenDocumentVersionList = components['schemas']['ReportGenDocumentVersionListData']
export type ReportGenRender = components['schemas']['ReportGenRenderData']
export type ReportGenEditOperation = components['schemas']['ReportGenEditOperationRequest']
export type ReportGenEditRequest = components['schemas']['ReportGenEditRequest']
export type ReportGenEditRejection = components['schemas']['ReportGenEditRejection']
export type ReportGenEditRemoval = components['schemas']['ReportGenEditRemoval']
export type ReportGenEditResult = components['schemas']['ReportGenEditResultData']

export type ReportGenOpinion = components['schemas']['ReportGenOpinionData']
export type ReportGenOpinionList = components['schemas']['ReportGenOpinionListData']
export type ReportGenOpinionDigestBrief = components['schemas']['ReportGenOpinionDigestBrief']
export type ReportGenOpinionDigest = components['schemas']['ReportGenOpinionDigestData']
export type ReportGenOpinionDigestList = components['schemas']['ReportGenOpinionDigestListData']
export type ReportGenOpinionStatus = 'active' | 'disabled'

export const REPORT_GEN_OPINION_STATUS_META: Record<ReportGenOpinionStatus, { label: string; color: string }> = {
  active: { label: '生效中', color: 'processing' },
  disabled: { label: '已停用', color: 'default' },
}

/** 汇总状态：fallback 要明确说出来，否则会被误以为「模型认真总结过」。 */
export const REPORT_GEN_DIGEST_STATUS_META: Record<string, { label: string; color: string }> = {
  ok: { label: 'AI 已归纳', color: 'success' },
  fallback: { label: '原始意见汇总', color: 'warning' },
}

/** 版本来源标签：在线编辑与人工上传必须区分开，否则回溯时分不清是站内改的还是外面改的。 */
export const REPORT_GEN_VERSION_KIND_LABEL: Record<string, string> = {
  ai_draft: 'AI 初稿',
  manual_upload: '人工上传',
  manual_edit: '在线编辑',
  manual_render: '重新生成',
}

export function versionKindLabel(kind: string): string {
  return REPORT_GEN_VERSION_KIND_LABEL[kind] ?? kind
}

/** 清单语义：已写 / 需核对 / 冲突 / 位置失效 / 空位 / 锁定（母本固定内容）。 */
export type ReportGenFieldState =
  | 'written'
  | 'needs_verify'
  | 'conflict'
  | 'anchor_unresolved'
  | 'blank'
  | 'locked'

interface FieldStateMeta {
  label: string
  /** antd Tag 的 color，沿用现有页面的语义色 */
  color: string
  text: string
  bg: string
  border: string
  /** 预览标记用虚线框：只对「空位」生效，提示这里等着补 */
  dashed?: boolean
}

export const REPORT_GEN_FIELD_STATE_META: Record<ReportGenFieldState, FieldStateMeta> = {
  written: { label: '已填写', color: 'processing', text: '#1677FF', bg: '#E6F4FF', border: '#91CAFF' },
  needs_verify: { label: '待确认', color: 'warning', text: '#D97706', bg: '#FFF7E6', border: '#FFD591' },
  conflict: { label: '内容冲突', color: 'error', text: '#DC2626', bg: '#FEF2F2', border: '#FCA5A5' },
  anchor_unresolved: { label: '位置已失效', color: 'error', text: '#DC2626', bg: '#FEF2F2', border: '#FCA5A5' },
  blank: { label: '待填写', color: 'default', text: '#8C8C8C', bg: '#FAFBFC', border: '#D9D9D9', dashed: true },
  locked: { label: '模板固定', color: 'default', text: '#595959', bg: '#F5F5F5', border: '#E5E5E5' },
}

const MANUAL_META: FieldStateMeta = {
  label: '人工修改',
  color: 'success',
  text: '#16A34A',
  bg: '#F0FDF4',
  border: '#86EFAC',
}

/**
 * 展示优先级：位置失效压过人工标记（改过但也失效了，必须让人先看到失效），
 * 人工改过压过已写（同一处既被 AI 写过、又被人改过，说「人工改过」更准确）。
 */
export function fieldStateMeta(state: string, editSource?: string | null): FieldStateMeta {
  if (state === 'anchor_unresolved') return REPORT_GEN_FIELD_STATE_META.anchor_unresolved
  if (editSource === 'manual' && state !== 'blank') return MANUAL_META
  return REPORT_GEN_FIELD_STATE_META[state as ReportGenFieldState] ?? REPORT_GEN_FIELD_STATE_META.blank
}

export const REPORT_GEN_FIELD_FILTERS = [
  { value: 'all', label: '全部' },
  { value: 'written', label: '已填写' },
  { value: 'blank', label: '待填写' },
  { value: 'fixed', label: '模板固定' },
  { value: 'needs_verify', label: '待确认' },
  { value: 'manual', label: '人工修改' },
] as const

export type ReportGenFieldFilter = (typeof REPORT_GEN_FIELD_FILTERS)[number]['value']

/** 筛选口径：需核对把「无来源」「冲突」「位置失效」合成一类，都是要人看一眼才能定稿的情况。 */
export function matchFieldFilter(item: ReportGenFieldItem, filter: ReportGenFieldFilter): boolean {
  if (filter === 'all') return true
  if (filter === 'written') return item.state === 'written'
  // 「空位」沿用 AI 覆盖口径，和顶部统计一致；母本固定内容单独一类
  if (filter === 'blank') return item.state === 'blank' && item.writable !== false
  if (filter === 'fixed') return item.writable === false
  if (filter === 'manual') return item.edit_source === 'manual'
  return ['needs_verify', 'conflict', 'anchor_unresolved'].includes(item.state)
}

/** 位置 key 是给机器看的，人需要的是「第几段/第几行第几列」：列表右侧只显示缩写。 */
export function fieldKeyLabel(key: string): string {
  if (/^p\d+$/.test(key)) return `第 ${Number(key.slice(1)) + 1} 段`
  const table = key.match(/^t(\d+)r(\d+)c(\d+)$/)
  if (table) return `表${Number(table[1]) + 1} · ${Number(table[2]) + 1} 行 ${Number(table[3]) + 1} 列`
  if (key === 'ref') return '参考资料'
  if (key.startsWith('ap')) return `新增段 ${key.slice(2)}`
  if (key.startsWith('at')) return `新增行 ${key.slice(2)}`
  return key
}

export type ReportGenModelTest = components['schemas']['ReportGenModelTestData']
export type ReportGenModelTestRequest = components['schemas']['ReportGenModelTestRequest']

export type ReportGenMetrics = components['schemas']['ReportGenMetricsData']

/** 指标时间窗；顺序即 Segmented 顺序。 */
export const REPORT_GEN_METRIC_WINDOWS = [7, 30, 90] as const

export type ReportGenMetricWindow = (typeof REPORT_GEN_METRIC_WINDOWS)[number]

export const REPORT_GEN_METRIC_DEFAULT_WINDOW: ReportGenMetricWindow = 30

/**
 * 比率 → 百分比文案。
 * null/undefined 表示窗口内没有样本，显示「—」而不是 0%，否则「刚上线没跑过任务」会被误读成「成功率 0%」。
 */
export function formatRate(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

/** 秒级均值 → 复用毫秒格式化，避免再写一套小时/分钟判断。 */
export function formatSeconds(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return '—'
  return formatDuration(Math.round(seconds * 1000))
}

/** 两个模型档位；顺序即配置页卡片顺序。 */
export const REPORT_GEN_MODEL_SLOTS = [
  { slot: 'main', title: '正文生成', description: '写正文用的模型：读模板、查资料、写内容都走这一档。' },
  { slot: 'fallback', title: '备用模型', description: '主模型报错或超时后自动换用，只切换一次。' },
] as const

export type ReportGenModelSlot = (typeof REPORT_GEN_MODEL_SLOTS)[number]['slot']

export interface ReportGenToolMeta {
  name: string
  label: string
  description: string
  /** 收尾工具恒开：关掉后模型无法声明完成，只能等轮次上限 */
  locked?: boolean
}

/** 工具开关清单；name 必须与后端 TOOL_NAMES 一致。 */
export const REPORT_GEN_TOOLS: ReportGenToolMeta[] = [
  {
    name: 'read_template_outline',
    label: '读取模板位置',
    description: '读取 Word 模板里可填写的段落与表格单元格，判断哪里能写。',
  },
  {
    name: 'read_project_context',
    label: '读取项目信息',
    description: '读取项目、品种、阶段等已有信息，避免 AI 编造。',
  },
  {
    name: 'search_knowledge_base',
    label: '检索知识库',
    description: '在项目知识库里找依据，并给出来源编号供引用。',
  },
  {
    name: 'write_paragraph',
    label: '写正文段落',
    description: '把有依据的内容批量写进空段落或占位段。',
  },
  {
    name: 'write_cell',
    label: '写表格单元格',
    description: '把有依据的内容写进表格里的空单元格。',
  },
  {
    name: 'append_paragraph',
    label: '新增段落',
    description: '模板里的条目不够时，按已有段落格式新增段落。',
  },
  {
    name: 'append_table_rows',
    label: '新增表格行',
    description: '按模板行格式往表格末尾新增行。',
  },
  {
    name: 'append_references',
    label: '整理参考资料',
    description: '按填写记录整理参考资料，只展示在页面右侧，不写进 Word 正文。',
  },
  {
    name: 'finalize',
    label: '结束并生成文档',
    description: '声明任务完成并生成最终 Word 文档。',
    locked: true,
  },
]

/** 逗号清单 → 工具名数组；空串表示全部启用。 */
export function parseDisabledTools(raw: string | null | undefined): string[] {
  return (raw ?? '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

/** 档位留空时的展示文案：空 = 没单独配，走全局默认模型。 */
export const REPORT_GEN_GLOBAL_MODEL_LABEL = '全局默认'

export function modelLabel(value: string | null | undefined): string {
  return (value ?? '').trim() || REPORT_GEN_GLOBAL_MODEL_LABEL
}

export interface ReportGenModelValues {
  /** 正文生成档原值（LLM 配置名或模型名），空串表示全局默认 */
  main: string
  fallback: string
  disabledTools: string[]
}

/** 从 core.module_settings 列表里抽两档模型与停用工具。 */
export function pickReportGenModels(
  settings: { key: string; value: string }[]
): ReportGenModelValues {
  const value = (key: string) => settings.find((item) => item.key === key)?.value?.trim() ?? ''
  return {
    main: value('REPORT_GEN_MODEL'),
    fallback: value('REPORT_GEN_FALLBACK_MODEL'),
    disabledTools: parseDisabledTools(value('REPORT_GEN_DISABLED_TOOLS')),
  }
}

export interface ReportGenJobModelSnapshot {
  main: string | null
  fallback: string | null
  usedFallback: boolean
}

/**
 * 任务创建时落库的模型快照。
 * 两档全空 = 快照列上线前的历史任务，返回 null 让页面显示「未记录」。
 * 结构识别档已下线：历史任务里的 structure_model_name 只是遗留数据，不再展示。
 */
export function jobModelSnapshot(job: ReportGenJob): ReportGenJobModelSnapshot | null {
  const main = job.model_name ?? job.model_config_name ?? null
  if (!main && !job.fallback_model_name) return null
  return {
    main,
    fallback: job.fallback_model_name ?? null,
    usedFallback: !!job.used_fallback,
  }
}

/** 生成期四个阶段；顺序即界面上阶段条的顺序，最后一个完成时 `stageOfJob` 返回 4。 */
export const REPORT_GEN_STAGES = ['读取模板', '汇总历史意见', '逐章写入资料', '生成 Word 文档'] as const

/**
 * 任务当前走到第几个阶段。
 *
 * 判定顺序：先看后端 current_step 的业务措辞（四阶段文案在 agent.py 里固定），
 * 措辞对不上（历史任务、被终止、文案改过）时退回按 progress 分段，
 * 保证任何情况下阶段条都不会卡在第一步。
 */
export function stageOfJob(job: ReportGenJob): number {
  if (job.status === 'completed') return REPORT_GEN_STAGES.length
  const step = job.current_step ?? ''
  if (step.includes('已完成')) return REPORT_GEN_STAGES.length
  if (step.includes('Word 文档') || step.includes('出稿')) return 3
  if (step.includes('写入') || /第 \d+ 轮/.test(step)) return 2
  if (step.includes('意见')) return 1
  if (step.includes('模板')) return 0
  const progress = job.progress ?? 0
  if (progress >= 92) return 3
  if (progress > 5) return 2
  if (progress >= 4) return 1
  return 0
}

export interface ReportGenFailureAdvice {
  /** 一句结论：说明「为什么没出来」，不是错误码 */
  title: string
  /** 2~3 条可执行建议，按最可能的原因排序 */
  suggestions: string[]
}

const FAILURE_ADVICE_RULES: { test: RegExp; advice: ReportGenFailureAdvice }[] = [
  {
    test: /模板|template|docx|document|损坏|打不开/i,
    advice: {
      title: 'Word 模板文件打不开',
      suggestions: [
        '回到「交付文档模板」页，确认这份模板的 Word 文件能正常打开',
        '重新上传一份模板（支持 .docx），再回到报告里重新生成',
        '如果模板刚换过版本，重新生成会按新版重算可填写位置',
      ],
    },
  },
  {
    test: /超时|timeout|timed out|超过 \d+ 秒/i,
    advice: {
      title: '生成时间超出上限，已中止',
      suggestions: [
        '点「重新生成」再跑一次，已填写的内容会保留、只补没写的部分',
        '资料很多时可以先补充项目知识库的关键文档，减少反复检索',
        '持续超时请让管理员检查生成设置里的模型与超时时间',
      ],
    },
  },
  {
    test: /知识库|检索|切片|RAG|embedding|向量/i,
    advice: {
      title: '资料检索没跑通',
      suggestions: [
        '到项目知识库里确认资料已「已入库」，处理中的文件要等它跑完',
        '确认知识库里有与报告主题相关的资料，没有依据的位置会留空',
        '点「重新生成」重试；仍失败请让管理员检查检索服务',
      ],
    },
  },
  {
    test: /模型|LLM|model|api[_ ]?key|401|403|429|5\d\d/i,
    advice: {
      title: '生成用的模型没有正常返回',
      suggestions: [
        '到报告列表页的「生成设置」里点「测试」确认模型可用',
        '确认备用模型也配好了：主模型报错时会自动换用一次',
        '稍后再点「重新生成」；反复失败请把下面的原始错误发给管理员',
      ],
    },
  },
]

/** 把后端错误翻成「结论 + 建议」：原始错误留给折叠区，便于报障。 */
export function describeJobFailure(message: string | null | undefined): ReportGenFailureAdvice {
  const text = (message ?? '').trim()
  for (const rule of FAILURE_ADVICE_RULES) {
    if (rule.test.test(text)) return rule.advice
  }
  return {
    title: '这次没有生成成功',
    suggestions: [
      '点「重新生成」再试一次；已经填写的内容会保留，不会被清空',
      '确认这份报告的 Word 模板能正常打开、项目知识库里的资料已入库',
      '如果一直失败，把下面的原始错误发给管理员定位',
    ],
  }
}

/** 预览定位结果 → 业务语言；不暴露对齐方式、段落数这类实现细节。 */
export function positionLocateText(marks: { hits: number; total: number } | null): string {
  if (!marks) return '正在定位可修改位置…'
  if (marks.total === 0) return '这份文档里没有可修改的位置'
  return `已定位 ${marks.hits}/${marks.total} 处可修改位置`
}