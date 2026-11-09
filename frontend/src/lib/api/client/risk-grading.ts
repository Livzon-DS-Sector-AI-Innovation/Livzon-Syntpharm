import { fetchApi } from '@/lib/api/client'
import type { WorkActivityHazardListApiResponse } from '@/types/safety/risk-grading'

const API_BASE = '/api/v1'

export interface WorkActivityHazardListParams {
  page?: number
  page_size?: number
}

/** 浏览器侧读取作业活动危险源台账（含分页 meta）。 */
export async function fetchWorkActivityHazards(
  params?: WorkActivityHazardListParams,
): Promise<WorkActivityHazardListApiResponse> {
  const searchParams = new URLSearchParams()
  searchParams.set('page', String(params?.page ?? 1))
  searchParams.set('page_size', String(params?.page_size ?? 20))
  return fetchApi<WorkActivityHazardListApiResponse>(
    `${API_BASE}/safety/work-activity-hazards?${searchParams.toString()}`,
    { method: 'GET' },
  )
}
