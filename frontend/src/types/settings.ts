// Settings types
// API input types are aliased from generated schema for single-source-of-truth.

import type { components } from '@/types/generated/schema'

// Type aliases for generated types
export type FeishuConfig = components['schemas']['FeishuConfigResponse']
export type FeishuConfigUpsert = components['schemas']['FeishuConfigUpsert']
export type FeishuDiagnosticStep = components['schemas']['FeishuDiagnosticStep']
export type FeishuDiagnosticResult = components['schemas']['FeishuDiagnosticResult']

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

// FeishuConfig (use generated type)

// FeishuConfigUpsert (use generated type)

// FeishuDiagnosticStep (use generated type)

// FeishuDiagnosticResult (use generated type)

export interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}
