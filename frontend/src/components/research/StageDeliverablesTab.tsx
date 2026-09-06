'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Card, Table, Tag, Button, Modal, Form, Input, Select, Collapse, Space, Popconfirm, Progress, Empty, Upload } from 'antd'
import {EditOutlined, DeleteOutlined, FileTextOutlined, CheckCircleOutlined, UploadOutlined, DownloadOutlined, HistoryOutlined, RobotOutlined} from '@ant-design/icons'
import {
  RdStageDeliverable, RdProjectStage, RdDeliverableStatus,
  DELIVERABLE_TYPES, DELIVERABLE_STATUS_LABELS, STAGE_LABELS, STAGE_ORDER,
} from '@/types/research/rd-project'
import { fetchDeliverables } from '@/lib/api/client/research/rd-project'
import { createDeliverable, updateDeliverable, deleteDeliverable, uploadDeliverableFile } from '@/actions/research/deliverables'
import { VersionHistoryDrawer } from './VersionHistoryDrawer'
import { fetchDeliverableTemplates } from '@/lib/api/client/research/rd-project'
import { generateReport } from '@/actions/research/rd-project'

interface Props {

  projectId: string
  currentStage?: RdProjectStage | null
}

// Row type for deliverable table
interface DeliverableRow {
  type: string
  label: string
  record?: RdStageDeliverable
}

const statusColorMap: Record<RdDeliverableStatus, string> = {
  draft: 'default',
  in_progress: 'processing',
  completed: 'success',
  approved: 'green',
}

const stageColorMap: Record<string, string> = {
  initiation: 'blue',
  route_dev: 'purple',
  optimization: 'orange',
  pilot: 'cyan',
  validation: 'green',
  filing: 'pink',
}

const formatFileSize = (bytes: number | null) => {
  if (!bytes) return '-'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function StageDeliverablesTab({ projectId, currentStage }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()

  const { data: deliverables = [], isLoading: loading } = useQuery({
    queryKey: ['deliverables', projectId],
    queryFn: async () => {
      const data = await fetchDeliverables(projectId)
      return data || []
    },
    enabled: !!projectId,
  })
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<RdStageDeliverable | null>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const [versionDrawerOpen, setVersionDrawerOpen] = useState(false)
  const [versionDrawerData, setVersionDrawerData] = useState<{stage: string; type: string; title: string; versions: RdStageDeliverable[]} | null>(null)
  const [aiGenerateModalOpen, setAiGenerateModalOpen] = useState(false)
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiGenerateTarget, setAiGenerateTarget] = useState<{stage: string; type: string; title: string} | null>(null)
  const [aiResult, setAiResult] = useState<string>('')
  const [templateFilter, setTemplateFilter] = useState<{stage: string; type: string} | null>(null)

  const { data: templates = [] } = useQuery({
    queryKey: ['deliverable-templates', templateFilter?.stage, templateFilter?.type],
    queryFn: async () => {
      if (!templateFilter) return []
      const allTemplates = await fetchDeliverableTemplates({ 
        stage: templateFilter.stage, 
        deliverable_type: templateFilter.type, 
        is_active: true 
      })
      return allTemplates || []
    },
    enabled: !!templateFilter,
  })
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [additionalContext, setAdditionalContext] = useState('')
  const [form] = Form.useForm()


  const handleExport = (record: RdStageDeliverable) => {
    const md = record.content || `# ${record.title}\n\n暂无内容`
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${record.title || record.deliverable_type}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    msgApi.success('导出成功')
  }

  const invalidateDeliverables = () => queryClient.invalidateQueries({ queryKey: ['deliverables', projectId] })

  const handleCreate = (stage: RdProjectStage, deliverableType: string, title: string) => {
    setEditingItem(null)
    form.setFieldsValue({
      stage,
      deliverable_type: deliverableType,
      title,
      status: 'draft',
      version: 'v1.0',
      content: '',
    })
    setEditModalOpen(true)
  }

  const handleEdit = (record: RdStageDeliverable) => {
    setEditingItem(record)
    form.setFieldsValue({
      stage: record.stage,
      deliverable_type: record.deliverable_type,
      title: record.title,
      status: record.status,
      version: record.version,
      content: record.content || '',
    })
    setEditModalOpen(true)
  }

  const handleContentFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      form.setFieldsValue({ content })
      msgApi.success(`已导入文件: ${file.name}`)
    }
    reader.readAsText(file)
    return false
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    try {
      if (editingItem) {
        await updateDeliverable(editingItem.id, {
          title: values.title,
          status: values.status,
          version: values.version,
          content: values.content,
        })
        msgApi.success('更新成功')
      } else {
        await createDeliverable({
          project_id: projectId,
          stage: values.stage,
          deliverable_type: values.deliverable_type,
          title: values.title,
          status: values.status,
          version: values.version,
          content: values.content,
        })
        msgApi.success('创建成功')
      }
      setEditModalOpen(false)
      form.resetFields()
      invalidateDeliverables()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteDeliverable(id)
      msgApi.success('已删除')
      invalidateDeliverables()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  const handleUpload = async (file: File, deliverableId: string) => {
    setUploadingId(deliverableId)
    try {
      const formData = new FormData()
      formData.append('file', file)
      await uploadDeliverableFile(deliverableId, formData)
      msgApi.success('上传成功')
      invalidateDeliverables()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '上传失败')
    } finally {
      setUploadingId(null)
    }
    return false
  }

  const handleAiGenerate = async (stage: string, type: string, title: string) => {
    setAiGenerateTarget({ stage, type, title })
    setAiResult('')
    setSelectedTemplateId(null)
    setAdditionalContext('')
    setAiGenerateModalOpen(true)
    
    // 加载可用模板
    setTemplateFilter({ stage, type })
  }


  const handleExportAiResult = () => {
    if (!aiResult || !aiGenerateTarget) return
    const blob = new Blob([aiResult], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${aiGenerateTarget.title || aiGenerateTarget.type}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    msgApi.success('导出成功')
  }

  const handleSaveAsDeliverable = async () => {
    if (!aiGenerateTarget || !aiResult) return
    try {
      await createDeliverable({
        project_id: projectId,
        stage: aiGenerateTarget.stage,
        deliverable_type: aiGenerateTarget.type,
        title: aiGenerateTarget.title,
        status: 'draft',
        version: 'v1.0',
        content: aiResult,
      })
      msgApi.success('已保存为交付物')
      setAiGenerateModalOpen(false)
      invalidateDeliverables()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '保存失败')
    }
  }

  const doAiGenerate = async () => {
    if (!aiGenerateTarget) return
    setAiGenerating(true)
    try {
      const result = await generateReport({
        project_id: projectId,
        deliverable_type: aiGenerateTarget.type,
        template_id: selectedTemplateId || undefined,
        additional_context: additionalContext || undefined,
      })
      setAiResult(result.content)
      msgApi.success('报告生成成功')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : 'AI 生成失败')
    } finally {
      setAiGenerating(false)
    }
  }

  const handleShowVersions = (stage: string, deliverableType: string, title: string) => {
    const versions = deliverables.filter(d => d.stage === stage && d.deliverable_type === deliverableType)
    setVersionDrawerData({ stage, type: deliverableType, title, versions })
    setVersionDrawerOpen(true)
  }

  const getStageData = (stage: RdProjectStage) => {
    const types = DELIVERABLE_TYPES[stage] || []
    const stageItems = deliverables.filter(d => d.stage === stage)
    const completed = stageItems.filter(d => d.status === 'completed' || d.status === 'approved').length
    const total = types.length
    const progress = total > 0 ? Math.round((completed / total) * 100) : 0
    return { types, stageItems, completed, total, progress }
  }

  const findItem = (stageItems: RdStageDeliverable[], deliverableType: string) => {
    return stageItems.find(d => d.deliverable_type === deliverableType)
  }

  const collapseItems = STAGE_ORDER.map(stage => {
    const { types, stageItems, completed, total, progress } = getStageData(stage as RdProjectStage)

    return {
      key: stage,
      label: (
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, width: '100%' }}>
          <Tag color={stageColorMap[stage]}>{STAGE_LABELS[stage as keyof typeof STAGE_LABELS] || stage}</Tag>
          <span style={{ fontSize: 13, color: '#666' }}>{completed}/{total} 项完成</span>
          <Progress percent={progress} size="small" style={{ width: 120, margin: 0 }} />
          {progress === 100 && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
        </div>
      ),
      children: (
        <Table
          dataSource={types.map(t => {
            const item = findItem(stageItems, t.type)
            return { ...t, record: item }
          })}
          rowKey="type"
          size="small"
          pagination={false}
          columns={[
            {
              title: '交付物',
              dataIndex: 'label',
              key: 'label',
              render: (label: string, row: DeliverableRow) => (
                <Space>
                  <FileTextOutlined style={{ color: row.record ? '#1677ff' : '#bbb' }} />
                  <span style={{ color: row.record ? '#333' : '#999' }}>{label}</span>
                </Space>
              ),
            },
            {
              title: '状态',
              key: 'status',
              width: 100,
              render: (_: unknown, row: DeliverableRow) => {
                if (!row.record) return <Tag>未创建</Tag>
                return (
                  <Tag color={statusColorMap[row.record.status as RdDeliverableStatus] || 'default'}>
                    {DELIVERABLE_STATUS_LABELS[row.record.status as RdDeliverableStatus] || row.record.status}
                  </Tag>
                )
              },
            },
            {
              title: '版本',
              key: 'version',
              width: 80,
              render: (_: unknown, row: DeliverableRow) => row.record?.version || '-',
            },
            {
              title: '附件',
              key: 'file',
              width: 200,
              render: (_: unknown, row: DeliverableRow) => {
                if (!row.record) return '-'
                if (row.record.file_name) {
                  return (
                    <Space>
                      <a href={row.record.file_url || undefined} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>
                        <DownloadOutlined /> {row.record.file_name}
                      </a>
                      <span style={{ fontSize: 11, color: '#999' }}>
                        {formatFileSize(row.record.file_size)}
                      </span>
                    </Space>
                  )
                }
                return <span style={{ color: '#999', fontSize: 12 }}>未上传</span>
              },
            },
            {
              title: '操作',
              key: 'actions',
              width: 180,
              render: (_: unknown, row: DeliverableRow) => (
                <Space size="small">
                  {(() => {
                    const allVersions = deliverables.filter(d => d.stage === stage && d.deliverable_type === row.type)
                    const hasMultiple = allVersions.length > 1
                    return (
                      <>
                        <Button
                          type="link"
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => row.record ? handleEdit(row.record) : handleCreate(stage as RdProjectStage, row.type, row.label)}
                        >
                          {row.record ? '编辑' : '创建'}
                        </Button>
                        {hasMultiple && (
                          <Button
                            type="link"
                            size="small"
                            icon={<HistoryOutlined />}
                            onClick={() => handleShowVersions(stage as string, row.type, row.label)}
                          >
                            历史({allVersions.length})
                          </Button>
                        )}
                        <Button
                          type="link"
                          size="small"
                          icon={<RobotOutlined />}
                          onClick={() => handleAiGenerate(stage as string, row.type, row.label)}
                        >
                          AI生成
                        </Button>
                      </>
                    )
                  })()}
                  {row.record && (
                    <>
                      <Button
                          type="link"
                          size="small"
                          icon={<DownloadOutlined />}
                          onClick={() => row.record && handleExport(row.record)}
                          disabled={!row.record.content}
                        >
                          导出
                        </Button>
                      <Upload
                        showUploadList={false}
                        beforeUpload={(file) => { if (row.record) handleUpload(file, row.record.id); return false }}
                        disabled={!row.record || uploadingId === row.record.id}
                      >
                        <Button
                          type="link"
                          size="small"
                          icon={<UploadOutlined />}
                          loading={!!row.record && uploadingId === row.record.id}
                        >
                          上传
                        </Button>
                      </Upload>
                      <Popconfirm title="确认删除？" onConfirm={() => row.record && handleDelete(row.record.id)} okText="删除" cancelText="取消">
                        <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                      </Popconfirm>
                    </>
                  )}
                </Space>
              ),
            },
          ]}
        />
      ),
    }
  })

  return (
    <div>
      <Card title="阶段交付物管理" extra={
        <span style={{ fontSize: 13, color: '#666' }}>
          共 {deliverables.length}/18 项 · 已完成 {deliverables.filter(d => d.status === 'completed' || d.status === 'approved').length} 项
        </span>
      }>
        {deliverables.length === 0 && !loading ? (
          <Empty description="暂无交付物记录，请在各阶段中创建" />
        ) : null}
        <Collapse
          items={collapseItems}
          defaultActiveKey={currentStage ? [currentStage] : ['initiation']}
          style={{ background: '#fff' }}
        />
      </Card>

      <Modal
        title={editingItem ? '编辑交付物' : '创建交付物'}
        open={editModalOpen}
        onOk={handleSave}
        onCancel={() => { setEditModalOpen(false); form.resetFields() }}
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请输入标题' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select options={[
              { value: 'draft', label: '草稿' },
              { value: 'in_progress', label: '编写中' },
              { value: 'completed', label: '已完成' },
              { value: 'approved', label: '已批准' },
            ]} />
          </Form.Item>
          <Form.Item name="version" label="版本号">
            <Input placeholder="如 v1.0" />
          </Form.Item>
          <Form.Item label="导入内容文件">
            <Upload
              beforeUpload={handleContentFileUpload}
              showUploadList={false}
              accept=".md,.txt,.markdown"
            >
              <Button icon={<UploadOutlined />} size="small">选择文件 (.md/.txt)</Button>
            </Upload>
          </Form.Item>

          <Form.Item name="content" label="内容摘要">
            <Input.TextArea rows={4} placeholder="交付物内容摘要或备注..." />
          </Form.Item>
        </Form>
      </Modal>

      {versionDrawerData && (
        <VersionHistoryDrawer
          open={versionDrawerOpen}
          onClose={() => { setVersionDrawerOpen(false); setVersionDrawerData(null) }}
          projectId={projectId}
          stage={versionDrawerData.stage}
          deliverableType={versionDrawerData.type}
          title={versionDrawerData.title}
          versions={versionDrawerData.versions}
          onRefresh={invalidateDeliverables}
        />
      )}

      {/* AI 报告生成模态框 */}
      <Modal
        title={`AI 生成报告 - ${aiGenerateTarget?.title || ''}`}
        open={aiGenerateModalOpen}
        onCancel={() => setAiGenerateModalOpen(false)}
        width={800}
        footer={[
          <Button key="cancel" onClick={() => setAiGenerateModalOpen(false)}>取消</Button>,
          <Button key="export" disabled={!aiResult} onClick={handleExportAiResult} icon={<DownloadOutlined />}>导出文件</Button>,
          <Button key="save" disabled={!aiResult} onClick={handleSaveAsDeliverable} icon={<FileTextOutlined />}>保存为交付物</Button>,
          <Button key="generate" type="primary" loading={aiGenerating} onClick={doAiGenerate} icon={<RobotOutlined />}>
            {aiResult ? '重新生成' : '生成报告'}
          </Button>,
        ]}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8 }}>
            <strong>选择模板（可选）：</strong>
            <Select
              style={{ width: '100%', marginTop: 8 }}
              placeholder="选择报告模板（可选）"
              value={selectedTemplateId}
              onChange={setSelectedTemplateId}
              allowClear
              options={[
                ...templates.map(t => ({ value: t.id, label: t.name })),
              ]}
            />
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong>额外要求（可选）：</strong>
            <Input.TextArea
              rows={3}
              placeholder="输入额外的生成要求..."
              value={additionalContext}
              onChange={(e) => setAdditionalContext(e.target.value)}
            />
          </div>
        </div>
        {aiResult && (
          <div>
            <strong>生成结果：</strong>
            <div style={{ marginTop: 8, padding: 16, background: '#f5f5f5', borderRadius: 4, maxHeight: 400, overflow: 'auto' }}>
              <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', margin: 0 }}>{aiResult}</pre>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
