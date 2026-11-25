import type {
  ProductDossier,
  Chapter,
  ChapterDetail,
  ChapterAsset,
  ChapterPreview,
  AssetCategory,
  AvailableAsset,
} from '@/types/dossier-writer'
import type { ApiResponse, PaginatedResponse } from '@/types/common'

const API_BASE = '/api/v1/registration/dossier-writer'

/**
 * 统一拉取并校验 JSON 响应：
 * - 非 2xx（如 401/502 返回 HTML 错误页）直接抛错，避免 `res.json()` 抛 SyntaxError 后被上游静默成「空列表」；
 * - 响应不是 JSON 时给出可读提示；
 * - 业务 code 非 200 抛后端 message；
 * - 成功返回 data。
 */
async function fetchJsonData<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(`请求失败: ${res.status} ${res.statusText}`)
  }
  let json: ApiResponse<T>
  try {
    json = (await res.json()) as ApiResponse<T>
  } catch {
    throw new Error('响应格式异常，请稍后重试')
  }
  if (json.code !== 200) {
    throw new Error(json.message || '请求失败')
  }
  return json.data
}

// ====== Product Dossier ======

export function fetchProductDossiers(
  skip: number = 0,
  limit: number = 100
): Promise<PaginatedResponse<ProductDossier>> {
  return fetchJsonData<PaginatedResponse<ProductDossier>>(
    `${API_BASE}/products?skip=${skip}&limit=${limit}`
  )
}

export function fetchProductDossier(id: string): Promise<ProductDossier> {
  return fetchJsonData<ProductDossier>(`${API_BASE}/products/${id}`)
}

// ====== Template Upload ======

// ====== Template Parsing ======

// ====== Chapter ======

export function fetchChapterTree(dossierId: string): Promise<Chapter[]> {
  return fetchJsonData<Chapter[]>(`${API_BASE}/products/${dossierId}/chapters`)
}

export function fetchChapterDetail(chapterId: string): Promise<ChapterDetail> {
  return fetchJsonData<ChapterDetail>(`${API_BASE}/chapters/${chapterId}`)
}

// ====== Asset ======

export function fetchChapterAssets(chapterId: string): Promise<ChapterAsset[]> {
  return fetchJsonData<ChapterAsset[]>(`${API_BASE}/chapters/${chapterId}/assets`)
}

// ====== Export ======

export function getDownloadUrl(dossierId: string, filename: string): string {
  return `${API_BASE}/products/${dossierId}/download?filename=${encodeURIComponent(filename)}`
}

// ====== Chapter Preview ======

export function getChapterPreview(chapterId: string): Promise<ChapterPreview> {
  return fetchJsonData<ChapterPreview>(`${API_BASE}/chapters/${chapterId}/preview`)
}

// ====== Asset Matching ======

// ====== AI Fill ======

export function fetchAssetCategories(chapterCode: string): Promise<AssetCategory[]> {
  return fetchJsonData<AssetCategory[]>(`${API_BASE}/chapters/${chapterCode}/asset-categories`)
}

// ====== Chapter Docx File ======

export function getChapterDocxUrl(chapterId: string): string {
  return `${API_BASE}/chapters/${chapterId}/docx-file`
}

export async function fetchChapterDocx(chapterId: string): Promise<ArrayBuffer | null> {
  try {
    // Add cache-busting timestamp to avoid browser caching
    const url = `${API_BASE}/chapters/${chapterId}/docx-file?t=${Date.now()}`
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

export function fetchAvailableAssets(chapterId: string): Promise<AvailableAsset[]> {
  return fetchJsonData<AvailableAsset[]>(`${API_BASE}/chapters/${chapterId}/available-assets`)
}

export function fetchSelectedAssets(chapterId: string): Promise<ChapterAsset[]> {
  return fetchJsonData<ChapterAsset[]>(`${API_BASE}/chapters/${chapterId}/selected-assets`)
}

// ====== AI Preview (客户端调用，绕过 server action 超时) ======
// POST operations moved to actions/dossier-writer.ts
