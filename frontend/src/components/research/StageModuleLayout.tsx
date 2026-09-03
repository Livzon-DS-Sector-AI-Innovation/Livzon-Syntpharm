'use client'

import { useState, useEffect, ReactNode } from 'react'
import {App, Card, Table, Tag, Button, Input} from 'antd'
import { ArrowLeftOutlined, SearchOutlined, EnterOutlined } from '@ant-design/icons'
import { fetchRdProjects } from '@/lib/api/client/research/rd-project'
import {
  RdProject, RdProjectStage,
  STAGE_LABELS,
} from '@/types/research/rd-project'

const PRIORITY_LABELS: Record<string, { label: string; color: string }> = {
  low: { label: '低', color: 'default' },
  normal: { label: '普通', color: 'blue' },
  high: { label: '高', color: 'red' },
  urgent: { label: '紧急', color: 'magenta' },
}

const STATUS_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  initiation: { label: '立项', color: '#1677ff', bg: '#e6f4ff' },
  active: { label: '进行中', color: '#52c41a', bg: '#e6f7e6' },
  completed: { label: '已完成', color: '#787671', bg: '#f0eeec' },
  on_hold: { label: '已暂停', color: '#fa8c16', bg: '#fff7e6' },
  terminated: { label: '已终止', color: '#e03131', bg: '#fff1f0' },
}

interface StageModuleLayoutProps {
  title: string
  description: string
  stage: RdProjectStage
  children: (projectId: string) => ReactNode
}

export function StageModuleLayout({ title, description, stage, children }: StageModuleLayoutProps) {
  const { message: msgApi } = App.useApp()
  const [projects, setProjects] = useState<RdProject[]>([])
  const [_total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [keyword, setKeyword] = useState('')

  useEffect(() => {
    loadProjects()
  }, [stage])

  const loadProjects = async () => {
    setLoading(true)
    try {
      const result = await fetchRdProjects({ page_size: 100, stage })
      setProjects(result.items)
      setTotal(result.total)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '加载项目列表失败')
    } finally {
      setLoading(false)
    }
  }

  const filteredProjects = keyword
    ? projects.filter(p =>
        p.name.toLowerCase().includes(keyword.toLowerCase()) ||
        p.api_name.toLowerCase().includes(keyword.toLowerCase()) ||
        (p.cas_number && p.cas_number.toLowerCase().includes(keyword.toLowerCase()))
      )
    : projects

  if (selectedProjectId) {
    return (
      <div>
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => setSelectedProjectId(null)}
          >
            返回{title}列表
          </Button>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>{title}</h1>
            <p style={{ color: '#666', margin: '2px 0 0 0', fontSize: 13 }}>{description}</p>
          </div>
        </div>
        {children(selectedProjectId)}
      </div>
    )
  }

  const columns = [
    {
      title: '品种名称',
      dataIndex: 'name',
      key: 'name',
      render: (v: string) => <span style={{ fontWeight: 500 }}>{v}</span>,
    },
    {
      title: 'API全称',
      dataIndex: 'api_name',
      key: 'api_name',
      render: (v: string) => v || '-',
    },
    {
      title: 'CAS号',
      dataIndex: 'cas_number',
      key: 'cas_number',
      render: (v: string) => v || '-',
    },
    {
      title: '适应症',
      dataIndex: 'indication',
      key: 'indication',
      ellipsis: true,
      render: (v: string) => v || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => {
        const cfg = STATUS_LABELS[v] || { label: v, color: '#787671', bg: '#f0eeec' }
        return <Tag style={{ color: cfg.color, background: cfg.bg, border: 'none' }}>{cfg.label}</Tag>
      },
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (v: string) => {
        const cfg = PRIORITY_LABELS[v] || { label: v, color: 'default' }
        return <Tag color={cfg.color}>{cfg.label}</Tag>
      },
    },
    {
      title: '进度',
      dataIndex: 'overall_progress',
      key: 'overall_progress',
      width: 80,
      render: (v: number) => v != null ? `${v}%` : '-',
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 110,
      render: (v: string) => v || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: unknown, record: RdProject) => (
        <Button
          type="link"
          icon={<EnterOutlined />}
          onClick={() => setSelectedProjectId(record.id)}
          style={{ padding: 0 }}
        >
          进入
        </Button>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>{title}</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>{description}</p>
      </div>

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Input
            placeholder="搜索品种名称 / API全称 / CAS号"
            allowClear
            style={{ width: 300 }}
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            prefix={<SearchOutlined style={{ color: '#a4a097' }} />}
          />
          <span style={{ color: '#999', fontSize: 13 }}>
            共 {filteredProjects.length} 个项目处于「{STAGE_LABELS[stage]}」阶段
          </span>
        </div>

        <Table
          dataSource={filteredProjects}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={filteredProjects.length > 10 ? {
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          } : false}
          onRow={(record) => ({
            onClick: () => setSelectedProjectId(record.id),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>
    </div>
  )
}
