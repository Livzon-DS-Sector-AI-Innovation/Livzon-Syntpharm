'use client'

import { useState, useEffect } from 'react'
import { Card, Table, Tag, Button, Space, Drawer, Descriptions, Timeline, Empty, App } from 'antd'
import { PlusOutlined, EyeOutlined } from '@ant-design/icons'
import { fetchProjectTracks } from '@/lib/api/client/research/rd-project'

interface ResearchTracksTabProps {
  projectId: string
}

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

export function ResearchTracksTab({ projectId }: ResearchTracksTabProps) {
  const { message } = App.useApp()
  const [tracks, setTracks] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedTrack, setSelectedTrack] = useState<any>(null)

  const loadTracks = async () => {
    setLoading(true)
    try {
      const data = await fetchProjectTracks(projectId)
      setTracks(data || [])
    } catch (e: any) {
      message.error(e.message || '加载研究项失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTracks()
  }, [projectId])

  const handleViewDetail = (track: any) => {
    setSelectedTrack(track)
    setDetailOpen(true)
  }

  const columns = [
    {
      title: '研究项名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: string) => (
        <Tag color={typeColorMap[type] || 'default'}>
          {typeLabels[type] || type}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusColorMap[status] || 'default'}>
          {statusLabels[status] || status}
        </Tag>
      ),
    },
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: string) => {
        const labels: Record<string, string> = { low: '低', normal: '普通', high: '高', urgent: '紧急' }
        const colors: Record<string, string> = { low: 'default', normal: 'blue', high: 'orange', urgent: 'red' }
        return <Tag color={colors[priority] || 'default'}>{labels[priority] || priority}</Tag>
      },
    },
    {
      title: '当前结论',
      dataIndex: 'current_conclusion',
      key: 'current_conclusion',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => (
        <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <>
      <Card
        title="研究项管理"
        extra={
          <Space>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => message.info('新建研究项功能开发中')}>
              新建研究项
            </Button>
            <Button onClick={loadTracks} loading={loading}>
              刷新
            </Button>
          </Space>
        }
      >
        <Table
          dataSource={tracks}
          rowKey="id"
          columns={columns}
          loading={loading}
          pagination={{ pageSize: 10 }}
          locale={{ emptyText: <Empty description="暂无研究项，点击右上角新建" /> }}
        />
      </Card>

      {/* 研究项详情抽屉 */}
      <Drawer
        title={selectedTrack?.name || '研究项详情'}
        placement="right"
        width={600}
        open={detailOpen}
        onClose={() => setDetailOpen(false)}
      >
        {selectedTrack && (
          <>
            <Descriptions column={1} bordered size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="类型">
                <Tag color={typeColorMap[selectedTrack.type] || 'default'}>
                  {typeLabels[selectedTrack.type] || selectedTrack.type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={statusColorMap[selectedTrack.status] || 'default'}>
                  {statusLabels[selectedTrack.status] || selectedTrack.status}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="优先级">{selectedTrack.priority}</Descriptions.Item>
              <Descriptions.Item label="结论版本">v{selectedTrack.conclusion_version || 0}</Descriptions.Item>
              <Descriptions.Item label="描述">{selectedTrack.description || '-'}</Descriptions.Item>
            </Descriptions>

            {selectedTrack.current_conclusion && (
              <Card size="small" title="当前结论" style={{ marginBottom: 16 }}>
                <p>{selectedTrack.current_conclusion}</p>
              </Card>
            )}

            <Card size="small" title="研究发现时间线">
              <Timeline>
                <Timeline.Item color="green">研究项创建</Timeline.Item>
                {selectedTrack.findings?.map((finding: any, index: number) => (
                  <Timeline.Item key={index}>
                    <div>{finding.conclusion || finding.data?.summary || '新增发现'}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>{finding.stage || '未知阶段'}</div>
                  </Timeline.Item>
                ))}
              </Timeline>
              {(!selectedTrack.findings || selectedTrack.findings.length === 0) && (
                <Empty description="暂无研究发现" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Card>
          </>
        )}
      </Drawer>
    </>
  )
}
