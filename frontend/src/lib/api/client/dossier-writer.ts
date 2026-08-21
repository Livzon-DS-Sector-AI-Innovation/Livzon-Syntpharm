import type {
  ProductDossier,
  Chapter,
  ChapterDetail,
  ChapterAsset,
  PaginatedResponse,
  ApiResponse,
  ChapterPreview,
  AssetCategory,
  AvailableAsset,
} from '@/types/dossier-writer'


const _headers = { 'Content-Type': 'application/json' }

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

// ====== AI Fill ======

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
// POST operations moved to actions/dossier-writer.ts
