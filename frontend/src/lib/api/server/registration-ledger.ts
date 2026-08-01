import { apiFetch, apiFetchRaw, getApiBaseUrl } from '@/lib/api/server/base'

const API_BASE = `${getApiBaseUrl()}/api/v1/registration`

export async function createDomesticApproval(data: unknown) {
  return apiFetch(`${API_BASE}/domestic-approvals`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importDomesticApprovals(formData: FormData) {
  return apiFetch(`${API_BASE}/domestic-approvals/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createOverseasApproval(data: unknown) {
  return apiFetch(`${API_BASE}/overseas-approvals`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importOverseasApprovals(formData: FormData) {
  return apiFetch(`${API_BASE}/overseas-approvals/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createInternationalReview(data: unknown) {
  return apiFetch(`${API_BASE}/international-reviews`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importInternationalReviews(formData: FormData) {
  return apiFetch(`${API_BASE}/international-reviews/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createCoppCertificate(data: unknown) {
  return apiFetch(`${API_BASE}/copp-certificates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importCoppCertificates(formData: FormData) {
  return apiFetch(`${API_BASE}/copp-certificates/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createWcCertificate(data: unknown) {
  return apiFetch(`${API_BASE}/wc-certificates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importWcCertificates(formData: FormData) {
  return apiFetch(`${API_BASE}/wc-certificates/import`, {
    method: 'POST',
    body: formData,
  })
}