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
import type { components } from '@/types/generated/schema'
import { apiFetch, unwrapResponse } from '@/lib/api/server/base'

type SplitConfirmData = components['schemas']['SplitConfirmData']
type AssetCategoryUpdateData = components['schemas']['AssetCategoryUpdateData']
type AssetUsageToggleData = components['schemas']['AssetUsageToggleData']
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
export async function uploadTemplates(dossierId: string, files: FileList | File[]): Promise<UploadResponse> {
  const formData = new FormData()
  if (files instanceof FileList) {
    Array.from(files).forEach((file: File) => formData.append('files', file))
  } else {
    files.forEach((file: File) => formData.append('files', file))
  }

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
  files: FileList | File[]
): Promise<{ assets: ChapterAsset[]; count: number }> {
  const formData = new FormData()
  if (files instanceof FileList) {
    Array.from(files).forEach((file: File) => formData.append('files', file))
  } else {
    files.forEach((file: File) => formData.append('files', file))
  }

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
  const result = unwrapResponse(await apiFetch<{code: number; data: AIPreviewResult; message?: string; meta?: unknown}>(`/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-preview`, {
    method: 'POST',
    signal: AbortSignal.timeout(600000),
  }))
  revalidatePath('/registration/dossier-writer')
  return result
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
): Promise<SplitConfirmData> {
  const result = unwrapResponse(await apiFetch<{code: number; data: SplitConfirmData; message?: string; meta?: unknown}>(
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
