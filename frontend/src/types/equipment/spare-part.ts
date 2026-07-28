import type { components } from '@/types/generated/schema'
export type CreateSparePartInput = components['schemas']['SparePartCreate']
export type UpdateSparePartInput = components['schemas']['SparePartUpdate']
export type StockInboundInput = components['schemas']['StockInboundRequest']
export type StockAdjustInput = components['schemas']['StockAdjustRequest']

// ==================== 备件管理 ====================
export interface SparePart {
  id: string
  code: string
  name: string
  specification: string | null
  unit: string
  category: string | null
  default_supplier: string | null
  unit_price: number | null
  min_qty: number
  current_qty: number
  is_active: boolean
  created_at: string
  updated_at: string
  created_by: string | null
  updated_by: string | null
}



export interface SparePartFilters {
  category?: string
  keyword?: string
  is_active?: boolean
  page?: number
  page_size?: number
}

export interface SparePartListResponse {
  items: SparePart[]
  total: number
  page: number
  page_size: number
}



export interface StockWarning {
  spare_part_id: string
  code: string
  name: string
  current_qty: number
  min_qty: number
}

export interface SparePartStockResponse {
  current_qty: number
  min_qty: number
}
