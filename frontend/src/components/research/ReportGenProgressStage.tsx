'use client'

import { Button, Flex, Progress, Steps, Tag } from 'antd'
import { UnorderedListOutlined } from '@ant-design/icons'
import { ReportGenStepTimeline } from './ReportGenStepTimeline'
import {
  REPORT_GEN_STAGES,
  stageOfJob,
  statusMeta,
  type ReportGenJob,
} from '@/types/research/report-gen'

interface Props {
  job: ReportGenJob
  /** 任务是否还在跑：终态（失败/终止）后「最近动作」不再轮询 */
  running: boolean
  /** 打开「完整生成过程」抽屉 */
  onOpenTrace: () => void
}

/**
 * 生成中的左栏：阶段条 + 覆盖率 + 最近动作。
 *
 * 替代原先生成期的空白预览位：任务最长可跑 24 分钟，这段时间里用户需要知道
 * 「走到第几步、已经写了多少处、AI 正在干什么」，而不是一句「生成完成后这里会显示文档」。
 */
export function ReportGenProgressStage({ job, running, onOpenTrace }: Props) {
  const meta = statusMeta(job.status)
  const current = stageOfJob(job)
  const percent = job.progress ?? 0
  // 失败/终止后进度条不能再显示「活动」：那会让用户以为还在跑
  const progressStatus = job.status === 'failed' ? 'exception' : running ? 'active' : 'normal'
  const total = job.slot_total ?? 0
  const filled = job.slot_filled ?? 0
  const gap = job.slot_gap ?? 0

  return (
    <Flex vertical style={{ height: '100%', minHeight: 0, background: '#FFFFFF' }}>
      <div style={{ padding: '14px 20px 10px', borderBottom: '1px solid #EDEFF2' }}>
        <Flex align="center" justify="space-between" wrap gap={8}>
          <Flex align="center" gap={8}>
            <Tag color={meta.color} style={{ margin: 0 }}>
              {meta.label}
            </Tag>
            {job.rounds > 0 && (
              <span style={{ fontSize: 12, color: '#8C8C8C' }}>第 {job.rounds} 轮</span>
            )}
          </Flex>
          <span style={{ fontSize: 12, color: '#8C8C8C' }}>{percent}%</span>
        </Flex>

        <Progress
          percent={percent}
          size="small"
          status={progressStatus}
          strokeColor={meta.stroke}
          style={{ margin: '10px 0 4px' }}
        />
        <div style={{ fontSize: 13, color: '#1F2329', marginTop: 2 }}>
          {job.current_step || '正在准备…'}
        </div>

        <Steps
          size="small"
          current={current}
          items={REPORT_GEN_STAGES.map((title) => ({ title }))}
          style={{ marginTop: 14 }}
        />
      </div>

      <div style={{ padding: '10px 20px', borderBottom: '1px solid #EDEFF2' }}>
        <Flex gap={24} wrap style={{ fontSize: 12, color: '#5A6472' }}>
          <span>可填写 {total} 处</span>
          <span style={{ color: '#1677FF' }}>已填写 {filled}</span>
          <span style={{ color: '#8C8C8C' }}>待填写 {gap}</span>
        </Flex>
      </div>

      <Flex align="center" justify="space-between" style={{ padding: '12px 20px 0' }}>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#1F2329' }}>最近动作</span>
        <Button
          type="link"
          size="small"
          icon={<UnorderedListOutlined />}
          onClick={onOpenTrace}
          style={{ paddingRight: 0 }}
        >
          查看完整生成过程
        </Button>
      </Flex>

      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden', padding: '0 20px 16px' }}>
        <ReportGenStepTimeline jobId={job.id} running={running} maxItems={8} autoScroll />
      </div>
    </Flex>
  )
}