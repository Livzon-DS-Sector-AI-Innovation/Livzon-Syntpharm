import { fetchApi } from '@/lib/api/client'
import type {
  EquipmentFacilityHazardListApiResponse,
  EquipmentFacilityHazardListParams,
  RiskGradingOptions,
  RiskGradingOptionsApiResponse,
  WorkActivityHazardListApiResponse,
  WorkActivityHazardListParams,
} from '@/types/safety/risk-grading'

const API_BASE = '/api/v1'

/** 读取后端权威的风险分级选项、矩阵与阈值（只读）。 */
export async function fetchRiskGradingOptions(): Promise<RiskGradingOptions> {
  const response = await fetchApi<RiskGradingOptionsApiResponse>(
    `${API_BASE}/safety/enums/risk-grading`,
    { method: 'GET' },
  )
  return response.data
}

/** 浏览器侧读取作业活动危险源台账（支持分页、筛选与关键字）。 */
export async function fetchWorkActivityHazards(
  params?: WorkActivityHazardListParams,
): Promise<WorkActivityHazardListApiResponse> {
  const searchParams = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  if (!searchParams.has('page')) searchParams.set('page', '1')
  if (!searchParams.has('page_size')) searchParams.set('page_size', '20')
  return fetchApi<WorkActivityHazardListApiResponse>(
    `${API_BASE}/safety/work-activity-hazards?${searchParams.toString()}`,
    { method: 'GET' },
  )
}

/** 浏览器侧读取设备设施危险源台账（分页）。 */
export async function fetchEquipmentFacilityHazards(
  params?: EquipmentFacilityHazardListParams,
): Promise<EquipmentFacilityHazardListApiResponse> {
  const searchParams = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value) !== '') {
      searchParams.set(key, String(value))
    }
  })
  if (!searchParams.has('page')) searchParams.set('page', '1')
  if (!searchParams.has('page_size')) searchParams.set('page_size', '20')
  return fetchApi<EquipmentFacilityHazardListApiResponse>(
    `${API_BASE}/safety/equipment-facility-hazards?${searchParams.toString()}`,
    { method: 'GET' },
  )
}
