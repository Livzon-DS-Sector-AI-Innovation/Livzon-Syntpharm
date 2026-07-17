'use server'

import { revalidatePath } from 'next/cache'
import type {
  ProductDossier,
  ProductDossierCreate,
  ProductDossierUpdate,
  ChapterAsset,
  ParseResult,
  ExportResult,
  AIPreviewResult,
  AIConfirmRequest,
  AIFillResult,
  PageSplitPreviewResult,
} from '@/types/dossier-writer'
import type {
  UploadResponse,
  MatchResult,
  FieldFillResult,
} from '@/types/dossier-writer'

const API_BASE_URL = process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000'

async function actionFetch<T>(url: string, options?: RequestInit): Promise<T> {
  // AI 相关接口需要更长的超时时间（OCR + LLM 处理可能需要 10 分钟）
  const isAiEndpoint = url.includes('/ai-preview') || url.includes('/ai-confirm')
  const timeout = isAiEndpoint ? 600000 : 30000 // AI: 10分钟，其他: 30秒
  
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeout)
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      signal: controller.signal,
    })
    if (!response.ok) {
      const errorBody = await response.text().catch(() => '')
      let errorMessage = `请求失败: ${response.status} ${response.statusText}`
      try {
        const errorJson = JSON.parse(errorBody)
        if (errorJson.message) errorMessage = errorJson.message
      } catch {}
      throw new Error(errorMessage)
    }
    const json = await response.json()
    if (json.code !== 200) {
      throw new Error(json.message || '操作失败')
    }
    return json.data
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('请求超时，请稍后重试')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}

// ====== Product Dossier ======
export async function createProductDossier(data: ProductDossierCreate): Promise<ProductDossier> {
  const result = await actionFetch<ProductDossier>(`${API_BASE_URL}/api/v1/registration/dossier-writer/products`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function updateProductDossier(id: string, data: ProductDossierUpdate): Promise<ProductDossier> {
  const result = await actionFetch<ProductDossier>(`${API_BASE_URL}/api/v1/registration/dossier-writer/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function deleteProductDossier(id: string): Promise<void> {
  await actionFetch(`${API_BASE_URL}/api/v1/registration/dossier-writer/products/${id}`, {
    method: 'DELETE',
  })
  revalidatePath('/registration/dossier-writer')
}

// ====== Template Upload & Parsing ======
export async function uploadTemplates(dossierId: string, files: File[]): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))

  const res = await fetch(`${API_BASE_URL}/api/v1/registration/dossier-writer/products/${dossierId}/templates`, {
    method: 'POST',
    body: formData,
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '上传失败')
  revalidatePath('/registration/dossier-writer')
  return json.data
}

export async function parseTemplates(dossierId: string): Promise<ParseResult> {
  const result = await actionFetch<ParseResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/products/${dossierId}/parse`, {
    method: 'POST',
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Chapter Asset ======
export async function uploadChapterAsset(
  chapterId: string,
  files: File[]
): Promise<{ assets: ChapterAsset[]; count: number }> {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))

  const res = await fetch(`${API_BASE_URL}/api/v1/registration/dossier-writer/chapters/${chapterId}/assets`, {
    method: 'POST',
    body: formData,
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '上传失败')
  revalidatePath('/registration/dossier-writer')
  return json.data
}

export async function deleteChapterAsset(assetId: string): Promise<void> {
  await actionFetch(`${API_BASE_URL}/api/v1/registration/dossier-writer/assets/${assetId}`, {
    method: 'DELETE',
  })
  revalidatePath('/registration/dossier-writer')
}

// ====== Export ======
export async function exportDossier(dossierId: string, chapterIds?: string[]): Promise<ExportResult> {
  const result = await actionFetch<ExportResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/products/${dossierId}/export`, {
    method: 'POST',
    body: JSON.stringify({ chapter_ids: chapterIds || null, format: 'docx' }),
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Asset Matching ======
export async function matchAssetsToChapters(dossierId: string): Promise<MatchResult> {
  const result = await actionFetch<MatchResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/products/${dossierId}/match-assets`, {
    method: 'POST',
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Field Filling ======
export async function fillChapterFields(chapterId: string): Promise<FieldFillResult> {
  const result = await actionFetch<FieldFillResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/chapters/${chapterId}/fill-fields`, {
    method: 'POST',
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== AI Fill ======
export async function aiPreviewExtraction(chapterId: string): Promise<AIPreviewResult> {
  const result = await actionFetch<AIPreviewResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-preview`, {
    method: 'POST',
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function aiConfirmAndFill(chapterId: string, data: AIConfirmRequest): Promise<AIFillResult> {
  const result = await actionFetch<AIFillResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-confirm`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function splitPreview(
  assetId: string,
  availableAppendixSlots: string[]
): Promise<PageSplitPreviewResult> {
  const result = await actionFetch<PageSplitPreviewResult>(`${API_BASE_URL}/api/v1/registration/dossier-writer/assets/${assetId}/split-preview`, {
    method: 'POST',
    body: JSON.stringify({ available_appendix_slots: availableAppendixSlots }),
  })
  return result
}

export async function splitConfirmAndInsert(
  chapterId: string,
  splits: Array<{
    split_id: string
    appendix_slot: string
    asset_id: string
    page_number: number
  }>
): Promise<{ success: boolean; message: string; inserted_count: number }> {
  const result = await actionFetch<{ success: boolean; message: string; inserted_count: number }>(
    `${API_BASE_URL}/api/v1/registration/dossier-writer/chapters/${chapterId}/split-confirm`,
    {
      method: 'POST',
      body: JSON.stringify({ splits }),
    }
  )
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Asset Category ======
export async function updateAssetCategory(
  assetId: string,
  categoryId: string | null
): Promise<{ id: string; category_id: string | null }> {
  const res = await fetch(`${API_BASE_URL}/api/v1/registration/dossier-writer/assets/${assetId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId }),
  })
  const json = await res.json()
  if (json.code !== 200) throw new Error(json.message || '更新分类失败')
  revalidatePath('/registration/dossier-writer')
  return json.data
}

// ====== Asset Usage (素材使用管理) ======
export async function toggleAssetUsage(
  chapterId: string,
  assetId: string,
  isSelected: boolean
): Promise<{ usage_id?: string; is_selected: boolean }> {
  const result = await actionFetch<{ usage_id?: string; is_selected: boolean }>(
    `${API_BASE_URL}/api/v1/registration/dossier-writer/chapters/${chapterId}/asset-usages/${assetId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ is_selected: isSelected }),
    }
  )
  revalidatePath('/registration/dossier-writer')
  return result
}
