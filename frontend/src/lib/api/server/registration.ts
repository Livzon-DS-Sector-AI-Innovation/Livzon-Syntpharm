import {apiFetch, apiFetchPaginated, getApiBaseUrl, unwrapResponse} from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'
import type { ApiResponse } from '@/types/common'
import type { PageResult } from '@/lib/api/page'
import type {
  AuthorizationLetterListItem,
  ParseCOAResponse,
  ProductInfo,
  ReferenceStandardListItem,
  RegistrationProject,
  SupplementaryReplyListItem,
} from '@/types/registration'

type DrugCreate = components['schemas']['DrugCreate']
type DrugUpdate = components['schemas']['DrugUpdate']

export async function generateAuthorizationLetter(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/authorization-letters/generate`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteAuthorizationLetter(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/authorization-letters/${id}`, {
    method: 'DELETE',
  })
}

export async function generateSupplementaryReply(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/supplementary-replies/generate`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteSupplementaryReply(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/supplementary-replies/${id}`, {
    method: 'DELETE',
  })
}

export async function generateReferenceStandard(formData: FormData) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/reference-standards/generate`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteReferenceStandard(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/reference-standards/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchAuthorizationLetters(
  params: { page: number; page_size: number },
): Promise<PageResult<AuthorizationLetterListItem>> {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetchPaginated<AuthorizationLetterListItem>(
    `${getApiBaseUrl()}/api/v1/registration/authorization-letters?${searchParams.toString()}`,
  )
}

export async function fetchRegistrationProducts(): Promise<ProductInfo[]> {
  const raw = await apiFetch<ApiResponse<ProductInfo[]>>(
    `${getApiBaseUrl()}/api/v1/registration/authorization-letters/products`,
  )
  return unwrapResponse(raw)
}

export async function fetchReferenceStandards(
  params: { page: number; page_size: number },
): Promise<PageResult<ReferenceStandardListItem>> {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetchPaginated<ReferenceStandardListItem>(
    `${getApiBaseUrl()}/api/v1/registration/reference-standards?${searchParams.toString()}`,
  )
}

export async function fetchSupplementaryReplies(
  params: { page: number; page_size: number },
): Promise<PageResult<SupplementaryReplyListItem>> {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetchPaginated<SupplementaryReplyListItem>(
    `${getApiBaseUrl()}/api/v1/registration/supplementary-replies?${searchParams.toString()}`,
  )
}

export async function createDrug(data: DrugCreate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/drugs/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDrug(id: string, data: DrugUpdate) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/drugs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDrug(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/drugs/${id}`, {
    method: 'DELETE',
  })
}

export async function parseCOA(file: File): Promise<ParseCOAResponse> {
  const formData = new FormData()
  formData.append('coa', file)
  // 后端 success_response(data=result) 包了一层信封，调用方要的是 data，不是整个信封
  const raw = await apiFetch<ApiResponse<ParseCOAResponse>>(
    `${getApiBaseUrl()}/api/v1/registration/reference-standards/parse-coa`,
    {
      method: 'POST',
      body: formData,
    },
  )
  return unwrapResponse(raw)
}

export async function fetchRegistrationProjects(): Promise<RegistrationProject[]> {
  // 该集合端点的规范路径带尾斜杠（后端 @router.get("/")）；浏览器直连会被 Next 的
  // trailingSlash 归一化 308 掉、再被后端 307 到 backend:8000 触发跨域，因此必须服务端取数。
  const raw = await apiFetch<ApiResponse<RegistrationProject[]>>(
    `${getApiBaseUrl()}/api/v1/registration/projects/`,
  )
  return unwrapResponse(raw)
}

export async function createRegistrationProject(data: components['schemas']['ProjectCreate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/projects/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateRegistrationProject(id: string, data: components['schemas']['ProjectUpdate']) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/projects/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteRegistrationProject(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/registration/projects/${id}`, {
    method: 'DELETE',
  })
}