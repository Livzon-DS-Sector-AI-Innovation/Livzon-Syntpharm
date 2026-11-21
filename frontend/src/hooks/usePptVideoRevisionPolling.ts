'use client'

import { useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'

import { loadScriptRevisions } from '@/actions/agent/ppt-video'
import { fetchPptVideoDetail } from '@/lib/api/client/agent'
import type { ProjectDetail, RevisionItem } from '@/types/agent/ppt-video'

/** 修订记录的终态：只有这两种才需要收尾 */
const TERMINAL = new Set(['succeeded', 'failed'])

const POLL_INTERVAL_MS = 2500

/**
 * 轮询一次讲稿改写任务。
 *
 * 改写统一走后台任务（接口 202 + revision_id），前端拿 revision_id 轮修订记录：
 * 终态时回拉一次详情交给调用方，避免各组件各写一套 setTimeout。
 *
 * @param revisionId 提交接口返回的修订 id；null 表示当前没有任务
 * @param onFinished 终态回调（详情可能为 null：回拉失败时也要让调用方收尾）
 */
export function usePptVideoRevisionPolling(
  projectId: string,
  revisionId: string | null,
  onFinished: (detail: ProjectDetail | null, revision: RevisionItem) => void,
): void {
  const finishedRef = useRef<string | null>(null)
  const callbackRef = useRef(onFinished)
  // ref 只在渲染后同步，避免渲染期写 ref；回调真正被调用时已是终态，取到的是最新值
  useEffect(() => {
    callbackRef.current = onFinished
  })

  const { data } = useQuery({
    queryKey: ['ppt-video', projectId, 'revision', revisionId],
    enabled: Boolean(revisionId),
    queryFn: async (): Promise<RevisionItem | null> => {
      const result = await loadScriptRevisions(projectId, 10)
      if (!result.success || !result.data) {
        throw new Error(result.message || '读取修订记录失败')
      }
      return result.data.find((item) => item.id === revisionId) ?? null
    },
    refetchInterval: (query) => {
      const revision = query.state.data
      if (revision && TERMINAL.has(revision.status)) return false
      return POLL_INTERVAL_MS
    },
  })

  useEffect(() => {
    if (!revisionId || !data || !TERMINAL.has(data.status)) return
    if (finishedRef.current === revisionId) return
    finishedRef.current = revisionId
    void fetchPptVideoDetail(projectId)
      .then((detail) => callbackRef.current(detail, data))
      .catch(() => callbackRef.current(null, data))
  }, [projectId, revisionId, data])
}