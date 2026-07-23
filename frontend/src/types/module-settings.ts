import type { components } from '@/types/generated/schema'

export type ModuleSettingCreate = components['schemas']['ModuleSettingCreate']
export type ModuleSettingUpdate = components['schemas']['ModuleSettingUpdate']

export interface ModuleSetting {
  id: string
  module: string
  key: string
  value: string
  value_type: string
  description: string | null
  created_at: string
  updated_at: string
}
