import { apiFetch, apiFetchRaw, getApiBaseUrl } from '@/lib/api/server/base'

function base(): string { return `${getApiBaseUrl()}/api/v1/registration` }

export async function createDomesticApproval(data: unknown) {
  return apiFetch(`${base()}/domestic-approvals`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importDomesticApprovals(formData: FormData) {
  return apiFetch(`${base()}/domestic-approvals/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createOverseasApproval(data: unknown) {
  return apiFetch(`${base()}/overseas-approvals`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importOverseasApprovals(formData: FormData) {
  return apiFetch(`${base()}/overseas-approvals/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createInternationalReview(data: unknown) {
  return apiFetch(`${base()}/international-reviews`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importInternationalReviews(formData: FormData) {
  return apiFetch(`${base()}/international-reviews/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createCoppCertificate(data: unknown) {
  return apiFetch(`${base()}/copp-certificates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importCoppCertificates(formData: FormData) {
  return apiFetch(`${base()}/copp-certificates/import`, {
    method: 'POST',
    body: formData,
  })
}

export async function createWcCertificate(data: unknown) {
  return apiFetch(`${base()}/wc-certificates`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function importWcCertificates(formData: FormData) {
  return apiFetch(`${base()}/wc-certificates/import`, {
    method: 'POST',
    body: formData,
  })
}