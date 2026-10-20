'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api/client'
import { fetchSyncJobClient } from '@/lib/api/client/energy'
import type { SyncJobResult } from '@/types/energy'

const POLL_INTERVAL_MS = 1500
const POLL_TIMEOUT_MS = 180_000

export type SyncJobPhase = 'idle' | 'running' | 'done' | 'failed' | 'timeout' | 'unavailable'

/**
 * 轮询 `/api/v1/energy/jobs/{job_id}`。
 *
 * `unavailable` 是必需的兜底态：任务状态存在后端**进程内**（`D-11`），重启即丢、多副本互不可见，
 * 所以 404 只代表「查不到状态」，不能当成「任务失败」——数据可能已经写进去了。
 */
export function useEnergySyncJob(jobId: string | null, startedAt: number | null) {
  const query = useQuery({
    queryKey: ['energy-sync-job', jobId],
    queryFn: () => fetchSyncJobClient(jobId as string),
    enabled: Boolean(jobId),
    retry: 1,
    refetchInterval: (state) => {
      if (state.state.data && state.state.data.status !== 'running') return false
      if (isNotFound(state.state.error)) return false
      if (startedAt !== null && Date.now() - startedAt > POLL_TIMEOUT_MS) return false
      return POLL_INTERVAL_MS
    },
  })

  const phase = useMemo<SyncJobPhase>(() => {
    if (!jobId) return 'idle'
    const status = query.data?.status
    if (status === 'done') return 'done'
    if (status === 'failed') return 'failed'
    if (isNotFound(query.error)) return 'unavailable'
    if (startedAt !== null && Date.now() - startedAt > POLL_TIMEOUT_MS) return 'timeout'
    return 'running'
  }, [jobId, query.data?.status, query.error, startedAt])

  return {
    phase,
    error: query.error,
    errorMessage: query.data?.error ?? null,
    result: (query.data?.result ?? null) as SyncJobResult | null,
  }
}

function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}
