'use client'

import { fetchSyncJobClient } from '@/lib/api/client/energy'
import type { SyncJobResult } from '@/types/energy'
import { usePollingJob } from './usePollingJob'
import type { JobPhase, JobState } from './usePollingJob'

export type SyncJobPhase = JobPhase

/** 轮询 `/api/v1/energy/jobs/{job_id}`（通用 `usePollingJob` 的 energy 封装）。 */
export function useEnergySyncJob(jobId: string | null, startedAt: number | null) {
  const { phase, error, errorMessage, result } = usePollingJob<SyncJobResult>({
    jobId,
    startedAt,
    queryKey: ['energy-sync-job', jobId],
    fetchJob: (id) => fetchSyncJobClient(id) as Promise<JobState<SyncJobResult>>,
  })

  return {
    phase,
    error,
    errorMessage,
    result,
  }
}
