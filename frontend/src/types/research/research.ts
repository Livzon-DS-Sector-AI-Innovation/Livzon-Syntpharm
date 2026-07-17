// Research module types
// NOTE: Some types use generated schema (ResearchProjectCreate/Update).
// Response and domain model types are hand-written as they represent
// the application's view model, not direct API contracts.

import type { components } from '@/types/generated/schema'

// 研发项目类型定义

export type ResearchProjectStage = '立项' | '研发中试' | '验证' | '注册' | '商业化'
export type ResearchProjectStatus = '进行中' | '已暂停' | '已完成' | '已终止'

export interface ResearchProject {
  id: string
  project_no: string
  name: string
  project_type: string | null
  stage: ResearchProjectStage
  status: ResearchProjectStatus
  leader: string | null
  start_date: string | null
  end_date: string | null
  description: string | null
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}

export interface ResearchProjectFilters {
  stage?: ResearchProjectStage | ''
  status?: ResearchProjectStatus | ''
  keyword?: string
  page?: number
  page_size?: number
}

export interface ResearchProjectListResponse {
  items: ResearchProject[]
  total: number
  page: number
  page_size: number
}

export type ResearchProjectCreate = components['schemas']['ResearchProjectCreate']

export type ResearchProjectUpdate = components['schemas']['ResearchProjectUpdate']

// EDBO+ 贝叶斯优化类型定义

export interface EDBOOptimizeRequest {
  objectives: string[]
  objective_modes: ('max' | 'min')[]
  batch_size: number
}

export interface EDBOOptimizeResponse {
  csv_data: string  // base64 encoded CSV
  row_count: number
  prediction_data?: string  // base64 encoded prediction CSV (optional)
  prediction_filename?: string  // prediction filename (optional)
}
