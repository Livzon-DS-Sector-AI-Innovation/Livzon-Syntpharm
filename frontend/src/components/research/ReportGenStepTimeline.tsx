'use client'

import { useEffect, useMemo, useRef, type ReactNode } from 'react'
import { Empty, Flex, Tag, Tooltip, Typography } from 'antd'
import {
  BulbOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  InfoCircleOutlined,
  ToolOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { fetchReportGenSteps } from '@/lib/api/client/research/report-gen'
import { formatDuration, stepKindMeta, type ReportGenStep } from '@/types/research/report-gen'

interface Props {
  jobId: string
  /** 任务未结束才轮询；终态后停掉，页面不会挂着空转 */
  running: boolean
  /** 只展示最后 N 条：进度舞台里看近况，完整过程走抽屉 */
  maxItems?: number
  autoScroll?: boolean
}

const KIND_ICON: Record<string, ReactNode> = {
  think: <BulbOutlined />,
  tool_call: <ToolOutlined />,
  tool_result: <CheckCircleOutlined />,
  error: <CloseCircleOutlined />,
  status: <InfoCircleOutlined />,
}

/** 单步耗时只在有值时显示：模型思考与状态行没有耗时，占位反而干扰阅读。 */
function MetaLine({ step }: { step: ReportGenStep }) {
  const parts: string[] = []
  if (step.tool_name) parts.push(step.tool_name)
  if (step.duration_ms !== null && step.duration_ms !== undefined) parts.push(formatDuration(step.duration_ms))
  if (!parts.length) return null
  return (
    <span style={{ fontSize: 11, color: '#8C8C8C', whiteSpace: 'nowrap' }}>
      {parts.join(' · ')}
    </span>
  )
}

function StepRow({ step }: { step: ReportGenStep }) {
  const meta = stepKindMeta(step.kind)
  const failed = step.status === 'failed'
  const icon = failed ? <ExclamationCircleOutlined /> : (KIND_ICON[step.kind] ?? <InfoCircleOutlined />)
  const summary = step.result_summary ?? ''

  return (
    <Flex gap={10} align="flex-start" style={{ padding: '6px 0' }}>
      <span
        style={{
          width: 22,
          height: 22,
          flexShrink: 0,
          marginTop: 1,
          borderRadius: 6,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 12,
          color: failed ? '#FF4D4F' : meta.color,
          background: failed ? '#FEF2F2' : '#F5F7FA',
        }}
      >
        {icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Flex gap={8} align="center" justify="space-between">
          <span
            style={{
              fontSize: 12,
              color: failed ? '#DC2626' : '#1F2329',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {step.title}
          </span>
          <MetaLine step={step} />
        </Flex>
        {summary && (
          <Tooltip title={summary}>
            <div
              style={{
                marginTop: 2,
                fontSize: 11,
                color: '#8C8C8C',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {summary}
            </div>
          </Tooltip>
        )}
      </div>
    </Flex>
  )
}

/**
 * 生成过程时间线：AI 每一步在做什么。
 *
 * 取数口径：每次按完整快照取（后端最多 400 条，单条只有标题与摘要），只保留最后
 * `maxItems` 条。不做 after_seq 累积——增量合并要维护本地游标状态，而这里的数据量
 * 完全撑得住快照式轮询，少一层状态就少一类「步骤重复/漏行」的问题。
 */
export function ReportGenStepTimeline({ jobId, running, maxItems = 200, autoScroll = false }: Props) {
  const listRef = useRef<HTMLDivElement | null>(null)
  const { data, isLoading, error } = useQuery({
    queryKey: ['report-gen-steps', jobId],
    queryFn: () => fetchReportGenSteps(jobId, 0, 500),
    refetchInterval: running ? 3000 : false,
    refetchOnWindowFocus: false,
    staleTime: 1000,
  })

  const steps = useMemo(() => {
    const items = data?.items ?? []
    return items.length > maxItems ? items.slice(items.length - maxItems) : items
  }, [data, maxItems])

  const lastSeq = steps.length ? steps[steps.length - 1].seq : 0

  useEffect(() => {
    if (!autoScroll) return
    const element = listRef.current
    if (!element) return
    element.scrollTop = element.scrollHeight
  }, [autoScroll, lastSeq])

  if (error) {
    return (
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        执行过程加载失败：{error instanceof Error ? error.message : '未知原因'}
      </Typography.Text>
    )
  }

  if (isLoading && !steps.length) {
    return (
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        正在读取执行过程…
      </Typography.Text>
    )
  }

  if (!steps.length) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={<span style={{ fontSize: 12 }}>还没有执行记录，任务起步后这里会出现</span>}
        style={{ margin: '8px 0' }}
      />
    )
  }

  return (
    <div ref={listRef} style={{ overflow: 'auto', height: '100%' }}>
      {steps.map((step) => (
        <StepRow key={step.seq} step={step} />
      ))}
      {running && (
        <Flex align="center" gap={8} style={{ padding: '6px 0', fontSize: 11, color: '#8C8C8C' }}>
          <Tag color="processing" style={{ margin: 0, fontSize: 11 }}>
            进行中
          </Tag>
          正在等待下一步…
        </Flex>
      )}
    </div>
  )
}