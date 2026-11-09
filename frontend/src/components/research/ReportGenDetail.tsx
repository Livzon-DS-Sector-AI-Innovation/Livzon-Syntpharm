'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, App, Button, Card, Col, Empty, Progress, Row, Space, Spin, Statistic, Tag, Tooltip,
} from 'antd'
import {
  ArrowLeftOutlined, DownloadOutlined, EyeOutlined, FileTextOutlined, ReloadOutlined, StopOutlined,
} from '@ant-design/icons'
import { cancelReportGenJob, submitReportGenJob } from '@/actions/research/report-gen'
import {
  downloadReportGenFile, fetchReportGenDocumentBlob, fetchReportGenJob, fetchReportGenSlots,
  fetchReportGenSteps,
} from '@/lib/api/client/research/report-gen'
import { fetchDeliverableReportLinks } from '@/lib/api/client/research/rd-project'
import { RETURN_TO_PARAM, sanitizeReturnTo, withReturnTo } from '@/lib/navigation/returnTo'
import { ReportGenTimeline } from './ReportGenTimeline'
import { ReportGenSlotTable } from './ReportGenSlotTable'
import { ReportGenFeedbackPanel } from './ReportGenFeedbackPanel'
import { DocxPreviewModal } from './DocxPreviewModal'
import { MarkdownPreviewModal } from './MarkdownPreviewModal'
import { useSmartBack } from './useSmartBack'
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
  const searchParams = useSearchParams()
const smartBack = useSmartBack({ fallbackHref: '/research/reports', fallbackLabel: '报告列表' })
// 重新生成会跳到一个新任务页，把当前来源签名原样转过去
const returnTo = sanitizeReturnTo(searchParams.get(RETURN_TO_PARAM))
  const [downloading, setDownloading] = useState<'document' | 'comparison' | ''>('')
  const [cancelling, setCancelling] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [comparisonOpen, setComparisonOpen] = useState(false)
  const [comparisonText, setComparisonText] = useState('')
  const [comparisonLoading, setComparisonLoading] = useState(false)

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

  // 从阶段交付文档发起的任务：显示来源，并给一条回项目的路
  const { data: sourceLink } = useQuery({
    queryKey: ['report-source-deliverable', job?.report_id],
    queryFn: () => fetchDeliverableReportLinks([job?.report_id as string]),
    enabled: !!job?.report_id,
    staleTime: 60_000,
    select: (items) => items[0] ?? null,
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
        : `${job.report_title || '报告'}-填充项对照表.md`
      await downloadReportGenFile(jobId, kind, fallback)
      msgApi.success('下载成功')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    } finally {
      setDownloading('')
    }
  }

  /** 预览对照表：只在首次打开时拉一次，Markdown 文本很小，不做缓存淘汰 */
  const handlePreviewComparison = async () => {
    setComparisonOpen(true)
    if (comparisonText || comparisonLoading) return
    setComparisonLoading(true)
    try {
      const blob = await fetchReportGenDocumentBlob(jobId, 'comparison')
      setComparisonText(await blob.text())
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '对照表加载失败')
    } finally {
      setComparisonLoading(false)
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
      msgApi.warning('这次生成没有记录用的哪个 Word 模板文件，没法原样重跑。请回到列表点「编辑」重新选模板再生成。')
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
      if (nextId && nextId !== jobId) {
        // 带上当前页的来源签名，新任务页的「返回」仍然回原来那个界面
        router.push(withReturnTo(`/research/reports/generation/${nextId}`, returnTo))
      } else refreshAll()
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
          <Button onClick={smartBack.back}>{smartBack.label}</Button>
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
            <Tooltip title={smartBack.hint}>
              <Button
                type="link"
                size="small"
                icon={<ArrowLeftOutlined />}
                style={{ paddingLeft: 0 }}
                onClick={smartBack.back}
              >
                {smartBack.label}
              </Button>
            </Tooltip>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 4, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 20, fontWeight: 600, color: '#1F2329' }}>
                {job.report_title || '研发报告生成'}
              </span>
              <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13, color: '#5A6472' }}>
              <span>文件编号：{job.doc_code || '-'}</span>
              <span>品种名称：{job.drug_name || '-'}</span>
              <span>Word 模板文件：{job.template_file_name || '-'}</span>
              <span>用时：{elapsed}</span>
              {sourceLink ? (
                <span>
                  来源交付文档：
                  <a href={`/research/projects/${sourceLink.project_id}?tab=deliverables`}>
                    {sourceLink.stage_label} · {sourceLink.deliverable_type_label}
                  </a>
                </span>
              ) : null}
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
                  <span>分析结构：</span>
                  <Tag style={{ margin: 0 }}>{snapshot.structure || '与正文同一个模型'}</Tag>
                  <span>自动补齐：</span>
                  <Tag color={snapshot.fallback ? 'orange' : 'default'} style={{ margin: 0 }}>
                    {snapshot.fallback || '未设置'}
                  </Tag>
                  {snapshot.usedFallback && (
                    <Tag color="orange" style={{ margin: 0 }}>
                      主模型失败，已换用自动补齐
                    </Tag>
                  )}
                </>
              ) : (
                <Tag style={{ margin: 0 }}>模型：未记录（历史任务）</Tag>
              )}
            </div>
            {appliedFeedback.length > 0 && (
              <div style={{ marginTop: 6, fontSize: 13, color: '#5A6472' }}>
                <span>这次参考了上一版评审的 {appliedFeedback.length} 条意见：</span>
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
            <Tooltip title={docReady ? '在线查看生成好的 Word 文档' : '生成完成后才能预览'}>
              <span>
                <Button
                  type="primary"
                  icon={<EyeOutlined />}
                  disabled={!docReady}
                  onClick={() => setPreviewOpen(true)}
                >
                  预览
                </Button>
              </span>
            </Tooltip>
            <Tooltip title={docReady ? '下载生成好的 Word 文档' : '生成完成后才能下载'}>
              <span>
                <Button
                  icon={<DownloadOutlined />}
                  disabled={!docReady}
                  loading={downloading === 'document'}
                  onClick={() => handleDownload('document')}
                >
                  下载 Word 文档
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="看看每项内容分别来自哪份资料">
              <span>
                <Button
                  icon={<FileTextOutlined />}
                  disabled={!job.status || job.status !== 'completed'}
                  loading={comparisonLoading}
                  onClick={handlePreviewComparison}
                >
                  查看对照表
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="下载对照表 Markdown，便于存档或随稿流转">
              <span>
                <Button
                  type="text"
                  icon={<DownloadOutlined />}
                  disabled={!job.status || job.status !== 'completed'}
                  loading={downloading === 'comparison'}
                  onClick={() => handleDownload('comparison')}
                >
                  下载对照表
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="会重新跑一次生成并覆盖当前文档，人工改过的内容不会自动带过去">
              <Button icon={<ReloadOutlined />} loading={regenerating} onClick={handleRegenerate}>
                重新生成
              </Button>
            </Tooltip>
            {running && (
              <Button danger icon={<StopOutlined />} loading={cancelling} onClick={handleCancel}>
                停止生成
              </Button>
            )}
          </Space>
        </div>

        {job.status === 'failed' && (
          <Alert
            type="error"
            showIcon
            style={{ marginTop: 16 }}
            message="这次没有生成成功"
            description={
              job.error_message ||
              '没有拿到具体原因。可以再点「重新生成」试一次；如果一直失败，检查一下 Word 模板文件能不能正常打开、知识库里的资料有没有处理失败。'
            }
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
            message="已停止生成"
            description="已经填好的内容还可以查看；要完整文档的话点「重新生成」。"
          />
        )}
      </Card>

      <ReportGenFeedbackPanel jobId={jobId} slots={slotData?.items ?? []} disabled={running} />

      <Row gutter={16}>
        <Col xs={24} xl={14}>
          <Card title="生成过程" styles={{ body: { maxHeight: 720, overflow: 'auto' } }}>
            <ReportGenTimeline steps={steps} running={running || stepsLoading} />
          </Card>
        </Col>
        <Col xs={24} xl={10}>
          <Card
            title="填充项结果"
            extra={
              <Space size={12}>
                <Tooltip title="已经写进文档的填充项数量">
                  <Statistic title="已填" value={slotData?.filled ?? job.slot_filled} valueStyle={{ fontSize: 16 }} />
                </Tooltip>
                <Tooltip title="找不到依据、需要人工补充的填充项数量">
                  <Statistic title="待补充" value={slotData?.gaps ?? job.slot_gap} valueStyle={{ fontSize: 16 }} />
                </Tooltip>
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
                {running ? '正在逐项填写内容…' : '还没有填写记录。可以点「重新生成」，让 AI 重新分析模板结构再写一遍。'}
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <DocxPreviewModal
        open={previewOpen}
        title={job.report_title || '报告预览'}
        loadBlob={() => fetchReportGenDocumentBlob(jobId, 'document')}
        onDownload={() => handleDownload('document')}
        onClose={() => setPreviewOpen(false)}
      />
      <MarkdownPreviewModal
        open={comparisonOpen}
        title={`${job.report_title || '报告'} · 填充项对照表`}
        markdown={comparisonLoading ? '正在加载对照表…' : comparisonText}
        onClose={() => setComparisonOpen(false)}
      />
    </div>
  )
}