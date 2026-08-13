import type { components } from '@/types/generated/schema'

/**
 * Domain model types (ViewModels) — not in OpenAPI spec.
 * API input types (Create/Update) use @/types/generated/schema.
 */

// product-output module TypeScript types

import type { ApiResponse } from '@/types/production'
// Annual Review types (from generated schema)
export type MonthlyTrend = components["schemas"]["app__modules__production__product__output_schemas__MonthlyTrend"]
export type WorkshopRanking = components["schemas"]["app__modules__production__product__output_schemas__WorkshopRanking"]
export type TopProduct = components["schemas"]["app__modules__production__product__output_schemas__TopProduct"]
export type AnnualOverview = components["schemas"]["app__modules__production__product__output_schemas__AnnualOverview"]
export type AnnualReviewData = components["schemas"]["app__modules__production__product__output_schemas__AnnualReviewResponse"]

export type { ApiResponse }

export const WORKSHOPS = [
  '101车间',
  '102车间',
  '103车间',
  '106车间',
  '201车间',
  '202车间',
  '203车间',
  '301车间',
  '302车间',
  '303车间',
  '溶剂回收车间',
] as const

export type Workshop = (typeof WORKSHOPS)[number]

export interface ProductOutput {
  id: string
  product_id: string | null
  workshop: string
  product_name: string
  batch_no: string
  production_date: string
  end_date?: string
  weight: number
  unit: string
  notes?: string
  created_at: string
  updated_at: string
}

export interface ProductOutputFormData {
  product_id: string | null
  workshop: string
  product_name: string
  batch_no: string
  production_date: string
  end_date?: string
  weight: number
  unit?: string
  notes?: string
}

export interface ProductOutputQueryParams {
  page?: number
  page_size?: number
  workshop?: string
  product_id?: string
  product_name?: string
  batch_no?: string
  start_date?: string
  end_date?: string
  sort_by?: string
  sort_order?: string
}

export interface WorkshopSummary {
  workshop: string
  daily_total: number
  monthly_total: number
  yearly_total: number
}

export interface SummaryData {
  target_date?: string
  month?: string
  year?: number
  workshops: WorkshopSummary[]
  grand_total: number
}


