import {
  ProductListResponse,
  ProductResponse,
  SyncStatusResponse,
} from '@/types/product'

export async function fetchProducts(
  params?: {
    name?: string
    category?: string
    product_type?: string
    keyword?: string
    page?: number
    page_size?: number
  }
): Promise<ProductListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.name) searchParams.set('name', params.name)
  if (params?.category) searchParams.set('category', params.category)
  if (params?.product_type) searchParams.set('product_type', params.product_type)
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const url = `/api/v1/product/products?${searchParams.toString()}`
  const res = await fetch(url, {
    cache: 'no-store',
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    console.error('[fetchProducts] failed:', res.status, url, text)
    throw new Error(`获取产品列表失败 (${res.status})`)
  }
  return res.json()
}

export async function fetchProductById(id: string): Promise<ProductResponse> {
  const res = await fetch(`/api/v1/product/products/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取产品详情失败')
  return res.json()
}

export async function fetchProductSyncStatus(): Promise<SyncStatusResponse> {
  const res = await fetch(`/api/v1/product/products/sync-status`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取同步状态失败')
  return res.json()
}


