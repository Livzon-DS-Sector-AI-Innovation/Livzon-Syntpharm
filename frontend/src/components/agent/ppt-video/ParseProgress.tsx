'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { App, Button, Progress, Typography } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'

import { requestParse } from '@/actions/agent/ppt-video'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { fetchPptVideoDetail, fetchPptVideoParseState } from '@/lib/api/client/agent'
import { PERM } from '@/lib/permissions/codes'
import type { ParseState, ProjectDetail } from '@/types/agent/ppt-video'

const POLL_INTERVAL_MS = 2000
/** 终态：不再轮询；succeeded 之后回拉整份详情把逐页记录带出来 */
const TERMINAL = new Set<ParseState['status']>(['succeeded', 'failed', 'none'])

/** 后端字段有默认值，OpenAPI 里是可选的；升级前拉的详情没有这一段 */
const NONE_STATE: ParseState = {
  status: 'none',
  stage: '',
  progress: 0,
  error_message: null,
  job_id: null,
  derived_from: 'none',
}

interface Props {
  detail: ProjectDetail
  onDetailChange: (detail: ProjectDetail) => void
}

/**
 * 上传后的「解析中」进度条。
 *
 * 解析（LibreOffice 转换 + 逐页）已改为 worker 队列任务，上传请求只返回 202；
 * 这里轮 `/parse`（主键单行查询），解析成功后回拉一次详情，时间轴与讲稿自动出现。
 * 空闲/已解析完成的历史项目不占位。
 */
export default function ParseProgress({ detail, onDetailChange }: Props) {
  const { message } = App.useApp()
  const [retrying, setRetrying] = useState(false)
  const notifiedRef = useRef<string | null>(null)
  const lastStatusRef = useRef<string | null>(null)

  const refreshDetail = useCallback(async () => {
    const fresh = await fetchPptVideoDetail(detail.id)
    onDetailChange(fresh)
  }, [detail.id, onDetailChange])

  const { data: polled, refetch } = useQuery({
    queryKey: ['ppt-video', detail.id, 'parse'],
    queryFn: () => fetchPptVideoParseState(detail.id),
    initialData: detail.parse ?? NONE_STATE,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === 'queued' || status === 'running' ? POLL_INTERVAL_MS : false
    },
  })

  const state: ParseState = polled ?? detail.parse ?? NONE_STATE
  const running = state.status === 'queued' || state.status === 'running'

  // 终态只处理一次：成功回拉详情（拿到逐页记录），失败提示原因
  useEffect(() => {
    const previous = lastStatusRef.current
    lastStatusRef.current = state.status
    if (previous === null || !TERMINAL.has(state.status) || state.status === 'none') return
    const key = `${state.job_id ?? 'none'}:${state.status}`
    if (notifiedRef.current === key) return
    notifiedRef.current = key
    if (state.status === 'succeeded') {
      void refreshDetail()
      return
    }
    message.error(state.error_message || 'PPT 解析失败')
  }, [state, refreshDetail, message])

  const handleRetry = async () => {
    setRetrying(true)
    const result = await requestParse(detail.id)
    setRetrying(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    void refetch()
  }

  if (!running && state.status !== 'failed') return null

  return (
    <div className="rounded-lg border border-[#E5E3DF] bg-white px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        {state.status === 'failed' ? (
          <Typography.Text type="danger" className="text-[12px]">
            PPT 解析失败
          </Typography.Text>
        ) : (
          <Typography.Text type="secondary" className="text-[12px]">
            {state.status === 'queued' ? '排队等待解析…' : `正在解析 PPT（${state.progress}%）`}
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
            {state.error_message || '未知原因'}
          </Typography.Text>
          <PermissionGate code={PERM.pptVideoManage}>
            <Button size="small" icon={<ReloadOutlined />} loading={retrying} onClick={handleRetry}>
              重试解析
            </Button>
          </PermissionGate>
        </div>
      )}
    </div>
  )
}