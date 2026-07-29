import type { components } from '@/types/generated/schema'
export type CreateFailureCodeInput = components['schemas']['FailureCodeCreate']
export type UpdateFailureCodeInput = components['schemas']['FailureCodeUpdate']

// ==================== 故障代码 ====================
export type FailureCodeType = 'symptom' | 'cause' | 'action'

export interface FailureCode {
  id: string
  code: string
  name: string
  description: string | null
  sort_order: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}


