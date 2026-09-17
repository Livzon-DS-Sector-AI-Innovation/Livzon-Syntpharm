'use server'

import { getAuthHeaders } from '@/lib/auth'
import {
  fetchPreviewPush as fetchPreviewPushApi,
  fetchPreviewPull as fetchPreviewPullApi,
  fetchUndoLastSync as fetchUndoLastSyncApi,
} from '@/lib/api/server/product-output'

export async function fetchPreviewPush(productId: string): Promise<Record<string, unknown>> {
  const authHeaders = await getAuthHeaders()
  return fetchPreviewPushApi(productId, authHeaders) as Promise<Record<string, unknown>>
}

export async function fetchPreviewPull(productId: string): Promise<Record<string, unknown>> {
  const authHeaders = await getAuthHeaders()
  return fetchPreviewPullApi(productId, authHeaders) as Promise<Record<string, unknown>>
}

export async function fetchUndoLastSync(productId: string): Promise<Record<string, unknown>> {
  const authHeaders = await getAuthHeaders()
  return fetchUndoLastSyncApi(productId, authHeaders) as Promise<Record<string, unknown>>
}
