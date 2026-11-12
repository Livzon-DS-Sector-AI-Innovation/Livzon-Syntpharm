import type { OrgSyncStatusData } from '@/types/hr'

/** Shape used when the status endpoint itself is unavailable. */
export function unavailableOrgSyncStatus(message = '同步状态暂时不可用'): OrgSyncStatusData {
  return {
    status: 'failed',
    last_synced_at: null,
    department_count: 0,
    people_count: 0,
    error_message: message,
  }
}
