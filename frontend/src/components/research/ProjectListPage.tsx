'use client'

import { useState } from 'react'
import { App, Card, Table, Tag, Button, Input, Select, Space, Modal, Form, DatePicker } from 'antd'
import { PlusOutlined, SearchOutlined, DownloadOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import {
  RdProject,
  STAGE_LABELS, STAGE_ORDER,
} from '@/types/research/rd-project'
import { fetchRdProjects } from '@/lib/api/client/research/rd-project'
import { createRdProject, deleteRdProject } from '@/actions/research/rd-project'

interface Props {
  initialProjects: RdProject[]
  initialTotal: number
}

const stageColorMap: Record<string, { color: string; bg: string }> = {
  initiation: { color: '#1677ff', bg: '#e6f4ff' },
  route_dev: { color: '#7b3ff2', bg: '#e6e0f5' },
  optimization: { color: '#fa8c16', bg: '#fff7e6' },
  pilot: { color: '#13c2c2', bg: '#e6fffb' },
  validation: { color: '#52c41a', bg: '#e6f7e6' },
  filing: { color: '#eb2f96', bg: '#fff0f6' },
}

const statusColorMap: Record<string, { color: string; bg: string }> = {
  initiation: { color: '#1677ff', bg: '#e6f4ff' },
  active: { color: '#52c41a', bg: '#e6f7e6' },
  completed: { color: '#787671', bg: '#f0eeec' },
  on_hold: { color: '#fa8c16', bg: '#fff7e6' },
  terminated: { color: '#e03131', bg: '#fff1f0' },
}

export function ProjectListPage({ initialProjects, initialTotal }: Props) {
  const { modal, message } = App.useApp()
  const router = useRouter()
  const [projects, setProjects] = useState<RdProject[]>(initialProjects)
  const [total, setTotal] = useState(initialTotal)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [filters, setFilters] = useState({ stage: '', status: '', keyword: '' })
  const [createModalOpen, setCreateModalOpen] = useState(false)
  const [createForm] = Form.useForm()

  const loadData = async (p = page, ps = pageSize, f = filters) => {
    setLoading(true)
    try {
      const result = await fetchRdProjects({ page: p, page_size: ps, ...f })
      setProjects(result.items)
      setTotal(result.total)
    } catch (e: any) {
      message.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = async () => {
    const values = await createForm.validateFields()
    try {
      const _project = await createRdProject({
        ...values,
        start_date: values.start_date?.format('YYYY-MM-DD'),
        target_filing_date: values.target_filing_date?.format('YYYY-MM-DD'),
      })
      message.success('创建成功')
      setCreateModalOpen(false)
      createForm.resetFields()
      loadData()
    } catch (e: any) {
      message.error(e.message || '创建失败')
    }
  }

  const handleDelete = (project: RdProject) => {
    modal.confirm({
      title: '警告',
      content: `您即将删除项目 "${project.name}"，这是一个高危操作，删除后数据将无法恢复。是否继续？`,
      okText: '继续',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        modal.confirm({
          title: '最终确认',
          content: (
            <div>
              <p>请输入项目名称 <strong>"{project.name}"</strong> 以确认删除：</p>
              <input
                id="delete-confirm-input"
                type="text"
                placeholder="请输入项目名称"
                style={{
                  width: '100%',
                  padding: '8px',
                  marginTop: '8px',
                  border: '1px solid #d9d9d9',
                  borderRadius: '4px',
                }}
              />
            </div>
          ),
          okText: '确认删除',
          cancelText: '取消',
          okButtonProps: { danger: true },
          onOk: async () => {
            const input = document.getElementById('delete-confirm-input') as HTMLInputElement
            if (input?.value !== project.name) {
              message.error('项目名称不匹配，删除已取消')
              return Promise.reject()
            }
            try {
              await deleteRdProject(project.id)
              message.success('删除成功')
              loadData()
            } catch (e: any) {
              message.error(e.message || '删除失败')
            }
          },
        })
      },
    })
  }
















  const handleExport = () => {
    window.open('/api/v1/research/export/projects', '_blank')
  }


  const columns = [
    {
      title: '品种名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string, record: RdProject) => (
        <a onClick={() => router.push(`/research/projects/${record.id}`)} style={{ fontWeight: 500 }}>{v}</a>
      ),
    },
    { title: 'API全称', dataIndex: 'api_name', key: 'api_name', render: (v: string) => v || '-' },
    { title: 'CAS号', dataIndex: 'cas_number', key: 'cas_number', render: (v: string) => v || '-' },
    {
      title: '当前阶段',
      dataIndex: 'current_stage',
      key: 'current_stage',
      render: (v: string) => {
        const cfg = stageColorMap[v] || { color: '#787671', bg: '#f0eeec' }
        return <Tag style={{ color: cfg.color, background: cfg.bg, border: 'none', fontWeight: 500 }}>{STAGE_LABELS[v as keyof typeof STAGE_LABELS] || v}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => {
        const cfg = statusColorMap[v] || { color: '#787671', bg: '#f0eeec' }
        return <Tag style={{ color: cfg.color, background: cfg.bg, border: 'none' }}>{v}</Tag>
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (v: string) => <Tag color={v === 'high' ? 'red' : v === 'urgent' ? 'magenta' : v === 'low' ? 'default' : 'blue'}>{v}</Tag>,
    },
    { title: '总体进度', dataIndex: 'overall_progress', key: 'overall_progress', render: (v: number) => v != null ? `${v}%` : '-' },
    { title: '开始日期', dataIndex: 'start_date', key: 'start_date', render: (v: string) => v || '-' },
    { title: '目标申报日期', dataIndex: 'target_filing_date', key: 'target_filing_date', render: (v: string) => v || '-' },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: RdProject) => (
        <Space>
          <a onClick={() => router.push(`/research/projects/${record.id}`)}>详情</a>
          <a onClick={() => handleDelete(record)} style={{ color: '#e03131' }}>删除</a>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>研发项目</h1>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleExport}>导出</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>新建项目</Button>
        </Space>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', gap: 12 }}>
          <Select placeholder="阶段" allowClear style={{ width: 140 }} value={filters.stage || undefined}
            onChange={(v) => { setFilters({ ...filters, stage: v || '' }); setPage(1); loadData(1, pageSize, { ...filters, stage: v || '' }) }}
            options={STAGE_ORDER.map(s => ({ value: s, label: STAGE_LABELS[s as keyof typeof STAGE_LABELS] }))}
          />
          <Select placeholder="状态" allowClear style={{ width: 120 }} value={filters.status || undefined}
            onChange={(v) => { setFilters({ ...filters, status: v || '' }); setPage(1); loadData(1, pageSize, { ...filters, status: v || '' }) }}
            options={[{ value: 'initiation', label: '立项' }, { value: 'active', label: '进行中' }, { value: 'completed', label: '已完成' }, { value: 'on_hold', label: '已暂停' }, { value: 'terminated', label: '已终止' }]}
          />
          <Input placeholder="搜索名称/CAS号" allowClear style={{ width: 200 }} value={filters.keyword}
            onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
            onPressEnter={() => { setPage(1); loadData(1, pageSize, { ...filters }) }}
            suffix={<SearchOutlined />}
          />
        </div>

        <Table
          dataSource={projects}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps); loadData(p, ps) },
          }}
        />
      </Card>

      <Modal title="新建研发项目" open={createModalOpen} onOk={handleCreate} onCancel={() => setCreateModalOpen(false)} width={600}>
        <Form form={createForm} layout="vertical">
          <Form.Item name="name" label="品种名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="api_name" label="API全称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="cas_number" label="CAS号">
            <Input />
          </Form.Item>
          <Form.Item name="molecular_formula" label="分子式">
            <Input />
          </Form.Item>
          <Form.Item name="molecular_weight" label="分子量">
            <Input type="number" />
          </Form.Item>
          <Form.Item name="indication" label="适应症">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item name="project_type" label="项目类型">
            <Select options={[{ value: 'generic', label: '仿制药' }, { value: 'improved', label: '改良型' }]} />
          </Form.Item>
          <Form.Item name="priority" label="优先级" initialValue="normal">
            <Select options={[{ value: 'low', label: '低' }, { value: 'normal', label: '普通' }, { value: 'high', label: '高' }, { value: 'urgent', label: '紧急' }]} />
          </Form.Item>
          <Form.Item name="start_date" label="开始日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="target_filing_date" label="目标申报日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="current_stage" label="起始阶段" initialValue="initiation">
            <Select options={STAGE_ORDER.map(s => ({ value: s, label: STAGE_LABELS[s as keyof typeof STAGE_LABELS] }))} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
