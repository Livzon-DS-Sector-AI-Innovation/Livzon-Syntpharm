import type {
  EnergyDeviceConfig,
  EnergyData,
  CollectLog,
  AlertRule,
  AlertRecord,
  EnergyWorkshop,
  EnergyMonthlyRecord,
  EnergyOverviewData,
  FeishuImportResult,
  CreateDeviceInput,
  UpdateDeviceInput,
  CreateRuleInput,
  UpdateRuleInput,
  ProcessRecordInput,
} from '@/types/energy'
import { apiFetchRaw, getApiBaseUrl, apiFetch as baseApiFetch } from './base'

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  const result = await baseApiFetch<T>(url, options)
  return ((result as Record<string, unknown>).data ?? result) as T
}

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy`)
}

// ── 设备配置 ──

export async function fetchEnergyDevices(params?: Record<string, unknown>): Promise<{ items: EnergyDeviceConfig[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value))
      }
    })
  }
  const query = searchParams.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/devices${query ? `?${query}` : ''}`)
}

export async function fetchEnergyDeviceById(id: string): Promise<EnergyDeviceConfig> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/devices/${id}`)
}

// ── 能耗数据 ──

export async function fetchEnergyData(params: Record<string, unknown>): Promise<{ items: EnergyDeviceConfig[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/data?${searchParams.toString()}`)
}

export async function fetchEnergyOverview(params: Record<string, unknown>): Promise<EnergyOverviewData> {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/overview?${searchParams.toString()}`)
}

// ── 采集管理 ──

export async function fetchCollectLogs(params?: Record<string, unknown>): Promise<{ items: CollectLog[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value))
      }
    })
  }
  const query = searchParams.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/collect/logs${query ? `?${query}` : ''}`)
}

// ── 预警规则 ──

export async function fetchAlertRules(params?: Record<string, unknown>): Promise<{ items: AlertRule[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value))
      }
    })
  }
  const query = searchParams.toString()
  const res = await apiFetchRaw(`/api/v1/energy/alerts/rules${query ? `?${query}` : ''}`)
  const json = await res.json()
  return {
    items: json.data || [],
    total: json.meta?.total || 0,
    page: json.meta?.page || 1,
    page_size: json.meta?.page_size || 20,
  }
}

export async function fetchAlertRuleById(id: string): Promise<AlertRule> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/rules/${id}`)
}

// ── 预警记录 ──

export async function fetchAlertRecords(params?: Record<string, unknown>): Promise<{ items: EnergyDeviceConfig[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value))
      }
    })
  }
  const query = searchParams.toString()
  const res = await apiFetchRaw(`/api/v1/energy/alerts/records${query ? `?${query}` : ''}`)
  const json = await res.json()
  return {
    items: json.data || [],
    total: json.meta?.total || 0,
    page: json.meta?.page || 1,
    page_size: json.meta?.page_size || 20,
  }
}

// ── 设备写操作 ──

export async function createEnergyDevice(data: CreateDeviceInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/devices`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEnergyDevice(id: string, data: UpdateDeviceInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/devices/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEnergyDevice(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/devices/${id}`, {
    method: 'DELETE',
  })
}

// ── 采集写操作 ──

export async function triggerCollect(platformCode?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/collect/trigger`, {
    method: 'POST',
    body: JSON.stringify({ platform_code: platformCode || 'all' }),
  })
}

// ── 预警规则写操作 ──

export async function createAlertRule(data: CreateRuleInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/rules`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateAlertRule(id: string, data: UpdateRuleInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/rules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteAlertRule(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/rules/${id}`, {
    method: 'DELETE',
  })
}

// ── 预警记录写操作 ──

export async function processAlertRecord(id: string, data: ProcessRecordInput) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/records/${id}/process`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

// ─── Workshop ───

export async function fetchWorkshops(params?: Record<string, unknown>): Promise<{ items: EnergyWorkshop[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) searchParams.set(k, String(v))
    })
  }
  const qs = searchParams.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/workshops${qs ? `?${qs}` : ''}`)
}

export async function fetchWorkshopById(id: string): Promise<EnergyWorkshop> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/workshops/${id}`)
}

export async function createWorkshop(data: Record<string, unknown>): Promise<EnergyWorkshop> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/workshops`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateWorkshop(id: string, data: Record<string, unknown>): Promise<EnergyWorkshop> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/workshops/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteWorkshop(id: string): Promise<void> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/workshops/${id}`, {
    method: 'DELETE',
  })
}

// ─── Monthly Records ───

export async function fetchMonthlyRecords(params?: Record<string, unknown>): Promise<{ items: EnergyMonthlyRecord[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) searchParams.set(k, String(v))
    })
  }
  const qs = searchParams.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/monthly${qs ? '?' + qs : ''}`)
}

export async function fetchMonthlyRecordById(id: string): Promise<EnergyMonthlyRecord> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/monthly/${id}`)
}

export async function createMonthlyRecord(data: Record<string, unknown>): Promise<EnergyMonthlyRecord> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/monthly`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteMonthlyRecord(id: string): Promise<void> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/monthly/${id}`, {
    method: 'DELETE',
  })
}

// ─── Feishu Import ───

export async function importFromFeishu(data: Record<string, unknown>): Promise<FeishuImportResult> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/import/feishu`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function crossImportFromBitable(data: Record<string, unknown>): Promise<{ status: string; year?: number; months_imported?: number; total_created?: number; total_updated?: number; total_errors?: number }> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/sync/bitable/cross-import`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function syncBitableDailyData(): Promise<{ total_created: number; total_updated: number; auto_check_alerts: number }> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/sync/bitable/daily-import`, {
    method: 'POST',
  })
}

// ─── Alerts ───

export async function checkAlerts(checkDate: string): Promise<{ alerts: AlertRecord[]; count: number }> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/check`, {
    method: 'POST',
    body: JSON.stringify({ check_date: checkDate }),
  })
}

export async function fetchAlertDates(): Promise<string[]> {
  return apiFetch(`${getApiBaseUrl()}/api/v1/energy/alerts/dates`)
}

