'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, App, Button, Card, Col, Empty, Progress, Row, Space, Spin, Statistic, Tag, Tooltip,
} from 'antd'
import {
  ArrowLeftOutlined, DownloadOutlined, FileTextOutlined, ReloadOutlined, StopOutlined,
} from '@ant-design/icons'
import { cancelReportGenJob, submitReportGenJob } from '@/actions/research/report-gen'
import {
  downloadReportGenFile, fetchReportGenJob, fetchReportGenSlots, fetchReportGenSteps,
} from '@/lib/api/client/research/report-gen'
import { ReportGenTimeline } from './ReportGenTimeline'
import { ReportGenSlotTable } from './ReportGenSlotTable'
import { ReportGenFeedbackPanel } from './ReportGenFeedbackPanel'
import {
  formatDuration, isTerminal, jobElapsedMs, jobModelSnapshot, statusMeta,
  type ReportGenJob, type ReportGenStep,
} from '@/types/research/report-gen'

interface Props {
  jobId: string
  initialJob: ReportGenJob | null
}

/** AI 报告执行过程详情：头部状态 + 执行时间线 + 槽位结果。 */
export function ReportGenDetail({ jobId, initialJob }: Props) {
  const { message: msgApi } = App.useApp()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [downloading, setDownloading] = useState<'document' | 'comparison' | ''>('')
  const [cancelling, setCancelling] = useState(false)
  const [regenerating, setRegenerating] = useState(false)

  const { data: job, error: jobError } = useQuery({
    queryKey: ['report-gen-job', jobId],
    queryFn: () => fetchReportGenJob(jobId),
    initialData: initialJob ?? undefined,
    refetchInterval: (query) => (isTerminal(query.state.data?.status ?? '') ? false : 3000),
    refetchOnWindowFocus: false,
  })

  const running = !!job && !isTerminal(job.status)

  // 步骤按 after_seq 增量追加：只在有新增时重建数组，避免整页刷新闪烁
  const seqRef = useRef(0)
  const accRef = useRef<ReportGenStep[]>([])
  const { data: steps = [], isLoading: stepsLoading } = useQuery({
    queryKey: ['report-gen-steps', jobId],
    queryFn: async () => {
      const page = await fetchReportGenSteps(jobId, seqRef.current)
      if (page.items.length > 0) {
        accRef.current = [...accRef.current, ...page.items]
        seqRef.current = page.last_seq
      }
      return accRef.current
    },
    refetchInterval: running ? 2000 : false,
    refetchOnWindowFocus: false,
  })

  const { data: slotData, isLoading: slotsLoading } = useQuery({
    queryKey: ['report-gen-slots', jobId],
    queryFn: () => fetchReportGenSlots(jobId),
    refetchInterval: running ? 4000 : false,
    refetchOnWindowFocus: false,
  })

  // 任务进入终态（完成/失败/取消）后补一次刷新：轮询周期内落库的步骤与槽位可能还没取到
  const statusRef = useRef(job?.status ?? null)
  useEffect(() => {
    const status = job?.status ?? null
    const prev = statusRef.current
    statusRef.current = status
    if (!prev || prev === status || !status || !isTerminal(status)) return
    queryClient.invalidateQueries({ queryKey: ['report-gen-steps', jobId] })
    queryClient.invalidateQueries({ queryKey: ['report-gen-slots', jobId] })
  }, [job?.status, jobId, queryClient])

  // 执行中每秒刷新耗时显示
  const [, setTick] = useState(0)
  useEffect(() => {
    if (!running) return
    const timer = setInterval(() => setTick((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [running])

  const meta = statusMeta(job?.status ?? 'queued')
  // 执行中 tick 每秒触发重渲染，耗时随更新时间推进
  const elapsed = job ? formatDuration(jobElapsedMs(job)) : '-'

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['report-gen-job', jobId] })
    queryClient.invalidateQueries({ queryKey: ['report-gen-steps', jobId] })
    queryClient.invalidateQueries({ queryKey: ['report-gen-slots', jobId] })
  }

  const handleDownload = async (kind: 'document' | 'comparison') => {
    if (!job) return
    setDownloading(kind)
    try {
      const fallback = kind === 'document'
        ? `${job.report_title || '报告'}.docx`
        : `${job.report_title || '报告'}-槽位对照表.md`
      await downloadReportGenFile(jobId, kind, fallback)
      msgApi.success('下载成功')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    } finally {
      setDownloading('')
    }
  }

  const handleCancel = async () => {
    setCancelling(true)
    try {
      await cancelReportGenJob(jobId)
      msgApi.info('已请求终止，Agent 会在下一步退出')
      refreshAll()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '终止失败')
    } finally {
      setCancelling(false)
    }
  }

  const handleRegenerate = async () => {
    if (!job) return
    if (!job.deliverable_template_id) {
      msgApi.warning('这条任务缺少模板母本记录，无法原样重跑，请回到列表重新编辑生成')
      return
    }
    setRegenerating(true)
    try {
      const created = await submitReportGenJob({
        report_id: job.report_id,
        project_id: job.project_id,
        deliverable_template_id: job.deliverable_template_id,
        doc_code: job.doc_code,
        drug_name: job.drug_name,
        supplement_text: job.supplement_text,
      })
      const nextId = (created as { data?: { id?: string } } | null)?.data?.id
      msgApi.success('已提交新的生成任务')
      if (nextId && nextId !== jobId) router.push(`/research/reports/generation/${nextId}`)
      else refreshAll()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '重新生成失败')
    } finally {
      setRegenerating(false)
    }
  }

  if (jobError && !job) {
    return (
      <Card>
        <Empty description="任务不存在或已删除" />
        <div style={{ textAlign: 'center' }}>
          <Button onClick={() => router.push('/research')}>返回列表</Button>
        </div>
      </Card>
    )
  }

  if (!job) {
    return <Card><div style={{ textAlign: 'center', padding: '60px 0' }}><Spin size="large" /></div></Card>
  }

  const docReady = job.status === 'completed' && job.has_document
  // 模型快照：任务创建时落库；快照列上线前的历史任务为 null
  const snapshot = jobModelSnapshot(job)
  const appliedFeedback = job.feedback_applied ?? []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card
        styles={{ body: { padding: '20px 24px' } }}
        style={{ borderRadius: 12, boxShadow: '0 2px 12px rgba(31, 35, 41, 0.06)' }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 320, flex: 1 }}>
            <Button type="link" size="small" icon={<ArrowLeftOutlined />} style={{ paddingLeft: 0 }} onClick={() => router.push('/research')}>
              返回研发报告
            </Button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 20, fontWeight: 600, color: '#1F2329' }}>
                {job.report_title || '研发报告生成'}
              </span>
              <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13, color: '#5A6472' }}>
              <span>受控编码：{job.doc_code || '-'}</span>
              <span>品种名称：{job.drug_name || '-'}</span>
              <span>母本：{job.template_file_name || '-'}</span>
              <span>耗时：{elapsed}</span>
            </div>
            <div
              style={{
                marginTop: 6,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                flexWrap: 'wrap',
                fontSize: 13,
                color: '#5A6472',
              }}
            >
              {snapshot ? (
                <>
                  <span>模型：</span>
                  <Tag style={{ margin: 0 }}>{snapshot.main || '未记录'}</Tag>
                  <span>结构识别：</span>
                  <Tag style={{ margin: 0 }}>{snapshot.structure || '复用主模型'}</Tag>
                  <span>兜底：</span>
                  <Tag color={snapshot.fallback ? 'orange' : 'default'} style={{ margin: 0 }}>
                    {snapshot.fallback || '未设置'}
                  </Tag>
                  {snapshot.usedFallback && (
                    <Tag color="orange" style={{ margin: 0 }}>
                      已降级
                    </Tag>
                  )}
                </>
              ) : (
                <Tag style={{ margin: 0 }}>模型：未记录（历史任务）</Tag>
              )}
            </div>
            {appliedFeedback.length > 0 && (
              <div style={{ marginTop: 6, fontSize: 13, color: '#5A6472' }}>
                <span>本次带入 {appliedFeedback.length} 条上版意见：</span>
                {appliedFeedback.map((item) => (
                  <Tooltip key={item.id} title={item.content}>
                    <Tag color="blue" style={{ marginInlineEnd: 6 }}>
                      {item.slot_key || '整篇'}
                    </Tag>
                  </Tooltip>
                ))}
              </div>
            )}
            {running && (
              <div style={{ marginTop: 12, maxWidth: 520 }}>
                <Progress percent={job.progress ?? 0} size="small" strokeColor={meta.stroke} status="active" />
                <div style={{ fontSize: 12, color: '#5A6472', marginTop: 4 }}>
                  {job.current_step || '正在准备…'}
                </div>
              </div>
            )}
          </div>

          <Space wrap size={8} style={{ alignItems: 'flex-start' }}>
            <Button
              icon={<DownloadOutlined />}
              disabled={!docReady}
              loading={downloading === 'document'}
              onClick={() => handleDownload('document')}
            >
              下载文档
            </Button>
            <Button
              icon={<FileTextOutlined />}
              disabled={!job.status || job.status !== 'completed'}
              loading={downloading === 'comparison'}
              onClick={() => handleDownload('comparison')}
            >
              下载对照表
            </Button>
            <Button icon={<ReloadOutlined />} loading={regenerating} onClick={handleRegenerate}>
              重新生成
            </Button>
            {running && (
              <Button danger icon={<StopOutlined />} loading={cancelling} onClick={handleCancel}>
                终止
              </Button>
            )}
          </Space>
        </div>

        {job.status === 'failed' && (
          <Alert
            type="error"
            showIcon
            style={{ marginTop: 16 }}
            message="生成失败"
            description={job.error_message || '未知错误，请重试或检查知识库与模板母本是否可读。'}
            action={
              <Button size="small" type="primary" loading={regenerating} onClick={handleRegenerate}>
                重新生成
              </Button>
            }
          />
        )}

        {job.status === 'cancelled' && (
          <Alert
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
            message="任务已终止"
            description="已填充的槽位仍可查看；如需成品请重新生成。"
          />
        )}
      </Card>

      <ReportGenFeedbackPanel jobId={jobId} slots={slotData?.items ?? []} disabled={running} />

      <Row gutter={16}>
        <Col xs={24} xl={14}>
          <Card title="执行过程" styles={{ body: { maxHeight: 720, overflow: 'auto' } }}>
            <ReportGenTimeline steps={steps} running={running || stepsLoading} />
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card
            title="槽位结果"
            extra={
              <Space size={12}>
                <Statistic title="已填" value={slotData?.filled ?? job.slot_filled} valueStyle={{ fontSize: 16 }} />
                <Statistic title="缺口" value={slotData?.gaps ?? job.slot_gap} valueStyle={{ fontSize: 16 }} />
              </Space>
            }
            styles={{ body: { maxHeight: 720, overflow: 'auto' } }}
          >
            <ReportGenSlotTable
              jobId={jobId}
              slots={slotData?.items ?? []}
              loading={slotsLoading}
              editable={isTerminal(job.status)}
            />
            {(slotData?.items ?? []).length === 0 && !slotsLoading && (
              <div style={{ padding: '32px 0', textAlign: 'center', color: '#8C8C8C', fontSize: 13 }}>
                {running ? '槽位正在逐个写入…' : '没有槽位记录，可重新生成以重新分析母本结构'}
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}