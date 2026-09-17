// Settings types
// API input types are aliased from generated schema for single-source-of-truth.

import type { components } from '@/types/generated/schema'

export interface LLMConfig {
  id: string
  config_name: string
  config_type: string
  api_base_url: string
  api_key_masked: string
  model_name: string
  temperature: number
  timeout_seconds: number
  is_active: boolean
  notes: string | null
  created_at: string
  updated_at: string
}

export type LLMConfigFormData = components['schemas']['LLMConfigCreate']

export type LLMConfigUpdate = components['schemas']['LLMConfigUpdate']

export interface FeishuConfig {
  config_name: string
  app_id: string
  app_secret?: string
  app_secret_masked?: string
  app_secret_configured?: boolean
  card_callback_verification_token?: string
  card_callback_verification_token_masked?: string
  card_callback_verification_token_configured?: boolean
  card_callback_encrypt_key?: string
  card_callback_encrypt_key_masked?: string
  card_callback_encrypt_key_configured?: boolean
  card_callback_url?: string
  sync_root_department_id: string
  sync_member_department_id: string
  is_active: boolean
  last_synced_at?: string
  last_sync_message?: string
  last_diagnostic_result?: string
  last_diagnostic_status?: string
  last_diagnostic_message?: string
}

export interface FeishuConfigUpsert {
  config_name: string
  app_id: string
  app_secret?: string
  card_callback_verification_token?: string
  card_callback_encrypt_key?: string
  sync_root_department_id: string
  sync_member_department_id: string
  is_active: boolean
}

export interface FeishuDiagnosticStep {
  status: "ok" | "warning" | "error" | "success" | "info"
  name: string
  message: string
  suggestion?: string
}

export interface FeishuDiagnosticResult {
  status: "ok" | "warning" | "error" | "success" | "info"
  message?: string
  department_count?: number
  sample_user_count?: number
  steps?: FeishuDiagnosticStep[]
}

export interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}
