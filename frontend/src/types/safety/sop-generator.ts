/**
 * Safety module domain model types (ViewModels).
 * These response types are not in the OpenAPI spec (backend uses dict responses).
 * API input types (Create/Update) use @/types/generated/schema.
 */

// ============ SOP Generator Types ============

export interface SopMeta {
  product_name: string
  post_name: string
  department: string
  doc_number: string
  effective_date: string
  company_name: string
}

export interface SopGenerateResult {
  regulation_id: string
  meta: SopMeta
  content: string
  status: string
}

