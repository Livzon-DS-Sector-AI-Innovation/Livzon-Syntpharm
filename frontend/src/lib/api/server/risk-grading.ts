import { apiFetchData, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

type WorkActivityHazardCreate = components['schemas']['WorkActivityHazardCreate']
type WorkActivityHazard = components['schemas']['WorkActivityHazardResponse']

export async function createWorkActivityHazard(data: WorkActivityHazardCreate): Promise<WorkActivityHazard> {
  return apiFetchData<WorkActivityHazard>(`${getApiBaseUrl()}/api/v1/safety/work-activity-hazards`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
