'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { App, Button, Progress, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

import { regeneratePageImages } from '@/actions/agent/ppt-video'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { fetchPageImagesStatus, fetchPptVideoDetail } from '@/lib/api/client/agent'
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
  onDetailChange: (detail: ProjectDetail) => void
}

/**
 * 左栏「页面」标题下方的页图生成进度。
 *
 * 只轮 `/page-images/status`（主键单行查询），终态时回拉一次整份详情：
 * 页图编好码后时间轴缩略图会自己冒出来，用户不用手动刷新。
 * 状态为空闲或已完成时不占位——生成中或失败时才出现。
 */
export default function PageImagesProgress({ detail, onDetailChange }: Props) {
  const { message } = App.useApp()
  const [polled, setPolled] = useState<PageImagesState | null>(null)
  const [retrying, setRetrying] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 轮询快照的选择规则（不写 setState-in-effect，避免级联渲染）：
  // 1. 本地快照是「进行中」→ 一律用它：重试后服务端详情还停在上一次失败的终态上，
  //    若按 job_id 比对会判成「不是同一个任务」而退回失败态，轮询当场停止；
  // 2. 本地快照是终态 → 只在它与服务端属于同一任务时才用，避免服务端已换新任务
  //    （换源、重新投递）却把旧的失败结论继续显示出来。
  const serverState = detail.page_images ?? IDLE_STATE
  const polledInFlight = polled?.status === 'queued' || polled?.status === 'running'
  const state = polled && (polledInFlight || (polled.job_id && polled.job_id === serverState.job_id))
    ? polled
    : serverState
  const running = state.status === 'queued' || state.status === 'running'

  const refreshDetail = useCallback(async () => {
    const fresh = await fetchPptVideoDetail(detail.id)
    onDetailChange(fresh)
  }, [detail.id, onDetailChange])

  useEffect(() => {
    if (!running) return
    let cancelled = false

    const tick = async () => {
      try {
        const next = await fetchPageImagesStatus(detail.id)
        if (cancelled) return
        setPolled(next)
        if (TERMINAL.has(next.status)) {
          // 终态回填一次详情：页图 version / 缩略图 url 都在详情里
          await refreshDetail()
          if (next.status === 'failed') message.error(next.error || '页图生成失败')
          return
        }
      } catch (error) {
        console.warn('轮询页图进度失败:', error)
      }
      if (!cancelled) timer.current = setTimeout(tick, POLL_INTERVAL_MS)
    }

    timer.current = setTimeout(tick, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      if (timer.current) clearTimeout(timer.current)
    }
  }, [running, detail.id, refreshDetail, message])

  const handleRetry = async () => {
    setRetrying(true)
    const result = await regeneratePageImages(detail.id)
    setRetrying(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    // 提交后项目行还没被后台任务认领，先给个乐观态，轮询到 running 会自然覆盖
    setPolled({
      status: 'queued',
      progress: 0,
      done: 0,
      total: detail.slide_count,
      error: null,
      job_id: result.data?.job_id ?? null,
    })
  }

  if (!running && state.status !== 'failed') return null

  const stage = pageImagesStageLabel(state.progress)

  return (
    <div className="mb-2 rounded-lg border border-[#E5E3DF] bg-white px-2 py-2">
      <div className="flex items-center justify-between gap-2">
        {state.status === 'failed' ? (
          <Typography.Text type="danger" className="text-[12px]">
            页图生成失败
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