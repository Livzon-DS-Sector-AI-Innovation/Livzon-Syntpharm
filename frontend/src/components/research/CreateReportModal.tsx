'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert, App, Button, Form, Input, Modal, Select, Spin, Tag, Tooltip,
} from 'antd'
import { CloudUploadOutlined, EyeOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { createReport as createReportAction, updateReport } from '@/actions/research/rd-project'
import { submitReportGenJob } from '@/actions/research/report-gen'
import { fetchDeliverableTemplates } from '@/lib/api/client/research/rd-project'
import { downloadDeliverableTemplate } from '@/lib/api/client/research/doc-gen'
import { fetchReportGenJobs } from '@/lib/api/client/research/report-gen'
import { useDocxPreview } from './useDocxPreview'
import { KnowledgeBaseModal } from './KnowledgeBaseModal'
import { useKnowledgeBase, useKbDocuments, summarizeKb } from './useKnowledgeBase'
import {
  RdDeliverableTemplate, RdReport, REPORT_TYPE_LABELS, STAGE_LABELS, deliverableTypeLabel,
} from '@/types/research/rd-project'
import { TERMS } from '@/lib/ui/research-copy'

interface Props {
  open: boolean
  projectId: string
  onCancel: () => void
  /** 生成任务已提交 / 报告已保存后触发，父组件据此刷新列表 */
  onCreated?: () => void
  /** 编辑模式传入当前报告 */
  editingReport?: RdReport | null
  /** 当前生效的正文生成模型，由列表页统一读取后传入，避免重复请求 */
  modelLabel?: string
}

interface ReportFormValues {
  title: string
  report_type: string
  stage?: string
  version: string
  doc_code?: string
  drug_name?: string
  template_id?: string
  summary?: string
  supplement?: string
}

/**
 * 新建 / 编辑研发报告。
 *
 * 「AI 生成报告」= 先落报告记录，再提交一条异步生成任务，然后立刻关闭弹窗；
 * 执行过程与成品都在列表页的「执行过程」里看，弹窗不承载进度状态机。
 */
export function CreateReportModal({ open, projectId, onCancel, onCreated, editingReport, modelLabel }: Props) {
  const { message: msgApi } = App.useApp()
  const [form] = Form.useForm<ReportFormValues>()
  const isEditMode = !!editingReport
  const queryClient = useQueryClient()
  const [submitting, setSubmitting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [kbModalOpen, setKbModalOpen] = useState(false)

  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: ['deliverable-templates', 'active'],
    queryFn: async (): Promise<RdDeliverableTemplate[]> => {
      try {
        return await fetchDeliverableTemplates({ is_active: true })
      } catch (e: unknown) {
        msgApi.error(e instanceof Error ? e.message : '加载已启用模板失败')
        return []
      }
    },
    enabled: open,
    staleTime: 30_000,
  })

  const templateId = Form.useWatch('template_id', form)
  const selectedTpl = useMemo(
    () => templates.find((tpl) => tpl.id === templateId),
    [templates, templateId],
  )

  // ─── 项目知识库：AI 生成报告的资料源 ───
  const { data: knowledgeBases = [] } = useKnowledgeBase(projectId, open)
  const kb = useMemo(() => knowledgeBases[0], [knowledgeBases])
  const { data: kbDocuments = [] } = useKbDocuments(kb?.id)
  const kbSummary = useMemo(() => summarizeKb(kbDocuments), [kbDocuments])

  const refreshKb = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['knowledge-bases', projectId] })
    queryClient.invalidateQueries({ queryKey: ['kb-documents', kb?.id] })
  }, [queryClient, projectId, kb?.id])

  // ─── 编辑模式：报告本体字段 + 最近一次任务的生成输入快照 ───
  useEffect(() => {
    if (!open) return
    form.resetFields()
    if (!editingReport) {
      form.setFieldsValue({ report_type: 'summary', version: 'v1.0' })
      return
    }
    form.setFieldsValue({
      title: editingReport.title,
      report_type: editingReport.report_type,
      stage: editingReport.stage || undefined,
      version: editingReport.version,
      summary: editingReport.summary || '',
    })
    // doc_code / drug_name / supplement 只存在于任务快照里，从最近一次任务回填
    let cancelled = false
    fetchReportGenJobs({ reportId: editingReport.id })
      .then((list) => {
        if (cancelled) return
        const latest = list.items[0]
        if (!latest) return
        form.setFieldsValue({
          doc_code: latest.doc_code || '',
          drug_name: latest.drug_name || '',
          supplement: latest.supplement_text || '',
          template_id: latest.deliverable_template_id || undefined,
        })
      })
      .catch(() => {
        // 回填失败不影响编辑：用户可重新填写
      })
    return () => { cancelled = true }
  }, [open, editingReport, form])

  // ─── 模板母本预览 ───
  const [tplPreviewOpen, setTplPreviewOpen] = useState(false)
  const [tplPreviewName, setTplPreviewName] = useState('')
  const tplPreviewRef = useRef<HTMLDivElement | null>(null)
  const { loading: tplPreviewLoading, error: tplPreviewError, renderDocx, reset } = useDocxPreview()

  const openTplPreview = async (tpl: RdDeliverableTemplate) => {
    setTplPreviewName(tpl.file_name || tpl.name)
    setTplPreviewOpen(true)
    try {
      const blob = await downloadDeliverableTemplate(tpl.id)
      setTimeout(() => { void renderDocx(blob, tplPreviewRef.current) }, 0)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '加载模板失败')
    }
  }

  const closeTplPreview = () => {
    setTplPreviewOpen(false)
    reset()
    if (tplPreviewRef.current) tplPreviewRef.current.innerHTML = ''
  }

  // ─── 保存（仅报告记录，不触发生成） ───
  const handleSave = async () => {
    if (saving || submitting) return
    let values: ReportFormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    setSaving(true)
    try {
      if (editingReport) {
        await updateReport(editingReport.id, {
          title: values.title,
          report_type: values.report_type,
          stage: values.stage || null,
          version: values.version,
          summary: values.summary?.trim() || null,
        })
        msgApi.success('已保存')
      } else {
        await createReportAction(projectId, {
          title: values.title,
          report_type: values.report_type,
          stage: values.stage || null,
          status: 'draft',
          version: values.version || 'v1.0',
          summary: values.summary?.trim() || null,
        })
        msgApi.success('已创建')
      }
      onCreated?.()
      onCancel()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : (editingReport ? '保存失败' : '创建失败'))
    } finally {
      setSaving(false)
    }
  }

  // ─── AI 生成：落库报告 → 提交异步任务 → 关闭弹窗 ───
  const handleGenerate = async () => {
    if (submitting || saving) return
    let values: ReportFormValues
    try {
      values = await form.validateFields()
    } catch {
      return
    }
    if (!selectedTpl) {
      msgApi.warning('请先选一份 Word 模板文件')
      return
    }
    if (!selectedTpl.file_object_key) {
      msgApi.warning('这个模板还没有上传 Word 文件，不能生成。请先到「交付文档模板」页给它上传文件。')
      return
    }
    setSubmitting(true)
    try {
      // 1) 报告记录：有则更新，无则新建
      let reportId = editingReport?.id
      if (reportId) {
        await updateReport(reportId, {
          title: values.title,
          report_type: values.report_type,
          stage: values.stage || null,
          version: values.version,
          summary: values.summary?.trim() || null,
        })
      } else {
        const created = await createReportAction(projectId, {
          title: values.title,
          report_type: values.report_type,
          stage: values.stage || null,
          status: 'draft',
          version: values.version || 'v1.0',
          summary: values.summary?.trim() || null,
        })
        reportId = (created as { data?: { id?: string } } | null)?.data?.id
        if (!reportId) throw new Error('创建报告失败，请重试')
      }

      // 2) 异步生成任务：后台 Agent 读母本 + 检索知识库 + 回写 docx
      await submitReportGenJob({
        report_id: reportId,
        project_id: projectId,
        deliverable_template_id: selectedTpl.id,
        doc_code: values.doc_code?.trim() || null,
        drug_name: values.drug_name?.trim() || null,
        supplement_text: values.supplement?.trim() || null,
      })

      msgApi.success('已开始生成，可以到那份报告的「生成详情」里看进度')
      onCreated?.()
      onCancel()
    } catch (e: unknown) {
      console.error('[CreateReportModal] 提交生成任务失败:', e)
      msgApi.error(e instanceof Error ? e.message : '提交生成任务失败')
    } finally {
      setSubmitting(false)
    }
  }

  const kbHint = kb
    ? `会参考知识库「${kb.name}」里的资料（已入库 ${kbSummary.parsed} 份 / 共 ${kbSummary.total || kb.document_count} 份）`
    : '这个项目还没有知识库。AI 只能用项目登记信息和下面的补充说明来写，找不到依据的项会标成「待补充」。'

  return (
    <>
      <Modal
        title={isEditMode ? '编辑报告' : '新建报告'}
        open={open}
        onCancel={onCancel}
        width={960}
        centered
        destroyOnClose
        footer={[
          <Button key="cancel" onClick={onCancel}>取消</Button>,
          <Tooltip key="save" title="只登记这份报告，先不生成文档；以后可以再点「编辑」用 AI 生成">
            <Button onClick={handleSave} loading={saving} disabled={submitting}>
              只保存，暂不生成
            </Button>
          </Tooltip>,
          <Tooltip
            key="generate"
            title={selectedTpl ? '选好模板文件后，AI 会在这份 Word 里填内容，生成可直接下载的文档' : '先在下面选一份 Word 模板文件'}
          >
            <span>
              <Button
                type="primary"
                icon={<ThunderboltOutlined />}
                onClick={handleGenerate}
                loading={submitting}
                disabled={saving || !selectedTpl}
              >
                用 AI 生成文档
              </Button>
            </span>
          </Tooltip>,
        ]}
      >
        {modelLabel && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
            message={`这次生成会用模型：${modelLabel}`}
            description="要换模型，请到报告列表页的「生成设置」里改。已经提交的任务会沿用提交那一刻的模型，不受影响。"
          />
        )}
        <Form form={form} layout="vertical" initialValues={{ report_type: 'summary', version: 'v1.0' }}>
          <Form.Item name="title" label="报告标题" rules={[{ required: true, message: '请输入报告标题' }]}>
            <Input placeholder="如：化合物A研发总结报告" />
          </Form.Item>

          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item name="report_type" label="报告类型" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Select options={Object.entries(REPORT_TYPE_LABELS).map(([value, label]) => ({ value, label }))} />
            </Form.Item>
            <Form.Item name="stage" label="所属阶段" style={{ flex: 1 }}>
              <Select
                allowClear
                options={[{ value: '', label: '无' }, ...Object.entries(STAGE_LABELS).map(([value, label]) => ({ value, label }))]}
              />
            </Form.Item>
            <Form.Item name="version" label="版本号" rules={[{ required: true }]} style={{ flex: 1 }}>
              <Input placeholder="如：v1.0" />
            </Form.Item>
          </div>

          <div style={{ display: 'flex', gap: 16 }}>
            <Form.Item
              name="doc_code"
              label={TERMS.fileCode.name}
              extra={TERMS.fileCode.hint}
              style={{ flex: 1 }}
            >
              <Input placeholder="如：RD-2024-001" />
            </Form.Item>
            <Form.Item name="drug_name" label="品种名称" style={{ flex: 1 }}>
              <Input placeholder="如：化合物A" />
            </Form.Item>
          </div>

          <Form.Item
            name="template_id"
            label={TERMS.templateFile.name}
            extra={TERMS.templateFile.hint}
            rules={[{ required: true, message: '请选一份 Word 模板文件' }]}
          >
            <Select
              placeholder={templatesLoading ? '加载中…' : '选一份 Word 模板文件'}
              showSearch
              allowClear
              loading={templatesLoading}
              optionFilterProp="label"
              notFoundContent={templatesLoading ? <Spin size="small" /> : '还没有可用的交付文档模板，先到「交付文档模板」页上传'}
              options={templates.map((tpl) => ({ value: tpl.id, label: tpl.name }))}
            />
          </Form.Item>

          {selectedTpl && (
            <div
              style={{
                marginTop: -16,
                marginBottom: 16,
                padding: '12px 16px',
                background: '#f6ffed',
                borderRadius: 6,
                border: '1px solid #b7eb8f',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, marginBottom: 4 }}>
                    {selectedTpl.name}
                    {selectedTpl.current_version_no ? (
                      <Tag color="green" style={{ marginLeft: 8 }}>v{selectedTpl.current_version_no}</Tag>
                    ) : (
                      <Tag style={{ marginLeft: 8 }}>还没上传文件</Tag>
                    )}
                    <Tag color="blue" style={{ marginLeft: 4 }}>
                      {STAGE_LABELS[selectedTpl.stage as keyof typeof STAGE_LABELS] ?? selectedTpl.stage}
                    </Tag>
                  </div>
                  {selectedTpl.description && (
                    <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>{selectedTpl.description}</div>
                  )}
                  <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#8c8c8c' }}>
                    <span>交付文档类型：{deliverableTypeLabel(selectedTpl.deliverable_type)}</span>
                    <span>模板文件：{selectedTpl.file_name || '还没上传'}</span>
                  </div>
                </div>
                <Button
                  type="link"
                  size="small"
                  icon={<EyeOutlined />}
                  disabled={!selectedTpl.file_object_key}
                  onClick={() => openTplPreview(selectedTpl)}
                >
                  预览模板文件
                </Button>
              </div>
            </div>
          )}

          {!kb && (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              message="未检测到项目知识库"
              description="AI 只能用项目登记信息和下面的补充说明来写，找不到依据的填充项会标成「待补充」。"
            />
          )}

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
              <div style={{ fontSize: 13, color: '#595959' }}>{kbHint}</div>
              <Button htmlType="button" icon={<CloudUploadOutlined />} onClick={() => setKbModalOpen(true)}>
                {kb ? '上传 / 管理资料' : '创建知识库并上传资料'}
              </Button>
            </div>
          </Form.Item>

          <Form.Item name="summary" label="摘要">
            <Input.TextArea rows={2} placeholder="简要描述本报告内容..." />
          </Form.Item>

          <Form.Item name="supplement" label="补充信息">
            <Input.TextArea rows={3} placeholder="补充说明信息，AI 生成时会一并参考..." />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        open={tplPreviewOpen}
        title={`预览模板文件 - ${tplPreviewName}`}
        width={960}
        onCancel={closeTplPreview}
        footer={<Button onClick={closeTplPreview}>关闭</Button>}
        destroyOnClose
      >
        {tplPreviewError && <Alert type="error" showIcon message={tplPreviewError} style={{ marginBottom: 12 }} />}
        {tplPreviewLoading && (
          <div style={{ textAlign: 'center', padding: '40px 0' }}><Spin tip="加载模板中..." /></div>
        )}
        <div
          ref={tplPreviewRef}
          style={{ maxHeight: '72vh', overflow: 'auto', background: '#f5f5f5', padding: 8 }}
        />
      </Modal>

      <KnowledgeBaseModal
        open={kbModalOpen}
        projectId={projectId}
        onClose={() => setKbModalOpen(false)}
        onChanged={refreshKb}
      />
    </>
  )
}