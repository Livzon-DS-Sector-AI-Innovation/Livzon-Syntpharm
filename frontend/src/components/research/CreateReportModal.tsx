'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  App,
  Button,
  Collapse,
  Form,
  Input,
  Modal,
  Progress,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  Upload,
} from 'antd'
import type { UploadFile } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileTextOutlined,
  LoadingOutlined,
  MinusCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
  UndoOutlined,
  UploadOutlined,
} from '@ant-design/icons'
import { renderAsync } from 'docx-preview'
import {
  createDocGenJob,
  downloadDeliverableTemplate,
  downloadDocGenDocument,
  fetchDocGenDocumentBlob,
  fetchDocGenExtractedInfo,
  fetchDocGenInputFileBlob,
  fetchDocGenJob,
  fetchDocGenJobsForReport,
  fetchUsableDocGenTemplates,
  fetchDocGenLimits,
  uploadJobFiles,
  type DocGenExtractedSlot,
  type DocGenFileRole,
  type DocGenInputFileResponse,
  type DocGenJobResponse,
  type DocGenLimits,
  type DocGenUsableTemplate,
} from '@/lib/api/client/research/doc-gen'
import { fetchDeliverableTemplates, updateReport } from '@/lib/api/client/research/rd-project'
import { cancelDocGenJob, confirmDocGenJob, extractDocGenJob, updateDocGenJob } from '@/actions/research/doc-gen'
import {
  DOC_GEN_STATUS_COLORS,
  DOC_GEN_STATUS_LABELS,
  isDocGenCompleted,
  isDocGenTerminal,
  type DocGenFormItem,
} from '@/types/research/doc-gen'
import {
  REPORT_TYPE_LABELS,
  STAGE_LABELS,
  type RdDeliverableTemplate,
} from '@/types/research/rd-project'
import { DocGenFilePreview } from './DocGenFilePreview'
import { DocGenSlotEditor } from './DocGenSlotEditor'

const { Text } = Typography

type Phase = 'form' | 'extracting' | 'review' | 'generating' | 'completed'

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

/** 单文件上限 20 MB（Qwen3.8-27B 可接受的最大输入大小） */
const MAX_FILE_MB = 20
const MAX_FILES = 20

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function normalizeExt(name: string): string {
  const idx = name.lastIndexOf('.')
  return idx >= 0 ? name.slice(idx + 1).toLowerCase() : ''
}

/** 文件解析状态摘要：显示哪些文件解析成功、哪些走了 AI 回退、哪些失败 */
function FileParseStatusSummary({ files }: { files: DocGenInputFileResponse[] }) {
  const done = files.filter((f) => f.parse_status === 'done')
  const aiFallback = files.filter((f) => f.parse_status === 'ai_fallback')
  const failed = files.filter((f) => f.parse_status === 'failed')
  const pending = files.filter((f) => f.parse_status === 'pending' || !f.parse_status)

  // 始终显示文件解析状态，让用户在 review 阶段就能看到文件解析情况

  const statusConfig: Record<string, { color: string; label: string; icon: string }> = {
    done: { color: 'success', label: '解析成功', icon: '✓' },
    ai_fallback: { color: 'warning', label: 'AI 解析', icon: '🤖' },
    failed: { color: 'error', label: '解析失败', icon: '✗' },
    pending: { color: 'default', label: '待解析', icon: '○' },
  }

  // 计算总字符数
  const totalChars = files.reduce((sum, f) => sum + (f.char_count || 0), 0)

  const items = [
    {
      key: 'parse-status',
      label: (
        <span>
          文件解析结果：
          {done.length > 0 && <Tag color="success">{done.length} 个成功</Tag>}
          {aiFallback.length > 0 && <Tag color="warning">{aiFallback.length} 个 AI 解析</Tag>}
          {failed.length > 0 && <Tag color="error">{failed.length} 个失败</Tag>}
          {pending.length > 0 && <Tag>{pending.length} 个待解析</Tag>}
          {totalChars > 0 && <Tag color="blue" style={{ marginLeft: 8 }}>共 {totalChars.toLocaleString()} 字</Tag>}
        </span>
      ),
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {files.map((file) => {
            const cfg = statusConfig[file.parse_status] || statusConfig.pending
            return (
              <div key={file.id} style={{ 
                display: 'flex', 
                alignItems: 'flex-start', 
                gap: 10, 
                padding: '8px 12px', 
                background: file.parse_status === 'failed' ? '#fff2f0' : file.parse_status === 'ai_fallback' ? '#fffbe6' : '#fafafa',
                borderRadius: 4,
                border: `1px solid ${file.parse_status === 'failed' ? '#ffccc7' : file.parse_status === 'ai_fallback' ? '#ffe58f' : '#f0f0f0'}`
              }}>
                <Tag color={cfg.color} style={{ flexShrink: 0, margin: 0 }}>{cfg.icon} {cfg.label}</Tag>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 500, marginBottom: 2 }}>{file.original_filename}</div>
                  <div style={{ fontSize: 12, color: '#8c8c8c', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                    {file.page_count ? <span>{file.page_count} 页</span> : null}
                    {file.char_count ? <span>{file.char_count.toLocaleString()} 字</span> : null}
                  </div>
                  {file.warnings && file.warnings.length > 0 && (
                    <div style={{ fontSize: 12, color: file.parse_status === 'failed' ? '#cf1322' : '#faad14', marginTop: 4 }}>
                      ⚠ {file.warnings.join('；')}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ),
    },
  ]

  return (
    <Collapse
      items={items}
      defaultActiveKey={['parse-status']}
      style={{ marginBottom: 16 }}
      size="small"
    />
  )
}

export function CreateReportModal({ open, projectId, onCancel, onCreated, editingReport }: Props) {
  const { message: msgApi } = App.useApp()
  const [form] = Form.useForm()
  const isEditMode = !!editingReport

  const [phase, setPhase] = useState<Phase>('form')
  const [templates, setTemplates] = useState<DocGenUsableTemplate[]>([])
  const [tplMeta, setTplMeta] = useState<Record<string, RdDeliverableTemplate>>({})
  const [limits, setLimits] = useState<DocGenLimits | null>(null)
  const [items, setItems] = useState<DocGenFormItem[]>([])
  // 已保存到服务端的文件（编辑模式从后端加载）
  const [serverFiles, setServerFiles] = useState<DocGenInputFileResponse[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [job, setJob] = useState<DocGenJobResponse | null>(null)
  const jobIdRef = useRef<string | null>(null)

  // 提取结果
  const [extractedSlots, setExtractedSlots] = useState<DocGenExtractedSlot[]>([])
  const [editedSlots, setEditedSlots] = useState<Record<string, string>>({})
  const [extracting, setExtracting] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [saving, setSaving] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [formReady, setFormReady] = useState(!editingReport) // 编辑模式下等数据加载完再显示表单

  // 提取结果统计（从 extractedSlots 计算）
  const extractStats = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const slot of extractedSlots) {
      counts[slot.state] = (counts[slot.state] || 0) + 1
    }
    return counts
  }, [extractedSlots])

  // 文件预览（由 DocGenFilePreview 组件管理）
  const [previewFile, setPreviewFile] = useState<File | null>(null)

  // 报告预览
  const reportPreviewRef = useRef<HTMLDivElement | null>(null)
  const [reportPreviewLoading, setReportPreviewLoading] = useState(false)
  const [reportPreviewError, setReportPreviewError] = useState<string | null>(null)

  // 模板预览
  const [tplPreviewOpen, setTplPreviewOpen] = useState(false)
  const [tplPreviewLoading, setTplPreviewLoading] = useState(false)
  const tplPreviewRef = useRef<HTMLDivElement | null>(null)
  const tplPreviewUrlRef = useRef<string | null>(null)

  // ─── 加载模板与限制 ───
  useEffect(() => {
    if (!open) return
    // 编辑模式下，先隐藏表单，等数据加载完再显示
    if (editingReport) setFormReady(false)
    else setFormReady(true)
    let cancelled = false
    ;(async () => {
      try {
        const [tpl, lim, rawTpl] = await Promise.all([
          fetchUsableDocGenTemplates(),
          fetchDocGenLimits(),
          fetchDeliverableTemplates({}),
        ])
        if (cancelled) return
        setTemplates(tpl)
        setLimits(lim)
        const meta: Record<string, RdDeliverableTemplate> = {}
        rawTpl.forEach((t) => { meta[t.id] = t })
        setTplMeta(meta)
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
            // 加载已保存的资料文件（供显示与预览）
            if (jobDetailResp.files?.length) {
              setServerFiles(jobDetailResp.files)
            }
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

  // 进入待确认 → review 阶段
  useEffect(() => {
    if (job?.status === 'awaiting_review') {
      setPhase('review')
      loadExtractedInfo()
      // 加载文件解析状态（新建任务时 serverFiles 可能为空）
      if (serverFiles.length === 0 && jobIdRef.current) {
        fetchDocGenJob(jobIdRef.current).then((detail) => {
          if (detail.files?.length) setServerFiles(detail.files)
        }).catch(() => { /* 忽略 */ })
      }
    }
  }, [job?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  // 生成完成 → completed 阶段
  useEffect(() => {
    if (job && isDocGenCompleted(job.status)) setPhase('completed')
  }, [job?.status])

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
    } catch (e: any) {
      msgApi.error('加载提取信息失败：' + (e.message || ''))
    } finally {
      setExtracting(false)
    }
  }

  // 加载报告预览
  useEffect(() => {
    if (!job || !isDocGenCompleted(job.status) || !job.has_document) return
    let cancelled = false
    setReportPreviewLoading(true)
    setReportPreviewError(null)
    ;(async () => {
      try {
        const blob = await fetchDocGenDocumentBlob(job.id)
        if (cancelled || !reportPreviewRef.current) return
        reportPreviewRef.current.innerHTML = ''
        await renderAsync(blob, reportPreviewRef.current, undefined, { inWrapper: true, ignoreWidth: true })
      } catch (e) {
        if (!cancelled) setReportPreviewError(e instanceof Error ? e.message : '预览失败')
      } finally {
        if (!cancelled) setReportPreviewLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [job?.id, job?.status, job?.has_document]) // eslint-disable-line react-hooks/exhaustive-deps

  // ─── 文件处理 ───
  const handleAddFile = useCallback(
    (file: File): boolean => {
      const ext = normalizeExt(file.name)
      const allowed = (limits?.allowed_extensions ?? []).map((e) => e.replace(/^\./, '').toLowerCase())
      if (allowed.length > 0 && !allowed.includes(ext)) {
        msgApi.warning(`文件「${file.name}」类型不支持`)
        return false
      }
      if (file.size > MAX_FILE_MB * 1024 * 1024) {
        msgApi.warning(`文件「${file.name}」超过单文件 ${MAX_FILE_MB}MB 上限`)
        return false
      }
      if (items.length >= MAX_FILES) {
        msgApi.warning(`最多 ${MAX_FILES} 个文件`)
        return false
      }
      setItems((prev) => {
        if (prev.some((p) => p.file.name === file.name && p.file.size === file.size)) {
          msgApi.warning(`文件「${file.name}」已在列表中`)
          return prev
        }
        return [...prev, { file, role: 'material' }]
      })
      return false
    },
    [limits, items, msgApi],
  )

  const removeFile = (index: number) => setItems((prev) => prev.filter((_, i) => i !== index))

  // ─── 文件预览（委托给 DocGenFilePreview 组件） ───
  const openFilePreview = (file: File) => setPreviewFile(file)
  const closeFilePreview = () => setPreviewFile(null)

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

  // ─── AI 创建报告（编辑模式：开始提取信息） ───
  const handleCreateAndExtract = async () => {
    // 校验模板选择
    const templateId = form.getFieldValue('template_id')
    if (!templateId) {
      msgApi.warning('请先选择模板')
      return
    }
    // 校验文件上传（本地 + 服务端已保存文件）
    if (totalFileCount === 0) {
      msgApi.warning('请先上传至少一个参考文件')
      return
    }

    // 立即切换到提取中界面，job 创建在后台进行
    console.log('[CreateReportModal] 开始创建提取任务, editingReport:', editingReport?.id, 'job:', job?.id, 'templateId:', templateId, 'files:', totalFileCount)
    setPhase('extracting')
    console.log('[CreateReportModal] phase 已设为 extracting')
    setSubmitting(true)
    try {
      let currentJob = job

      // 已终止的任务无法续跑，必须新建
      const needsNewJob = !currentJob || currentJob.status === 'cancelled'

      if (needsNewJob) {
        const values = form.getFieldsValue()
        const created = await createDocGenJob({
          templateId,
          docCode: values.doc_code || values.title,
          docVersion: values.version || 'v1.0',
          drugName: values.drug_name || values.title,
          supplementText: values.supplement?.trim() || undefined,
          fileRoles: items.map((it) => it.role),
          files: items.map((it) => it.file),
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

      // 显式调用 extract：draft/failed/awaiting_review 可提取
      // cancelled 已在上方新建分支处理；直达模式（chat_enabled=false）创建即 pending，worker 自动执行
      if (currentJob.status === 'draft' || currentJob.status === 'failed' || currentJob.status === 'awaiting_review') {
        try {
          const started = await extractDocGenJob(currentJob.id)
          setJob(started)
        } catch (extractErr) {
          // extract 失败时刷新 job 状态，给用户准确提示而非空白页
          try {
            const fresh = await fetchDocGenJob(currentJob.id)
            setJob(fresh.job)
          } catch { /* 忽略 */ }
          throw extractErr
        }
      }

      onCreated?.()
      msgApi.success('正在提取信息')
    } catch (e) {
      console.error('[CreateReportModal] 创建提取任务失败:', e)
      msgApi.error(e instanceof Error ? e.message : '提取信息失败')
      // 不自动切回表单，保留在提取视图让用户看到错误状态并自行操作
    } finally {
      setSubmitting(false)
      console.log('[CreateReportModal] handleCreateAndExtract 完成, phase 应保持 extracting')
    }
  }

  // ─── 保存/创建（新建报告时创建 job + RdReport，编辑报告时更新 job + RdReport） ───
  const handleSave = async () => {
    let values: Record<string, any>
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
        // 如果有新上传的文件，追加到任务
        if (items.length > 0) {
          const detail = await uploadJobFiles(
            job.id,
            items.map((it) => it.file),
            items.map((it) => it.role),
          )
          // 更新服务端文件列表
          if (detail.data?.files) {
            setServerFiles(detail.data.files)
          }
        }
        // 清空本地文件列表（已上传到服务端）
        setItems([])
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
            fileRoles: items.map((it) => it.role),
            files: items.map((it) => it.file),
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
          fileRoles: items.map((it) => it.role),
          files: items.map((it) => it.file),
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
      await cancelDocGenJob(job.id)
    } catch { /* 取消旧任务失败不阻塞 */ }
    setJob(null); jobIdRef.current = null
    setExtractedSlots([]); setEditedSlots({})
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
    setReportPreviewError(null)
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
    form.resetFields(); setItems([]); setServerFiles([]); setJob(null); jobIdRef.current = null
    setPhase('form'); setExtractedSlots([]); setEditedSlots({})
    setReportPreviewError(null); setFormReady(!editingReport)
    onCancel()
  }

  // 图片文件缩略图 URL（memo 避免每次渲染创建新 blob URL）
  const thumbUrls = useMemo(() => {
    const map = new Map<string, string>()
    items.forEach((it) => {
      const ext = normalizeExt(it.file.name)
      if (['png', 'jpg', 'jpeg', 'bmp', 'webp'].includes(ext)) {
        map.set('local:' + it.file.name + it.file.size, URL.createObjectURL(it.file))
      }
    })
    return map
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items.map((it) => it.file.name + it.file.size).join(',')])

  // 清理缩略图 URL
  useEffect(() => {
    return () => { thumbUrls.forEach((url) => URL.revokeObjectURL(url)) }
  }, [thumbUrls])

  // 总文件数（本地 + 服务端）
  const totalFileCount = items.length + serverFiles.length

  // 转换为 antd Upload fileList（合并本地文件与服务端已保存文件）
  const uploadFileList = useMemo<UploadFile[]>(() => {
    const localFiles = items.map((it, idx) => ({
      uid: `local-${idx}`,
      name: it.file.name,
      status: 'done' as const,
      size: it.file.size,
      originFileObj: it.file as any,
      thumbUrl: thumbUrls.get('local:' + it.file.name + it.file.size),
    }))
    const remoteFiles = serverFiles.map((sf, idx) => ({
      uid: `remote-${idx}`,
      name: sf.original_filename,
      status: 'done' as const,
      size: sf.size_bytes,
      // 标记为服务端文件，供 onPreview/onRemove 识别
      _serverFile: sf,
    }))
    return [...localFiles, ...remoteFiles]
  }, [items, serverFiles, thumbUrls])

  // 预览文件（支持本地文件与服务端文件）
  const handlePreviewFile = async (file: UploadFile) => {
    const sf = (file as any)._serverFile as DocGenInputFileResponse | undefined
    if (sf) {
      // 服务端文件：需要 jobId 才能下载
      if (!jobIdRef.current) {
        msgApi.warning('请先创建任务后再预览文件')
        return
      }
      try {
        const blob = await fetchDocGenInputFileBlob(jobIdRef.current, sf.id)
        const previewFile = new File([blob], sf.original_filename, { type: blob.type })
        setPreviewFile(previewFile)
      } catch (e) {
        msgApi.error(e instanceof Error ? e.message : '加载文件失败，请稍后重试')
      }
    } else {
      // 本地文件
      const f = file.originFileObj ?? items[Number(file.uid?.replace('local-', ''))]?.file
      if (f) {
        openFilePreview(f)
      } else {
        msgApi.warning('文件不存在或已过期')
      }
    }
  }

  // 下载文件（直接保存到本地）
  const handleDownloadFile = async (file: UploadFile) => {
    const sf = (file as any)._serverFile as DocGenInputFileResponse | undefined
    if (sf) {
      // 服务端文件：需要 jobId 才能下载
      if (!jobIdRef.current) {
        msgApi.warning('请先创建任务后再下载文件')
        return
      }
      try {
        const blob = await fetchDocGenInputFileBlob(jobIdRef.current, sf.id)
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = sf.original_filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } catch (e) {
        msgApi.error(e instanceof Error ? e.message : '下载文件失败，请稍后重试')
      }
    } else {
      // 本地文件：直接保存
      const f = file.originFileObj ?? items[Number(file.uid?.replace('local-', ''))]?.file
      if (f) {
        const url = window.URL.createObjectURL(f)
        const a = document.createElement('a')
        a.href = url
        a.download = f.name
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } else {
        msgApi.warning('文件不存在或已过期')
      }
    }
  }

  // 删除文件（支持本地文件与服务端文件）
  const handleRemoveFile = async (file: UploadFile): Promise<boolean> => {
    const sf = (file as any)._serverFile as DocGenInputFileResponse | undefined
    if (sf) {
      // 服务端文件
      if (jobIdRef.current) {
        // 有 job：尝试调用后端删除
        try {
          const res = await fetch(
            `/api/v1/research/doc-gen/jobs/${jobIdRef.current}/input-files/${sf.id}`,
            { method: 'DELETE', credentials: 'include' },
          )
          if (res.ok) {
            msgApi.success(`已删除「${sf.original_filename}」`)
          }
          // 无论后端是否成功，都从本地状态移除（后端可能因 job 状态拒绝，但用户仍可从 UI 移除）
        } catch {
          // 网络错误等，仍然从本地移除
        }
      }
      // 从本地状态移除
      setServerFiles((prev) => prev.filter((f) => f.id !== sf.id))
    } else {
      // 本地文件
      const idx = Number(file.uid?.replace('local-', ''))
      if (!isNaN(idx)) removeFile(idx)
    }
    return true
  }

  const selectedTplId = Form.useWatch('template_id', form) as string | undefined
  const selectedTpl = templates.find((t) => t.id === selectedTplId)
  const allowedExts = (limits?.allowed_extensions ?? []).map((e) => e.replace(/^\./, '').toLowerCase())

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
              onClick={handleCreateAndExtract}
              loading={submitting}
            >
              AI 创建报告
            </Button>,
          ]
        }
        // 新建模式：创建 + AI 创建报告
        return [
          <Button key="cancel" onClick={handleClose}>取消</Button>,
          <Button key="create" onClick={handleSave} loading={saving}>创建</Button>,
          <Button
            key="ai-extract"
            type="primary"
            icon={<ThunderboltOutlined />}
            onClick={handleCreateAndExtract}
            loading={submitting}
          >
            AI 创建报告
          </Button>,
        ]
      case 'extracting': {
        const isTerminal = isDocGenTerminal(job?.status ?? '')
        const buttons: React.ReactNode[] = []
        // job 创建失败（无 job 且不在提交中）→ 显示返回修改按钮
        if (!job && !submitting) {
          buttons.push(
            <Button key="back" type="primary" icon={<UndoOutlined />} onClick={() => setPhase('form')}>
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
            <Button key="back" icon={<UndoOutlined />} onClick={handleReExtract}>
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
          <Button key="back" icon={<UndoOutlined />} onClick={() => setPhase('form')}>返回修改</Button>,
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

          {/* 第四行：参考文件上传 */}
          <Form.Item
            label={`参考文件上传（最多 ${MAX_FILES} 个，单文件 ≤ ${MAX_FILE_MB}MB）`}
          >
            <div style={{ display: 'flex', gap: 16 }}>
              {/* 左侧：上传区域 + 文件列表 */}
              <div style={{ flex: 1 }}>
                {/* 上传按钮 */}
                <Upload
                  multiple
                  fileList={uploadFileList}
                  beforeUpload={handleAddFile}
                  accept={allowedExts.length > 0 ? allowedExts.map((e) => `.${e}`).join(',') : undefined}
                  disabled={totalFileCount >= MAX_FILES}
                  showUploadList={false}
                >
                  <Button icon={<UploadOutlined />} disabled={totalFileCount >= MAX_FILES}>
                    选择文件
                  </Button>
                </Upload>
                {/* 文件列表区域：固定高度，超出滚动 */}
                {uploadFileList.length > 0 && (
                  <div
                    style={{
                      maxHeight: 200,
                      overflowY: 'auto',
                      marginTop: 8,
                      padding: '0 4px',
                    }}
                  >
                    {uploadFileList.map((file) => {
                      const sf = (file as any)._serverFile as DocGenInputFileResponse | undefined
                      const parseStatus = sf?.parse_status
                      const parseFailed = parseStatus === 'failed'
                      const parseWarnings = sf?.warnings || []
                      return (
                        <div
                          key={file.uid}
                          style={{
                            display: 'flex',
                            alignItems: 'flex-start',
                            justifyContent: 'space-between',
                            padding: '8px 12px',
                            marginBottom: 8,
                            backgroundColor: parseFailed ? '#fff2f0' : '#fafafa',
                            border: `1px solid ${parseFailed ? '#ffccc7' : '#d9d9d9'}`,
                            borderRadius: 6,
                          }}
                        >
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                              <span
                                style={{
                                  fontSize: 14,
                                  color: parseFailed ? '#cf1322' : '#262626',
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                }}
                                title={file.name}
                              >
                                {file.name}
                              </span>
                              {sf && (
                                <Tag
                                  color={
                                    parseStatus === 'failed' ? 'error' :
                                    parseStatus === 'ai_fallback' ? 'warning' :
                                    parseStatus === 'done' ? 'success' : 'default'
                                  }
                                  style={{ margin: 0, fontSize: 11 }}
                                >
                                  {parseStatus === 'failed' ? '解析失败' :
                                   parseStatus === 'ai_fallback' ? 'AI 解析' :
                                   parseStatus === 'done' ? '已解析' : '待解析'}
                                </Tag>
                              )}
                            </div>
                            <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>
                              {file.size ? `${(file.size / 1024).toFixed(1)} KB` : ''}
                              {sf?.char_count ? ` · ${sf.char_count} 字` : ''}
                            </div>
                            {parseFailed && parseWarnings.length > 0 && (
                              <div style={{ fontSize: 12, color: '#cf1322', marginTop: 4 }}>
                                {parseWarnings[0]}
                              </div>
                            )}
                          </div>
                          <Space size={4}>
                            <Button
                              type="link"
                              size="small"
                              icon={<EyeOutlined />}
                              onClick={() => handlePreviewFile(file)}
                            >
                              预览
                            </Button>
                            <Button
                              type="link"
                              size="small"
                              icon={<DownloadOutlined />}
                              onClick={() => handleDownloadFile(file)}
                            >
                              下载
                            </Button>
                            <Button
                              type="link"
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleRemoveFile(file)}
                            >
                              删除
                            </Button>
                          </Space>
                        </div>
                      )
                    })}
                  </div>
                )}
                {totalFileCount === 0 && (
                  <div style={{ padding: '8px 0', color: '#999' }}>
                    点击按钮选择参考文件，支持图片、PDF、Word、Excel、Markdown 等格式
                  </div>
                )}
              </div>
              {/* 右侧：AI 提取文档信息按钮 */}
              <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                <Button
                  type="primary"
                  htmlType="button"
                  icon={<ThunderboltOutlined />}
                  onClick={handleCreateAndExtract}
                  loading={submitting}
                  size="large"
                >
                  AI 提取文档信息
                </Button>
              </div>
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

      {/* ═══ Phase 2: 信息提取中 ═══ */}
      {phase === 'extracting' && (
        <div style={{ padding: '40px 24px' }}>
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
              {/* 失败/取消时显示返回按钮 */}
              {job?.status === 'cancelled' && (
                <Button
                  icon={<UndoOutlined />}
                  onClick={handleReExtract}
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
          {serverFiles.length > 0 && (
            <FileParseStatusSummary files={serverFiles} />
          )}
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
      <DocGenFilePreview file={previewFile} onClose={closeFilePreview} />

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
