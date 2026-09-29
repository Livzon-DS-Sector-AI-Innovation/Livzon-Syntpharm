'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Form,
  Input,
  Modal,
  Progress,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from 'antd'
import {
  CheckCircleOutlined,
  CloudUploadOutlined,
  CloseCircleOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileTextOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UndoOutlined,
} from '@ant-design/icons'
import { renderAsync } from 'docx-preview'
import {
  createDocGenJob,
  downloadDeliverableTemplate,
  downloadDocGenDocument,
  fetchDocGenDocumentBlob,
  fetchDocGenExtractedInfo,
  fetchDocGenJob,
  fetchDocGenJobsForReport,
  fetchDocGenKbCoverage,
  fetchUsableDocGenTemplates,
  type DocGenExtractedSlot,
  type DocGenJobResponse,
  type DocGenKbCoverage,
  type DocGenUsableTemplate,
} from '@/lib/api/client/research/doc-gen'
import { updateReport } from '@/lib/api/client/research/rd-project'
import { cancelDocGenJob, confirmDocGenJob, extractDocGenJob, updateDocGenJob } from '@/actions/research/doc-gen'
import {
  DOC_GEN_STATUS_COLORS,
  DOC_GEN_STATUS_LABELS,
  isDocGenCompleted,
  isDocGenTerminal,
} from '@/types/research/doc-gen'
import {
  REPORT_TYPE_LABELS,
  STAGE_LABELS,
} from '@/types/research/rd-project'
import { DocGenSlotEditor } from './DocGenSlotEditor'
import { KnowledgeBaseModal } from './KnowledgeBaseModal'
import { summarizeKb, useKbDocuments, useKnowledgeBase } from './useKnowledgeBase'
import { fetchKbDocuments, fetchKnowledgeBasesByProject } from '@/lib/api/client/research/knowledge-base'

const { Text } = Typography

type Phase = 'form' | 'extracting' | 'review' | 'generating' | 'completed'

/** 报告新建/编辑表单值（validateFields 返回值） */
interface ReportFormValues {
  title: string
  report_type: string
  stage?: string
  version: string
  doc_code?: string
  drug_name?: string
  summary?: string
  supplement?: string
  template_id: string
}

interface Props {
  open: boolean
  projectId: string
  onCancel: () => void
  onCreated?: () => void
  /** 编辑模式：传入已有报告数据 */
  editingReport?: {
    id: string
    title: string
    report_type: string
    stage?: string | null
    version: string
    doc_code?: string | null
    drug_name?: string | null
    summary?: string | null
  } | null
}



export function CreateReportModal({ open, projectId, onCancel, onCreated, editingReport }: Props) {
  const { message: msgApi } = App.useApp()
  const [form] = Form.useForm()
  const isEditMode = !!editingReport

  const [phase, setPhase] = useState<Phase>('form')
  const [templates, setTemplates] = useState<DocGenUsableTemplate[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [job, setJob] = useState<DocGenJobResponse | null>(null)
  const jobIdRef = useRef<string | null>(null)
  // 嵌套「项目知识库」弹窗：建库/上传/看进度都在弹窗内完成，不跳页面
  const [kbModalOpen, setKbModalOpen] = useState(false)
  // 在生成前预检里点过「查看知识库」：关闭弹窗后自动重新预检，用户不必再点一次生成
  const resumeAfterKbRef = useRef(false)

  // 提取结果
  const [extractedSlots, setExtractedSlots] = useState<DocGenExtractedSlot[]>([])
  const [editedSlots, setEditedSlots] = useState<Record<string, string>>({})
  const [extracting, setExtracting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [formReady, setFormReady] = useState(!editingReport) // 编辑模式下等数据加载完再显示表单
  // 弹窗开关时重置表单可见性（官方「渲染期调整状态」模式，避免 effect 内同步 setState）
  const [prevOpen, setPrevOpen] = useState(open)
  if (open !== prevOpen) {
    setPrevOpen(open)
    setFormReady(!isEditMode)
  }

  // 提取结果统计（从 extractedSlots 计算）
  const extractStats = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const slot of extractedSlots) {
      counts[slot.state] = (counts[slot.state] || 0) + 1
    }
    return counts
  }, [extractedSlots])

  // ─── 项目知识库：生成报告的资料来源 ───
  const queryClient = useQueryClient()
  const { data: knowledgeBases = [] } = useKnowledgeBase(projectId, open)
  const kb = useMemo(() => knowledgeBases[0], [knowledgeBases])
  const { data: kbDocuments = [] } = useKbDocuments(kb?.id)
  const kbSummary = useMemo(() => summarizeKb(kbDocuments), [kbDocuments])

  const refreshKb = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['knowledge-bases', projectId] })
    queryClient.invalidateQueries({ queryKey: ['kb-documents', kb?.id] })
  }, [queryClient, projectId, kb?.id])

  // 任务统计里的知识库快照：完成后如实交代「本次基于几份已解析资料」
  const kbStats = (job?.stats ?? {}) as Record<string, unknown>
  const kbStatsParsed = Number(kbStats.kb_documents_parsed ?? 0)
  const kbStatsTotal = Number(kbStats.kb_documents_total ?? 0)
  const kbStatsName = typeof kbStats.kb_name === 'string' ? kbStats.kb_name : ''

  // 覆盖预检快照（A2）：生成前逐项算过「库里有没有料」，完成后据此解释哪些项天生就缺
  const coverageChecked = Number(kbStats.kb_coverage_checked ?? 0)
  const coverageFillable = Number(kbStats.kb_coverage_fillable ?? 0)
  const coveragePartial = Number(kbStats.kb_coverage_partial ?? 0)
  const coverageMissing = Number(kbStats.kb_coverage_missing ?? 0)
  const coverageRatio = Number(kbStats.kb_coverage_ratio ?? 0)
  const coverageMissingLabels = Array.isArray(kbStats.kb_coverage_missing_labels)
    ? kbStats.kb_coverage_missing_labels.filter((label): label is string => typeof label === 'string')
    : []

  /**
   * 生成前预检：知识库缺失、文档未解析、填充项覆盖不足时，让用户明确知情后再继续。
   *
   * 覆盖预检（A2）只做归类不做抽取，回答「这些填充项库里有没有料」：资料齐全且没有
   * 无资料项时直接放行，否则把预计缺口写进确认框——让用户在等十几分钟之前就知道大概
   * 会缺什么。预检本身失败不阻塞生成（它只是提示）。点「查看知识库」会打开嵌套弹窗，
   * 并在关闭后自动重新预检，避免"确认框内容已过期"的误导。
   */
  const confirmBeforeGenerate = async (templateId: string): Promise<boolean> => {
    // 预检必须读实时数据：知识库与文档状态可能刚在弹窗里变过，React Query 缓存未必是最新
    let freshKb = kb
    let docSummary = kbSummary
    try {
      const list = await fetchKnowledgeBasesByProject(projectId)
      freshKb = list[0]
      if (freshKb) docSummary = summarizeKb(await fetchKbDocuments(freshKb.id))
    } catch {
      // 取不到就退回缓存值：后端仍按真实状态执行，这里不阻塞用户
    }
    const supplement = String(form.getFieldValue('supplement') || '').trim()
    const { parsed, pending, failed } = docSummary

    // 有已解析资料时才值得逐项预检（一份都没有时下面的提示更直接）
    let coverage: DocGenKbCoverage | null = null
    if (freshKb && parsed > 0) {
      const hideLoading = msgApi.loading('正在预检知识库覆盖情况…', 0)
      try {
        coverage = await fetchDocGenKbCoverage(templateId, projectId)
      } catch {
        coverage = null // 预检失败只丢提示，生成照常进行
      } finally {
        hideLoading()
      }
    }

    if (freshKb && parsed > 0 && pending === 0 && failed === 0 && (!coverage || coverage.missing === 0)) return true

    const lines: string[] = []
    if (!freshKb) {
      lines.push(
        supplement
          ? '该项目还没有项目知识库，AI 将仅使用项目登记数据与补充信息生成报告。'
          : '该项目还没有项目知识库，且未填写补充信息，生成结果可能大量为「待补充」。',
      )
    } else if (parsed === 0) {
      lines.push('知识库中还没有解析完成的资料，生成结果可能大量为「待补充」。')
    }
    if (pending > 0) {
      lines.push(`还有 ${pending} 份资料正在解析（或排队中），报告只能使用已解析完成的 ${parsed} 份。`)
    }
    if (failed > 0) {
      lines.push(`另有 ${failed} 份资料解析失败，建议先在知识库中重新解析。`)
    }
    if (coverage) {
      if (coverage.missing > 0) {
        lines.push(
          `按模板逐项预检：预计可填 ${coverage.fillable} 项、部分可填 ${coverage.partial} 项、无资料 ${coverage.missing} 项。`,
        )
        const labels = (coverage.slots ?? [])
          .filter((slot) => slot.status === 'no_material')
          .map((slot) => slot.label || slot.key)
        if (labels.length > 0) {
          lines.push(`无资料项：${labels.slice(0, 8).join('、')}${labels.length > 8 ? ' 等' : ''}`)
        }
      } else if (!(coverage.warnings ?? []).length) {
        lines.push(`按模板逐项预检：${coverage.checked} 个填充项都有可参考资料。`)
      }
      // 预检自己的告警（如「尚未建立索引」）：直接呈现，别让用户以为覆盖预检失效了
      lines.push(...(coverage.warnings ?? []))
    }
    return new Promise<boolean>((resolve) => {
      Modal.confirm({
        title: '生成前请确认',
        width: 520,
        content: (
          <div>
            <div style={{ whiteSpace: 'pre-line' }}>{`${lines.join('\n')}\n\n是否继续生成？`}</div>
            <Button
              type="link"
              size="small"
              style={{ paddingLeft: 0, marginTop: 4 }}
              icon={<CloudUploadOutlined />}
              onClick={() => {
                resumeAfterKbRef.current = true
                Modal.destroyAll()
                setKbModalOpen(true)
                resolve(false)
              }}
            >
              {freshKb ? '查看知识库' : '创建知识库并上传资料'}
            </Button>
          </div>
        ),
        okText: '继续生成',
        cancelText: '取消',
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      })
    })
  }

  // 报告预览
  const reportPreviewRef = useRef<HTMLDivElement | null>(null)
  // 预览加载/错误为派生值：previewState 只在异步回调里写入，effect 体不做同步 setState
  const [previewState, setPreviewState] = useState<{ jobId: string; error?: string } | null>(null)
  const activePreviewJobId = job && isDocGenCompleted(job.status) && job.has_document ? job.id : null
  const reportPreviewLoading = activePreviewJobId !== null && previewState?.jobId !== activePreviewJobId
  const reportPreviewError =
    activePreviewJobId !== null && previewState?.jobId === activePreviewJobId && previewState.error
      ? previewState.error
      : null

  // 模板预览
  const [tplPreviewOpen, setTplPreviewOpen] = useState(false)
  const [tplPreviewLoading, setTplPreviewLoading] = useState(false)
  const tplPreviewRef = useRef<HTMLDivElement | null>(null)
  const tplPreviewUrlRef = useRef<string | null>(null)

  // ─── 加载模板与限制 ───
  useEffect(() => {
    if (!open) return
    let cancelled = false
    ;(async () => {
      try {
        const tpl = await fetchUsableDocGenTemplates()
        if (cancelled) return
        setTemplates(tpl)
        // 编辑模式：预填充表单 + 加载关联的 DocGenJob
        if (editingReport) {
          form.setFieldsValue({
            title: editingReport.title,
            report_type: editingReport.report_type,
            stage: editingReport.stage || undefined,
            version: editingReport.version,
            doc_code: editingReport.doc_code || '',
            drug_name: editingReport.drug_name || '',
            summary: editingReport.summary || '',
          })
          // 加载该报告关联的 job（取最新一条）
          const jobs = await fetchDocGenJobsForReport(editingReport.id)
          if (cancelled) return
          if (jobs.length > 0) {
            const latestJob = jobs[0]
            // 获取完整 job 详情（返回 { job, files, slots, sections }）
            const jobDetailResp = await fetchDocGenJob(latestJob.id)
            if (cancelled) return
            const jobData = jobDetailResp.job
            setJob(jobData)
            jobIdRef.current = jobData.id
            // 预填充 job 中的字段
            form.setFieldsValue({
              doc_code: jobData.meta?.doc_code || editingReport.doc_code || '',
              drug_name: jobData.meta?.drug_name || editingReport.drug_name || '',
              version: jobData.meta?.doc_version || editingReport.version,
              supplement: jobData.supplement_text || '',
              // 使用 deliverable_template_id（UUID）而非 template_code（字符串代码）
              template_id: (jobData.meta?.deliverable_template_id as string) || undefined,
            })
            // 根据 job 状态设置 phase（如果还在进行中，显示进度页）
            if (!cancelled) {
              if (jobData.status === 'awaiting_review') {
                setPhase('review')
              } else if (isDocGenCompleted(jobData.status)) {
                setPhase('completed')
              } else if (!isDocGenTerminal(jobData.status)) {
                // 进行中状态（pending/processing 等）→ 显示提取进度页
                setPhase('extracting')
              } else {
                // failed/cancelled → 也显示 extracting 阶段（会显示错误/取消状态）
                setPhase('extracting')
              }
            }
          }
          // 数据加载完毕，显示表单
          if (!cancelled) setFormReady(true)
        }
      } catch {
        if (!cancelled) {
          msgApi.error('加载模板配置失败')
          setFormReady(true) // 出错也要显示表单
        }
      }
    })()
    return () => { cancelled = true }
  }, [open]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 轮询任务状态 ───
  useEffect(() => {
    if (!jobIdRef.current) return
    if (isDocGenTerminal(job?.status ?? '')) return
    if (job?.status === 'awaiting_review') return
    if (isDocGenCompleted(job?.status ?? '')) return
    const timer = setInterval(async () => {
      try {
        const detail = await fetchDocGenJob(jobIdRef.current!)
        setJob(detail.job)
      } catch { /* 轮询瞬时失败忽略 */ }
    }, 3000)
    return () => clearInterval(timer)
  }, [job?.status])

  // job 状态 → phase 迁移（渲染期调整状态，避免 effect 内同步 setState 触发级联渲染）
  const [prevJobStatus, setPrevJobStatus] = useState(job?.status)
  if (job?.status !== prevJobStatus) {
    setPrevJobStatus(job?.status)
    if (job?.status === 'awaiting_review') setPhase('review')
    else if (job && isDocGenCompleted(job.status)) setPhase('completed')
  }

  // 进入待确认 → 加载提取结果（数据加载副作用，状态迁移见上方渲染期调整）
  useEffect(() => {
    if (job?.status === 'awaiting_review') loadExtractedInfo()
  }, [job?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // 提取失败/取消 → 显示错误提示
  useEffect(() => {
    if (job?.status === 'failed' && phase === 'extracting') {
      msgApi.error(job.error_message || '提取失败，请重试')
    }
    if (job?.status === 'cancelled' && phase === 'extracting') {
      msgApi.info('已取消提取')
    }
  }, [job?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // 加载提取信息
  const loadExtractedInfo = async () => {
    if (!jobIdRef.current) return
    setExtracting(true)
    try {
      const res = await fetchDocGenExtractedInfo(jobIdRef.current)
      setExtractedSlots(res.slots)
    } catch (e: unknown) {
      msgApi.error('加载提取信息失败：' + (e instanceof Error ? e.message : ''))
    } finally {
      setExtracting(false)
    }
  }

  // 加载报告预览
  useEffect(() => {
    if (!job || !activePreviewJobId) return
    const jobId = job.id
    let cancelled = false
    ;(async () => {
      try {
        const blob = await fetchDocGenDocumentBlob(jobId)
        if (cancelled || !reportPreviewRef.current) return
        reportPreviewRef.current.innerHTML = ''
        await renderAsync(blob, reportPreviewRef.current, undefined, { inWrapper: true, ignoreWidth: true })
        if (!cancelled) setPreviewState({ jobId })
      } catch (e) {
        if (!cancelled) setPreviewState({ jobId, error: e instanceof Error ? e.message : '预览失败' })
      }
    })()
    return () => { cancelled = true }
  }, [activePreviewJobId]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 模板预览 ───
  const openTplPreview = async (tplId: string) => {
    setTplPreviewOpen(true)
    setTplPreviewLoading(true)
    if (tplPreviewUrlRef.current) { URL.revokeObjectURL(tplPreviewUrlRef.current); tplPreviewUrlRef.current = null }
    try {
      const blob = await downloadDeliverableTemplate(tplId)
      if (!tplPreviewRef.current) return
      tplPreviewRef.current.innerHTML = ''
      await renderAsync(blob, tplPreviewRef.current, undefined, { inWrapper: true, ignoreWidth: true })
    } catch {
      if (tplPreviewRef.current) tplPreviewRef.current.innerHTML = '<div style="color:red;padding:16px">模板预览加载失败</div>'
    } finally { setTplPreviewLoading(false) }
  }

  const closeTplPreview = () => {
    setTplPreviewOpen(false)
    if (tplPreviewUrlRef.current) { URL.revokeObjectURL(tplPreviewUrlRef.current); tplPreviewUrlRef.current = null }
  }

  /**
   * AI 生成报告（新流程）：资料来自项目知识库，不再上传任务级文件、不再有人工提取步骤。
   *
   * 直达生成模式（DOC_GEN_CHAT_ENABLED=false）下任务创建即 pending，worker 一次跑完
   * 「模板分析 → 知识库逐填充项检索取值 → 证据回检 → 成文 → 渲染」；
   * 若运行时仍开着对话复核，则显式触发一次提取以保持兼容。
   */
  const handleCreateAndGenerate = async () => {
    const templateId = form.getFieldValue('template_id')
    if (!templateId) {
      msgApi.warning('请先选择模板')
      return
    }
    const proceed = await confirmBeforeGenerate(templateId)
    if (!proceed) return

    setPhase('extracting')
    setSubmitting(true)
    try {
      let currentJob = job
      // 已终止/已完成的任务无法续跑，必须新建
      const needsNewJob = !currentJob || currentJob.status === 'cancelled' || currentJob.status === 'completed'

      if (needsNewJob) {
        const values = form.getFieldsValue()
        const created = await createDocGenJob({
          templateId,
          docCode: values.doc_code || values.title,
          docVersion: values.version || 'v1.0',
          drugName: values.drug_name || values.title,
          supplementText: values.supplement?.trim() || undefined,
          // 资料统一进项目知识库：新流程不再携带任务级文件
          files: [],
          fileRoles: [],
          projectId,
          reportId: editingReport?.id,
          reportTitle: values.title,
          reportType: values.report_type,
          reportStage: values.stage || undefined,
          reportSummary: values.summary?.trim() || undefined,
        })
        currentJob = created
        setJob(created)
        jobIdRef.current = created.id
      }

      if (!currentJob) return

      if (['draft', 'failed', 'awaiting_review'].includes(currentJob.status)) {
        try {
          const started = await extractDocGenJob(currentJob.id)
          setJob(started)
        } catch (extractErr) {
          // 触发失败时刷新 job 状态，给用户准确提示而非空白页
          try {
            const fresh = await fetchDocGenJob(currentJob.id)
            setJob(fresh.job)
          } catch { /* 忽略 */ }
          throw extractErr
        }
      }

      onCreated?.()
      msgApi.success('已开始生成报告')
    } catch (e) {
      console.error('[CreateReportModal] 生成报告失败:', e)
      msgApi.error(e instanceof Error ? e.message : '生成报告失败')
      // 不自动切回表单，保留在进度视图让用户看到错误状态并自行操作
    } finally {
      setSubmitting(false)
    }
  }

  // ─── 保存/创建（新建报告时创建 job + RdReport，编辑报告时更新 job + RdReport） ───
  const handleSave = async () => {
    let values: ReportFormValues
    try {
      values = await form.validateFields()
    } catch {
      return // 表单校验未通过，antd 自动显示错误提示
    }
    setSaving(true)
    try {
      // 编辑模式：先更新 RdReport（包含摘要）
      if (editingReport) {
        await updateReport(editingReport.id, {
          title: values.title,
          report_type: values.report_type,
          stage: values.stage || null,
          version: values.version,
          summary: values.summary?.trim() || null,
        })
      }

      if (job) {
        // 编辑模式且有 job：更新 job 信息（包含模板）
        await updateDocGenJob(job.id, {
          doc_code: values.doc_code || null,
          doc_version: values.version || null,
          drug_name: values.drug_name || null,
          supplement_text: values.supplement || null,
          template_code: values.template_id || null,
        })
        msgApi.success('已保存')
        onCreated?.() // 刷新列表
        handleClose() // 关闭弹窗
      } else if (editingReport) {
        // 编辑模式但无 job：如果选择了模板则创建 job，否则只保存报告
        if (values.template_id) {
          const created = await createDocGenJob({
            templateId: values.template_id,
            docCode: values.doc_code || values.title,
            docVersion: values.version || 'v1.0',
            drugName: values.drug_name || values.title,
            supplementText: values.supplement?.trim() || undefined,
            // 资料统一进项目知识库：不再携带任务级文件
            files: [],
            fileRoles: [],
            projectId,
            reportId: editingReport.id, // 关联已有报告
            reportTitle: values.title,
            reportType: values.report_type,
            reportStage: values.stage || undefined,
            reportSummary: values.summary?.trim() || undefined,
          })
          setJob(created)
          jobIdRef.current = created.id
        }
        msgApi.success('已保存')
        onCreated?.() // 刷新列表
        handleClose() // 关闭弹窗
      } else {
        // 新建模式：创建 job（后端同步创建 RdReport，使报告列表可见）
        const created = await createDocGenJob({
          templateId: values.template_id,
          docCode: values.doc_code || values.title,
          docVersion: values.version || 'v1.0',
          drugName: values.drug_name || values.title,
          supplementText: values.supplement?.trim() || undefined,
          // 资料统一进项目知识库：不再携带任务级文件
          files: [],
          fileRoles: [],
          projectId,
          reportTitle: values.title,
          reportType: values.report_type,
          reportStage: values.stage || undefined,
          reportSummary: values.summary?.trim() || undefined,
        })
        setJob(created)
        jobIdRef.current = created.id
        msgApi.success('已创建')
        onCreated?.()
        handleClose()
      }
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : (job ? '保存失败' : '创建失败'))
    } finally { setSaving(false) }
  }

  // ─── 确认提取结果 → 开始生成报告 ───
  const handleConfirmAndGenerate = async () => {
    if (!job) return
    // 立即切换到生成中界面
    setPhase('generating')
    setConfirming(true)
    try {
      const confirmed = await confirmDocGenJob(job.id, editedSlots)
      setJob(confirmed)
      msgApi.success('已确认，正在生成报告')
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '确认失败')
      // 失败时切回 review
      setPhase('review')
    } finally { setConfirming(false) }
  }

  // ─── 重新提取 ───
  const handleReExtract = async () => {
    if (!job) return
    try {
      // 直接调用后端原地重新提取，保留已上传的文件
      const started = await extractDocGenJob(job.id)
      setJob(started)
      setExtractedSlots([]); setEditedSlots({})
      setPhase('extracting')
      msgApi.success('正在重新提取信息')
    } catch (e) {
      console.error('[CreateReportModal] 重新提取失败:', e)
      msgApi.error(e instanceof Error ? e.message : '重新提取失败')
    }
  }

  // ─── 返回修改（清空任务状态，回到表单重新开始） ───
  const handleBackToForm = () => {
    setJob(null); jobIdRef.current = null
    setExtractedSlots([]); setEditedSlots({})
    setPreviewState(null)
    setPhase('form')
  }

  // ─── 终止提取流程 ───
  const handleCancelJob = async () => {
    if (!job) return
    Modal.confirm({
      title: '确认终止',
      content: '终止后当前提取进度将丢失，需要重新开始。确定要终止吗？',
      okText: '终止',
      okType: 'danger',
      cancelText: '继续',
      onOk: async () => {
        setCancelling(true)
        try {
          await cancelDocGenJob(job.id)
          setJob(null); jobIdRef.current = null
          setExtractedSlots([]); setEditedSlots({})
          msgApi.success('已终止')
          // 返回表单，保留已上传的文件
          setPhase('form')
        } catch (e) {
          msgApi.error(e instanceof Error ? e.message : '终止失败')
        } finally {
          setCancelling(false)
        }
      },
    })
  }

  // ─── 重新生成 ───
  const handleRegenerate = () => {
    setJob(null); jobIdRef.current = null
    setExtractedSlots([]); setEditedSlots({})
    setPreviewState(null)
    setPhase('form')
  }

  // ─── 下载报告 ───
  const handleDownload = async () => {
    if (!job) return
    try {
      const res = await fetch(`${`/api/v1/research/doc-gen/jobs/${job.id}/document`}`, { cache: 'no-store' })
      if (!res.ok) throw new Error('下载失败')
      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${form.getFieldValue('title') || 'report'}.docx`
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      window.URL.revokeObjectURL(url)
    } catch (e) {
      msgApi.error(e instanceof Error ? e.message : '下载报告失败')
    }
  }

  // ─── 关闭弹窗 ───
  const handleClose = () => {
    form.resetFields(); setJob(null); jobIdRef.current = null
    setPhase('form'); setExtractedSlots([]); setEditedSlots({})
    setPreviewState(null); setFormReady(!editingReport)
    onCancel()
  }

  // 注：任务级资料上传已随新流程移除，资料统一在项目知识库里管理（KnowledgeBaseModal）

  const selectedTplId = Form.useWatch('template_id', form) as string | undefined
  const selectedTpl = templates.find((t) => t.id === selectedTplId)

  // ─── 弹窗底部按钮 ───
  const renderFooter = () => {
    switch (phase) {
      case 'form':
        if (isEditMode) {
          // 编辑模式：保存 + AI 创建报告
          return [
            <Button key="cancel" onClick={handleClose}>取消</Button>,
            <Button key="save" onClick={handleSave} loading={saving}>保存</Button>,
            <Button
              key="generate"
              type="primary"
              icon={<ThunderboltOutlined />}
              onClick={handleCreateAndGenerate}
              loading={submitting}
            >
              AI 生成报告
            </Button>,
          ]
        }
        // 新建模式：创建 + AI 创建报告
        return [
          <Button key="cancel" onClick={handleClose}>取消</Button>,
          <Button key="create" onClick={handleSave} loading={saving}>创建</Button>,
          <Button
            key="ai-generate"
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleCreateAndGenerate}
            loading={submitting}
          >
            AI 生成报告
          </Button>,
        ]
      case 'extracting': {
        const isTerminal = isDocGenTerminal(job?.status ?? '')
        const buttons: React.ReactNode[] = []
        // job 创建失败（无 job 且不在提交中）→ 显示返回修改按钮
        if (!job && !submitting) {
          buttons.push(
            <Button key="back" type="primary" icon={<UndoOutlined />} onClick={handleBackToForm}>
              返回修改
            </Button>
          )
        }
        // 失败时显示重新提取
        if (job?.status === 'failed') {
          buttons.push(
            <Button key="retry" type="primary" icon={<ReloadOutlined />} onClick={handleReExtract}>
              重新提取
            </Button>
          )
        }
        // 取消时显示返回修改
        if (job?.status === 'cancelled') {
          buttons.push(
            <Button key="back" icon={<UndoOutlined />} onClick={handleBackToForm}>
              返回修改
            </Button>
          )
        }
        // 进行中时显示终止按钮
        if (!isTerminal && job) {
          buttons.push(
            <Button key="cancel" danger onClick={handleCancelJob} loading={cancelling}>
              终止流程
            </Button>
          )
        }
        buttons.push(<Button key="close" onClick={handleClose}>关闭</Button>)
        return buttons
      }
      case 'review':
        return [
          <Button key="cancel" onClick={handleClose}>取消</Button>,
          <Button key="save" onClick={handleSave} loading={saving}>
            保存
          </Button>,
          <Button
            key="generate"
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleConfirmAndGenerate}
            loading={confirming}
          >
            AI 创建报告
          </Button>,
        ]
      case 'generating':
        return [<Button key="close" onClick={handleClose}>关闭</Button>]
      case 'completed':
        return [
          <Button key="close" onClick={handleClose}>关闭</Button>,
          <Button key="back" icon={<UndoOutlined />} onClick={handleBackToForm}>返回修改</Button>,
          <Button key="regen" icon={<ReloadOutlined />} onClick={handleRegenerate}>重新生成</Button>,
          <Button key="download" type="primary" icon={<DownloadOutlined />} onClick={handleDownload}>
            下载文档出版
          </Button>,
        ]
    }
  }

  return (
    <Modal
      title={isEditMode ? '编辑报告' : '新建报告'}
      open={open}
      onCancel={handleClose}
      width={960}
      centered
      destroyOnClose
      footer={renderFooter()}
    >
      {/* ═══ Phase 1: 表单 ═══ */}
      {phase === 'form' && !formReady && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}><Text type="secondary">加载数据中...</Text></div>
        </div>
      )}
      {phase === 'form' && formReady && (
        <Form form={form} layout="vertical" initialValues={{ report_type: 'summary', version: 'v1.0' }}>
          {/* 第一行：报告标题 */}
          <Form.Item name="title" label="报告标题" rules={[{ required: true, message: '请输入报告标题' }]}>
            <Input placeholder="如：化合物A研发总结报告" />
          </Form.Item>

          {/* 第二行：报告类型 / 关联阶段 / 版本号 */}
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="report_type" label="报告类型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select
                options={Object.entries(REPORT_TYPE_LABELS).map(([value, label]) => ({ value, label }))}
              />
            </Form.Item>
            <Form.Item name="stage" label="关联阶段" style={{ flex: 1 }}>
              <Select
                options={[{ value: '', label: '无' }, ...Object.entries(STAGE_LABELS).map(([value, label]) => ({ value, label }))]}
                allowClear
              />
            </Form.Item>
            <Form.Item name="version" label="版本号" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input placeholder="如：v1.0" />
            </Form.Item>
          </div>

          {/* 第三行：受控编码 / 品种名称 */}
          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="doc_code" label="受控编码" style={{ flex: 1 }}>
              <Input placeholder="如：RD-2024-001" />
            </Form.Item>
            <Form.Item name="drug_name" label="品种名称" style={{ flex: 1 }}>
              <Input placeholder="如：化合物A" />
            </Form.Item>
          </div>

          {/* 第四行：模板选择 */}
          <Form.Item name="template_id" label="模板选择">
            <Select
              placeholder="选择交付物模板"
              showSearch
              optionFilterProp="label"
              options={templates.map((t) => ({
                value: t.id,
                label: `${t.name}（${t.slot_count} 处可自动填充）`,
              }))}
            />
          </Form.Item>
          {selectedTpl && (
            <div style={{ marginTop: -16, marginBottom: 16, padding: '12px 16px', background: '#f6ffed', borderRadius: 6, border: '1px solid #b7eb8f' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>
                    {selectedTpl.name}
                    <Tag color="green" style={{ marginLeft: 8 }}>v{selectedTpl.template_version}</Tag>
                    <Tag color="blue" style={{ marginLeft: 4 }}>{selectedTpl.stage}</Tag>
                  </div>
                  {selectedTpl.description && (
                    <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>{selectedTpl.description}</div>
                  )}
                  <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#8c8c8c' }}>
                    <span>共 {selectedTpl.slot_count} 个填充项</span>
                    <span>必填 {selectedTpl.required_count} 个</span>
                    {selectedTpl.unfilled_notes && selectedTpl.unfilled_notes.length > 0 && (
                      <span style={{ color: '#faad14' }}>⚠ {selectedTpl.unfilled_notes.length} 项需人工补充</span>
                    )}
                  </div>
                </div>
                <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openTplPreview(selectedTpl.id)}>
                  预览模板
                </Button>
              </div>
            </div>
          )}

          {/* 第四行：项目知识库（AI 生成报告的资料源；建库/上传/看进度都在弹窗内完成，不跳页面） */}
          <Form.Item label="项目知识库">
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 12,
                padding: '10px 12px',
                border: '1px solid #d9d9d9',
                borderRadius: 6,
                background: '#fafafa',
              }}
            >
              <div style={{ fontSize: 13, color: '#595959' }}>
                {kb ? (
                  <Space size={8} wrap>
                    <span>
                      已关联知识库 <b>{kb.name}</b>
                    </span>
                    <Tag color="success">已解析 {kbSummary.parsed}</Tag>
                    {kbSummary.pending > 0 ? <Tag color="processing">解析中 {kbSummary.pending}</Tag> : null}
                    {kbSummary.failed > 0 ? <Tag color="error">失败 {kbSummary.failed}</Tag> : null}
                    <span style={{ color: '#8c8c8c' }}>共 {kbSummary.total || kb.document_count} 份资料</span>
                  </Space>
                ) : (
                  '该项目还没有项目知识库。AI 将仅使用项目登记数据与补充信息生成报告；建议先上传项目资料到知识库。'
                )}
              </div>
              <Button htmlType="button" icon={<CloudUploadOutlined />} onClick={() => setKbModalOpen(true)}>
                {kb ? '上传 / 管理资料' : '创建知识库并上传资料'}
              </Button>
            </div>
          </Form.Item>

          {/* 第五行：摘要 */}
          <Form.Item name="summary" label="摘要">
            <Input.TextArea rows={2} placeholder="简要描述本报告内容..." />
          </Form.Item>

          {/* 第六行：补充信息 */}
          <Form.Item name="supplement" label="补充信息">
            <Input.TextArea rows={3} placeholder="补充说明信息，AI 生成时将一并参考..." />
          </Form.Item>
        </Form>
      )}

      {/* ═══ Phase 2: AI 生成中（从项目知识库检索并按模板填充）═══ */}
      {phase === 'extracting' && (
        <div style={{ padding: '40px 24px' }}>
          <div style={{ textAlign: 'center', marginBottom: 16, color: '#595959' }}>
            AI 正在从项目知识库检索资料并填充模板，请稍候…
          </div>
          {/* 进度条 */}
          <div style={{ marginBottom: 24 }}>
            <Progress
              percent={job?.progress ?? 0}
              status={
                job?.status === 'failed' ? 'exception' :
                job?.status === 'cancelled' ? 'normal' :
                'active'
              }
              strokeColor={
                job?.status === 'cancelled' ? '#d9d9d9' :
                { from: '#108ee9', to: '#87d068' }
              }
            />
          </div>

          {/* 状态与步骤 */}
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            {/* job 尚未创建 */}
            {!job && submitting && (
              <div style={{ padding: '24px 0' }}>
                <Spin size="large" />
                <div style={{ marginTop: 16, fontSize: 15, color: '#595959' }}>
                  正在创建提取任务...
                </div>
              </div>
            )}
            {/* job 创建失败 */}
            {!job && !submitting && (
              <Alert
                type="error"
                showIcon
                message="任务创建失败"
                description="提取任务创建失败，请检查填写信息后重试。"
                style={{ textAlign: 'left', marginBottom: 16 }}
              />
            )}

            <div style={{ marginBottom: 12 }}>
              {job && (
                <Tag
                  color={DOC_GEN_STATUS_COLORS[job.status] || 'default'}
                  style={{ fontSize: 14, padding: '4px 12px' }}
                >
                  {DOC_GEN_STATUS_LABELS[job.status] || job.status}
                </Tag>
              )}
            </div>

            {/* 失败状态显示错误信息 */}
            {job?.status === 'failed' && (
              <Alert
                type="error"
                showIcon
                message="提取失败"
                description={job.error_message || '处理过程中出现错误，请重试'}
                style={{ textAlign: 'left', marginBottom: 16 }}
              />
            )}

            {/* 取消状态 */}
            {job?.status === 'cancelled' && (
              <Alert
                type="warning"
                showIcon
                message="已取消"
                description="提取流程已被终止"
                style={{ textAlign: 'left', marginBottom: 16 }}
              />
            )}

            {/* 进行中状态显示步骤 */}
            {job?.step && !isDocGenTerminal(job.status) && (
              <div style={{ fontSize: 15, color: '#595959' }}>
                <Spin size="small" style={{ marginRight: 8 }} />
                {job.step}
              </div>
            )}

            {/* 文件解析进度列表 */}
            {job?.status === 'parsing' && Array.isArray(job.meta?.parse_progress) && job.meta.parse_progress.length > 0 && (
              <div style={{ marginTop: 16, padding: '12px 16px', background: '#fafafa', borderRadius: 8, border: '1px solid #f0f0f0' }}>
                <div style={{ fontSize: 13, color: '#595959', marginBottom: 8, fontWeight: 500 }}>文件解析进度</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {job.meta.parse_progress.map((item: { name: string; status: string }, idx: number) => {
                    const statusConfig: Record<string, { icon: React.ReactNode; color: string; text: string }> = {
                      done: { icon: <CheckCircleOutlined style={{ color: '#52c41a' }} />, color: '#52c41a', text: '解析成功' },
                      failed: { icon: <CloseCircleOutlined style={{ color: '#ff4d4f' }} />, color: '#ff4d4f', text: '解析失败' },
                      parsing: { icon: <LoadingOutlined style={{ color: '#1677ff' }} spin />, color: '#1677ff', text: '解析中...' },
                      pending: { icon: <MinusCircleOutlined style={{ color: '#d9d9d9' }} />, color: '#8c8c8c', text: '等待解析' },
                    }
                    const config = statusConfig[item.status] || statusConfig.pending
                    return (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 13 }}>
                        <span style={{ color: '#262626', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {item.name}
                        </span>
                        <span style={{ display: 'flex', alignItems: 'center', gap: 4, color: config.color, marginLeft: 12, flexShrink: 0 }}>
                          {config.icon}
                          {config.text}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* 进行中提示 */}
            {!isDocGenTerminal(job?.status ?? '') && (
              <>
                <div style={{ marginTop: 12, fontSize: 13, color: '#8c8c8c' }}>
                  正在使用 AI 读取模板信息并解析上传文件，请耐心等待。
                </div>
                <div style={{ marginTop: 4, fontSize: 13, color: '#faad14' }}>
                  当前所有信息不可编辑，请等待提取完成。
                </div>
              </>
            )}
          </div>

          {/* 操作按钮 */}
          <div style={{ textAlign: 'center' }}>
            <Space size={16}>
              {/* 失败/取消时显示重新提取按钮 */}
              {job?.status === 'failed' && (
                <Button
                  type="primary"
                  icon={<ReloadOutlined />}
                  onClick={handleReExtract}
                  size="large"
                >
                  重新提取
                </Button>
              )}
              {/* 进行中或失败/取消时显示终止按钮 */}
              {!isDocGenTerminal(job?.status ?? '') && (
                <Button
                  danger
                  icon={<CloseCircleOutlined />}
                  onClick={handleCancelJob}
                  loading={cancelling}
                  size="large"
                >
                  终止流程
                </Button>
              )}
              {/* 取消时显示返回按钮 */}
              {job?.status === 'cancelled' && (
                <Button
                  icon={<UndoOutlined />}
                  onClick={handleBackToForm}
                  size="large"
                >
                  返回修改
                </Button>
              )}
            </Space>
          </div>
        </div>
      )}

      {/* ═══ Phase 3: 提取结果展示（可编辑） ═══ */}
      {phase === 'review' && (
        <div>
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            title="信息提取完成，请核对"
            description="以下为 AI 从上传文件中提取的信息，可直接编辑修改。确认无误后点击「AI 创建报告」生成报告。"
          />
          {/* 模板信息卡片 */}
          {(() => {
            const tpl = templates.find((t) => t.template_code === job?.template_code)
            if (!tpl && !job?.template_code) return null
            return (
              <div style={{ marginBottom: 16, padding: '12px 16px', background: '#f9f0ff', borderRadius: 6, border: '1px solid #d3adf7' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500, fontSize: 14, marginBottom: 6 }}>
                      <FileTextOutlined style={{ marginRight: 6, color: '#722ed1' }} />
                      {tpl ? tpl.name : job?.template_code}
                      <Tag color="purple" style={{ marginLeft: 8 }}>v{tpl?.template_version || job?.template_version}</Tag>
                      {tpl?.stage && <Tag color="cyan" style={{ marginLeft: 4 }}>{tpl.stage}</Tag>}
                    </div>
                    {tpl?.description && (
                      <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>{tpl.description}</div>
                    )}
                    <div style={{ display: 'flex', gap: 16, fontSize: 12, color: '#8c8c8c' }}>
                      {tpl && (
                        <>
                          <span>填充项 {tpl.slot_count} 个</span>
                          <span>必填 {tpl.required_count} 个</span>
                        </>
                      )}
                      {typeof job?.stats?.extract_duration_seconds === 'number' && (
                        <span>提取耗时 {job.stats.extract_duration_seconds} 秒</span>
                      )}
                    </div>
                  </div>
                  {tpl && (
                    <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => openTplPreview(tpl.id)}>
                      预览模板
                    </Button>
                  )}
                </div>
              </div>
            )
          })()}
          {/* 提取内容总述 */}
          {extractedSlots.length > 0 && (
            <div style={{ marginBottom: 16, padding: '12px 16px', background: '#fafafa', borderRadius: 6, border: '1px solid #f0f0f0' }}>
              <div style={{ marginBottom: 8, fontWeight: 500, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span>提取结果统计</span>
              </div>
              {/* 提取到的文本内容 */}
              <div style={{ maxHeight: 200, overflow: 'auto', marginBottom: 8 }}>
                {extractedSlots
                  .filter(slot => slot.text && slot.text.trim() && !slot.text.startsWith('[待补充'))
                  .map(slot => (
                    <div key={slot.slot_key} style={{ marginBottom: 8, padding: '8px 12px', background: '#fff', borderRadius: 4, border: '1px solid #e8e8e8' }}>
                      <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>{slot.label || slot.slot_key}</div>
                      <div style={{ fontSize: 13, color: '#333', lineHeight: 1.6 }}>
                        {slot.text!.length > 200 ? slot.text!.slice(0, 200) + '...' : slot.text}
                      </div>
                    </div>
                  ))}
                {extractedSlots.filter(slot => slot.text && slot.text.trim() && !slot.text.startsWith('[待补充')).length === 0 && (
                  <div style={{ color: '#999', textAlign: 'center', padding: 16 }}>暂无提取到的有效内容</div>
                )}
              </div>
              {/* 统计标签 */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, borderTop: '1px solid #e8e8e8', paddingTop: 8 }}>
                <Tag color="default">共 {extractedSlots.length} 项</Tag>
                {extractStats['ok'] > 0 && <Tag color="success">已填充 {extractStats['ok']}</Tag>}
                {extractStats['ai_draft'] > 0 && <Tag color="blue">AI草稿 {extractStats['ai_draft']}</Tag>}
                {extractStats['needs_verify'] > 0 && <Tag color="gold">需核对 {extractStats['needs_verify']}</Tag>}
                {extractStats['pending'] > 0 && <Tag color="warning">待补充 {extractStats['pending']}</Tag>}
                {extractStats['manual_only'] > 0 && <Tag color="processing">需人工 {extractStats['manual_only']}</Tag>}
                {extractStats['conflict'] > 0 && <Tag color="orange">来源冲突 {extractStats['conflict']}</Tag>}
                {extractStats['ai_failed'] > 0 && <Tag color="error">提取失败 {extractStats['ai_failed']}</Tag>}
              </div>
            </div>
          )}
          {/* 文件解析状态摘要 */}
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
            <Button icon={<ReloadOutlined />} onClick={handleReExtract} loading={extracting}>
              重新提取
            </Button>
          </div>
          {extracting ? (
            <div style={{ textAlign: 'center', padding: '32px 0' }}><Spin /></div>
          ) : (
            <div style={{ maxHeight: 480, overflow: 'auto' }}>
              <DocGenSlotEditor
                slots={extractedSlots}
                editedSlots={editedSlots}
                onEditedSlotsChange={setEditedSlots}
              />
            </div>
          )}
        </div>
      )}

      {/* ═══ Phase 4: AI 报告生成中 ═══ */}
      {phase === 'generating' && (
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 24, fontSize: 16 }}>
            <Text strong>AI 报告生成中...</Text>
          </div>
          <div style={{ marginTop: 8 }}>
            <Text type="secondary">
              正在使用 Local-DeepSeek-V4-Flash 将提取的信息填入模板并生成出版报告，请耐心等待。
            </Text>
          </div>
          {job && (
            <div style={{ marginTop: 16 }}>
              <Tag color={DOC_GEN_STATUS_COLORS[job.status] || 'default'}>
                {DOC_GEN_STATUS_LABELS[job.status] || job.status}
              </Tag>
              {job.step && <Text type="secondary"> — {job.step}</Text>}
            </div>
          )}
        </div>
      )}

      {/* ═══ Phase 5: 报告生成完成 ═══ */}
      {phase === 'completed' && (
        <div>
          <Alert
            type="success"
            showIcon
            style={{ marginBottom: 16 }}
            title="报告已生成"
            description="AI 生成内容需人工审核确认后方可使用。"
          />
          {/* 资料来源：知识库里未解析完的资料检索不到，这里如实说明参与了哪些 */}
          <div style={{ marginBottom: 16, fontSize: 13, color: '#595959' }}>
            {kbStatsTotal > 0 ? (
              <Space size={8} wrap>
                <span>
                  本次基于项目知识库{kbStatsName ? `「${kbStatsName}」` : ''}中 <b>{kbStatsParsed}</b> 份已解析资料生成
                  {kbStatsTotal > kbStatsParsed ? `（共 ${kbStatsTotal} 份，其余解析中或失败，未参与）` : ''}
                </span>
                <Button type="link" size="small" onClick={() => setKbModalOpen(true)}>
                  查看知识库
                </Button>
              </Space>
            ) : (
              '本次未关联项目知识库：内容来自项目登记数据与补充信息。'
            )}
          </div>
          {/* 覆盖预检：把「哪些项本来就没有资料」说清楚，避免用户以为 AI 漏填了 */}
          {coverageChecked > 0 && (
            <div style={{ marginBottom: 16, fontSize: 13, color: '#595959' }}>
              <div>
                生成前逐项预检：<b>{coverageChecked}</b> 个填充项中，可填 {coverageFillable} 项、部分可填{' '}
                {coveragePartial} 项
                {coverageMissing > 0 ? `、知识库中无资料 ${coverageMissing} 项` : ''}
                （加权覆盖率 {Math.round(coverageRatio * 100)}%）。
              </div>
              {coverageMissingLabels.length > 0 && (
                <div style={{ marginTop: 4 }}>
                  无资料项：{coverageMissingLabels.join('、')}
                  {coverageMissing > coverageMissingLabels.length ? ' 等' : ''}
                  ——生成时无资料可引，报告中以「待补充」呈现，需人工填写。
                </div>
              )}
            </div>
          )}
          {/* 操作按钮 */}
          {job && (
            <div style={{ marginBottom: 16 }}>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={async () => {
                  const filename = `${editingReport?.title || '报告'}.docx`
                  try {
                    await downloadDocGenDocument(job.id, filename)
                    msgApi.success('下载成功')
                  } catch {
                    msgApi.error('下载失败')
                  }
                }}
              >
                下载报告
              </Button>
            </div>
          )}
          {/* 报告预览区域 */}
          <div style={{ marginBottom: 16 }}>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>报告预览</Text>
            {reportPreviewError ? (
              <Alert type="warning" showIcon title="无法在线预览" description={reportPreviewError} />
            ) : (
              <>
                {reportPreviewLoading && (
                  <div style={{ textAlign: 'center', padding: '16px 0' }}>
                    <Spin />
                    <div style={{ marginTop: 8, color: '#787671' }}>正在加载预览...</div>
                  </div>
                )}
                <div
                  ref={reportPreviewRef}
                  style={{ maxHeight: 480, overflow: 'auto', border: '1px solid #d9d9d9', borderRadius: 8, padding: 8 }}
                />
              </>
            )}
          </div>
        </div>
      )}

      {/* ─── 文件预览弹窗 ─── */}
      <KnowledgeBaseModal
        open={kbModalOpen}
        projectId={projectId}
        onChanged={refreshKb}
        onClose={() => {
          setKbModalOpen(false)
          refreshKb()
          // 是从「生成前确认」里点进来的：关闭后自动重跑预检，用户不必再点一次生成
          if (resumeAfterKbRef.current) {
            resumeAfterKbRef.current = false
            void handleCreateAndGenerate()
          }
        }}
      />

      {/* ─── 模板预览弹窗 ─── */}
      <Modal
        open={tplPreviewOpen}
        title="模板预览"
        footer={null}
        width={900}
        onCancel={closeTplPreview}
      >
        {tplPreviewLoading && <div style={{ textAlign: 'center', padding: '16px 0' }}><Spin /></div>}
        <div ref={tplPreviewRef} style={{ maxHeight: '70vh', overflow: 'auto', background: '#f5f5f5', padding: 8 }} />
      </Modal>
    </Modal>
  )
}
