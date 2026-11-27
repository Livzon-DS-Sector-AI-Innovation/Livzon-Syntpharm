/** 质量检验台账类型定义。 */

export type QcLevel = 'oos' | 'internal' | 'trend' | 'normal' | 'skip' | 'pending'

export type QcCategory = 'raw' | 'intermediate' | 'finished'

export type QcValueType = 'quant' | 'qual' | 'grade'

export interface QcProductListItem {
  id: string
  name: string
  abbr: string
  category: string
  quality_standard: string | null
  status: string
  last_inspected_at: string | null
  batch_count: number
  normal_count: number
  oos_count: number
  internal_count: number
  trend_count: number
  pending_count: number
  pass_rate: number
  top_level: QcLevel
}

export interface QcProduct {
  id: string
  name: string
  abbr: string
  category: string
  quality_standard: string | null
  source_file_name: string | null
  status: string
  last_inspected_at: string | null
  created_at: string
  updated_at: string
}

/** 某一层标准最终取自哪份文件，供导入完成页核对。 */
export interface QcStandardSourceItem {
  column_letter: string
  item_name: string
  layer: 'legal' | 'internal' | 'sigma'
  layer_label: string
  final_text: string | null
  source: 'excel' | 'docx' | 'none'
  /** true = 按人工裁决，false = 默认取值 */
  from_choice: boolean
}

export interface QcBatchImportResult {
  created_count: number
  skipped_count: number
  skipped_batch_nos: string[]
  level_counts: Record<string, number>
}

export interface QcUnmatchedCandidate {
  letter: string
  name: string
}

export interface QcUnmatchedItem {
  item_name: string
  candidates: QcUnmatchedCandidate[]
  docx_legal_text: string | null
  docx_internal_text: string | null
  docx_sigma_text: string | null
  /** 当前已对应的列字母，未对应为 null */
  matched_column_letter: string | null
  matched_column_name: string | null
}

export interface QcStandardConflict {
  column_index: number
  column_letter: string
  item_name: string
  layer: 'legal' | 'internal' | 'sigma'
  layer_label: string
  excel_text: string | null
  docx_text: string | null
  note: string | null
  /** numeric 数值范围不同（必须确认）/ text 仅文字表述不同（默认采用结果表） */
  severity: 'numeric' | 'text'
}

export interface QcImportSummary {
  total_columns: number
  same_count: number
  conflict_count: number
  only_excel_count: number
  skipped_standard_items: string[]
}

export interface QcItem {
  id: string
  product_id: string
  item_no: number
  item_name: string
  standard_item_name: string | null
  standard_source: string | null
  column_group_start: number | null
  sub_label: string | null
  value_type: QcValueType
  unit: string | null
  legal_text: string | null
  internal_text: string | null
  sigma_text: string | null
  source_column: string | null
  is_record_only: boolean
  sigma_basis_period: string | null
  sigma_updated_by: string | null
  sigma_updated_at: string | null
  sort_order: number
  is_enabled: boolean
}

export interface QcBatchRow {
  id: string
  batch_no: string
  level: QcLevel
  note: string | null
  entered_by_name: string | null
  source: string
  created_at: string
  values: Record<string, string | null>
  levels: Record<string, QcLevel>
}

export interface QcBatchPageData {
  total: number
  page: number
  page_size: number
  items: QcBatchRow[]
}

export interface QcStats {
  total: number
  oos: number
  internal: number
  trend: number
  normal: number
  skip: number
  pending: number
}

export interface QcAttentionBatch {
  product_id: string
  product_name: string
  batch_id: string
  batch_no: string
  level: QcLevel
  reason: string | null
}

export interface QcImportPreviewItem {
  item_no: number
  item_name: string
  value_type: QcValueType
  unit: string | null
  legal_text: string | null
  internal_text: string | null
  sigma_text: string | null
  /** 该列在标准表里对应的项目名 */
  matched_column: string | null
  /** same 一致 / diff 待确认 / pending 标准表没对上 / only_excel 仅结果表有 */
  match_kind: 'same' | 'diff' | 'pending' | 'only_excel'
  /** 标准表里还没对上的项目名，供人工指定这一列对应哪个 */
  candidates: string[]
}

export interface QcImportExtraColumn {
  column_index: number
  column_name: string
}

export interface QcImportPreview {
  docx_file_name: string
  xlsx_file_name: string
  sheet_title: string
  batch_count: number
  data_start_row: number
  column_count: number
  product_name_suggestion: string
  abbr_suggestion: string
  quality_standard_suggestion: string | null
  items: QcImportPreviewItem[]
  extra_columns: QcImportExtraColumn[]
  batch_no_samples: string[]
  sample_values: Record<string, string | null>[]
  unrecognized_items: string[]
  conflicts: QcStandardConflict[]
  unmatched_items: QcUnmatchedItem[]
  summary: QcImportSummary | null
}

export interface QcImportCommitResult {
  product_id: string
  product_name: string
  item_count: number
  record_only_count: number
  batch_count: number
  value_count: number
  unrecognized_items: string[]
  skipped_standard_items: string[]
  resolved_conflicts: number
  /** 两份文件不一致的层，最终用了哪份的值、是否人工裁决 */
  standard_sources: QcStandardSourceItem[]
}

export interface QcItemUpdatePayload {
  legal_text?: string | null
  internal_text?: string | null
  sigma_text?: string | null
}

export interface QcRejudgeResult {
  product_id: string
  batch_count: number
  value_count: number
  /** 有任一单元格判定变化的批次数 */
  changed_batch_count: number
  /** 判定发生变化的检验值条数 */
  changed_value_count: number
}

export interface QcBatchCreateInput {
  batch_no: string
  note?: string | null
  values: Record<string, string>
}

export interface QcRejudgeResult {
  product_id: string
  batch_count: number
  value_count: number
  /** 有任一单元格判定变化的批次数 */
  changed_batch_count: number
  /** 判定发生变化的检验值条数 */
  changed_value_count: number
}

/** 等级 → 展示文案。 */
export const QC_LEVEL_LABEL: Record<QcLevel, string> = {
  oos: '超法定',
  internal: '超内控',
  trend: '超趋势',
  normal: '正常',
  skip: '仅记录',
  pending: '待检',
}

/**
 * 等级 → 判定色（对齐视觉基准稿，值与设计 token 逐值一致）。
 *
 * 判定色只用在这里，绝不与品牌紫混用。
 * `dot` 用于胶囊小方块、表格行左侧竖条、分布条分段；
 * `bg`/`border` 只用于「判定有颜色」的三档，normal 以下在表格里不铺底色。
 */
export const QC_LEVEL_STYLE: Record<
  QcLevel,
  { text: string; bg: string; border: string; dot: string }
> = {
  oos: { text: '#D64545', bg: '#FDECEA', border: '#F5CDC8', dot: '#D64545' },
  internal: { text: '#D97A0B', bg: '#FDF3E7', border: '#F3D9B4', dot: '#D97A0B' },
  trend: { text: '#9A7B0A', bg: '#FBF6DE', border: '#EDE0A8', dot: '#C9A227' },
  normal: { text: '#1E8E5A', bg: '#E9F7EF', border: '#BFE6D2', dot: '#1E8E5A' },
  skip: { text: '#9CA3AF', bg: 'transparent', border: 'transparent', dot: '#C4C9D1' },
  pending: { text: '#9CA3AF', bg: 'transparent', border: 'transparent', dot: '#C4C9D1' },
}

export const QC_CATEGORY_LABEL: Record<string, string> = {
  raw: '原料',
  intermediate: '中间体',
  finished: '成品',
}

/** 只保留成品与中间体；`raw` 仅用于兼容历史数据显示。 */
export const QC_CATEGORY_OPTIONS: { value: QcCategory; label: string }[] = [
  { value: 'finished', label: '成品' },
  { value: 'intermediate', label: '中间体' },
]

export const QC_LEVEL_OPTIONS: { value: QcLevel; label: string }[] = [
  { value: 'oos', label: '超法定' },
  { value: 'internal', label: '超内控' },
  { value: 'trend', label: '超趋势' },
  { value: 'normal', label: '正常' },
  { value: 'pending', label: '待检' },
]

/** 空值统一显示为短横线；表格里用它区分「没检」和「漏导」。 */
export const QC_EMPTY = '—'

/** Excel 列号（1=A）→ 列字母，用于区分同名项目。 */
export function qcColumnLetter(index: number): string {
  let n = index
  let text = ''
  while (n > 0) {
    const rem = (n - 1) % 26
    text = String.fromCharCode(65 + rem) + text
    n = Math.floor((n - 1) / 26)
  }
  return text
}
