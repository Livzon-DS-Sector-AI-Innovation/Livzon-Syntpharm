'use server'

import { API_BASE_URL } from '@/lib/api/server/base'

export async function previewPush(productId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}/preview-push`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return res.json()
}

export async function previewPull(productId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}/preview-pull`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return res.json()
}

export async function undoLastSync(productId: string) {
  const res = await fetch(`${API_BASE_URL}/api/v1/production/product-sync-config/${productId}/undo-last-sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  return res.json()
}
