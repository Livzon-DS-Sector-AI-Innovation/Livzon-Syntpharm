/**
 * 质量检验台账：服务端只读取数。
 *
 * 注意：读操作必须走这里，不能包进 `actions/`（'use server'），
 * 否则 cookies() 取不到 auth_token，后端 401、整页 500。
 */

import { apiFetch, buildQueryString, unwrapResponse } from '@/lib/api/server/base'
import type {
  QcAttentionBatch,
  QcBatchPageData,
  QcItem,
  QcProduct,
  QcProductListItem,
  QcStats,
} from '@/types/qc-report'

const BASE = '/api/v1/quality/qc-report'

export async function fetchQcProducts(params?: {
  keyword?: string
  category?: string
  top_level?: string
}): Promise<QcProductListItem[]> {
  const qs = buildQueryString({
    keyword: params?.keyword,
    category: params?.category,
    top_level: params?.top_level,
  })
  const raw = await apiFetch<{ code: number; data: QcProductListItem[] }>(`${BASE}/products${qs}`)
  return unwrapResponse(raw) ?? []
}

export async function fetchQcProduct(productId: string): Promise<QcProduct> {
  const raw = await apiFetch<{ code: number; data: QcProduct }>(`${BASE}/products/${productId}`)
  return unwrapResponse(raw)
}

/**
 * 取品种；不存在时返回 null 而不是抛错。
 * 品种被删掉后再访问它的报表页是很常见的（书签、历史记录），
 * 这种情况应该走 404，不该在控制台打一屏堆栈。
 */
export async function fetchQcProductOrNull(productId: string): Promise<QcProduct | null> {
  try {
    return await fetchQcProduct(productId)
  } catch (error) {
    if (error instanceof Error && /不存在|未找到|404|not found/i.test(error.message)) {
      return null
    }
    throw error
  }
}

export async function fetchQcItems(productId: string): Promise<QcItem[]> {
  const raw = await apiFetch<{ code: number; data: QcItem[] }>(`${BASE}/products/${productId}/items`)
  return unwrapResponse(raw) ?? []
}

export async function fetchQcBatches(params: {
  productId: string
  page?: number
  page_size?: number
  batch_no?: string
  level?: string
}): Promise<QcBatchPageData> {
  const qs = buildQueryString({
    page: params.page,
    page_size: params.page_size,
    batch_no: params.batch_no,
    level: params.level,
  })
  const raw = await apiFetch<{ code: number; data: QcBatchPageData }>(
    `${BASE}/products/${params.productId}/batches${qs}`,
  )
  return unwrapResponse(raw)
}

export async function fetchQcStats(productId: string): Promise<QcStats> {
  const raw = await apiFetch<{ code: number; data: QcStats }>(`${BASE}/products/${productId}/stats`)
  return unwrapResponse(raw)
}

export async function fetchQcAttentionBatches(limit = 20): Promise<QcAttentionBatch[]> {
  const raw = await apiFetch<{ code: number; data: QcAttentionBatch[] }>(
    `${BASE}/attention-batches?limit=${limit}`,
  )
  return unwrapResponse(raw) ?? []
}
