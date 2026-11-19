'use client'

import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Progress, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

import { regeneratePageImages } from '@/actions/agent/ppt-video'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { fetchPageImagesStatus } from '@/lib/api/client/agent'
import { PERM } from '@/lib/permissions/codes'
import {
  pageImagesStageLabel,
  type PageImagesState,
  type ProjectDetail,
} from '@/types/agent/ppt-video'

const POLL_INTERVAL_MS = 2000
/** 终态：不再轮询；done 之后缩略图由回拉的详情带出来 */
const TERMINAL = new Set<PageImagesState['status']>(['done', 'failed'])

/** 后端字段有默认值，OpenAPI 里是可选的；老详情（升级前拉的）可能没有这一段 */
const IDLE_STATE: PageImagesState = { status: 'idle', progress: 0, done: 0, total: 0 }

interface Props {
  detail: ProjectDetail
}

/**
 * 左栏「页面」标题下方的页图生成进度。
 *
 * 只轮 `/page-images/status`（主键单行查询），终态时回拉一次整份详情：
 * 页图编好码后时间轴缩略图会自己冒出来，用户不用手动刷新。
 * 状态为空闲或已完成时不占位——生成中或失败时才出现。
 */
export default function PageImagesProgress({ detail }: Props) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [optimistic, setOptimistic] = useState<PageImagesState | null>(null)
  const [retrying, setRetrying] = useState(false)
  const notifiedRef = useRef<string | null>(null)
  const lastStatusRef = useRef<string | null>(null)

  /**
   * 轮询规则：
   * 1. 服务端详情还是「进行中」→ 以轮询结果为准；
   * 2. 服务端已是终态、但本地有更新的乐观态（刚点重试）→ 用乐观态，等后台认领后再切回来。
   */
  const { data: polled, refetch: refetchStatus } = useQuery({
    queryKey: ['ppt-video', detail.id, 'page-images'],
    queryFn: () => fetchPageImagesStatus(detail.id),
    initialData: detail.page_images ?? IDLE_STATE,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? POLL_INTERVAL_MS : false
    },
  })

  const serverState = detail.page_images ?? IDLE_STATE
  // 乐观态只在「轮询结果还不是这个 job」时生效；拿到同一个 job 后就交给服务端数据
  const state: PageImagesState =
    optimistic && polled?.job_id !== optimistic.job_id ? optimistic : (polled ?? serverState)
  const running = state.status === 'queued' || state.status === 'running'

  // 终态只提示一次：done 时回拉详情把页图 version 与缩略图带回来
  useEffect(() => {
    const previous = lastStatusRef.current
    lastStatusRef.current = state.status
    // 首次渲染就是终态（打开已完成的历史项目）不需要回拉与提示
    if (previous === null || !TERMINAL.has(state.status)) return
    const key = `${state.job_id ?? 'none'}:${state.status}`
    if (notifiedRef.current === key) return
    notifiedRef.current = key
    // 详情由工作台的 React Query 缓存持有：失效即重取，不在 effect 里自己 fetch + setState
    void queryClient.invalidateQueries({ queryKey: ['ppt-video', detail.id] }).then(() => {
      if (state.status === 'failed') message.error(state.error || '页面图生成失败')
    })
  }, [state, queryClient, detail.id, message])

  const handleRetry = async () => {
    setRetrying(true)
    const result = await regeneratePageImages(detail.id)
    setRetrying(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    // 提交后项目行还没被后台任务认领，先给个乐观态，轮询到 running 会自然覆盖
    setOptimistic({
      status: 'queued',
      progress: 0,
      done: 0,
      total: detail.slide_count,
      error: null,
      job_id: result.data?.job_id ?? null,
    })
    // 立刻拉一次：拿到 queued 才会让 refetchInterval 开始计时
    void refetchStatus()
  }

  if (!running && state.status !== 'failed') return null

  const stage = pageImagesStageLabel(state.progress)

  return (
    <div className="mb-2 rounded-lg border border-[#E5E3DF] bg-white px-2 py-2">
      <div className="flex items-center justify-between gap-2">
        {state.status === 'failed' ? (
          <Typography.Text type="danger" className="text-[12px]">
            页面图生成失败
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary" className="text-[12px]">
            {state.progress >= 100 ? stage : `${stage}中…`}
          </Typography.Text>
        )}
        {state.total > 0 && (
          <Typography.Text type="secondary" className="text-[12px]">
            已完成 {state.done} / 共 {state.total} 页
          </Typography.Text>
        )}
      </div>

      {state.status !== 'failed' && (
        <Progress
          percent={state.progress}
          status="active"
          strokeColor="#5645D4"
          size="small"
          className="!mb-0 !mt-1"
        />
      )}

      {state.status === 'failed' && (
        <div className="mt-1 flex items-start justify-between gap-2">
          <Typography.Text type="secondary" className="text-[12px]">
            {state.error || '未知原因'}
          </Typography.Text>
          <PermissionGate code={PERM.pptVideoManage}>
            <Button size="small" icon={<ReloadOutlined />} loading={retrying} onClick={handleRetry}>
              重试
            </Button>
          </PermissionGate>
        </div>
      )}
    </div>
  )
}