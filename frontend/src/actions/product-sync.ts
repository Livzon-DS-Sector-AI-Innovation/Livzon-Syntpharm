'use server'

import { getAuthHeaders } from '@/lib/auth'
import {
  fetchPreviewPush as fetchPreviewPushApi,
  fetchPreviewPull as fetchPreviewPullApi,
  fetchUndoLastSync as fetchUndoLastSyncApi,
} from '@/lib/api/server/product-output'

export async function fetchPreviewPush(productId: string) {
  const authHeaders = await getAuthHeaders()
  return fetchPreviewPushApi(productId, authHeaders) as any
}

export async function fetchPreviewPull(productId: string) {
  const authHeaders = await getAuthHeaders()
  return fetchPreviewPullApi(productId, authHeaders) as any
}

export async function fetchUndoLastSync(productId: string) {
  const authHeaders = await getAuthHeaders()
  return fetchUndoLastSyncApi(productId, authHeaders) as any
}
