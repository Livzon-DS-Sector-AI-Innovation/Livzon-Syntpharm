import { apiFetch, getApiBaseUrl } from './base'

export async function createGiftRequisitionApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/gift-requisitions`, {
    method: 'POST', body: JSON.stringify(data), headers,
  })
}

export async function updateGiftRequisitionApi(id: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/gift-requisitions/${id}`, {
    method: 'PUT', body: JSON.stringify(data), headers,
  })
}

export async function deleteGiftRequisitionApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/gift-requisitions/${id}`, { method: 'DELETE', headers })
}

export async function createRegulationApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/regulations`, {
    method: 'POST', body: JSON.stringify(data), headers,
  })
}

export async function updateRegulationApi(id: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/regulations/${id}`, {
    method: 'PUT', body: JSON.stringify(data), headers,
  })
}

export async function deleteRegulationApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/regulations/${id}`, { method: 'DELETE', headers })
}

export async function extractRegulationTextApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/regulations/extract`, {
    method: 'POST', body: JSON.stringify(data), headers,
  })
}

export async function createGiftInventoryApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/gift-inventories`, {
    method: 'POST', body: JSON.stringify(data), headers,
  })
}

export async function updateGiftInventoryApi(id: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/gift-inventories/${id}`, {
    method: 'PUT', body: JSON.stringify(data), headers,
  })
}

export async function deleteGiftInventoryApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/gift-inventories/${id}`, { method: 'DELETE', headers })
}

export async function createVehicleApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/vehicles`, {
    method: 'POST', body: JSON.stringify(data), headers,
  })
}

export async function updateVehicleApi(id: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/vehicles/${id}`, {
    method: 'PUT', body: JSON.stringify(data), headers,
  })
}

export async function deleteVehicleApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/administration/vehicles/${id}`, { method: 'DELETE', headers })
}

export async function batchImportVehiclesApi(data: FormData) {
  const url = `${getApiBaseUrl()}/api/v1/administration/vehicles/batch-import`
  const res = await fetch(url, { method: 'POST', body: data })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`批量导入失败 (HTTP ${res.status}): ${text}`)
  }
  return res.json()
}
