/**
 * SOP AI 模块类型定义
 * 文件合规校验模块的类型声明
 */

// ============ 配置相关类型 ============

export interface SopAiConfig {
  id: string
  config_key: string
  config_value: string
  description?: string
  operator?: string
  created_at: string
  updated_at: string
}

// ============ 校验相关类型 ============

export type CheckStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type CheckType = 'single' | 'batch' | 'scheduled'
export type FileType = 'doc' | 'docx' | 'pdf' | 'txt'
export type RiskLevel = 'high' | 'medium' | 'low'
export type ProblemType = 'duplicate' | 'conflict' | 'compliance' | 'format' | 'content'
export type HandleStatus = 'pending' | 'confirmed' | 'ignored' | 'fixed'

export interface CheckProblem {
  id: string
  main_id: string
  problem_type?: ProblemType
  risk_level?: RiskLevel
  location?: string
  description?: string
  source_file?: string
  suggestion?: string
  handle_status: HandleStatus
  ignore_reason?: string
  operator?: string
  created_at: string
  updated_at: string
}

export interface CheckMain {
  id: string
  file_code?: string
  file_name?: string
  file_type?: FileType
  check_type?: CheckType
  status: CheckStatus
  result_summary?: string
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

export interface SingleCheckRequest {
  file_path: string
  file_name: string
  check_type?: CheckType
  operator?: string
}

export interface BatchCheckRequest {
  file_paths: string[]
  check_type?: CheckType
  operator?: string
}

export interface ProblemHandleRequest {
  handle_status: HandleStatus
  ignore_reason?: string
  operator?: string
}

// ============ 响应类型 ============

export interface CheckTaskResponse {
  task_id: string
  status: CheckStatus
  message?: string
  result?: {
    total_problems: number
    risk_high: number
    risk_medium: number
    risk_low: number
    problems: CheckProblem[]
  }
}

export interface BatchCheckResult {
  task_id: string
  status: CheckStatus
  result: {
    total_files: number
    total_problems: number
    file_results: {
      file_path: string
      status: CheckStatus
      task_id: string
      total_problems: number
      risk_high: number
      risk_medium: number
      risk_low: number
    }[]
  }
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// ============ 定时任务类型 ============

export interface ScheduledJob {
  job_id: string
  job_name: string
  cron_expression: string
  file_pattern: string
  enabled: boolean
  next_run_time?: string
  last_run_time?: string
  run_count: number
}

// ============ 过滤器类型 ============

export interface CheckRecordFilter {
  status?: CheckStatus
  file_code?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}