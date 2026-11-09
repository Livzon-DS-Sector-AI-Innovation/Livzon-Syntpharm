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
export type ReportGenSlot = components['schemas']['ReportGenSlotData']
export type ReportGenSlotList = components['schemas']['ReportGenSlotListData']
export type ReportGenJobCreate = components['schemas']['ReportGenJobCreateRequest']
export type ReportGenSlotUpdate = components['schemas']['ReportGenSlotUpdateRequest']
export type ReportGenFeedback = components['schemas']['ReportGenFeedbackData']
export type ReportGenFeedbackList = components['schemas']['ReportGenFeedbackListData']
export type ReportGenFeedbackCreate = components['schemas']['ReportGenFeedbackCreateRequest']
export type ReportGenExamplePromote = components['schemas']['ReportGenExamplePromoteData']
export type ReportGenExample = components['schemas']['ReportGenExampleData']
export type ReportGenExampleList = components['schemas']['ReportGenExampleListData']
export type ReportGenExampleUpdate = components['schemas']['ReportGenExampleUpdateRequest']

export type ReportGenJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
export type ReportGenStepKind = 'think' | 'tool_call' | 'tool_result' | 'error' | 'status'
export type ReportGenSlotState = 'filled' | 'conflict' | 'pending' | 'gap' | 'anchor_unresolved'

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

export const REPORT_GEN_SLOT_STATE_META: Record<ReportGenSlotState, { label: string; color: string }> = {
  filled: { label: '已填写', color: 'success' },
  conflict: { label: '资料不一致', color: 'warning' },
  pending: { label: '待确认', color: 'processing' },
  gap: { label: '未填写', color: 'default' },
  anchor_unresolved: { label: '未找到对应位置', color: 'error' },
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

export function slotStateMeta(state: string): { label: string; color: string } {
  return REPORT_GEN_SLOT_STATE_META[state as ReportGenSlotState] ?? { label: state, color: 'default' }
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

export type ReportGenModelTest = components['schemas']['ReportGenModelTestData']
export type ReportGenModelTestRequest = components['schemas']['ReportGenModelTestRequest']

export type ReportGenMetrics = components['schemas']['ReportGenMetricsData']
export type ReportGenStructureRun = components['schemas']['ReportGenStructureRunData']
export type ReportGenStructureRunList = components['schemas']['ReportGenStructureRunListData']
export type ReportGenStructureDiff = components['schemas']['ReportGenStructureDiff']

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

/** 三个模型档位；顺序即配置页卡片顺序。 */
export const REPORT_GEN_MODEL_SLOTS = [
  { slot: 'main', title: '正文生成', description: '写正文用的模型：查资料、填内容的调用都走这一档。' },
  {
    slot: 'structure',
    title: '分析结构',
    description: '分析 Word 模板文件、判断填充项时使用；留空则与正文生成用同一个模型。',
  },
  { slot: 'fallback', title: '自动补齐', description: '主模型报错或超时后自动换用，只切换一次。' },
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
  { name: 'read_template_outline', label: '读取模板大纲', description: '读取模板里已分析好的填充项清单和章节顺序。' },
  {
    name: 'read_project_context',
    label: '读取项目信息',
    description: '读取项目、品种、阶段等已有信息，避免 AI 编造。',
  },
  {
    name: 'search_knowledge_base',
    label: '检索知识库',
    description: '在项目知识库里找依据，并给出来源。',
  },
  {
    name: 'fill_slot',
    label: '填写填充项',
    description: '把有依据的内容写进指定填充项；多处资料不一致时标出来。',
  },
  {
    name: 'mark_gap',
    label: '标记未填写',
    description: '没有依据时明确留空并标注，不猜着写。',
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
  structure: string
  fallback: string
  disabledTools: string[]
}

/** 从 core.module_settings 列表里抽三档模型与停用工具。 */
export function pickReportGenModels(
  settings: { key: string; value: string }[]
): ReportGenModelValues {
  const value = (key: string) => settings.find((item) => item.key === key)?.value?.trim() ?? ''
  return {
    main: value('REPORT_GEN_MODEL'),
    structure: value('REPORT_GEN_STRUCTURE_MODEL'),
    fallback: value('REPORT_GEN_FALLBACK_MODEL'),
    disabledTools: parseDisabledTools(value('REPORT_GEN_DISABLED_TOOLS')),
  }
}

export interface ReportGenJobModelSnapshot {
  main: string | null
  structure: string | null
  fallback: string | null
  usedFallback: boolean
}

/**
 * 任务创建时落库的模型快照。
 * 三档全空 = 快照列上线前的历史任务，返回 null 让页面显示「未记录」。
 */
export function jobModelSnapshot(job: ReportGenJob): ReportGenJobModelSnapshot | null {
  const main = job.model_name ?? job.model_config_name ?? null
  if (!main && !job.structure_model_name && !job.fallback_model_name) return null
  return {
    main,
    structure: job.structure_model_name ?? null,
    fallback: job.fallback_model_name ?? null,
    usedFallback: !!job.used_fallback,
  }
}