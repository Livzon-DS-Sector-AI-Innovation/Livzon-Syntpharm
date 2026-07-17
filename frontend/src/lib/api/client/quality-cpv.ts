// CPV API 调用

import {
  CpvProduct,
  CpvProductWithStats,
  CpvParameter,
  CpvBatch,
  CpvBatchWide,
  CpvStatistics,
  CpvTrendResponse,
  CpvImportTask,
  CpvProductListResponse,
  CpvBatchListResponse,
  CpvBatchWideListResponse,
  CpvImportTaskListResponse,
} from "@/types/quality-cpv"

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status} ${response.statusText}`)
  }
  const data = await response.json()
  return data.data
}

async function apiFetchPaginated<T>(url: string, options?: RequestInit): Promise<{ items: T[]; total: number; page: number; page_size: number }> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status} ${response.statusText}`)
  }
  const result = await response.json()
  return {
    items: result.data || [],
    total: result.meta?.total || 0,
    page: result.meta?.page || 1,
    page_size: result.meta?.page_size || 20,
  }
}

// 产品管理
export async function fetchCpvProducts(params?: {
  keyword?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<CpvProductListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.keyword) searchParams.set("keyword", params.keyword)
  if (params?.status) searchParams.set("status", params.status)
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  
  return apiFetchPaginated<CpvProductWithStats>(`/api/v1/quality/cpv/products?${searchParams}`)
}

export async function fetchCpvProduct(productId: string): Promise<CpvProduct> {
  return apiFetch<CpvProduct>(`/api/v1/quality/cpv/products/${productId}`)
}

// 参数管理
export async function fetchCpvParameters(productId: string, type?: "CPP" | "CQA"): Promise<CpvParameter[]> {
  const searchParams = new URLSearchParams()
  if (type) searchParams.set("type", type)
  
  return apiFetch<CpvParameter[]>(`/api/v1/quality/cpv/products/${productId}/parameters?${searchParams}`)
}

// 批次数据
export async function fetchCpvBatches(productId: string, params?: {
  data_type?: "CPP" | "CQA"
  batch_no?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}): Promise<CpvBatchListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.data_type) searchParams.set("data_type", params.data_type)
  if (params?.batch_no) searchParams.set("batch_no", params.batch_no)
  if (params?.start_date) searchParams.set("start_date", params.start_date)
  if (params?.end_date) searchParams.set("end_date", params.end_date)
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  
  return apiFetchPaginated<CpvBatch>(`/api/v1/quality/cpv/products/${productId}/batches?${searchParams}`)
}

export async function fetchCppBatchesWide(productId: string, params?: {
  batch_no?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}): Promise<CpvBatchWideListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.batch_no) searchParams.set("batch_no", params.batch_no)
  if (params?.start_date) searchParams.set("start_date", params.start_date)
  if (params?.end_date) searchParams.set("end_date", params.end_date)
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  
  return apiFetchPaginated<CpvBatchWide>(`/api/v1/quality/cpv/products/${productId}/cpp?${searchParams}`)
}

export async function fetchCqaBatchesWide(productId: string, params?: {
  batch_no?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}): Promise<CpvBatchWideListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.batch_no) searchParams.set("batch_no", params.batch_no)
  if (params?.start_date) searchParams.set("start_date", params.start_date)
  if (params?.end_date) searchParams.set("end_date", params.end_date)
  if (params?.page) searchParams.set("page", String(params.page))
  if (params?.page_size) searchParams.set("page_size", String(params.page_size))
  
  return apiFetchPaginated<CpvBatchWide>(`/api/v1/quality/cpv/products/${productId}/cqa?${searchParams}`)
}

// 统计分析
export async function fetchCpvStatistics(productId: string, parameterId: string, params?: {
  batch_no?: string
  start_date?: string
  end_date?: string
}): Promise<CpvStatistics> {
  const searchParams = new URLSearchParams()
  searchParams.set("parameter_id", parameterId)
  if (params?.batch_no) searchParams.set("batch_no", params.batch_no)
  if (params?.start_date) searchParams.set("start_date", params.start_date)
  if (params?.end_date) searchParams.set("end_date", params.end_date)
  
  return apiFetch<CpvStatistics>(`/api/v1/quality/cpv/products/${productId}/statistics?${searchParams}`)
}

export async function fetchCpvTrend(productId: string, parameterId: string, params?: {
  batch_no?: string
  start_date?: string
  end_date?: string
}): Promise<CpvTrendResponse> {
  const searchParams = new URLSearchParams()
  searchParams.set("parameter_id", parameterId)
  if (params?.batch_no) searchParams.set("batch_no", params.batch_no)
  if (params?.start_date) searchParams.set("start_date", params.start_date)
  if (params?.end_date) searchParams.set("end_date", params.end_date)
  
  return apiFetch<CpvTrendResponse>(`/api/v1/quality/cpv/products/${productId}/trend?${searchParams}`)
}

// 导入


export async function fetchCpvImportTasks(productId?: string, page?: number, page_size?: number): Promise<CpvImportTaskListResponse> {
  const searchParams = new URLSearchParams()
  if (productId) searchParams.set("product_id", productId)
  if (page) searchParams.set("page", String(page))
  if (page_size) searchParams.set("page_size", String(page_size))
  
  return apiFetchPaginated<CpvImportTask>(`/api/v1/quality/cpv/import/tasks?${searchParams}`)
}

export async function fetchCpvImportTask(taskId: string): Promise<CpvImportTask> {
  return apiFetch<CpvImportTask>(`/api/v1/quality/cpv/import/tasks/${taskId}`)
}
