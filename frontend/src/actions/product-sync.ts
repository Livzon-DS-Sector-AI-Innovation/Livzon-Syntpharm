'use server'

import { getAuthHeaders } from '@/lib/auth'
import {
  previewPush as previewPushApi,
  previewPull as previewPullApi,
  undoLastSync as undoLastSyncApi,
} from '@/lib/api/server/product-output'

export async function previewPush(productId: string) {
  const authHeaders = await getAuthHeaders()
  return previewPushApi(productId, authHeaders)
}

export async function previewPull(productId: string) {
  const authHeaders = await getAuthHeaders()
  return previewPullApi(productId, authHeaders)
}

export async function undoLastSync(productId: string) {
  const authHeaders = await getAuthHeaders()
  return undoLastSyncApi(productId, authHeaders)
}
