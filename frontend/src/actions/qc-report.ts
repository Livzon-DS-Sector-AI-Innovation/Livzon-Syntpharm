'use server'

/**
 * 质量检验台账：写操作。
 *
 * 只放小体积写操作；文件上传走浏览器直连（见 lib/api/client/qc-report.ts）。
 * 读操作一律在 lib/api/server/qc-report.ts，不要放这里。
 */

import { apiFetch } from '@/lib/api/server/base'
import type {
  QcBatchCreateInput,
  QcBatchRow,
  QcItem,
  QcProduct,
  QcRejudgeResult,
} from '@/types/qc-report'

const BASE = '/api/v1/quality/qc-report'

export async function createQcProductAction(input: {
  name: string
  abbr: string
  category: string
  quality_standard?: string | null
}): Promise<QcProduct> {
  const raw = await apiFetch<{ code: number; data: QcProduct }>(`${BASE}/products`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
  return raw.data
}

export async function updateQcItemAction(
  itemId: string,
  input: {
    legal_text?: string | null
    internal_text?: string | null
    sigma_text?: string | null
    sigma_basis_period?: string | null
    is_enabled?: boolean
  },
): Promise<QcItem> {
  const raw = await apiFetch<{ code: number; data: QcItem }>(`${BASE}/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(input),
  })
  return raw.data
}

export async function createQcBatchAction(
  productId: string,
  input: QcBatchCreateInput,
): Promise<QcBatchRow> {
  const raw = await apiFetch<{ code: number; data: QcBatchRow }>(
    `${BASE}/products/${productId}/batches`,
    { method: 'POST', body: JSON.stringify(input) },
  )
  return raw.data
}

export async function rejudgeQcProductAction(productId: string): Promise<QcRejudgeResult> {
  const raw = await apiFetch<{ code: number; data: QcRejudgeResult }>(
    `${BASE}/products/${productId}/rejudge`,
    { method: 'POST' },
  )
  return raw.data
}

export async function deleteQcProductAction(productId: string): Promise<void> {
  await apiFetch(`${BASE}/products/${productId}`, { method: 'DELETE' })
}
