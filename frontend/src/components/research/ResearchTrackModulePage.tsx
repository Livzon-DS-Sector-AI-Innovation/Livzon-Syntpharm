'use client'

import { useState, useEffect, useCallback } from 'react'
import {App, Card, Select, Table, Tag, Tabs, Button, Drawer, Descriptions} from 'antd'
import { ExperimentOutlined, SearchOutlined, EyeOutlined, CheckCircleOutlined, UnorderedListOutlined, ReloadOutlined } from '@ant-design/icons'
import { fetchAllTracks, fetchRdProjects } from '@/lib/api/client/research/rd-project'
import { RdProject, RdResearchTrack } from '@/types/research/rd-project'

const TRACK_TYPE_TABS = [
  { key: 'all', label: '全部研究项', icon: <UnorderedListOutlined /> },
  { key: 'impurity', label: '杂质研究', icon: <SearchOutlined /> },
  { key: 'crystal_form', label: '晶型研究', icon: <EyeOutlined /> },
  { key: 'stability', label: '稳定性考察', icon: <CheckCircleOutlined /> },
  { key: 'quality_standard', label: '质量标准', icon: <ExperimentOutlined /> },
]

const typeLabels: Record<string, string> = {
  impurity: '杂质研究',
  crystal_form: '晶型研究',
  stability: '稳定性考察',
  quality_standard: '质量标准',
  custom: '自定义',
}

const typeColorMap: Record<string, string> = {
  impurity: 'red',
  crystal_form: 'purple',
  stability: 'cyan',
  quality_standard: 'blue',
  custom: 'default',
}

const statusLabels: Record<string, string> = {
  active: '进行中',
  paused: '已暂停',
  completed: '已完成',
  archived: '已归档',
}

const statusColorMap: Record<string, string> = {
  active: 'processing',
  paused: 'warning',
  completed: 'success',
  archived: 'default',
}

const priorityLabels: Record<string, string> = {
  low: '低',
  normal: '普通',
  high: '高',
  urgent: '紧急',
}

const priorityColorMap: Record<string, string> = {
  low: 'default',
  normal: 'blue',
  high: 'orange',
  urgent: 'red',
}

export function ResearchTrackModulePage() {
  const { message: msgApi } = App.useApp()
  const [projects, setProjects] = useState<RdProject[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeType, setActiveType] = useState<string>('all')
  const [tracks, setTracks] = useState<RdResearchTrack[]>([])
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedTrack, setSelectedTrack] = useState<RdResearchTrack | null>(null)

  const loadProjects = useCallback(async () => {
    try {
      const result = await fetchRdProjects({ page_size: 100 })
      setProjects(result.items)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '加载项目列表失败')
    }
  }, [])

  const loadTracks = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchAllTracks({
        projectId: selectedProjectId || undefined,
        trackType: activeType === 'all' ? undefined : activeType,
      })
      setTracks(data)
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '加载研究项失败')
    } finally {
      setLoading(false)
    }
  }, [selectedProjectId, activeType])

  useEffect(() => {
    loadProjects()
  }, [])

  useEffect(() => {
    loadTracks()
  }, [loadTracks])

  const columns = [
    {
      title: '研究项名称',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: RdResearchTrack) => (
        <a onClick={() => { setSelectedTrack(record); setDetailOpen(true) }}>{text}</a>
      ),
    },
    {
      title: '所属项目',
      dataIndex: 'project_name',
      key: 'project_name',
      render: (text: string) => text || '-',
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={typeColorMap[type]}>{typeLabels[type] || type}</Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColorMap[status]}>{statusLabels[status] || status}</Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      render: (priority: string) => (
        <Tag color={priorityColorMap[priority]}>{priorityLabels[priority] || priority}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (d: string) => d ? new Date(d).toLocaleDateString('zh-CN') : '-',
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>研究项管理</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>管理跨阶段研究活动：杂质研究、晶型研究、稳定性考察、质量标准等</p>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
          <span>筛选项目：</span>
          <Select
            style={{ width: 300 }}
            placeholder="显示所有项目的研究项"
            loading={loading}
            value={selectedProjectId}
            onChange={(v) => setSelectedProjectId(v)}
            options={projects.map(p => ({ value: p.id, label: p.name }))}
            allowClear
            onClear={() => setSelectedProjectId(null)}
          />
          <Button icon={<ReloadOutlined />} onClick={loadTracks}>刷新</Button>
          <span style={{ color: '#999', marginLeft: 'auto' }}>共 {tracks.length} 条研究项</span>
        </div>

        <Tabs
          activeKey={activeType}
          onChange={setActiveType}
          items={TRACK_TYPE_TABS.map(tab => ({
            key: tab.key,
            label: (
              <span>
                {tab.icon}
                <span style={{ marginLeft: 4 }}>{tab.label}</span>
              </span>
            ),
          }))}
        />
      </Card>

      <Card>
        <Table
          scroll={{ x: 'max-content' }}
          dataSource={tracks}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (total) => `共 ${total} 条` }}
          size="middle"
        />
      </Card>

      <Drawer
        title={selectedTrack?.name || '研究项详情'}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
        size="large"
      >
        {selectedTrack && (
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label="名称">{selectedTrack.name}</Descriptions.Item>
            <Descriptions.Item label="所属项目">{(selectedTrack as RdResearchTrack & { project_name?: string }).project_name || '-'}</Descriptions.Item>
            <Descriptions.Item label="类型">
              <Tag color={typeColorMap[selectedTrack.type]}>{typeLabels[selectedTrack.type] || selectedTrack.type}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusColorMap[selectedTrack.status]}>{statusLabels[selectedTrack.status] || selectedTrack.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={priorityColorMap[selectedTrack.priority]}>{priorityLabels[selectedTrack.priority] || selectedTrack.priority}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="描述">{selectedTrack.description || '-'}</Descriptions.Item>
            <Descriptions.Item label="当前结论">{selectedTrack.current_conclusion || '-'}</Descriptions.Item>
            <Descriptions.Item label="结论版本">v{selectedTrack.conclusion_version || 0}</Descriptions.Item>
            <Descriptions.Item label="结论置信度">{selectedTrack.conclusion_confidence || '-'}</Descriptions.Item>
            <Descriptions.Item label="活跃阶段">{selectedTrack.active_stages?.join(', ') || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{selectedTrack.created_at ? new Date(selectedTrack.created_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{selectedTrack.updated_at ? new Date(selectedTrack.updated_at).toLocaleString('zh-CN') : '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </div>
  )
}
