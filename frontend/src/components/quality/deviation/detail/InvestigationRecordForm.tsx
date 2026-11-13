'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { App, Button, Checkbox, DatePicker, Form, Input, Modal, Popconfirm, Select, Space, Upload } from 'antd'
import {
  DeleteOutlined,
  DownloadOutlined,
  EyeOutlined,
  FileTextOutlined,
  PlusOutlined,
  UploadOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'
import {
  appendDeviationInvestigationRecord,
  deleteDeviationAttachment,
  deleteDeviationInvestigationDraft,
  saveDeviationInvestigationDraft,
  submitDeviationCrossDeptInvestigation,
  submitDeviationInvestigation,
  uploadDeviationAttachment,
} from '@/actions/quality'
import { fetchDeviationAttachmentCommentSummary } from '@/lib/api/client/quality'
import type {
  DeviationAttachment,
  DeviationInvestigationDraft,
  DeviationInvestigationDraftInput,
  DeviationInvestigationInput,
  DeviationInvestigationPrefill,
  DeviationLedgerDetail,
} from '@/types/quality'

const { TextArea } = Input

interface CapaRowValue {
  summary?: string
  executor?: string
  due?: Dayjs
}

interface FormValues {
  nonconformity_description?: string
  root_cause_analysis?: string
  risk_assessment?: string
  capa_proposals?: CapaRowValue[]
  has_urgent?: boolean
  urgent_measures?: string
  attachment_file_ids?: string[]
}

interface InvestigationRecordFormProps {
  ledger: DeviationLedgerDetail
  /** submit=提交调查；append=追加记录（不流转）；cross-dept=跨部门调查人提交本部门调查 */
  mode: 'submit' | 'append' | 'cross-dept'
  /** cross-dept 模式必填：本行部门名（行标识） */
  department?: string
  /** 本人该范围的已暂存草稿：打开表单时自动回填 */
  initialDraft?: DeviationInvestigationDraft | null
  /** AI 分析的一键填写载荷：只补空白项，不提交、不自动暂存 */
  prefill?: DeviationInvestigationPrefill | null
  /** 应用完 prefill 后回调实际写入项数（0 表示无空白项可填） */
  onPrefillApplied?: (filled: number) => void
  /** 提交/追加成功：宿主收起表单并刷新 */
  onSubmitted: (ledger: DeviationLedgerDetail) => void
  /** 仅台账数据变化（如上传/删除附件、暂存草稿）：宿主刷新但不收起表单 */
  onLedgerChange: (ledger: DeviationLedgerDetail) => void
  /** 打开附件预览抽屉（左文档 + 右批注） */
  onPreviewAttachment?: (attachment: DeviationAttachment) => void
  onCancel: () => void
}

/** 单文件上限 20MB，与台账上传一致 */
const MAX_ATTACHMENT_SIZE = 20 * 1024 * 1024

function formatSize(size: number): string {
  if (!size) return '-'
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

function formatDraftTime(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString('zh-CN', { hour12: false })
}

function attachmentUrl(ledgerId: string, fileId: string): string {
  return `/api/v1/quality/deviation/ledger/${ledgerId}/attachments/${fileId}/download`
}

/** 台账内所有附件的未处理批注总数；取不到时返回 0，不阻断提交 */
async function countPendingAttachmentComments(ledgerId: string): Promise<number> {
  try {
    const summary = await fetchDeviationAttachmentCommentSummary(ledgerId)
    return (summary.items ?? []).reduce((total, item) => total + (item.open_count ?? 0), 0)
  } catch {
    // 批注汇总属提醒性质，失败时按「无未处理批注」处理
    return 0
  }
}

/**
 * 结构化调查记录表单：提交调查报告 / 追加记录 / 跨部门提交本部门调查共用。
 * 顺序：不符合事项 / 根本原因 / 风险评估 → CAPA 多行 →「有紧急处理措施」→ 记录附件。
 * 二选一规则：引用 ≥1 个台账附件（调查报告）时文本与 CAPA 可免填；未引用附件时三者必填。
 * 草稿：未提交前可「暂存草稿」（后端按人 + 部门持久化），再次打开自动回填，提交后自动清除。
 */
export function InvestigationRecordForm({
  ledger,
  mode,
  department,
  initialDraft,
  prefill,
  onPrefillApplied,
  onSubmitted,
  onLedgerChange,
  onPreviewAttachment,
  onCancel,
}: InvestigationRecordFormProps) {
  const { message, modal } = App.useApp()
  const [form] = Form.useForm<FormValues>()
  const [busy, setBusy] = useState(false)
  const [savingDraft, setSavingDraft] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [draftSavedAt, setDraftSavedAt] = useState<string | null>(initialDraft?.updated_at ?? null)
  //: 提交审核二次确认：确认弹窗内可填写提交信息（选填，写入流转记录）
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false)
  const [submitInfo, setSubmitInfo] = useState('')
  const pendingSubmitRef = useRef<DeviationInvestigationInput | null>(null)
  const hasUrgent = Form.useWatch('has_urgent', form)
  const attachmentIds = Form.useWatch('attachment_file_ids', form)
  const referencedIds = useMemo(() => attachmentIds ?? [], [attachmentIds])
  const viaAttachment = referencedIds.length > 0
  const attachments = ledger.attachments ?? []
  const canDeleteAttachment = ledger.can_delete_attachment === true
  // 草稿回填只做一次（同一草稿版本），避免宿主刷新后覆盖用户正在编辑的内容
  const restoredDraftRef = useRef<string | null>(null)
  // 表单初始快照：用于「取消时是否有未保存改动」判断
  const baselineRef = useRef<string>('')
  // 已消费的 AI 填充载荷 nonce：同一份载荷只填一次，避免重复渲染覆盖
  const appliedPrefillRef = useRef<string | null>(null)

  const buildSnapshot = (values: FormValues): string =>
    JSON.stringify({
      nonconformity_description: values.nonconformity_description ?? '',
      root_cause_analysis: values.root_cause_analysis ?? '',
      risk_assessment: values.risk_assessment ?? '',
      capa_proposals: (values.capa_proposals ?? []).map((row) => ({
        summary: row.summary ?? '',
        executor: row.executor ?? '',
        due: row.due ? row.due.format('YYYY-MM-DD') : '',
      })),
      has_urgent: Boolean(values.has_urgent),
      urgent_measures: values.urgent_measures ?? '',
      attachment_file_ids: values.attachment_file_ids ?? [],
    })

  useEffect(() => {
    const key = initialDraft ? `${initialDraft.updated_at ?? ''}|${initialDraft.department ?? ''}` : null
    if (!initialDraft || !key || restoredDraftRef.current === key) {
      if (!initialDraft && restoredDraftRef.current === null) {
        baselineRef.current = buildSnapshot(form.getFieldsValue(true) as FormValues)
      }
      return
    }
    restoredDraftRef.current = key
    form.setFieldsValue({
      nonconformity_description: initialDraft.nonconformity_description || undefined,
      root_cause_analysis: initialDraft.root_cause_analysis || undefined,
      risk_assessment: initialDraft.risk_assessment || undefined,
      capa_proposals: (initialDraft.capa_proposals ?? []).map((capa) => ({
        summary: capa.summary,
        executor: capa.executor ?? undefined,
        due: capa.expected_completion_date ? dayjs(capa.expected_completion_date) : undefined,
      })),
      has_urgent: initialDraft.has_urgent,
      urgent_measures: initialDraft.urgent_measures ?? undefined,
      attachment_file_ids: initialDraft.attachment_file_ids ?? [],
    })
    baselineRef.current = buildSnapshot(form.getFieldsValue(true) as FormValues)
  }, [form, initialDraft])

  // AI 一键填写：只补空白项（文本为空、CAPA 各行全空），不提交、不暂存、不改 baseline
  useEffect(() => {
    if (!prefill || appliedPrefillRef.current === prefill.nonce) return
    appliedPrefillRef.current = prefill.nonce
    const current = form.getFieldsValue(true) as FormValues
    const next: FormValues = {}
    let filled = 0
    const fillText = (
      key: 'nonconformity_description' | 'root_cause_analysis' | 'risk_assessment',
      value: string,
    ) => {
      if (!value) return
      if ((current[key] ?? '').trim().length > 0) return
      next[key] = value
      filled += 1
    }
    fillText('nonconformity_description', prefill.nonconformity_description)
    fillText('root_cause_analysis', prefill.root_cause_analysis)
    fillText('risk_assessment', prefill.risk_assessment)
    //: CAPA 只要有一行已填人工内容就整块保留，避免拆行结果与人工条目混排
    const hasCapaContent = (current.capa_proposals ?? []).some((row) => (row.summary ?? '').trim().length > 0)
    if (!hasCapaContent && prefill.capa_proposals.length > 0) {
      next.capa_proposals = prefill.capa_proposals.map((row) => ({ summary: row.summary }))
      filled += prefill.capa_proposals.length
    }
    if (filled > 0) form.setFieldsValue(next)
    onPrefillApplied?.(filled)
  }, [form, prefill, onPrefillApplied])

  const buildDraftBody = (): DeviationInvestigationDraftInput => {
    const values = form.getFieldsValue(true) as FormValues
    return {
      department: department ?? null,
      nonconformity_description: (values.nonconformity_description ?? '').trim(),
      root_cause_analysis: (values.root_cause_analysis ?? '').trim(),
      risk_assessment: (values.risk_assessment ?? '').trim(),
      capa_proposals: (values.capa_proposals ?? []).map((row, index) => ({
        sequence: index + 1,
        summary: (row.summary ?? '').trim(),
        executor: row.executor?.trim() || null,
        expected_completion_date: row.due ? row.due.format('YYYY-MM-DD') : null,
      })),
      has_urgent: Boolean(values.has_urgent),
      urgent_measures: values.has_urgent ? (values.urgent_measures ?? '').trim() || null : null,
      attachment_file_ids: values.attachment_file_ids ?? [],
    }
  }

  const handleSaveDraft = async () => {
    setSavingDraft(true)
    const result = await saveDeviationInvestigationDraft(ledger.id, buildDraftBody())
    setSavingDraft(false)
    if (result.code === 200 && result.data) {
      const saved = (result.data.investigation_drafts ?? []).find(
        (draft) => (draft.department ?? null) === (department ?? null),
      )
      setDraftSavedAt(saved?.updated_at ?? new Date().toISOString())
      //: 记录已保存版本，避免宿主刷新后再次回填覆盖当前编辑
      restoredDraftRef.current = `${saved?.updated_at ?? ''}|${saved?.department ?? ''}`
      //: 已暂存的内容视为已保存状态，取消时不再提示「未保存改动」
      baselineRef.current = buildSnapshot(form.getFieldsValue(true) as FormValues)
      message.success('草稿已暂存')
      onLedgerChange(result.data)
    } else {
      message.error(result.message)
    }
  }

  const handleClearDraft = () => {
    modal.confirm({
      title: '清除草稿？',
      content: '清除后再次打开表单将不再回填当前内容。',
      okText: '清除',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        const result = await deleteDeviationInvestigationDraft(ledger.id, department)
        if (result.code === 200 && result.data) {
          form.resetFields()
          restoredDraftRef.current = null
          baselineRef.current = buildSnapshot(form.getFieldsValue(true) as FormValues)
          setDraftSavedAt(null)
          message.success('草稿已清除')
          onLedgerChange(result.data)
        } else {
          message.error(result.message)
        }
      },
    })
  }

  const handleCancel = () => {
    const dirty = buildSnapshot(form.getFieldsValue(true) as FormValues) !== baselineRef.current
    if (!dirty) {
      onCancel()
      return
    }
    modal.confirm({
      title: '有未保存的改动',
      content: '暂存草稿可保留当前内容；直接离开将丢失未保存的修改。',
      okText: '放弃改动',
      cancelText: '继续编辑',
      okButtonProps: { danger: true },
      onOk: onCancel,
    })
  }

  const runSubmit = async (body: DeviationInvestigationInput) => {
    setBusy(true)
    const result =
      mode === 'submit'
        ? await submitDeviationInvestigation(ledger.id, body)
        : mode === 'cross-dept'
          ? await submitDeviationCrossDeptInvestigation(ledger.id, { ...body, department: department ?? '' })
          : await appendDeviationInvestigationRecord(ledger.id, body)
    setBusy(false)
    if (result.code === 200 && result.data) {
      message.success(
        mode === 'submit'
          ? '调查已提交，进入部门负责人审核'
          : mode === 'cross-dept'
            ? '本部门调查已提交，等待部门负责人审核'
            : '调查记录已追加，流程状态不变',
      )
      setDraftSavedAt(null)
      onSubmitted(result.data)
    } else {
      message.error(result.message)
    }
  }

  const handleSubmit = async (values: FormValues) => {
    const capaRows = (values.capa_proposals ?? []).filter((row) => (row.summary ?? '').trim().length > 0)
    const body: DeviationInvestigationInput = {
      // 附件路线下三个文本允许不填，值为 undefined，必须空值兜底再 trim
      nonconformity_description: (values.nonconformity_description ?? '').trim(),
      root_cause_analysis: (values.root_cause_analysis ?? '').trim(),
      risk_assessment: (values.risk_assessment ?? '').trim(),
      urgent_measures: values.has_urgent ? (values.urgent_measures ?? '').trim() : null,
      capa_proposals: capaRows.map((row, index) => ({
        sequence: index + 1,
        summary: (row.summary ?? '').trim(),
        executor: row.executor?.trim() || null,
        expected_completion_date: row.due ? row.due.format('YYYY-MM-DD') : null,
      })),
      attachment_file_ids: values.attachment_file_ids ?? [],
    }
    //: 二选一校验：引用了调查文档附件，或调查记录已填写，有其一才能提交审核
    const hasRecordText = [
      body.nonconformity_description,
      body.root_cause_analysis,
      body.risk_assessment,
    ].some((value) => (value ?? '').trim().length > 0)
    const hasCapa = (body.capa_proposals ?? []).length > 0
    const hasAttachment = (body.attachment_file_ids ?? []).length > 0
    if (mode === 'submit' && !hasAttachment && !hasRecordText && !hasCapa) {
      message.warning('请先填写调查记录，或上传并引用调查报告附件后再提交审核')
      return
    }
    if (mode !== 'append') {
      const pending = await countPendingAttachmentComments(ledger.id)
      if (pending > 0) {
        modal.confirm({
          title: `还有 ${pending} 条未处理批注`,
          content: '未处理的文档批注不会阻断流程。建议先处理或标记解决后再提交调查。',
          okText: '仍然提交',
          cancelText: '返回处理',
          okButtonProps: { danger: true },
          onOk: () => openSubmitConfirm(body),
        })
        return
      }
    }
    if (mode === 'submit') {
      openSubmitConfirm(body)
      return
    }
    await runSubmit(body)
  }

  /** 打开「确认提交审核」弹窗：取消只关弹窗，表单内容保留 */
  const openSubmitConfirm = (body: DeviationInvestigationInput) => {
    pendingSubmitRef.current = body
    setSubmitInfo('')
    setSubmitConfirmOpen(true)
  }

  const handleConfirmSubmit = async () => {
    const body = pendingSubmitRef.current
    if (!body) return
    const payload: DeviationInvestigationInput = {
      ...body,
      submit_content: submitInfo.trim() || null,
    }
    setSubmitConfirmOpen(false)
    await runSubmit(payload)
  }

  /** 附件先上传到台账，再把新增 file_id 自动加入本记录引用 */
  const handleUpload = async (file: File) => {
    if (file.size > MAX_ATTACHMENT_SIZE) {
      message.error('单个文档不能超过 20MB')
      return
    }
    const knownIds = new Set(attachments.map((item) => item.file_id))
    const formData = new FormData()
    formData.append('file', file)
    setUploading(true)
    const result = await uploadDeviationAttachment(ledger.id, formData)
    setUploading(false)
    if (result.code === 200 && result.data) {
      const known = new Set(attachments.map((item) => item.file_id))
      const newIds = (result.data.attachments ?? [])
        .filter((item) => !known.has(item.file_id) && !knownIds.has(item.file_id))
        .map((item) => item.file_id)
      const current = (form.getFieldValue('attachment_file_ids') ?? []) as string[]
      form.setFieldValue('attachment_file_ids', [...current, ...newIds])
      onLedgerChange(result.data)
    } else {
      message.error(result.message)
    }
  }

  const handleDeleteAttachment = async (fileId: string) => {
    const result = await deleteDeviationAttachment(ledger.id, fileId)
    if (result.code === 200 && result.data) {
      const current = (form.getFieldValue('attachment_file_ids') ?? []) as string[]
      form.setFieldValue(
        'attachment_file_ids',
        current.filter((id) => id !== fileId),
      )
      message.success('附件已删除')
      onLedgerChange(result.data)
    } else {
      message.error(result.message)
    }
  }

  const referencedAttachments = referencedIds
    .map((fileId) => attachments.find((item) => item.file_id === fileId))
    .filter((item): item is DeviationAttachment => Boolean(item))

  const submitLabel =
    mode === 'submit'
      ? '提交审核'
      : mode === 'cross-dept'
        ? '提交本部门调查记录'
        : '追加调查记录'

  return (
    <Form<FormValues>
      form={form}
      layout="vertical"
      className="mt-3 rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface-soft,#fafafa)] p-3"
      initialValues={{ capa_proposals: [{}], has_urgent: false }}
      onFinish={handleSubmit}
      scrollToFirstError
    >
      {draftSavedAt && (
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-[#c7d7fb] bg-[#eff4ff] px-2.5 py-1.5 text-[12px] text-[#2f4b8f]">
          <span>草稿已暂存 · {formatDraftTime(draftSavedAt)}</span>
          <Button type="link" size="small" className="!h-auto !p-0 !text-[12px]" onClick={handleClearDraft}>
            清除草稿
          </Button>
        </div>
      )}

      {viaAttachment ? (
        <div className="mb-3 rounded-lg border border-blue-200 bg-blue-50 p-3 text-[13px] text-blue-800">
          已引用调查报告附件：下方文本与 CAPA 可不填，由审核人查阅文档。取消附件引用后将恢复必填。
        </div>
      ) : (
        <div className="mb-3 text-[12px] text-[var(--color-slate)]">
          填写调查记录，或在下方「调查文档」中上传/引用调查报告（二者满足其一即可提交）。
        </div>
      )}

      <Form.Item
        name="nonconformity_description"
        label="不符合事项描述"
        rules={viaAttachment ? [] : [{ required: true, whitespace: true, message: '请填写不符合事项描述' }]}
      >
        <TextArea rows={3} maxLength={4000} showCount placeholder="客观描述偏差事实：发生了什么、何时何地、涉及什么" />
      </Form.Item>

      <Form.Item
        name="root_cause_analysis"
        label="根本原因分析"
        rules={viaAttachment ? [] : [{ required: true, whitespace: true, message: '请填写根本原因分析' }]}
      >
        <TextArea rows={3} maxLength={4000} showCount placeholder="说明导致偏差的根本原因（人/机/料/法/环）" />
      </Form.Item>

      <Form.Item
        name="risk_assessment"
        label="风险评估"
        rules={viaAttachment ? [] : [{ required: true, whitespace: true, message: '请填写风险评估' }]}
      >
        <TextArea rows={3} maxLength={4000} showCount placeholder="评估对本批次/后续批次/患者与合规的影响" />
      </Form.Item>

      <div className="mb-1 text-[13px] font-medium">改进建议（CAPA）{viaAttachment ? '（可空）' : '，至少一条'}</div>
      <Form.List
        name="capa_proposals"
        rules={
          viaAttachment
            ? []
            : [
                {
                  validator: (_, value?: CapaRowValue[]) =>
                    value && value.length > 0 ? Promise.resolve() : Promise.reject(new Error('至少需要一条 CAPA 建议')),
                },
              ]
        }
      >
        {(fields, { add, remove }) => (
          <div className="mb-2 flex flex-col gap-2">
            {fields.map((field, index) => (
              <div key={field.key} className="flex flex-col gap-2 rounded-lg border border-[var(--color-hairline)] p-2 sm:flex-row sm:items-start">
                <span className="mt-1 w-5 shrink-0 text-center text-[12px] text-[var(--color-slate)]">{index + 1}</span>
                <Form.Item
                  name={[field.name, 'summary']}
                  rules={viaAttachment ? [] : [{ required: true, whitespace: true, message: '请填写 CAPA 内容简述' }]}
                  className="!mb-0 min-w-0 flex-1"
                >
                  <Input placeholder="CAPA 内容简述" maxLength={500} />
                </Form.Item>
                <Form.Item name={[field.name, 'executor']} className="!mb-0 w-full sm:w-[140px]">
                  <Input placeholder="执行人" maxLength={100} />
                </Form.Item>
                <Form.Item name={[field.name, 'due']} className="!mb-0 w-full sm:w-[150px]">
                  <DatePicker className="w-full" placeholder="预计完成日期" />
                </Form.Item>
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  aria-label="删除该条 CAPA"
                  onClick={() => remove(field.name)}
                  disabled={fields.length === 1}
                />
              </div>
            ))}
            <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({})}>
              增加一条 CAPA
            </Button>
          </div>
        )}
      </Form.List>

      <Form.Item name="has_urgent" valuePropName="checked" className="!mb-2">
        <Checkbox>
          <span className="inline-flex items-center gap-1 text-[13px]">
            <WarningOutlined className="text-amber-600" />
            有紧急处理措施
          </span>
        </Checkbox>
      </Form.Item>
      {hasUrgent && (
        <div className="mb-4 rounded-lg border border-amber-300 bg-amber-50 p-3">
          <Form.Item
            name="urgent_measures"
            label={<span className="text-amber-800">紧急处理措施</span>}
            rules={[{ required: true, whitespace: true, message: '勾选后请填写紧急处理措施' }]}
            className="!mb-0"
          >
            <TextArea rows={2} maxLength={2000} showCount placeholder="为防止偏差扩大已立即采取的措施" />
          </Form.Item>
        </div>
      )}

      <Form.Item
        name="attachment_file_ids"
        label="调查文档"
        extra="上传后自动引用到本记录；提交后文档只能预览与下载"
      >
        <Select
          mode="multiple"
          allowClear
          placeholder="从已上传的台账文档中选择（可先上传再选）"
          options={attachments.map((item) => ({ value: item.file_id, label: item.file_name }))}
          optionFilterProp="label"
          notFoundContent="暂无台账文档，可先上传"
        />
      </Form.Item>

      {referencedAttachments.length > 0 && (
        <div className="mb-3 flex flex-col gap-1.5">
          {referencedAttachments.map((attachment) => (
            <div
              key={attachment.file_id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-white px-2.5 py-1.5 transition-colors hover:bg-[var(--color-fill,#f4f4f5)]"
            >
              <span className="flex min-w-0 items-center gap-1.5 text-[12px]">
                <FileTextOutlined className="shrink-0 text-[var(--color-slate)]" />
                <span className="truncate text-[var(--color-ink)]">{attachment.file_name}</span>
                <span className="shrink-0 text-[var(--color-stone)]">{formatSize(attachment.size)}</span>
              </span>
              <Space size={2} className="shrink-0">
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  onClick={() => onPreviewAttachment?.(attachment)}
                >
                  预览
                </Button>
                <Button
                  type="link"
                  size="small"
                  icon={<DownloadOutlined />}
                  href={attachmentUrl(ledger.id, attachment.file_id)}
                >
                  下载
                </Button>
                {canDeleteAttachment && (
                  <Popconfirm
                    title="删除该附件？"
                    description="删除后将同时从本记录的引用中移除。"
                    onConfirm={() => handleDeleteAttachment(attachment.file_id)}
                  >
                    <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                      删除
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            </div>
          ))}
        </div>
      )}

      <Upload showUploadList={false} beforeUpload={(file) => { void handleUpload(file); return false }}>
        <Button size="small" icon={<UploadOutlined />} loading={uploading} className="mb-3">
          上传并挂到本记录
        </Button>
      </Upload>

      <Space className="w-full justify-end" size={8} wrap>
        <Button onClick={handleCancel} disabled={busy}>
          取消
        </Button>
        <Button onClick={() => void handleSaveDraft()} loading={savingDraft} disabled={busy}>
          暂存草稿
        </Button>
        <Button type="primary" htmlType="submit" loading={busy} disabled={savingDraft}>
          {submitLabel}
        </Button>
      </Space>

      <Modal
        open={submitConfirmOpen}
        title="确认提交审核？"
        okText="确认提交"
        cancelText="取消"
        confirmLoading={busy}
        onOk={() => void handleConfirmSubmit()}
        onCancel={() => setSubmitConfirmOpen(false)}
        destroyOnHidden
      >
        <div className="flex flex-col gap-2">
          <p className="text-[13px] text-[var(--color-slate)]">
            提交后进入部门负责人审核，本次提交说明会记录在「审核记录」中。
          </p>
          <TextArea
            rows={3}
            value={submitInfo}
            maxLength={500}
            showCount
            placeholder="提交信息（选填），如：已完成根本原因分析与 CAPA 制定"
            onChange={(event) => setSubmitInfo(event.target.value)}
          />
        </div>
      </Modal>
    </Form>
  )
}