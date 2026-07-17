/**
 * 文档AI校验模块类型定义
 * 文件合规校验模块的类型声明
 */

// ============ 枚举类型 ============

export type CheckStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type FileType = 'sop' | 'procedure' | 'standard' | 'quality_system'
export type RiskLevel = 'high' | 'medium' | 'low'
export type HandleStatus = 'pending' | 'confirmed' | 'ignored' | 'fixed'
export type CheckItemType = 'duplicate' | 'conflict' | 'regulation' | 'internal_control'

// ============ 文件类型 ============

export interface DocFile {
  id?: string
  file_name: string
  file_path?: string
  file_no?: string
  file_version?: string
  file_type?: FileType
  preparer?: string
  prepare_date?: string
  file_size?: number
  file_ext?: string
}

// ============ 校验配置类型 ============

export interface CheckConfig {
  // 校验开关
  enable_duplicate_check: boolean // 全文智能查重
  enable_conflict_check: boolean // 跨文件条款冲突检测
  enable_regulation_check: boolean // GMP/药典法规合规校验
  enable_internal_control_check: boolean // 企业内控标准校验
  // 后台参数
  severe_duplicate_threshold: number // 严重重复阈值（默认85%）
  suspected_duplicate_threshold: number // 疑似重复阈值（默认70%）
}

// ============ 校验进度类型 ============

export interface CheckProgress {
  status: CheckStatus
  progress: number // 0-100
  current_step: string
  message?: string
  error?: string
}

// 校验步骤
export const CHECK_STEPS = [
  { key: 'parsing', label: '文件解析中', value: 20 },
  { key: 'chunking', label: '文本切片中', value: 40 },
  { key: 'embedding', label: '向量检索中', value: 60 },
  { key: 'analyzing', label: 'AI精检中', value: 80 },
  { key: 'generating', label: '报告生成完成', value: 100 },
] as const

// ============ 问题类型 ============

export interface CheckProblem {
  id: string
  main_id: string
  problem_type: CheckItemType
  risk_level: RiskLevel
  location?: string // 问题位置
  description: string // 问题描述
  source_file?: string // 源文件（查重）
  source_file_no?: string // 源文件编号
  similarity?: number // 相似度（查重）
  conflict_param?: string // 冲突参数（冲突）
  system_content?: string // 系统标准内容（冲突）
  regulation_basis?: string // 法规依据（法规合规）
  internal_file_basis?: string // 上级文件依据（内控合规）
  suggestion?: string // 整改建议
  handle_status: HandleStatus
  ignore_reason?: string
  operator?: string
  created_at: string
  updated_at: string
}

// ============ 校验主记录类型 ============

export interface CheckMain {
  id: string
  file_name: string
  file_no?: string
  file_version?: string
  file_type?: FileType
  preparer?: string
  prepare_date?: string
  status: CheckStatus
  total_problems: number
  risk_high: number
  risk_medium: number
  risk_low: number
  operator?: string
  created_at: string
  updated_at: string
}

export interface CheckMainDetail extends CheckMain {
  problems: CheckProblem[]
}

// ============ 请求类型 ============

export interface UploadFileRequest {
  file: File
  file_name: string
  file_no?: string
  file_version?: string
  file_type?: FileType
  preparer?: string
  prepare_date?: string
}

export interface StartCheckRequest {
  file_id: string
  file_name?: string
  check_config: CheckConfig
  operator?: string
}

export interface BatchCheckRequest {
  file_ids: string[]
  check_config: CheckConfig
  operator?: string
}

export interface HandleProblemRequest {
  handle_status: HandleStatus
  ignore_reason?: string
  operator?: string
}

export interface QueryCheckRecordsRequest {
  status?: CheckStatus
  file_no?: string
  file_name?: string
  file_type?: FileType
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

// ============ 响应类型 ============

export interface UploadFileResponse {
  file_id: string
  file_name: string
  file_path: string
  file_size: number
  file_ext: string
}

export interface StartCheckResponse {
  task_id: string
  status: CheckStatus
  message?: string
}

export interface CheckProgressResponse {
  task_id: string
  status: CheckStatus
  progress: number
  current_step: string
  message?: string
  result?: {
    total_problems: number
    risk_high: number
    risk_medium: number
    risk_low: number
    problems: CheckProblem[]
  }
}

export interface CheckRecordResponse {
  items: CheckMain[]
  total: number
  page: number
  page_size: number
}

export type CheckRecordDetailResponse = CheckMainDetail

export interface ExportReportResponse {
  download_url: string
  file_name: string
}

export interface HandleProblemResponse {
  id: string
  handle_status: HandleStatus
  ignore_reason?: string
}

// ============ API 通用响应 ============

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// ============ 选项配置 ============

// 文件类型选项
export const FILE_TYPE_OPTIONS = [
  { label: 'SOP', value: 'sop' },
  { label: '管理规程', value: 'procedure' },
  { label: '技术标准', value: 'standard' },
  { label: '质量制度', value: 'quality_system' },
] as const

// 风险等级选项
export const RISK_LEVEL_OPTIONS = [
  { label: '高风险', value: 'high', color: 'red' },
  { label: '中风险', value: 'medium', color: 'orange' },
  { label: '低风险', value: 'low', color: 'green' },
] as const

// 处理状态选项
export const HANDLE_STATUS_OPTIONS = [
  { label: '待处理', value: 'pending' },
  { label: '已确认', value: 'confirmed' },
  { label: '已忽略', value: 'ignored' },
  { label: '已整改', value: 'fixed' },
] as const

// 校验状态选项
export const CHECK_STATUS_OPTIONS = [
  { label: '待处理', value: 'pending' },
  { label: '校验中', value: 'running' },
  { label: '已完成', value: 'completed' },
  { label: '已失败', value: 'failed' },
  { label: '已取消', value: 'cancelled' },
] as const

// 校验项配置
export const CHECK_ITEM_OPTIONS = [
  { label: '全文智能查重', value: 'duplicate_check', key: 'enableDuplicateCheck' },
  { label: '跨文件条款冲突检测', value: 'conflict_check', key: 'enableConflictCheck' },
  { label: 'GMP/药典法规合规校验', value: 'regulation_check', key: 'enableRegulationCheck' },
  { label: '企业内控标准校验', value: 'internal_control_check', key: 'enableInternalControlCheck' },
] as const