'use client'
import { deleteRegistrationProject } from '@/actions/registration'

import { Suspense, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Table, Button, Space, Tag, Modal, Form, Input, Select, DatePicker,
  Card, Typography, message, Popconfirm, Empty,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined, ReloadOutlined, EditOutlined, DeleteOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'

const { Title } = Typography

interface Project {
  id: string
  product_name: string
  market: string
  registration_type: string | null
  status: string
  submitted_at: string | null
  accepted_at: string | null
  approved_at: string | null
  expected_completion_at: string | null
  owner: string | null
  latest_progress: string | null
  created_at: string
  updated_at: string
}

const STATUS_OPTIONS = [
  { value: 'draft', label: '草稿' },
  { value: 'preparing', label: '准备中' },
  { value: 'submitted', label: '已申报' },
  { value: 'accepted', label: '已受理' },
  { value: 'under_review', label: '审评中' },
  { value: 'supplementary', label: '发补中' },
  { value: 'approved', label: '已获批' },
  { value: 'withdrawn', label: '已撤回' },
  { value: 'terminated', label: '已终止' },
]

const STATUS_MAP: Record<string, { color: string; label: string }> = Object.fromEntries(
  STATUS_OPTIONS.map(o => [o.value, { color: o.value === 'approved' ? 'success' : o.value === 'under_review' ? 'processing' : o.value === 'terminated' ? 'error' : 'default', label: o.label }])
)

function ProjectsContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [modalOpen, setModalOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [form] = Form.useForm()

  const statusFilter = searchParams.get('status')

  const loadProjects = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/v1/registration/projects/')
      const json = await res.json()
      setProjects(json.data || [])
    } catch {
      message.error('加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const handleAdd = () => {
    setEditingProject(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (project: Project) => {
    setEditingProject(project)
    form.setFieldsValue({
      ...project,
      submitted_at: project.submitted_at ? dayjs(project.submitted_at) : null,
      accepted_at: project.accepted_at ? dayjs(project.accepted_at) : null,
      approved_at: project.approved_at ? dayjs(project.approved_at) : null,
      expected_completion_at: project.expected_completion_at ? dayjs(project.expected_completion_at) : null,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteRegistrationProject(id)
      message.success('删除成功')
      loadProjects()
    } catch {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      const payload = {
        ...values,
        submitted_at: values.submitted_at?.format('YYYY-MM-DD') || null,
        accepted_at: values.accepted_at?.format('YYYY-MM-DD') || null,
        approved_at: values.approved_at?.format('YYYY-MM-DD') || null,
        expected_completion_at: values.expected_completion_at?.format('YYYY-MM-DD') || null,
      }

      const url = editingProject
        ? `/api/v1/registration/projects/${editingProject.id}`
        : '/api/v1/registration/projects/'
      const method = editingProject ? 'PUT' : 'POST'

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) throw new Error()
      message.success(editingProject ? '更新成功' : '创建成功')
      setModalOpen(false)
      loadProjects()
    } catch {
      message.error('操作失败')
    }
  }

  const filteredProjects = statusFilter
    ? projects.filter(p => p.status === statusFilter || (statusFilter.includes(',') && statusFilter.split(',').includes(p.status)))
    : projects

  const columns: ColumnsType<Project> = [
    { title: '品种名称', dataIndex: 'product_name', key: 'product_name', width: 160 },
    { title: '注册市场', dataIndex: 'market', key: 'market', width: 100 },
    { title: '注册类型', dataIndex: 'registration_type', key: 'registration_type', width: 100,
      render: v => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: status => {
        const cfg = STATUS_MAP[status] || { color: 'default', label: status }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    { title: '申报日期', dataIndex: 'submitted_at', key: 'submitted_at', width: 110,
      render: v => v || '-' },
    { title: '受理日期', dataIndex: 'accepted_at', key: 'accepted_at', width: 110,
      render: v => v || '-' },
    { title: '获批日期', dataIndex: 'approved_at', key: 'approved_at', width: 110,
      render: v => v || '-' },
    { title: '预计完成', dataIndex: 'expected_completion_at', key: 'expected_completion_at', width: 110,
      render: v => v || '-' },
    { title: '负责人', dataIndex: 'owner', key: 'owner', width: 80,
      render: v => v || '-' },
    { title: '最新进展', dataIndex: 'latest_progress', key: 'latest_progress', ellipsis: true,
      render: v => v || '-' },
    { title: '操作', key: 'action', width: 120, fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Title level={4} className="mb-0">注册项目管理</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={loadProjects}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增项目</Button>
        </Space>
      </div>

      <Card variant="borderless" className="shadow-sm">
        {filteredProjects.length > 0 ? (
          <Table
            columns={columns}
            dataSource={filteredProjects}
            rowKey="id"
            loading={loading}
            size="small"
            scroll={{ x: 1400 }}
            pagination={{ pageSize: 20, showSizeChanger: true, showTotal: total => `共 ${total} 条` }}
          />
        ) : (
          <Empty description="暂无注册项目" />
        )}
      </Card>

      <Modal
        title={editingProject ? '编辑注册项目' : '新增注册项目'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={() => setModalOpen(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="product_name" label="品种名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="market" label="注册市场/国家" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="registration_type" label="注册类型">
            <Select allowClear placeholder="选择注册类型" options={[
              { value: '新注册', label: '新注册' },
              { value: '再注册', label: '再注册' },
              { value: '变更', label: '变更' },
              { value: '补充申请', label: '补充申请' },
            ]} />
          </Form.Item>
          <Form.Item name="status" label="状态" rules={[{ required: true }]}>
            <Select options={STATUS_OPTIONS} />
          </Form.Item>
          <Form.Item name="submitted_at" label="申报日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="accepted_at" label="受理日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="approved_at" label="获批日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="expected_completion_at" label="预计完成时间">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="owner" label="负责人">
            <Input />
          </Form.Item>
          <Form.Item name="latest_progress" label="最新进展">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

export default function ProjectsPage() {
  return (
    <Suspense>
      <ProjectsContent />
    </Suspense>
  )
}
