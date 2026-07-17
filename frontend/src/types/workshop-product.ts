/**
 * Domain model types (ViewModels) — not in OpenAPI spec.
 * API input types (Create/Update) use @/types/generated/schema.
 */

// Workshop Product types (for production module)

export interface WorkshopProduct {
  id: string
  workshop: string
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface WorkshopProductCreate {
  workshop: string
  name: string
  description?: string
}

export interface WorkshopProductUpdate {
  name?: string
  description?: string
}
