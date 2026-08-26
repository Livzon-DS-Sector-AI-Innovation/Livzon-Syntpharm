import type { components } from '@/types/generated/schema'

// Dossier Writer TypeScript types

export interface ProductDossier {
  id: string
  product_name: string
  sterile_type: string
  manufacturer: string
  template_original_product_name?: string
  template_original_manufacturer?: string
  status: string
  parse_status: string
  parse_error?: string
  source_templates_path?: string
  working_path?: string
  assets_path?: string
  outputs_path?: string
  chapter_count: number
  created_at: string
  updated_at: string
}

export type ProductDossierCreate = components['schemas']['ProductDossierCreate']

export type ProductDossierUpdate = components['schemas']['ProductDossierUpdate']

export interface DossierTemplate {
  id: string
  original_filename: string
  file_size?: number
  uploaded_at: string
}

export interface Chapter {
  id: string
  parent_id?: string
  chapter_code?: string
  chapter_title: string
  level: number
  sort_order: number
  has_content: boolean
  has_assets: boolean
  asset_count: number
  children: Chapter[]
}

export interface ChapterDetail {
  id: string
  chapter_code?: string
  chapter_title: string
  level: number
  has_content: boolean
  has_assets: boolean
  source_file?: string
  working_file?: string
  assets: ChapterAsset[]
}

export interface ChapterAsset {
  id: string
  original_filename: string
  file_type?: string
  file_size?: number
  uploaded_at: string
  category_id?: string | null
}

export interface ParseResult {
  success: boolean
  message: string
  chapter_count?: number
  error?: string
}

export interface ExportResult {
  success: boolean
  message: string
  file_path?: string
  filename?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

// ====== AI Fill Types ======

export interface AssetCategory {
  id: string
  category_name: string
  category_type: 'document' | 'image_appendix' | 'both'
  appendix_slot?: string
  description?: string
  sort_order: number
}

export interface AIFieldResult {
  field_name: string
  field_type: string
  value: string | number | null | Array<Array<string>>
  confidence: number
  source: string
  field_mapping_id: string
  source_category?: string
}

export interface AIPreviewResult {
  success: boolean
  message: string
  fields: AIFieldResult[]
  token_usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  // 新增字段：部分成功和错误详情
  partial_success?: boolean
  failed_count?: number
  llm_error?: boolean
  error_details?: {
    total_fields: number
    failed_fields: number
    errors: string[]
  }
}

export interface AIConfirmRequest {
  fields: Array<{
    field_name: string
    field_type: string
    value: string | number | null | Array<Array<string>>
    confidence: number
    field_mapping_id: string
  }>
}

export interface AIFillResult {
  success: boolean
  message: string
  results: Array<{
    field_name: string
    status: string
    message: string
  }>
}

export type PageSplitInfo = components['schemas']['PageSplitItem']

export interface PageSplitPreviewResult {
  success: boolean
  message: string
  pages: PageSplitInfo[]
  page_count: number
}

export interface PageSplitRecord {
  id: string
  page_number: number
  page_type: string
  content_summary?: string
  appendix_slot?: string
  status: string
}


// Response wrapper types
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
}

export interface UploadResult {
  file_id?: string
  filename: string
  file_path?: string
  file_size?: number
  status: 'success' | 'failed'
  error?: string
}

export interface UploadResponse {
  results: UploadResult[]
  success_count: number
  failed_count: number
  matched_count?: number
  unmatched_files?: string[]
}

// Asset matching and field filling
export interface MatchResult {
  success: boolean
  message: string
  matched_count: number
  unmatched_files: string[]
}

export interface FieldFillResult {
  success: boolean
  message: string
  filled_count: number
  total_fields: number
  results: Array<{
    field_name: string
    status: string
    filled_value: string | null
  }>
}

// Chapter preview
export interface ChapterPreview {
  success: boolean
  chapter_code: string
  chapter_title: string
  paragraphs: Array<{ text: string; style: string }>
  tables: string[][][]
  message?: string
}

// ====== Asset Usage Types ======

export interface AvailableAsset {
  id: string
  original_filename: string
  file_path?: string
  file_type?: string
  file_size?: number
  uploaded_at: string
  category_id?: string | null
  chapter_id: string
  parent_chapter_code?: string | null
  is_inherited: boolean
  is_selected: boolean
}

export interface AssetUsageToggle {
  usage_id?: string
  is_selected: boolean
}
