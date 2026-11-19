/** 文档翻译（/registration/docx-translator）接口类型，对齐后端 docx_translator/schemas.py */

export type DocxTranslationMode = 'bilingual' | 'replace' | 'both'
export type DocxTranslationOutputKind = 'bilingual' | 'translated'
export type DocxTranslationJobStatus = 'running' | 'done' | 'failed'

export interface DocxTranslationOutput {
  kind: DocxTranslationOutputKind
  filename: string
  file_index: number
}

export interface DocxTranslationFileResult {
  filename: string
  success: boolean
  outputs: DocxTranslationOutput[]
  translated_units: number
  total_units: number
  success_rate: number
  warnings: string[]
  error: string | null
}

export interface DocxTranslationJobState {
  job_id: string
  status: DocxTranslationJobStatus
  files_done: number
  files_total: number
  current_file: string | null
  files: DocxTranslationFileResult[]
  error: string | null
}

export interface DocxTranslationSubmitResult {
  job_id: string
  status: 'running'
}

export type DocxGlossaryTermSource = 'builtin' | 'manual' | 'import'

export interface DocxGlossaryTerm {
  id: string
  term_en: string
  term_zh: string
  is_enabled: boolean
  source: DocxGlossaryTermSource
  created_at?: string | null
  updated_at?: string | null
}

export interface DocxGlossaryTermPage {
  items: DocxGlossaryTerm[]
  total: number
}

export interface DocxGlossaryImportResult {
  imported: number
  updated: number
  skipped: number
  total: number
}

export interface DocxTranslationSubmitPayload {
  files: File[]
  sourceLang: 'en' | 'zh'
  targetLang: 'en' | 'zh'
  mode: DocxTranslationMode
  batchSize?: number
}

export interface DocxTranslationFileRecord {
  id: string
  job_ref: string
  source_filename: string
  output_filename: string
  output_kind: DocxTranslationOutputKind
  source_lang: string
  target_lang: string
  mode: string
  success_rate: number
  translated_units: number
  total_units: number
  file_size: number
  warnings: string[]
  created_at?: string | null
  created_by_name?: string | null
  can_delete: boolean
}

export interface DocxTranslationFilePage {
  items: DocxTranslationFileRecord[]
  total: number
}

export interface DocxTranslationTaskRecord {
  id: string
  job_ref: string
  status: 'running' | 'done' | 'failed'
  source_count: number
  success_count: number
  fail_count: number
  first_source_filename: string
  source_lang: string
  target_lang: string
  mode: string
  elapsed_seconds: number
  total_file_size: number
  created_at?: string | null
  created_by_name?: string | null
  can_delete: boolean
  can_retranslate: boolean
}

export interface DocxTranslationTaskFile {
  id: string
  source_filename: string
  output_filename: string
  output_kind: string
  success: boolean
  success_rate: number
  translated_units: number
  total_units: number
  file_size: number
  error: string | null
}

export interface DocxTranslationTaskPage {
  items: DocxTranslationTaskRecord[]
  total: number
}

export interface DocxTranslationTaskDetail {
  task: DocxTranslationTaskRecord
  files: DocxTranslationTaskFile[]
  warnings: string[]
}
