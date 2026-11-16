'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Collapse, Drawer, Empty, Space, Spin, Tabs, Tag, Tooltip } from 'antd'
import {
  ArrowLeftOutlined,
  DownloadOutlined,
  HistoryOutlined,
  ReloadOutlined,
  StopOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { cancelReportGenJob, submitReportGenJob } from '@/actions/research/report-gen'
import {
  downloadReportGenFile, fetchReportGenJob, fetchReportGenOutline, fetchReportGenVersions,
} from '@/lib/api/client/research/report-gen'
import { fetchDeliverableReportLinks } from '@/lib/api/client/research/rd-project'
import { RETURN_TO_PARAM, sanitizeReturnTo, withReturnTo } from '@/lib/navigation/returnTo'
import { ReportGenFeedbackPanel } from './ReportGenFeedbackPanel'
import { ReportGenFieldPanel } from './ReportGenFieldPanel'
import { ReportGenPreviewPane } from './ReportGenPreviewPane'
import { ReportGenProgressStage } from './ReportGenProgressStage'
import { ReportGenReferencePanel } from './ReportGenReferencePanel'
import { ReportGenSlotEditor } from './ReportGenSlotEditor'
import { ReportGenStepTimeline } from './ReportGenStepTimeline'
import { ReportGenVersionList } from './ReportGenVersionList'
import { ElapsedTime } from './ElapsedTime'
import { useSmartBack } from './useSmartBack'
import {
  describeJobFailure, isTerminal, jobModelSnapshot, statusMeta,
  type ReportGenFieldItem,
  type ReportGenJob,
} from '@/types/research/report-gen'

interface Props {
  jobId: string
  initialJob: ReportGenJob | null
}

/** AI 报告生成详情：头部状态 + 生成过程 + 写入覆盖率。 */
export function ReportGenDetail({ jobId, initialJob }: Props) {
  const { message: msgApi } = App.useApp()
  const router = useRouter()
  const queryClient = useQueryClient()
  const searchParams = useSearchParams()
  const smartBack = useSmartBack({ fallbackHref: '/research/reports', fallbackLabel: '报告列表' })
  // 重新生成会跳到一个新任务页，把当前来源签名原样转过去
  const returnTo = sanitizeReturnTo(searchParams.get(RETURN_TO_PARAM))
  const [downloading, setDownloading] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [versionsOpen, setVersionsOpen] = useState(false)
  const [traceOpen, setTraceOpen] = useState(false)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  // 右栏是否处于编辑态：编辑卡直接占用右栏（不再弹抽屉）。
  // 浮层会盖住右侧清单、把 body 锁死滚动，于是「点一处就编辑」时预览和右栏都被挡住没法用。
  const [editing, setEditing] = useState(false)
  // 右栏页签：填写清单（位置与编辑卡）/ 参考资料（引用源，不进正文）
  const [rightTab, setRightTab] = useState<'fields' | 'references'>('fields')
  // 每次保存/回滚都换一版文件，预览需要重新拉取，不能只靠文件名判断
  const [documentVersion, setDocumentVersion] = useState(0)

  const { data: job, error: jobError } = useQuery({
    queryKey: ['report-gen-job', jobId],
    queryFn: () => fetchReportGenJob(jobId),
    initialData: initialJob ?? undefined,
    refetchInterval: (query) => (isTerminal(query.state.data?.status ?? '') ? false : 3000),
    refetchOnWindowFocus: false,
  })

  const running = !!job && !isTerminal(job.status)

  // 可写位置清单：生成中也要取（那时只有位置、还没有写入值，正好展示「准备写哪些地方」）
  const {
    data: outline,
    isLoading: outlineLoading,
    error: outlineError,
  } = useQuery({
    queryKey: ['report-gen-outline', jobId],
    queryFn: () => fetchReportGenOutline(jobId),
    enabled: !!job,
    // 8 秒：写工具批内会推进进度，但清单本身只随轮次变化，5 秒一取纯属浪费
    refetchInterval: running ? 8000 : false,
    refetchOnWindowFocus: false,
  })

  const selectedItem = useMemo(() => {
    if (!outline || !selectedKey) return null
    return (
      outline.items?.find((item) => item.key === selectedKey) ??
      outline.locked_items?.find((item) => item.key === selectedKey) ??
      null
    )
  }, [outline, selectedKey])

  // 版本列表：编辑要带 base_version_id 做并发校验，回滚入口也在这里
  const { data: versionData, refetch: refetchVersions } = useQuery({
    queryKey: ['report-gen-versions', jobId],
    queryFn: () => fetchReportGenVersions(jobId),
    enabled: !!job,
    staleTime: 10_000,
  })
  const currentVersionId = useMemo(
    () => versionData?.items?.find((item) => item.is_current)?.id ?? null,
    [versionData],
  )

  // 任务完成的那一刻补拉一次清单：完成前拉到的清单还没有文档（has_document=false），
  // 而运行态一结束就不再轮询，不补拉的话清单与预览的定位标记会停在完成前那一份。
  // 任务状态与 document_object_key 是同一次 commit 落库的，补拉一定能看到文档。
  useEffect(() => {
    if (job?.status !== 'completed' || !job.has_document) return
    void queryClient.invalidateQueries({ queryKey: ['report-gen-outline', jobId] })
    // 完成瞬间可能刚好有一次生成期发出的清单请求在途（回来后仍是旧数据），2.5 秒后再补一次
    const timer = window.setTimeout(() => {
      void queryClient.invalidateQueries({ queryKey: ['report-gen-outline', jobId] })
    }, 2500)
    return () => window.clearTimeout(timer)
  }, [job?.status, job?.has_document, jobId, queryClient])

  const handleContentSaved = useCallback(() => {
    setEditing(false)
    setDocumentVersion((value) => value + 1)
    void queryClient.invalidateQueries({ queryKey: ['report-gen-outline', jobId] })
    void queryClient.invalidateQueries({ queryKey: ['report-gen-job', jobId] })
    void refetchVersions()
  }, [queryClient, jobId, refetchVersions])

  // 从阶段交付文档发起的任务：显示来源，并给一条回项目的路
  const { data: sourceLink } = useQuery({
    queryKey: ['report-source-deliverable', job?.report_id],
    queryFn: () => fetchDeliverableReportLinks([job?.report_id as string]),
    enabled: !!job?.report_id,
    staleTime: 60_000,
    select: (items) => items[0] ?? null,
  })

  const meta = statusMeta(job?.status ?? 'queued')

  const refreshAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['report-gen-job', jobId] })
  }, [queryClient, jobId])

  const handleDownload = async () => {
    if (!job) return
    setDownloading(true)
    try {
      await downloadReportGenFile(jobId, `${job.report_title || '报告'}.docx`)
      msgApi.success('下载成功')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '下载失败')
    } finally {
      setDownloading(false)
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
      msgApi.warning('这次生成没有记录用的哪个 Word 模板文件，没法按原样重新生成。请回到列表点「编辑」，重新选择模板再生成。')
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

  const handleSelectField = useCallback((item: ReportGenFieldItem) => {
    // 在预览/清单里点位置时统一回到「填写清单」，右栏编辑卡才对应得上
    setRightTab('fields')
    setSelectedKey(item.key)
    setEditing(true)
  }, [])

  const handleLocateKey = useCallback((key: string) => {
    setRightTab('fields')
    setSelectedKey(key)
    setEditing(true)
  }, [])

  // 只收起编辑卡，保留选中行：清单重新出现时会滚回那一行，用户知道刚才改的是哪一处
  const closeEditor = useCallback(() => setEditing(false), [])

  const openTrace = useCallback(() => setTraceOpen(true), [])

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
  const failure = job.status === 'failed' ? describeJobFailure(job.error_message) : null

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
              <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0, color: '#1F2329' }}>
                {job.report_title || '研发报告生成'}
              </h1>
              <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
            </div>
            <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap', fontSize: 13, color: '#5A6472' }}>
              <span>文件编号：{job.doc_code || '-'}</span>
              <span>品种名称：{job.drug_name || '-'}</span>
              <span>Word 模板文件：{job.template_file_name || '-'}</span>
              <span>用时：<ElapsedTime job={job} /></span>
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
                  <span>备用模型：</span>
                  <Tag color={snapshot.fallback ? 'orange' : 'default'} style={{ margin: 0 }}>
                    {snapshot.fallback || '未设置'}
                  </Tag>
                  {snapshot.usedFallback && (
                    <Tag color="orange" style={{ margin: 0 }}>
                      主模型失败，已换用备用模型
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
            {job.opinion_digest && (
              <div style={{ marginTop: 6, fontSize: 13, color: '#5A6472' }}>
                <span>本次按意见库汇总生成：</span>
                <Tooltip title={job.opinion_digest.digest_preview || '汇总内容为空'}>
                  <Tag
                    color={job.opinion_digest.status === 'fallback' ? 'orange' : 'purple'}
                    style={{ marginInlineEnd: 6 }}
                  >
                    {job.opinion_digest.item_count} 条历史意见 ·{' '}
                    {job.opinion_digest.status === 'fallback' ? '原始意见汇总' : 'AI 已归纳'}
                  </Tag>
                </Tooltip>
              </div>
            )}
          </div>

          <Space wrap size={8} style={{ alignItems: 'flex-start' }}>
            <Tooltip title={docReady ? '下载生成好的 Word 文档' : '生成完成后才能下载'}>
              <span>
                <Button
                  icon={<DownloadOutlined />}
                  disabled={!docReady}
                  loading={downloading}
                  onClick={() => void handleDownload()}
                >
                  下载 Word 文档
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="查看 AI 初稿、在线编辑与人工上传的历史版本，可回滚">
              <span>
                <Button icon={<HistoryOutlined />} disabled={!docReady} onClick={() => setVersionsOpen(true)}>
                  版本
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="会重新跑一次生成并生成新文档；人工修改过的位置会保留人工写法，AI 不会覆盖">
              <Button icon={<ReloadOutlined />} loading={regenerating} onClick={handleRegenerate}>
                重新生成
              </Button>
            </Tooltip>
            <Tooltip title="看 AI 每一步在做什么">
              <Button icon={<UnorderedListOutlined />} onClick={openTrace}>
                生成过程
              </Button>
            </Tooltip>
            {running && (
              <Button danger icon={<StopOutlined />} loading={cancelling} onClick={handleCancel}>
                停止生成
              </Button>
            )}
          </Space>
        </div>

        {failure && (
          <Alert
            type="error"
            showIcon
            style={{ marginTop: 16 }}
            message={failure.title}
            description={
              <div>
                <ul style={{ margin: '4px 0 8px', paddingLeft: 18 }}>
                  {failure.suggestions.map((item) => (
                    <li key={item} style={{ fontSize: 13 }}>{item}</li>
                  ))}
                </ul>
                <Collapse
                  size="small"
                  ghost
                  items={[
                    {
                      key: 'raw',
                      label: <span style={{ fontSize: 12 }}>原始错误信息（报障时用）</span>,
                      children: (
                        <div style={{ fontSize: 12, color: '#5A6472', whiteSpace: 'pre-wrap' }}>
                          {job.error_message || '没有拿到具体原因'}
                        </div>
                      ),
                    },
                  ]}
                />
              </div>
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

      <Card
        styles={{ body: { padding: 0 } }}
        style={{ borderRadius: 12, overflow: 'hidden', boxShadow: '0 2px 12px rgba(31, 35, 41, 0.06)' }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            height: 'min(760px, 76vh)',
            minHeight: 520,
          }}
        >
          <div
            style={{
              flex: '1 1 620px',
              minWidth: 0,
              height: '100%',
              borderRight: '1px solid #EDEFF2',
            }}
          >
            {docReady ? (
              <ReportGenPreviewPane
                jobId={jobId}
                data={outline}
                hasDocument={job.has_document}
                selectedKey={selectedKey}
                documentVersion={documentVersion}
                onSelect={handleSelectField}
              />
            ) : (
              <ReportGenProgressStage job={job} running={running} onOpenTrace={openTrace} />
            )}
          </div>
          <div
            style={{
              position: 'relative',
              flex: '0 1 430px',
              minWidth: 340,
              height: '100%',
              background: '#FFFFFF',
            }}
          >
            {/* 清单常驻不卸载：编辑某一处时不丢它的滚动位置与筛选条件 */}
            <Tabs
              size="small"
              activeKey={rightTab}
              onChange={(key) => setRightTab(key as 'fields' | 'references')}
              style={{ height: '100%' }}
              styles={{
                root: { height: '100%', display: 'flex', flexDirection: 'column' },
                header: { margin: 0, paddingLeft: 8 },
                body: { flex: 1, minHeight: 0 },
                content: { height: '100%' },
              }}
              items={[
                {
                  key: 'fields',
                  label: '填写清单',
                  children: (
                    <div style={{ height: '100%', minHeight: 0 }}>
                      <ReportGenFieldPanel
                        data={outline}
                        loading={outlineLoading}
                        error={outlineError instanceof Error ? outlineError : null}
                        selectedKey={selectedKey}
                        onSelect={handleSelectField}
                      />
                    </div>
                  ),
                },
                {
                  key: 'references',
                  label: `参考资料 ${outline?.references?.length ?? 0}`,
                  children: (
                    <div style={{ height: '100%', minHeight: 0 }}>
                      <ReportGenReferencePanel
                        data={outline}
                        loading={outlineLoading}
                        onLocate={handleLocateKey}
                      />
                    </div>
                  ),
                },
              ]}
            />
            {/* 编辑卡只在右栏这一格里浮起：预览与页面其余部分照常可见可点，
                也不像整屏抽屉那样盖住右栏、锁死滚动。 */}
            {editing && selectedItem && (
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  zIndex: 2,
                  display: 'flex',
                  flexDirection: 'column',
                  background: '#FFFFFF',
                  borderLeft: '1px solid #EDEFF2',
                }}
              >
                <ReportGenSlotEditor
                  key={selectedItem.key}
                  jobId={jobId}
                  item={selectedItem}
                  baseVersionId={currentVersionId}
                  onBack={closeEditor}
                  onSaved={handleContentSaved}
                />
              </div>
            )}
          </div>
        </div>
      </Card>

      <ReportGenFeedbackPanel jobId={jobId} disabled={running} />

      <Drawer
        open={traceOpen}
        onClose={() => setTraceOpen(false)}
        title="生成过程"
        width="min(560px, 92vw)"
        destroyOnClose
        styles={{ body: { padding: '8px 20px 20px', display: 'flex', flexDirection: 'column' } }}
      >
        <div style={{ flex: 1, minHeight: 0 }}>
          <ReportGenStepTimeline jobId={jobId} running={running} maxItems={400} autoScroll />
        </div>
      </Drawer>

      <ReportGenVersionList
        jobId={jobId}
        open={versionsOpen}
        currentVersionId={currentVersionId}
        onClose={() => setVersionsOpen(false)}
        onRestored={handleContentSaved}
      />
    </div>
  )
}