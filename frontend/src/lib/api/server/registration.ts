import { apiFetch, apiFetchRaw, API_BASE_URL } from '@/lib/api/server/base'
import type { AuthorizationLetterCreateInput } from '@/types/registration'
import type { components } from '@/types/generated/schema'

type DrugCreate = components['schemas']['DrugCreate']
type DrugUpdate = components['schemas']['DrugUpdate']

export async function generateAuthorizationLetter(formData: FormData) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/authorization-letters/generate`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteAuthorizationLetter(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/authorization-letters/${id}`, {
    method: 'DELETE',
  })
}

export async function generateSupplementaryReply(formData: FormData) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/supplementary-replies/generate`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteSupplementaryReply(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/supplementary-replies/${id}`, {
    method: 'DELETE',
  })
}

export async function generateReferenceStandard(formData: FormData) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/reference-standards/generate`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteReferenceStandard(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/reference-standards/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchAuthorizationLetters(params: { page: number; page_size: number }) {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetch(`${API_BASE_URL}/api/v1/registration/authorization-letters?${searchParams.toString()}`)
}

export async function fetchRegistrationProducts() {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/authorization-letters/products`)
}

export async function fetchReferenceStandards(params: { page: number; page_size: number }) {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetch(`${API_BASE_URL}/api/v1/registration/reference-standards?${searchParams.toString()}`)
}

export async function fetchSupplementaryReplies(params: { page: number; page_size: number }) {
  const searchParams = new URLSearchParams({
    page: params.page.toString(),
    page_size: params.page_size.toString(),
  })
  return apiFetch(`${API_BASE_URL}/api/v1/registration/supplementary-replies?${searchParams.toString()}`)
}

export async function createDrug(data: DrugCreate) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/drugs/`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateDrug(id: string, data: DrugUpdate) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/drugs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteDrug(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/drugs/${id}`, {
    method: 'DELETE',
  })
}

export async function parseCOA(file: File) {
  const formData = new FormData()
  formData.append('coa', file)
  return apiFetch(`${API_BASE_URL}/api/v1/registration/reference-standards/parse-coa`, {
    method: 'POST',
    body: formData,
  })
}

export async function deleteRegistrationProject(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/registration/projects/${id}`, {
    method: 'DELETE',
  })
}