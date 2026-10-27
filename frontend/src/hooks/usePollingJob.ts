'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError } from '@/lib/api/client'

const DEFAULT_POLL_INTERVAL_MS = 1500
const DEFAULT_POLL_TIMEOUT_MS = 180_000

export type JobPhase = 'idle' | 'running' | 'done' | 'failed' | 'timeout' | 'unavailable'

export interface JobState<T = unknown> {
  job_id: string
  status: 'running' | 'done' | 'failed'
  result: T | null
  error: string | null
}

interface UsePollingJobOptions<T> {
  /** 任务 ID，null 表示未提交 */
  jobId: string | null
  /** 提交时间戳（Date.now()），用于超时判断；未提交传 null */
  startedAt: number | null
  /** React Query key（必须含 jobId） */
  queryKey: unknown[]
  /** 拉取任务状态的请求函数 */
  fetchJob: (jobId: string) => Promise<JobState<T>>
  pollIntervalMs?: number
  timeoutMs?: number
}

/**
 * 通用「提交任务 + 轮询状态」hook（后端 `app/core/job_store.py` 模式配套）。
 *
 * `unavailable` 是必需的兜底态：任务状态存在后端**进程内**（`D-11`），重启即丢、
 * 多副本互不可见，所以 404 只代表「查不到状态」，不能当成「任务失败」。
 */
export function usePollingJob<T = unknown>({
  jobId,
  startedAt,
  queryKey,
  fetchJob,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  timeoutMs = DEFAULT_POLL_TIMEOUT_MS,
}: UsePollingJobOptions<T>) {
  const query = useQuery({
    queryKey,
    queryFn: () => fetchJob(jobId as string),
    enabled: Boolean(jobId),
    retry: 1,
    refetchInterval: (state) => {
      if (state.state.data && state.state.data.status !== 'running') return false
      if (isNotFound(state.state.error)) return false
      if (startedAt !== null && Date.now() - startedAt > timeoutMs) return false
      return pollIntervalMs
    },
  })

  const phase = useMemo<JobPhase>(() => {
    if (!jobId) return 'idle'
    const status = query.data?.status
    if (status === 'done') return 'done'
    if (status === 'failed') return 'failed'
    if (isNotFound(query.error)) return 'unavailable'
    if (startedAt !== null && Date.now() - startedAt > timeoutMs) return 'timeout'
    return 'running'
  }, [jobId, query.data?.status, query.error, startedAt, timeoutMs])

  return {
    phase,
    error: query.error,
    errorMessage: query.data?.error ?? null,
    result: (query.data?.result ?? null) as T | null,
  }
}

export function isJobNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404
}

function isNotFound(error: unknown): boolean {
  return isJobNotFound(error)
}
