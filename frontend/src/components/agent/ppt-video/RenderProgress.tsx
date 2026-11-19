'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
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
  const [submitting, setSubmitting] = useState(false)
  // 刚提交时的乐观态：轮询一旦返回同一个 job_id 就交给服务端数据
  const [optimisticJob, setOptimisticJob] = useState<JobState | null>(null)
  const notifiedRef = useRef<string | null>(null)
  const lastStatusRef = useRef<string | null>(null)

  const refreshDetail = useCallback(async () => {
    const fresh = await fetchPptVideoDetail(detail.id)
    onDetailChange(fresh)
  }, [detail.id, onDetailChange])

  // 轮询等价于「任务未终态」：refetchInterval 返回 false 即停
  const { data: polledJob, refetch: refetchJob } = useQuery({
    queryKey: ['ppt-video', detail.id, 'job'],
    queryFn: () => fetchPptVideoJob(detail.id),
    initialData: detail.latest_job ?? undefined,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status && !TERMINAL.has(status) ? 2000 : false
    },
  })

  const job: JobState | null =
    optimisticJob && polledJob?.job_id !== optimisticJob.job_id
      ? optimisticJob
      : (polledJob ?? detail.latest_job ?? null)
  const running = job ? !TERMINAL.has(job.status) : false

  // 终态只提示一次：按 job_id+status 去重；首次渲染就是终态（打开已出片的项目）不提示
  useEffect(() => {
    if (!job) return
    const previous = lastStatusRef.current
    lastStatusRef.current = `${job.job_id}:${job.status}`
    if (previous === null || !TERMINAL.has(job.status)) return
    const key = `${job.job_id}:${job.status}`
    if (notifiedRef.current === key) return
    notifiedRef.current = key
    void refreshDetail().then(() => {
      if (job.status === 'succeeded') message.success('视频已生成，可在右侧版本列表下载')
      if (job.status === 'failed') message.error(job.error_message || '生成失败')
    })
  }, [job, refreshDetail, message])

  const handleRender = async () => {
    setSubmitting(true)
    const result = await requestRender(detail.id)
    setSubmitting(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    if (result.data) {
      setOptimisticJob({
        job_id: result.data.job_id,
        kind: 'render',
        status: 'queued',
        stage: 'queued',
        progress: 0,
        attempts: 0,
      })
      // 提交后立刻拉一次：拿到 queued 才会让 refetchInterval 开始计时
      void refetchJob()
    }
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
          <Tag>语速 {detail.speed.toFixed(2)} 倍</Tag>
          {running && <Tag color="processing">生成中</Tag>}
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
          message="内容有改动，需要重新生成"
          description="各页讲稿、语言、音色或语速与上一版不同，旧的成片不能沿用；重新生成只重做有改动的页，其余页直接沿用。"
        />
      )}

      {job?.status === 'failed' && (
        <Alert
          type="error"
          showIcon
          className="!mt-3"
          message={`生成失败：${job.error_message || '未知原因'}`}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={handleRender}>
              重试
            </Button>
          }
        />
      )}

      {running && (
        <Typography.Text type="secondary" className="mt-2 block text-[12px]">
          进度每 2 秒自动刷新，可离开页面，任务在后台继续
        </Typography.Text>
      )}
    </div>
  )
}