/**
 * Product module TypeScript types
 * 
 * NOTE: These types are hand-written because the backend doesn't export them via OpenAPI.
 * The backend routes use `response_model=dict` or return dicts via `success_response()`,
 * so these types don't appear in the generated schema.
 * 
 * To fix this properly, the backend needs to:
 * 1. Add `response_model=ProductResponse` to routes in `app/modules/product/api.py`
 * 2. Use typed response models instead of `success_response()` dicts
 * 3. Regenerate OpenAPI spec and frontend types
 * 
 * See AGENTS.md: "所有 API 相关的类型必须从 @/types/generated/schema 导入"
 */

export interface Product {
  id: string
  name: string
  major_category?: string
  formulation_code?: string
  product_type?: string
  spec?: string
  capacity_range?: string
  unit?: string
  indication?: string
  feishu_record_id?: string
  feishu_synced_at?: string
  created_at?: string
  updated_at?: string
}

export interface ProductCreateInput {
  name: string
  major_category?: string
  formulation_code?: string
  product_type?: string
  spec?: string
  capacity_range?: string
  unit?: string
  indication?: string
}

export interface ProductUpdateInput {
  name?: string
  major_category?: string
  formulation_code?: string
  product_type?: string
  spec?: string
  capacity_range?: string
  unit?: string
  indication?: string
}

export interface ProductListResponse {
  code: number
  message: string
  data: Product[]
  meta?: {
    page: number
    page_size: number
    total: number
  }
}

export interface ProductResponse {
  code: number
  message: string
  data: Product
}

export interface SyncStatusResponse {
  code: number
  message: string
  data: {
    local_total: number
    feishu_total: number
    synced_count: number
    unsynced_count: number
    last_sync_at: string | null
  }
}
