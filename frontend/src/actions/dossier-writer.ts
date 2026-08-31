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
  OCRTaskStartResponse,
  OCRTaskStatusResponse,
  AIConfirmRequest,
  AIFillResult,
  PageSplitPreviewResult,
} from '@/types/dossier-writer'
import type {
  UploadResponse,
  MatchResult,
  FieldFillResult,
} from '@/types/dossier-writer'
import type { components } from '@/types/generated/schema'
import { apiFetch, unwrapResponse } from '@/lib/api/server/base'

type SplitConfirmData = components['schemas']['SplitConfirmData']
type AssetCategoryUpdateData = components['schemas']['AssetCategoryUpdateData']
type AssetUsageToggleData = components['schemas']['AssetUsageToggleData']

type SplitConfirmResult = SplitConfirmData
import {
  uploadTemplatesApi,
  uploadChapterAssetApi,
  updateAssetCategoryApi,
} from '@/lib/api/server/dossier-writer'

// ====== Product Dossier ======
export async function createProductDossier(data: ProductDossierCreate): Promise<ProductDossier> {
  const result = unwrapResponse(await apiFetch<{code: number; data: ProductDossier; message?: string; meta?: unknown}>('/api/v1/registration/dossier-writer/products', {
    method: 'POST',
    body: JSON.stringify(data),
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function updateProductDossier(id: string, data: ProductDossierUpdate): Promise<ProductDossier> {
  const result = unwrapResponse(await apiFetch<{code: number; data: ProductDossier; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/products/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function deleteProductDossier(id: string): Promise<void> {
  unwrapResponse(await apiFetch<{code: number; data: void; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/products/${id}`, {
    method: 'DELETE',
  }))
  revalidatePath('/registration/dossier-writer')
}

// ====== Template Upload & Parsing ======
export async function uploadTemplates(dossierId: string, files: any): Promise<UploadResponse> {
  const formData = new FormData()
  files.forEach((file: any) => formData.append('files', file))

  const result = await uploadTemplatesApi(dossierId, formData)
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function parseTemplates(dossierId: string): Promise<ParseResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: ParseResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/products/${dossierId}/parse`, {
    method: 'POST',
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Chapter Asset ======
export async function uploadChapterAsset(
  chapterId: string,
  files: any
): Promise<{ assets: ChapterAsset[]; count: number }> {
  const formData = new FormData()
  files.forEach((file: any) => formData.append('files', file))

  const result = await uploadChapterAssetApi(chapterId, formData)
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function deleteChapterAsset(assetId: string): Promise<void> {
  unwrapResponse(await apiFetch<{code: number; data: void; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/assets/${assetId}`, {
    method: 'DELETE',
  }))
  revalidatePath('/registration/dossier-writer')
}

// ====== Export ======
export async function exportDossier(dossierId: string, chapterIds?: string[]): Promise<ExportResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: ExportResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/products/${dossierId}/export`, {
    method: 'POST',
    body: JSON.stringify({ chapter_ids: chapterIds || null, format: 'docx' }),
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Asset Matching ======
export async function matchAssetsToChapters(dossierId: string): Promise<MatchResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: MatchResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/products/${dossierId}/match-assets`, {
    method: 'POST',
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Field Filling ======
export async function fillChapterFields(chapterId: string): Promise<FieldFillResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: FieldFillResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/chapters/${chapterId}/fill-fields`, {
    method: 'POST',
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== AI Fill ======
export async function aiPreviewExtraction(chapterId: string): Promise<AIPreviewResult> {
  // Start OCR tasks (returns immediately with task_ids)
  const startResponse = await apiFetch<{code: number; data: OCRTaskStartResponse; message?: string}>(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-preview`,
    {
      method: 'POST',
    }
  )
  
  if (!startResponse || !startResponse.data) {
    throw new Error('Invalid response from server')
  }
  
  const startResult = unwrapResponse(startResponse)
  const taskIds = startResult.task_ids
  
  if (!taskIds || taskIds.length === 0) {
    throw new Error('No OCR tasks created')
  }
  
  // Poll for task completion
  const pollTask = async (attempt: number = 0): Promise<AIPreviewResult> => {
    const maxAttempts = 600 // 20 minutes at 2 second intervals
    
    if (attempt >= maxAttempts) {
      throw new Error('OCR tasks timed out')
    }
    
    try {
      const taskResults = await Promise.all(
        taskIds.map(async (taskId: string) => {
          const response = await apiFetch<{code: number; data: OCRTaskStatusResponse}>(
            `/api/v1/registration/dossier-writer/ocr-tasks/${taskId}`,
            { method: 'GET' }
          )
          if (!response || !response.data) {
            throw new Error('Invalid polling response')
          }
          return unwrapResponse(response)
        })
      )
      
      const allCompleted = taskResults.every(task => task.status === 'completed')
      const anyFailed = taskResults.some(task => task.status === 'failed')
      
      if (anyFailed) {
        const failedTask = taskResults.find(task => task.status === 'failed')
        throw new Error(failedTask?.error_message || 'OCR task failed')
      }
      
      if (allCompleted) {
        const mergedFields: AIFieldResult[] = []
        let tokenUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
        
        for (const task of taskResults) {
          if (task.result) {
            mergedFields.push(...task.result.fields)
            if (task.result.token_usage) {
              tokenUsage.prompt_tokens += task.result.token_usage.prompt_tokens
              tokenUsage.completion_tokens += task.result.token_usage.completion_tokens
              tokenUsage.total_tokens += task.result.token_usage.total_tokens
            }
          }
        }
        
        revalidatePath('/registration/dossier-writer')
        
        return {
          success: true,
          message: 'AI extraction completed',
          fields: mergedFields,
          token_usage: tokenUsage,
        }
      }
    } catch (error) {
      console.error('[OCR] Polling error:', error)
    }
    
    await new Promise(resolve => setTimeout(resolve, 2000))
    return pollTask(attempt + 1)
  }
  
  return pollTask()
}

export async function aiConfirmAndFill(chapterId: string, data: AIConfirmRequest): Promise<AIFillResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: AIFillResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-confirm`, {
    method: 'POST',
    body: JSON.stringify(data),
    signal: AbortSignal.timeout(600000),
  }))
  revalidatePath('/registration/dossier-writer')
  return result
}

export async function splitPreview(
  assetId: string,
  availableAppendixSlots: string[]
): Promise<PageSplitPreviewResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: PageSplitPreviewResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/assets/${assetId}/split-preview`, {
    method: 'POST',
    body: JSON.stringify({ available_appendix_slots: availableAppendixSlots }),
    signal: AbortSignal.timeout(600000), // 拆分预览含 OCR，需要 10 分钟超时
  }))
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
): Promise<SplitConfirmResult> {
  const result = unwrapResponse(await apiFetch<{code: number; data: SplitConfirmResult; message?: string; meta?: unknown}>(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/split-confirm`,
    {
      method: 'POST',
      body: JSON.stringify({ splits }),
    }
  ))
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Asset Category ======
export async function updateAssetCategory(
  assetId: string,
  categoryId: string | null
): Promise<AssetCategoryUpdateData> {
  const result = await updateAssetCategoryApi(assetId, categoryId)
  revalidatePath('/registration/dossier-writer')
  return result
}

// ====== Asset Usage (素材使用管理) ======
export async function toggleAssetUsage(
  chapterId: string,
  assetId: string,
  isSelected: boolean
): Promise<AssetUsageToggleData> {
  const result = unwrapResponse(await apiFetch<{code: number; data: AssetUsageToggleData; message?: string; meta?: unknown}>(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/asset-usages/${assetId}`,
    {
      method: 'PATCH',
      body: JSON.stringify({ is_selected: isSelected }),
    }
  ))
  revalidatePath('/registration/dossier-writer')
  return result
}
