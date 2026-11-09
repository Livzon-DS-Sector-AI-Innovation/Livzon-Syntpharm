'use client'

import { Collapse, Empty, Spin, Tag, Timeline, Typography } from 'antd'
import {
  CheckCircleOutlined, CloseCircleOutlined, LoadingOutlined, ThunderboltOutlined,
} from '@ant-design/icons'
import { formatDuration, stepKindMeta, type ReportGenStep } from '@/types/research/report-gen'

interface Props {
  steps: ReportGenStep[]
  running: boolean
}

function PayloadBlock({ label, text }: { label: string; text: string }) {
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ fontSize: 12, color: '#8c8c8c', marginBottom: 4 }}>{label}</div>
      <pre
        style={{
          margin: 0,
          padding: '8px 10px',
          background: '#f7f9fc',
          borderRadius: 4,
          fontSize: 12,
          lineHeight: 1.6,
          maxHeight: 220,
          overflow: 'auto',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-all',
        }}
      >
        {text}
      </pre>
    </div>
  )
}

/** 单步内容：标题 + 耗时 + 状态，参数与结果收在折叠区里 */
function StepBody({ step }: { step: ReportGenStep }) {
  const meta = stepKindMeta(step.kind)
  const args = step.args_summary ? JSON.stringify(step.args_summary, null, 2) : ''
  const hasDetail = !!args || !!step.result_summary
  const failed = step.status === 'failed' || step.kind === 'error'

  return (
    <div style={{ paddingBottom: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 500, color: '#1F2329' }}>{step.title}</span>
        {step.tool_name && <Tag color="cyan" style={{ margin: 0 }}>{step.tool_name}</Tag>}
        <Tag color={failed ? 'error' : 'default'} style={{ margin: 0 }}>{meta.label}</Tag>
        {step.duration_ms !== null && step.duration_ms !== undefined && (
          <span style={{ fontSize: 12, color: '#8c8c8c' }}>{formatDuration(step.duration_ms)}</span>
        )}
      </div>
      {hasDetail && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 4 }}
          items={[
            {
              key: 'detail',
              label: <span style={{ fontSize: 12, color: '#1677FF' }}>查看参数与结果</span>,
              children: (
                <div>
                  {args && <PayloadBlock label="入参" text={args} />}
                  {step.result_summary && <PayloadBlock label="结果" text={step.result_summary} />}
                </div>
              ),
            },
          ]}
        />
      )}
    </div>
  )
}

/** Agent 执行过程时间线：按 seq 顺序追加，执行中最新一条带脉冲。 */
export function ReportGenTimeline({ steps, running }: Props) {
  if (steps.length === 0) {
    return (
      <div style={{ padding: '48px 0' }}>
        {running ? (
          <div style={{ textAlign: 'center', color: '#5A6472' }}>
            <Spin indicator={<LoadingOutlined spin />} />
            <div style={{ marginTop: 12, fontSize: 13 }}>AI 正在准备工作…</div>
            <div style={{ marginTop: 4, fontSize: 12, color: '#8C8C8C' }}>
              正在分析模板结构、读取项目信息、检索知识库
            </div>
          </div>
        ) : (
          <Empty description="还没有生成记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </div>
    )
  }

  const items = steps.map((step, index) => {
    const failed = step.status === 'failed' || step.kind === 'error'
    const isLast = index === steps.length - 1
    const color = failed ? '#FF4D4F' : stepKindMeta(step.kind).color
    const dot = failed
      ? <CloseCircleOutlined style={{ color }} />
      : step.kind === 'tool_call'
        ? <ThunderboltOutlined style={{ color }} />
        : isLast && running
          ? <LoadingOutlined style={{ color }} spin />
          : <CheckCircleOutlined style={{ color }} />
    return {
      key: step.id,
      color,
      dot,
      children: (
        <div
          className="report-gen-step"
          style={{
            // 最新一条在执行中时轻微高亮，肉眼能跟上追加节奏
            background: isLast && running ? '#FFFFFF' : undefined,
            borderRadius: 6,
            padding: isLast && running ? '4px 8px' : undefined,
            boxShadow: isLast && running ? '0 2px 8px rgba(22, 119, 255, 0.12)' : undefined,
            transition: 'background 200ms ease',
          }}
        >
          <StepBody step={step} />
        </div>
      ),
    }
  })

  return (
    <>
      <Timeline items={items} style={{ paddingTop: 8 }} />
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        共 {steps.length} 条记录
      </Typography.Text>
    </>
  )
}