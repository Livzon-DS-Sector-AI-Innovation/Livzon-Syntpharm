'use client'

import { useState, useEffect } from 'react'
import { App, Card, Table, Button, Drawer, Form, Input, Select, Tag, Space, Popconfirm, Switch, Upload } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, UploadOutlined, DownloadOutlined, InboxOutlined } from '@ant-design/icons'
import { fetchDeliverableTemplates } from '@/lib/api/client/research/rd-project'
import { RdDeliverableTemplate, STAGE_LABELS, DELIVERABLE_TYPES, RdProjectStage } from '@/types/research/rd-project'
import { createDeliverableTemplate, updateDeliverableTemplate, deleteDeliverableTemplate } from '@/actions/research/rd-project'

const { TextArea } = Input

export function DeliverableTemplatePage() {
  const { message: msgApi } = App.useApp()
  const [templates, setTemplates] = useState<RdDeliverableTemplate[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<RdDeliverableTemplate | null>(null)
  const [form] = Form.useForm()


  const [batchUploading, setBatchUploading] = useState(false)

  const handleBatchUpload = async (file: File) => {
    setBatchUploading(true)
    const reader = new FileReader()
    reader.onload = async (e) => {
      const templateContent = e.target?.result as string
      const fileName = file.name.replace(/\.(md|txt|markdown)$/i, '')
      try {
        await createDeliverableTemplate({
          name: fileName,
          template_content: templateContent,
          is_active: true,
        })
        msgApi.success(`模板 "${fileName}" 创建成功`)
        loadData()
      } catch (err: any) {
        msgApi.error(`创建失败: ${err.message}`)
      } finally {
        setBatchUploading(false)
      }
    }
    reader.readAsText(file)
    return false
  }

  const handleExportTemplate = (record: RdDeliverableTemplate) => {
    const md = record.template_content || `# ${record.name}\n\n暂无内容`
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${record.name}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    msgApi.success('导出成功')
  }

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchDeliverableTemplates()
      setTemplates(data)
    } catch (e: any) {
      msgApi.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [])

  const openCreate = () => {
    setEditingTemplate(null)
    form.resetFields()
    form.setFieldsValue({ is_active: true })
    setDrawerOpen(true)
  }

  const openEdit = (template: RdDeliverableTemplate) => {
    setEditingTemplate(template)
    form.setFieldsValue({
      name: template.name,
      stage: template.stage,
      deliverable_type: template.deliverable_type,
      description: template.description,
      template_content: template.template_content,
      is_active: template.is_active,
    })
    setDrawerOpen(true)
  }

  const handleFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target?.result as string
      form.setFieldsValue({ template_content: content })
      msgApi.success(`已导入文件: ${file.name}`)
    }
    reader.readAsText(file)
    return false
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      if (editingTemplate) {
        await updateDeliverableTemplate(editingTemplate.id, values)
        msgApi.success('更新成功')
      } else {
        await createDeliverableTemplate(values)
        msgApi.success('创建成功')
      }
      setDrawerOpen(false)
      loadData()
    } catch (e: any) {
      if (e.errorFields) return
      msgApi.error(e.message || '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
    await deleteDeliverableTemplate(id)
    msgApi.success('删除成功')
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '删除失败')
    }
  }

  // 获取所有交付物类型选项
  const getAllDeliverableTypes = () => {
    const types: { value: string; label: string }[] = []
    Object.entries(DELIVERABLE_TYPES).forEach(([stage, items]) => {
      items.forEach(item => {
        types.push({ value: item.type, label: `${STAGE_LABELS[stage as RdProjectStage]} - ${item.label}` })
      })
    })
    return types
  }

  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '阶段',
      dataIndex: 'stage',
      key: 'stage',
      render: (stage: string) => <Tag>{STAGE_LABELS[stage as RdProjectStage] || stage}</Tag>,
    },
    {
      title: '交付物类型',
      dataIndex: 'deliverable_type',
      key: 'deliverable_type',
      render: (type: string) => {
        const allTypes = getAllDeliverableTypes()
        const found = allTypes.find(t => t.value === type)
        return <Tag color="blue">{found ? found.label : type}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => <Tag color={active ? 'green' : 'default'}>{active ? '启用' : '禁用'}</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: RdDeliverableTemplate) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          <Button type="link" icon={<DownloadOutlined />} onClick={() => handleExportTemplate(record)} disabled={!record.template_content} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>交付物模板管理</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>管理各阶段交付物的报告模板，用于 AI 生成报告</p>
      </div>

      <Card
        extra={
          <Space>
            <Upload
              beforeUpload={handleBatchUpload}
              showUploadList={false}
              accept=".md,.txt,.markdown"
              disabled={batchUploading}
            >
              <Button icon={<UploadOutlined />} loading={batchUploading}>
                快速上传模板
              </Button>
            </Upload>
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建模板
            </Button>
          </Space>
        }
      >
        <div style={{ marginBottom: 16 }}>
          <Upload.Dragger
            beforeUpload={handleBatchUpload}
            showUploadList={false}
            accept=".md,.txt,.markdown"
            disabled={batchUploading}
            style={{ padding: '20px 0' }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined style={{ fontSize: 32, color: '#1677ff' }} />
            </p>
            <p className="ant-upload-text">点击或拖拽模板文件到此区域上传</p>
            <p className="ant-upload-hint">支持 .md、.txt、.markdown 格式，文件名即为模板名称</p>
          </Upload.Dragger>
        </div>

        <Table
          dataSource={templates}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          size="small"
        />
      </Card>

      <Drawer
        title={editingTemplate ? '编辑模板' : '新建模板'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        size="large"
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSave}>保存</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="模板名称" rules={[{ required: true }]}>
            <Input placeholder="如：标准技术调研报告模板" />
          </Form.Item>
          <Form.Item name="stage" label="所属阶段" rules={[{ required: true }]}>
            <Select
              placeholder="选择阶段"
              options={Object.entries(STAGE_LABELS).map(([value, label]) => ({ value, label }))}
            />
          </Form.Item>
          <Form.Item name="deliverable_type" label="交付物类型" rules={[{ required: true }]}>
            <Select
              placeholder="选择交付物类型"
              options={getAllDeliverableTypes()}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="description" label="模板描述">
            <TextArea rows={3} placeholder="模板用途说明" />
          </Form.Item>
          <Form.Item label="导入模板文件">
            <Upload
              beforeUpload={handleFileUpload}
              showUploadList={false}
              accept=".md,.txt,.markdown"
            >
              <Button icon={<UploadOutlined />}>选择文件 (.md/.txt)</Button>
            </Upload>
          </Form.Item>

          <Form.Item name="template_content" label="模板内容" rules={[{ required: true }]}>
            <TextArea
              rows={15}
              placeholder="输入模板内容，支持 Markdown 格式。AI 生成报告时会参考此模板的结构和格式。"
              style={{ fontFamily: 'monospace' }}
            />
          </Form.Item>
          <Form.Item name="is_active" label="是否启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
