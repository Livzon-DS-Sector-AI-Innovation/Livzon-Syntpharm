import type {
  ProductDossier,
  Chapter,
  ChapterDetail,
  ChapterAsset,
  PaginatedResponse,
  ApiResponse,
  UploadResult,
  UploadResponse,
} from '@/types/dossier-writer'


const headers = { 'Content-Type': 'application/json' }

// ====== Product Dossier ======

export async function fetchProductDossiers(
  skip: number = 0,
  limit: number = 100
): Promise<PaginatedResponse<ProductDossier>> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/products?skip=${skip}&limit=${limit}`
  )
  const json: ApiResponse<PaginatedResponse<ProductDossier>> = await res.json()
  return json.data
}

export async function fetchProductDossier(id: string): Promise<ProductDossier> {
  const res = await fetch(`/api/v1/registration/dossier-writer/products/${id}`)
  const json: ApiResponse<ProductDossier> = await res.json()
  return json.data
}

// ====== Template Upload ======

export async function uploadTemplatesClient(dossierId: string, files: FileList): Promise<UploadResponse> {
  const formData = new FormData()
  Array.from(files).forEach(file => formData.append('files', file))

  const res = await fetch(`/api/v1/registration/dossier-writer/products/${dossierId}/templates`, {
    method: 'POST',
    body: formData,
  })
  const json: ApiResponse<UploadResponse> = await res.json()
  if (json.code !== 200) throw new Error(json.message || '上传失败')
  return json.data
}


// ====== Template Parsing ======

// ====== Chapter ======

export async function fetchChapterTree(dossierId: string): Promise<Chapter[]> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/products/${dossierId}/chapters`
  )
  const json: ApiResponse<Chapter[]> = await res.json()
  return json.data
}

export async function fetchChapterDetail(chapterId: string): Promise<ChapterDetail> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}`
  )
  const json: ApiResponse<ChapterDetail> = await res.json()
  return json.data
}

// ====== Asset ======

export async function fetchChapterAssets(chapterId: string): Promise<ChapterAsset[]> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/assets`
  )
  const json: ApiResponse<ChapterAsset[]> = await res.json()
  return json.data
}

// ====== Export ======

export function getDownloadUrl(dossierId: string, filename: string): string {
  return `/api/v1/registration/dossier-writer/products/${dossierId}/download?filename=${encodeURIComponent(filename)}`
}


// ====== Chapter Preview ======

export interface ChapterPreview {
  success: boolean
  chapter_code: string
  chapter_title: string
  paragraphs: Array<{ text: string; style: string }>
  tables: string[][][]
  message?: string
}

export async function getChapterPreview(chapterId: string): Promise<ChapterPreview> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/preview`
  )
  const json: ApiResponse<ChapterPreview> = await res.json()
  
  if (json.code !== 200) {
    throw new Error(json.message || '获取预览失败')
  }
  
  return json.data
}

// ====== Asset Matching ======

export interface MatchResult {
  success: boolean
  message: string
  matched_count: number
  unmatched_files: string[]
}

// ====== Field Filling ======

export interface FieldFillResult {
  success: boolean
  message: string
  filled_count: number
  total_fields: number
  results: Array<{
    field_name: string
    status: string
    filled_value: string | null
  }>
}

// ====== AI Fill ======

import type {
  AssetCategory,
} from '@/types/dossier-writer'

export async function fetchAssetCategories(chapterCode: string): Promise<AssetCategory[]> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/chapters/${chapterCode}/asset-categories`
  )
  const json: ApiResponse<AssetCategory[]> = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '获取素材分类失败')
  }
  return json.data
}

// ====== Chapter Docx File ======

export function getChapterDocxUrl(chapterId: string): string {
  return `/api/v1/registration/dossier-writer/chapters/${chapterId}/docx-file`
}

export async function fetchChapterDocx(chapterId: string): Promise<ArrayBuffer | null> {
  try {
    // Add cache-busting timestamp to avoid browser caching
    const url = `/api/v1/registration/dossier-writer/chapters/${chapterId}/docx-file?t=${Date.now()}`
    const res = await fetch(url, {
      cache: 'no-cache',
      headers: {
        'Cache-Control': 'no-cache',
      },
    })
    if (!res.ok) return null
    return await res.arrayBuffer()
  } catch {
    return null
  }
}

// ====== Asset Category ======



// ====== Asset Usage (素材使用管理) ======

import type { AvailableAsset } from '@/types/dossier-writer'

export async function fetchAvailableAssets(chapterId: string): Promise<AvailableAsset[]> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/available-assets`
  )
  const json: ApiResponse<AvailableAsset[]> = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '获取可用素材失败')
  }
  return json.data
}

export async function fetchSelectedAssets(chapterId: string): Promise<ChapterAsset[]> {
  const res = await fetch(
    `/api/v1/registration/dossier-writer/chapters/${chapterId}/selected-assets`
  )
  const json: ApiResponse<ChapterAsset[]> = await res.json()
  if (json.code !== 200) {
    throw new Error(json.message || '获取已选素材失败')
  }
  return json.data
}

// ====== AI Preview (客户端调用，绕过 server action 超时) ======
export async function aiPreviewExtractionClient(chapterId: string): Promise<any> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 600000) // 10分钟超时
  
  try {
    const res = await fetch(
      `/api/v1/registration/dossier-writer/chapters/${chapterId}/ai-preview`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
      }
    )
    
    // 安全解析响应：检查 content-type 和响应状态
    const contentType = res.headers.get('content-type') || ''
    let payload: any
    
    if (contentType.includes('application/json')) {
      payload = await res.json()
    } else {
      // 非 JSON 响应，读取文本内容
      const text = await res.text()
      throw new Error(`AI解析失败：HTTP ${res.status} ${text || res.statusText}`)
    }
    
    // 检查响应状态
    if (!res.ok || payload.code !== 200) {
      throw new Error(payload.message || payload.error?.message || `AI解析失败：HTTP ${res.status}`)
    }
    
    return payload.data
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('AI 解析超时（10分钟），请稍后重试或减少素材数量')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}
