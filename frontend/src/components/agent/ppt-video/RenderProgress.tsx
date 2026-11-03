'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, App, Button, Progress, Space, Tag, Typography } from 'antd'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons'

import { requestRender } from '@/actions/agent/ppt-video'
import { fetchPptVideoDetail, fetchPptVideoJob } from '@/lib/api/client/agent'
import { STAGE_LABEL, type JobState, type ProjectDetail } from '@/types/agent/ppt-video'

const TERMINAL = new Set(['succeeded', 'failed', 'canceled'])

interface Props {
  detail: ProjectDetail
  onDetailChange: (detail: ProjectDetail) => void
}

/**
 * 顶部状态条：进度 + 阶段文案 + 「生成视频」。
 *
 * 轮询 2 秒一次，只打 `/job`（单行查询）；终态时回拉一次详情，
 * 让版本列表与 body_stale 同步，避免前端自己猜状态。
 */
export default function RenderProgress({ detail, onDetailChange }: Props) {
  const { message } = App.useApp()
  const [job, setJob] = useState<JobState | null>(detail.latest_job ?? null)
  const [submitting, setSubmitting] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const running = job ? !TERMINAL.has(job.status) : false
  // 轮询区间等价于「任务未终态」，不再单独存一份布尔状态
  const polling = running

  const refreshDetail = useCallback(async () => {
    const fresh = await fetchPptVideoDetail(detail.id)
    onDetailChange(fresh)
  }, [detail.id, onDetailChange])

  useEffect(() => {
    if (!running) return
    let cancelled = false

    const tick = async () => {
      try {
        const next = await fetchPptVideoJob(detail.id)
        if (cancelled) return
        setJob(next)
        if (next && TERMINAL.has(next.status)) {
          await refreshDetail()
          if (next.status === 'succeeded') message.success('视频已生成，可在右侧版本列表下载')
          if (next.status === 'failed') message.error(next.error_message || '渲染失败')
          return
        }
      } catch (error) {
        console.warn('轮询渲染进度失败:', error)
      }
      if (!cancelled) timer.current = setTimeout(tick, 2000)
    }

    timer.current = setTimeout(tick, 2000)
    return () => {
      cancelled = true
      if (timer.current) clearTimeout(timer.current)
    }
  }, [running, detail.id, refreshDetail, message])

  const handleRender = async () => {
    setSubmitting(true)
    const result = await requestRender(detail.id)
    setSubmitting(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    setJob({
      job_id: result.data?.job_id ?? '',
      status: 'queued',
      stage: 'queued',
      progress: 0,
      attempts: 0,
    })
  }

  return (
    <div className="rounded-xl border border-[#E5E3DF] bg-white px-5 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Space size={8} wrap>
          <Typography.Title level={4} className="!mb-0 !text-[18px]">
            {detail.name}
          </Typography.Title>
          <Tag color="purple">{detail.slide_count} 页</Tag>
          <Tag color={detail.default_language === 'zh' ? 'blue' : 'geekblue'}>
            {detail.default_language === 'zh' ? '中文旁白' : '英文旁白'}
          </Tag>
          <Tag>语速 {detail.speed.toFixed(2)}x</Tag>
          {running && <Tag color="processing">渲染中</Tag>}
        </Space>
        <Space>
          {job && (
            <Typography.Text type="secondary" className="text-[13px]">
              {STAGE_LABEL[job.stage] ?? job.stage}
              {job.progress > 0 && job.progress < 100 ? ` ${job.progress}%` : ''}
            </Typography.Text>
          )}
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            loading={submitting || running}
            onClick={handleRender}
          >
            {detail.versions?.length ? '生成新版本' : '生成视频'}
          </Button>
        </Space>
      </div>

      {running && (
        <Progress
          percent={job?.progress ?? 0}
          status="active"
          strokeColor="#5645D4"
          className="!mt-3 !mb-0"
          size="small"
        />
      )}

      {detail.body_stale && (
        <Alert
          type="warning"
          showIcon
          className="!mt-3"
          message="正文已变更，需重新生成"
          description="正文各页讲稿、语言、音色或语速与上一版不同，旧版本无法复用；重新生成只会重算改动页，其余页命中缓存。"
        />
      )}

      {job?.status === 'failed' && (
        <Alert
          type="error"
          showIcon
          className="!mt-3"
          message={`渲染失败：${job.error_message || '未知原因'}`}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={handleRender}>
              重试
            </Button>
          }
        />
      )}

      {polling && (
        <Typography.Text type="secondary" className="mt-2 block text-[12px]">
          进度每 2 秒自动刷新，可离开页面，任务在后台继续
        </Typography.Text>
      )}
    </div>
  )
}