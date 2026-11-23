/**
 * 文档翻译（/registration/docx-translator）类型。
 *
 * 契约模型一律从 OpenAPI 生成类型派生（AGENTS.md：API 类型只能来自 spec）；
 * 仅「表单入参」与「UI 枚举标签」属前端专属，保留手写。
 */

import type { components } from '@/types/generated/schema'

type Schemas = components['schemas']

export type DocxTranslationOutput = Schemas['DocxTranslationOutput']
export type DocxTranslationOutputKind = DocxTranslationOutput['kind']
export type DocxTranslationFileResult = Schemas['DocxTranslationFileResult']
export type DocxTranslationJobState = Schemas['DocxTranslationJobState']
export type DocxTranslationJobStatus = DocxTranslationJobState['status']
export type DocxTranslationSubmitResult = Schemas['DocxTranslationJobAccepted']

export type DocxTranslationFileRecord = Schemas['DocxTranslationFileRecord']
export type DocxTranslationTaskRecord = Schemas['DocxTranslationTaskRecord']
export type DocxTranslationTaskFile = Schemas['DocxTranslationTaskFile']
export type DocxTranslationTaskDetail = Schemas['DocxTranslationTaskDetailData']

export type DocxGlossaryTerm = Schemas['DocxGlossaryTermResponse']
export type DocxGlossaryImportResult = Schemas['DocxGlossaryImportData']

/** 输出模式（后端 Literal，前端下拉用） */
export type DocxTranslationMode = 'bilingual' | 'replace' | 'both'

/** 术语来源（后端返回 str，前端做标签映射） */
export type DocxGlossaryTermSource = 'builtin' | 'manual' | 'import'

/** 提交入参（表单模型，非 API 契约） */
export interface DocxTranslationSubmitPayload {
  files: File[]
  sourceLang: 'en' | 'zh'
  targetLang: 'en' | 'zh'
  mode: DocxTranslationMode
  batchSize?: number
}

/** 分页查询参数（表单模型） */
export interface DocxPageQuery {
  keyword?: string
  page: number
  pageSize: number
}

/** 任务列表查询参数（表单模型） */
export interface DocxTaskQuery extends DocxPageQuery {
  status?: DocxTranslationJobStatus
  mine?: boolean
}
