import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function markDocumentRead(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/regulatory-documents/${id}/read`, {
    method: 'PATCH',
  })
}

export async function fetchAIAnalysis(docId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/regulatory-documents/${docId}/analyze`, {
    method: 'POST',
    cache: 'no-store',
  })
}

export async function fetchAIBatchAnalysis(docIds: string[]) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/regulatory-documents/analyze?limit=${docIds.length}`, {
    method: 'POST',
    body: JSON.stringify({ doc_ids: docIds }),
    cache: 'no-store',
  })
}