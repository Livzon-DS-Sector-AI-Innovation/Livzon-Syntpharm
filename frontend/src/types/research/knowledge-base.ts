/**
 * 研发项目知识库类型与展示映射。
 *
 * 类型统一来自后端 OpenAPI 生成的 schema（契约唯一来源），
 * 本文件只补充前端展示需要的常量与派生逻辑。
 */
import type { components } from '@/types/generated/schema'

export type KnowledgeBaseItem = components['schemas']['KnowledgeBaseItem']
export type KbDocumentItem = components['schemas']['KbDocumentItem']
export type KbLimits = components['schemas']['KbLimits']
export type KbUploadResult = components['schemas']['KbUploadResult']

export const KB_RUN_LABELS: Record<string, string> = {
  UNSTART: '排队中',
  RUNNING: '入库中',
  DONE: '已入库',
  FAIL: '处理失败',
  CANCEL: '已取消',
}

/** 每个状态的一句话解释：悬停或列头说明用，避免「已取消」被当成失败 */
export const KB_RUN_HINTS: Record<string, string> = {
  UNSTART: '已提交，等待系统处理；前面的资料处理完就开始。',
  RUNNING: '正在把资料转换成可检索的文字，通常几分钟内完成。',
  DONE: '资料已处理完，AI 写报告时可以检索到里面的内容。',
  FAIL: '这次没处理成功，可以点「重新处理」再试，或换一份文件。',
  CANCEL: '这次处理被取消了，不算失败；需要的话可以点「重新处理」。',
}

/** 分段方式：把后端的技术取值翻成人话，界面上不直接显示 naive 这类英文 */
export const KB_CHUNK_METHOD_LABELS: Record<string, string> = {
  naive: '按段落切分（默认）',
  manual: '按人工标记切分',
  qa: '按问答对切分',
  table: '按表格切分',
  paper: '按论文章节切分',
  book: '按书籍章节切分',
  laws: '按法条切分',
  one: '整篇不分段',
  knowledge_graph: '抽成知识图谱',
}

export function chunkMethodLabel(method?: string | null): string {
  if (!method) return '按段落切分（默认）'
  return KB_CHUNK_METHOD_LABELS[method] ?? '按段落切分（默认）'
}

export const KB_RUN_COLORS: Record<string, string> = {
  UNSTART: 'default',
  RUNNING: 'processing',
  DONE: 'success',
  FAIL: 'error',
  CANCEL: 'warning',
}

/** 知识库本身的就绪状态 */
export const KB_STATUS_LABELS: Record<string, string> = {
  creating: '创建中',
  active: '可用',
  failed: '异常',
}

export const KB_STATUS_COLORS: Record<string, string> = {
  creating: 'processing',
  active: 'success',
  failed: 'error',
}

/** 解析是否已有终态结果：未终态时列表需要持续轮询 */
export function isKbDocumentSettled(doc: KbDocumentItem): boolean {
  return doc.run === 'DONE' || doc.run === 'FAIL' || doc.run === 'CANCEL'
}

/** 知识库是否还有文档在解析（决定是否轮询） */
export function hasPendingKbDocument(documents: KbDocumentItem[]): boolean {
  return documents.some((doc) => !isKbDocumentSettled(doc))
}

/** 进度百分比（后端给 0~1 的小数） */
export function kbProgressPercent(doc: KbDocumentItem): number {
  if (doc.run === 'DONE') return 100
  const percent = Math.round((doc.progress || 0) * 100)
  return Math.max(0, Math.min(99, percent))
}

/** 一条解析切片（预览「解析内容」用） */
export type KbChunkItem = components['schemas']['KbChunkItem']
export type KbChunkList = components['schemas']['KbChunkList']

/** 原文预览方式：决定怎么渲染（见 KbDocumentPreviewModal） */
export type KbPreviewKind = 'docx' | 'pdf' | 'image' | 'text' | 'sheet' | 'office' | 'unsupported'

/** 浏览器原生可渲染：直接取原件 */
const DOCX_EXTS = ['.docx', '.dotx']
const PDF_EXTS = ['.pdf']
const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tif', '.tiff']
const TEXT_EXTS = ['.txt', '.md', '.csv', '.json', '.log']
/** 表格：前端用 SheetJS 直接解析成网格（比服务端转 PDF 快得多，大表尤其明显） */
const SHEET_EXTS = ['.xls', '.xlsx']
/** 浏览器渲染不了、也没法在前端解析，只能由服务端 LibreOffice 转 PDF */
const OFFICE_EXTS = ['.doc', '.ppt', '.pptx', '.rtf', '.odt', '.ods']

/**
 * 按扩展名决定原文预览方式。
 *
 * 浏览器只能原生渲染 pdf / 图片 / 纯文本。`.doc`、`.ppt(x)` 这类格式内联打开
 * 只会触发下载（这正是「源文件无法在线预览」的原因）→ `office`：请服务端转 PDF；
 * `.xls(x)` 前端解析成网格 → `sheet`；其余（如压缩包）归 `unsupported`。
 */
export function kbPreviewKind(fileExt: string): KbPreviewKind {
  const ext = (fileExt || '').toLowerCase()
  if (DOCX_EXTS.includes(ext)) return 'docx'
  if (PDF_EXTS.includes(ext)) return 'pdf'
  if (IMAGE_EXTS.includes(ext)) return 'image'
  if (TEXT_EXTS.includes(ext)) return 'text'
  if (SHEET_EXTS.includes(ext)) return 'sheet'
  if (OFFICE_EXTS.includes(ext)) return 'office'
  return 'unsupported'
}



export function formatBytes(bytes: number): string {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`
}
