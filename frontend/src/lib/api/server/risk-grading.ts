import { apiFetchData, apiFetchRaw, buildQueryString, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'
import type {
  EquipmentFacilityHazardExportParams,
  WorkActivityHazardExportParams,
} from '@/types/safety/risk-grading'

type WorkActivityHazardCreate = components['schemas']['WorkActivityHazardCreate']
type WorkActivityHazard = components['schemas']['WorkActivityHazardResponse']

const HAZARDS_PATH = '/api/v1/safety/work-activity-hazards'

export async function createWorkActivityHazard(data: WorkActivityHazardCreate): Promise<WorkActivityHazard> {
  return apiFetchData<WorkActivityHazard>(`${getApiBaseUrl()}${HAZARDS_PATH}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateWorkActivityHazard(
  id: string,
  data: WorkActivityHazardCreate,
): Promise<WorkActivityHazard> {
  return apiFetchData<WorkActivityHazard>(`${getApiBaseUrl()}${HAZARDS_PATH}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteWorkActivityHazard(id: string): Promise<null> {
  return apiFetchData<null>(`${getApiBaseUrl()}${HAZARDS_PATH}/${id}`, { method: 'DELETE' })
}

export async function exportWorkActivityHazards(
  params?: WorkActivityHazardExportParams,
): Promise<{ blob: Blob; filename: string }> {
  const query = buildQueryString((params ?? {}) as Record<string, unknown>)
  const response = await apiFetchRaw(`${getApiBaseUrl()}${HAZARDS_PATH}/export${query}`, { method: 'GET' })

  const disposition = response.headers.get('Content-Disposition') ?? ''
  const encodedMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  let filename = `作业活动危险源台账_${new Date().toISOString().slice(0, 10)}.xlsx`
  if (encodedMatch?.[1]) {
    filename = decodeURIComponent(encodedMatch[1])
  }

  return { blob: await response.blob(), filename }
}

type EquipmentFacilityHazardCreate = components['schemas']['EquipmentFacilityHazardCreate']
type EquipmentFacilityHazard = components['schemas']['EquipmentFacilityHazardResponse']

const EQUIPMENT_HAZARDS_PATH = '/api/v1/safety/equipment-facility-hazards'

export async function createEquipmentFacilityHazard(
  data: EquipmentFacilityHazardCreate,
): Promise<EquipmentFacilityHazard> {
  return apiFetchData<EquipmentFacilityHazard>(`${getApiBaseUrl()}${EQUIPMENT_HAZARDS_PATH}`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateEquipmentFacilityHazard(
  id: string,
  data: EquipmentFacilityHazardCreate,
): Promise<EquipmentFacilityHazard> {
  return apiFetchData<EquipmentFacilityHazard>(`${getApiBaseUrl()}${EQUIPMENT_HAZARDS_PATH}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteEquipmentFacilityHazard(id: string): Promise<null> {
  return apiFetchData<null>(`${getApiBaseUrl()}${EQUIPMENT_HAZARDS_PATH}/${id}`, { method: 'DELETE' })
}

export async function exportEquipmentFacilityHazards(
  params?: EquipmentFacilityHazardExportParams,
): Promise<{ blob: Blob; filename: string }> {
  const query = buildQueryString((params ?? {}) as Record<string, unknown>)
  const response = await apiFetchRaw(`${getApiBaseUrl()}${EQUIPMENT_HAZARDS_PATH}/export${query}`, {
    method: 'GET',
  })

  const disposition = response.headers.get('Content-Disposition') ?? ''
  const encodedMatch = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  let filename = `设备设施危险源台账_${new Date().toISOString().slice(0, 10)}.xlsx`
  if (encodedMatch?.[1]) {
    filename = decodeURIComponent(encodedMatch[1])
  }

  return { blob: await response.blob(), filename }
}
