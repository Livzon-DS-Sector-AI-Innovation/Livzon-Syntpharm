import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type {
  ProductDossierCreate,
  ProductDossierUpdate,
  AIConfirmRequest,
} from '@/types/dossier-writer'

async function apiFetchFormData(url: string, body: FormData): Promise<any> {
  const res = await fetch(url, {
    method: 'POST',
    body,
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '上传失败')
  return json.data
}

export async function createProductDossierApi(data: ProductDossierCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProductDossierApi(id: string, data: ProductDossierUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProductDossierApi(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products/${id}`, {
    method: 'DELETE',
  })
}

export async function uploadTemplatesApi(dossierId: string, formData: FormData) {
  return apiFetchFormData(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products/${dossierId}/templates`, formData)
}

export async function parseTemplatesApi(dossierId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products/${dossierId}/parse`, {
    method: 'POST',
  })
}

export async function uploadChapterAssetApi(chapterId: string, formData: FormData) {
  return apiFetchFormData(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/chapters/${chapterId}/assets`, formData)
}

export async function deleteChapterAssetApi(assetId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/assets/${assetId}`, {
    method: 'DELETE',
  })
}

export async function exportDossierApi(dossierId: string, chapterIds?: string[]) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products/${dossierId}/export`, {
    method: 'POST',
    body: JSON.stringify({ chapter_ids: chapterIds || null, format: 'docx' }),
  })
}

export async function matchAssetsToChaptersApi(dossierId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/products/${dossierId}/match-assets`, {
    method: 'POST',
  })
}

export async function fillChapterFieldsApi(chapterId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/chapters/${chapterId}/fill-fields`, {
    method: 'POST',
  })
}

export async function aiPreviewExtractionApi(chapterId: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-preview`, {
    method: 'POST',
  })
}

export async function aiConfirmAndFillApi(chapterId: string, data: AIConfirmRequest) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-confirm`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function splitPreviewApi(assetId: string, availableAppendixSlots: string[]) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/assets/${assetId}/split-preview`, {
    method: 'POST',
    body: JSON.stringify({ available_appendix_slots: availableAppendixSlots }),
  })
}

export async function splitConfirmAndInsertApi(
  chapterId: string,
  splits: Array<{
    split_id: string
    appendix_slot: string
    asset_id: string
    page_number: number
  }>
) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/chapters/${chapterId}/split-confirm`, {
    method: 'POST',
    body: JSON.stringify({ splits }),
  })
}

export async function updateAssetCategoryApi(assetId: string, categoryId: string | null) {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/registration/dossier-writer/assets/${assetId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId }),
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '更新分类失败')
  return json.data
}