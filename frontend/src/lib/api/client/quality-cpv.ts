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
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

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
  return apiGet<CpvProduct>(`/api/v1/quality/cpv/products/${productId}`)
}

export async function fetchCpvParameters(productId: string, type?: "CPP" | "CQA"): Promise<CpvParameter[]> {
  const searchParams = new URLSearchParams()
  if (type) searchParams.set("type", type)
  
  return apiGet<CpvParameter[]>(`/api/v1/quality/cpv/products/${productId}/parameters?${searchParams}`)
}

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
  
  return apiGet<CpvStatistics>(`/api/v1/quality/cpv/products/${productId}/statistics?${searchParams}`)
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
  
  return apiGet<CpvTrendResponse>(`/api/v1/quality/cpv/products/${productId}/trend?${searchParams}`)
}

export async function fetchCpvImportTasks(productId?: string, page?: number, page_size?: number): Promise<CpvImportTaskListResponse> {
  const searchParams = new URLSearchParams()
  if (productId) searchParams.set("product_id", productId)
  if (page) searchParams.set("page", String(page))
  if (page_size) searchParams.set("page_size", String(page_size))
  
  return apiFetchPaginated<CpvImportTask>(`/api/v1/quality/cpv/import/tasks?${searchParams}`)
}

export async function fetchCpvImportTask(taskId: string): Promise<CpvImportTask> {
  return apiGet<CpvImportTask>(`/api/v1/quality/cpv/import/tasks/${taskId}`)
}
