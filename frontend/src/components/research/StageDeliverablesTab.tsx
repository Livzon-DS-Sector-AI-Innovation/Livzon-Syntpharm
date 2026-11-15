'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Card, Table, Tag, Button, Modal, Form, Input, Select, Collapse, Space, Progress, Empty, Upload, Dropdown, type MenuProps } from 'antd'
import {EditOutlined, DeleteOutlined, FileTextOutlined, CheckCircleOutlined, UploadOutlined, DownloadOutlined, HistoryOutlined, RobotOutlined, SyncOutlined, DownOutlined, FileWordOutlined} from '@ant-design/icons'
import {
  RdStageDeliverable, RdProjectStage, RdDeliverableStatus,
  DELIVERABLE_TYPES, DELIVERABLE_STATUS_LABELS, STAGE_LABELS, STAGE_ORDER,
} from '@/types/research/rd-project'
import { fetchDeliverables } from '@/lib/api/client/research/rd-project'
import { createDeliverable, updateDeliverable, deleteDeliverable, uploadDeliverableFile } from '@/actions/research/deliverables'
import { VersionHistoryDrawer } from './VersionHistoryDrawer'
import { DeliverableGenerateWizard } from './DeliverableGenerateWizard'
import { DocxPreviewModal } from './DocxPreviewModal'
import { MarkdownPreviewModal } from './MarkdownPreviewModal'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'
import { withReturnTo } from '@/lib/navigation/returnTo'
import { fetchBlob } from '@/lib/api/client/blob'

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

  const { can, loading: permLoading } = usePermission()

  const { data: deliverables = [], isLoading: loading } = useQuery({
    queryKey: ['deliverables', projectId],
    queryFn: async () => {
      const data = await fetchDeliverables(projectId)
      return data || []
    },
    enabled: !!projectId,
    // 有任务在跑时才 3 秒回源一次，全部落定后自动停；避免空闲时打后端
    refetchInterval: (query) => {
      const rows = query.state.data ?? []
      return rows.some((row) => row.generation?.status === 'queued' || row.generation?.status === 'running')
        ? 3000
        : false
    },
  })
  const [editModalOpen, setEditModalOpen] = useState(false)
  // AI 生成向导：记录当前操作的是哪个阶段的哪类交付文档
  const [genTarget, setGenTarget] = useState<{ stage: string; type: string; label: string; deliverableId?: string | null } | null>(null)
  const [editingItem, setEditingItem] = useState<RdStageDeliverable | null>(null)
  const [uploadingId, setUploadingId] = useState<string | null>(null)
  const [versionDrawerOpen, setVersionDrawerOpen] = useState(false)
  const [versionDrawerData, setVersionDrawerData] = useState<{stage: string; type: string; title: string; versions: RdStageDeliverable[]} | null>(null)
  // 附件预览：只对 Word 走弹层渲染，其他格式直接新窗口打开
  const [attachmentPreview, setAttachmentPreview] = useState<{ id: string; name: string } | null>(null)
  // 正文预览：表格行「查看内容」与编辑弹窗「预览」共用
  const [contentPreview, setContentPreview] = useState<{ title: string; markdown: string } | null>(null)
  const [form] = Form.useForm()
  const formContent = Form.useWatch('content', form)


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
              title: '交付文档',
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
                const generation = row.record.generation
                return (
                  <Space size={4} wrap>
                    <Tag color={statusColorMap[row.record.status as RdDeliverableStatus] || 'default'}>
                      {DELIVERABLE_STATUS_LABELS[row.record.status as RdDeliverableStatus] || row.record.status}
                    </Tag>
                    {generation?.status === 'queued' || generation?.status === 'running' ? (
                      <Tag color="processing" icon={<SyncOutlined spin />}>
                        {generation.progress ? `生成中 ${generation.progress}%` : '生成中'}
                      </Tag>
                    ) : generation?.status === 'failed' ? (
                      <Tag color="error">生成失败</Tag>
                    ) : generation?.status === 'completed' ? (
                      <Tag color="gold">{generation.slot_gap > 0 ? `待补充 ${generation.slot_gap} 项` : '已出稿待核对'}</Tag>
                    ) : null}
                  </Space>
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
                const sourceJobId = row.record.report_gen_job_id
                const sourceLink = sourceJobId ? (
                  <a
                    href={withReturnTo(
                      `/research/reports/generation/${sourceJobId}`,
                      `/research/projects/${projectId}?tab=deliverables`,
                    )}
                    style={{ fontSize: 11, color: '#1677ff' }}
                  >
                    源报告
                  </a>
                ) : null
                const fileName = row.record.file_name
                if (fileName) {
                  const record = row.record
                  const previewable = /\.docx?$/i.test(fileName)
                  return (
                    <Space size={4} wrap>
                      {previewable ? (
                        <Button
                          type="link"
                          size="small"
                          icon={<FileWordOutlined />}
                          style={{ padding: 0, fontSize: 12, height: 'auto' }}
                          title="点击在线预览"
                          onClick={() => setAttachmentPreview({ id: record.id, name: record.file_name as string })}
                        >
                          {record.file_name}
                        </Button>
                      ) : (
                        <a href={record.file_url || undefined} target="_blank" rel="noopener noreferrer" style={{ fontSize: 12 }}>
                          <FileWordOutlined /> {record.file_name}
                        </a>
                      )}
                      <span style={{ fontSize: 11, color: '#999' }}>
                        {formatFileSize(record.file_size)}
                      </span>
                      {sourceLink}
                    </Space>
                  )
                }
                if (sourceLink) return sourceLink
                return <span style={{ color: '#999', fontSize: 12 }}>未上传</span>
              },
            },
            {
              title: '操作',
              key: 'actions',
              width: 190,
              render: (_: unknown, row: DeliverableRow) => {
                const allVersions = deliverables.filter(d => d.stage === stage && d.deliverable_type === row.type)
                const generation = row.record?.generation
                const generating = generation?.status === 'queued' || generation?.status === 'running'
                const produced = !!row.record?.file_name || !!row.record?.report_gen_job_id
                const recordId = row.record?.id

                // 「查看」下拉：编辑/导出/上传/删除按权限逐项过滤，避免每行堆 6 个按钮
                const viewItems: MenuProps['items'] = []
                if (!permLoading) {
                  const canEdit = can(
                    row.record ? PERM.researchStageDeliverableUpdate : PERM.researchStageDeliverableCreate,
                  )
                  if (canEdit) {
                    viewItems.push({
                      key: 'edit',
                      icon: <EditOutlined />,
                      label: row.record ? '编辑' : '创建',
                      onClick: () =>
                        row.record
                          ? handleEdit(row.record)
                          : handleCreate(stage as RdProjectStage, row.type, row.label),
                    })
                  }
                  if (row.record?.content) {
                    viewItems.push({
                      key: 'preview',
                      icon: <FileTextOutlined />,
                      label: '查看内容',
                      onClick: () => row.record && setContentPreview({
                        title: `${row.record.title} · 内容`,
                        markdown: row.record.content ?? '',
                      }),
                    })
                    viewItems.push({
                      key: 'export',
                      icon: <DownloadOutlined />,
                      label: '导出 Markdown',
                      onClick: () => row.record && handleExport(row.record),
                    })
                  }
                  if (recordId && can(PERM.researchStageDeliverableCreate)) {
                    viewItems.push({
                      key: 'upload',
                      icon: <UploadOutlined />,
                      label: (
                        <Upload
                          showUploadList={false}
                          beforeUpload={(file) => {
                            handleUpload(file, recordId)
                            return false
                          }}
                        >
                          <span>{uploadingId === recordId ? '上传中…' : '上传附件'}</span>
                        </Upload>
                      ),
                    })
                  }
                  if (recordId && can(PERM.researchStageDeliverableDelete)) {
                    viewItems.push({
                      key: 'delete',
                      danger: true,
                      icon: <DeleteOutlined />,
                      label: '删除',
                      onClick: () => {
                        Modal.confirm({
                          title: '删除这条交付文档记录？',
                          content: '会连同它的历史版本一起删除，已下载到本地的文件不受影响。删除后不可恢复。',
                          okText: '删除',
                          okButtonProps: { danger: true },
                          cancelText: '取消',
                          onOk: () => handleDelete(recordId),
                        })
                      },
                    })
                  }
                }

                return (
                  <Space size="small">
                    <PermissionGate code={PERM.researchStageDeliverableCreate}>
                      <Button
                        type="link"
                        size="small"
                        icon={generating ? <SyncOutlined spin /> : <RobotOutlined />}
                        onClick={() =>
                          setGenTarget({
                            stage: stage as string,
                            type: row.type,
                            label: row.label,
                            deliverableId: recordId ?? null,
                          })
                        }
                      >
                        {generating ? '查看进度' : produced ? '重新生成' : 'AI 生成'}
                      </Button>
                    </PermissionGate>
                    {viewItems.length > 0 && (
                      <Dropdown menu={{ items: viewItems }} trigger={['click']}>
                        <Button type="link" size="small">
                          查看 <DownOutlined />
                        </Button>
                      </Dropdown>
                    )}
                    {allVersions.length > 1 && (
                      <Button
                        type="link"
                        size="small"
                        icon={<HistoryOutlined />}
                        onClick={() => handleShowVersions(stage as string, row.type, row.label)}
                      >
                        历史({allVersions.length})
                      </Button>
                    )}
                  </Space>
                )
              },
            },
          ]}
        />
      ),
    }
  })

  return (
    <div>
      <Card title="各阶段交付文档" extra={
        <span style={{ fontSize: 13, color: '#666' }}>
          共 {deliverables.length}/18 项 · 已完成 {deliverables.filter(d => d.status === 'completed' || d.status === 'approved').length} 项
        </span>
      }>
        {deliverables.length === 0 && !loading ? (
          <Empty description="还没有任何交付文档。展开下面某个阶段，点该阶段里的「新建」即可添加。" />
        ) : null}
        <Collapse
          items={collapseItems}
          defaultActiveKey={currentStage ? [currentStage] : ['initiation']}
          style={{ background: '#fff' }}
        />
      </Card>

      <Modal
        title={editingItem ? '编辑交付文档' : '新建交付文档'}
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

          <Form.Item
            name="content"
            label={(
              <Space size={8}>
                <span>内容摘要</span>
                <Button
                  type="link"
                  size="small"
                  style={{ padding: 0, height: 'auto', fontSize: 12 }}
                  onClick={() => setContentPreview({
                    title: `${form.getFieldValue('title') || '交付文档'} · 内容预览`,
                    markdown: formContent ?? '',
                  })}
                >
                  预览
                </Button>
              </Space>
            )}
          >
            <Input.TextArea rows={4} placeholder="这份交付文档写了什么，简单备注一下…" />
          </Form.Item>
        </Form>
      </Modal>

      {genTarget && (
        <DeliverableGenerateWizard
          open
          onClose={() => setGenTarget(null)}
          projectId={projectId}
          stage={genTarget.stage}
          deliverableType={genTarget.type}
          deliverableLabel={genTarget.label}
          deliverableId={genTarget.deliverableId ?? null}
          onSubmitted={invalidateDeliverables}
        />
      )}

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

      <DocxPreviewModal
        open={!!attachmentPreview}
        title={attachmentPreview?.name ?? '附件预览'}
        loadBlob={() =>
          fetchBlob(
            `/api/v1/research/rd-stage-deliverables/${attachmentPreview?.id}/download`,
            '附件还没有生成',
          )
        }
        onDownload={() => {
          if (!attachmentPreview) return
          const url = `/api/v1/research/rd-stage-deliverables/${attachmentPreview.id}/download`
          // 后端仍是 attachment 响应，这里用隐藏 <a> 触发浏览器原生下载
          const link = document.createElement('a')
          link.href = url
          link.download = attachmentPreview.name
          document.body.appendChild(link)
          link.click()
          document.body.removeChild(link)
        }}
        onClose={() => setAttachmentPreview(null)}
      />

      <MarkdownPreviewModal
        open={!!contentPreview}
        title={contentPreview?.title ?? '内容预览'}
        markdown={contentPreview?.markdown ?? ''}
        onClose={() => setContentPreview(null)}
      />

    </div>
  )
}
