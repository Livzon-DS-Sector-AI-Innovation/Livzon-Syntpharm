import { fetchApi } from '@/lib/api/client'
import type {
  WorkActivityHazardListApiResponse,
  WorkActivityHazardListParams,
} from '@/types/safety/risk-grading'

const API_BASE = '/api/v1'

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
