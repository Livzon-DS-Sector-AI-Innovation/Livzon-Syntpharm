import type { components } from '@/types/generated/schema'

export type DomesticApproval = components['schemas']['DomesticApprovalResponse']

export interface OverseasApproval {
  id: string
  product_name: string
  certificate_name: string | null
  batch_no: string | null
  issuing_authority: string | null
  issue_date: string | null
  valid_until: string | null
  product_scope: string | null
  quality_standard: string | null
  is_expired: string | null
  production_workshop: string | null
  product_validity: string | null
  storage_condition: string | null
  created_at: string
  updated_at: string
}

export interface InternationalReview {
  id: string
  product_name: string
  approved_countries: string | null
  approved_country_count: number | null
  approved_clients: string | null
  approved_client_count: number | null
  reviewing_countries: string | null
  reviewing_country_count: number | null
  reviewing_clients: string | null
  reviewing_client_count: number | null
  created_at: string
  updated_at: string
}

export interface CoppCertificate {
  id: string
  product_name: string
  certificate_name: string | null
  batch_no: string | null
  issuing_authority: string | null
  issue_date: string | null
  valid_until: string | null
  product_scope: string | null
  applicable_countries: string | null
  is_expired: string | null
  created_at: string
  updated_at: string
}

export interface WcCertificate {
  id: string
  product_name: string
  certificate_name: string | null
  batch_no: string | null
  issuing_authority: string | null
  issue_date: string | null
  valid_until: string | null
  product_scope: string | null
  is_expired: string | null
  created_at: string
  updated_at: string
}

export interface LedgerSummary {
  domestic_count: number
  overseas_count: number
  overseas_countries: number
  international_review_count: number
  copp_count: number
  wc_count: number
  reviewing_count: number
  planned_count: number
}

export interface ReviewingDrug {
  id: string
  product_name: string
  drug_type: string
  acceptance_date: string | null
  current_node: number
  node_1?: string | null
  node_2?: string | null
  node_3?: string | null
  node_4?: string | null
  node_5?: string | null
  node_6?: string | null
  node_7?: string | null
  node_8?: string | null
  node_9?: string | null
  node_10?: string | null
  created_at: string
  updated_at: string
}