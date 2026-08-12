import type {
  CreateDeviceInput,
  UpdateDeviceInput,
  CreateRuleInput,
  UpdateRuleInput,
  ProcessRecordInput,
} from '@/types/energy'
import { apiFetch, apiFetchPaginated, unwrapResponse } from './base'

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return unwrapResponse(await apiFetch<{ code: number; data: { code: string; name: string; description: string }; message?: string; meta?: unknown }>('/api/v1/energy'))
}

export async function fetchEnergyDevices(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        qs.set(key, String(value))
      }
    })
  }
  return apiFetchPaginated(`/api/v1/energy/devices${qs.size ? `?${qs}` : ''}`)
}

export async function fetchEnergyDeviceById(id: string): Promise<any> {
  return unwrapResponse(await apiFetch(`/api/v1/energy/devices/${id}`))
}

export async function fetchEnergyData(params: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      qs.set(key, String(value))
    }
  })
  return apiFetchPaginated(`/api/v1/energy/data?${qs}`)
}

export async function fetchEnergyOverview(params: any): Promise<any> {
  const qs = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      qs.set(key, String(value))
    }
  })
  return unwrapResponse(await apiFetch(`/api/v1/energy/overview?${qs}`))
}

export async function fetchCollectLogs(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        qs.set(key, String(value))
      }
    })
  }
  return apiFetchPaginated(`/api/v1/energy/collect/logs${qs.size ? `?${qs}` : ''}`)
}

export async function fetchAlertRules(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        qs.set(key, String(value))
      }
    })
  }
  return apiFetchPaginated(`/api/v1/energy/alerts/rules${qs.size ? `?${qs}` : ''}`)
}

export async function fetchAlertRuleById(id: string): Promise<any> {
  return unwrapResponse(await apiFetch(`/api/v1/energy/alerts/rules/${id}`))
}

export async function fetchAlertRecords(params?: any): Promise<{ items: any[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        qs.set(key, String(value))
      }
    })
  }
  return apiFetchPaginated(`/api/v1/energy/alerts/records${qs.size ? `?${qs}` : ''}`)
}

export async function createEnergyDevice(data: CreateDeviceInput) {
  return apiFetch('/api/v1/energy/devices', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEnergyDevice(id: string, data: UpdateDeviceInput) {
  return apiFetch(`/api/v1/energy/devices/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEnergyDevice(id: string) {
  return apiFetch(`/api/v1/energy/devices/${id}`, {
    method: 'DELETE',
  })
}

export async function triggerCollect(platformCode?: string) {
  return apiFetch('/api/v1/energy/collect/trigger', {
    method: 'POST',
    body: JSON.stringify({ platform_code: platformCode || 'all' }),
  })
}

export async function createAlertRule(data: CreateRuleInput) {
  return apiFetch('/api/v1/energy/alerts/rules', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAlertRule(id: string, data: UpdateRuleInput) {
  return apiFetch(`/api/v1/energy/alerts/rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAlertRule(id: string) {
  return apiFetch(`/api/v1/energy/alerts/rules/${id}`, {
    method: 'DELETE',
  })
}

export async function processAlertRecord(id: string, data: ProcessRecordInput) {
  return apiFetch(`/api/v1/energy/alerts/records/${id}/process`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function fetchWorkshops(params?: Record<string, unknown>): Promise<any> {
  const qs = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) qs.set(k, String(v))
    })
  }
  return unwrapResponse(await apiFetch(`/api/v1/energy/workshops${qs.size ? `?${qs}` : ''}`))
}

export async function fetchWorkshopById(id: string): Promise<any> {
  return unwrapResponse(await apiFetch(`/api/v1/energy/workshops/${id}`))
}

export async function createWorkshop(data: Record<string, unknown>): Promise<any> {
  return apiFetch('/api/v1/energy/workshops', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateWorkshop(id: string, data: Record<string, unknown>): Promise<any> {
  return apiFetch(`/api/v1/energy/workshops/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteWorkshop(id: string): Promise<any> {
  return apiFetch(`/api/v1/energy/workshops/${id}`, {
    method: 'DELETE',
  })
}

export async function fetchMonthlyRecords(params?: Record<string, unknown>): Promise<any> {
  const qs = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) qs.set(k, String(v))
    })
  }
  return unwrapResponse(await apiFetch(`/api/v1/energy/monthly${qs.size ? `?${qs}` : ''}`))
}

export async function fetchMonthlyRecordById(id: string): Promise<any> {
  return unwrapResponse(await apiFetch(`/api/v1/energy/monthly/${id}`))
}

export async function createMonthlyRecord(data: Record<string, unknown>): Promise<any> {
  return apiFetch('/api/v1/energy/monthly', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteMonthlyRecord(id: string): Promise<any> {
  return apiFetch(`/api/v1/energy/monthly/${id}`, {
    method: 'DELETE',
  })
}

export async function importFromFeishu(data: Record<string, unknown>): Promise<any> {
  return apiFetch('/api/v1/energy/import/feishu', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function crossImportFromBitable(data: Record<string, unknown>): Promise<any> {
  return apiFetch('/api/v1/energy/sync/bitable/cross-import', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function syncBitableDailyData(): Promise<any> {
  return apiFetch('/api/v1/energy/sync/bitable/daily-import', {
    method: 'POST',
  })
}

export async function checkAlerts(checkDate: string): Promise<any> {
  return apiFetch('/api/v1/energy/alerts/check', {
    method: 'POST',
    body: JSON.stringify({ check_date: checkDate }),
  })
}

export async function fetchAlertDates(): Promise<any> {
  return unwrapResponse(await apiFetch('/api/v1/energy/alerts/dates'))
}

export async function syncMonthlyFromBitableApi(): Promise<any> {
  return apiFetch('/api/v1/energy/sync/monthly', {
    method: 'POST',
  })
}

export async function getJobStatus(jobId: string): Promise<any> {
  return unwrapResponse(await apiFetch(`/api/v1/energy/jobs/${jobId}`))
}