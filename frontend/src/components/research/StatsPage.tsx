'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { App, Card, Row, Col, Statistic, Table, Tag, Progress, Spin } from 'antd'
import { ProjectOutlined, ExperimentOutlined, FileTextOutlined, CheckCircleOutlined } from '@ant-design/icons'
import { fetchStatsOverview, fetchProjectProgress, RdStatsOverview, RdProjectProgress } from '@/lib/api/client/research/rd-project'
import { STAGE_LABELS, TRACK_TYPE_LABELS } from '@/types/research/rd-project'

const stageColorMap: Record<string, string> = {
  initiation: 'blue',
  route_dev: 'purple',
  optimization: 'orange',
  pilot: 'cyan',
  validation: 'green',
  filing: 'pink',
}

const typeColorMap: Record<string, string> = {
  impurity: 'red',
  crystal_form: 'purple',
  stability: 'cyan',
  quality_standard: 'blue',
  custom: 'default',
}

export function StatsPage() {
  const { message: msgApi } = App.useApp()
  const [stats, setStats] = useState<RdStatsOverview | null>(null)
  const [progress, setProgress] = useState<RdProjectProgress[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        const [s, p] = await Promise.all([
          fetchStatsOverview(),
          fetchProjectProgress(),
        ])
        setStats(s)
        setProgress(p)
      } catch (e: any) {
        msgApi.error(e.message || '加载统计数据失败')
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!stats) return null

  // Stage distribution table data
  const stageData = Object.entries(stats.projects.by_stage).map(([stage, count]) => ({
    key: stage,
    stage: STAGE_LABELS[stage as keyof typeof STAGE_LABELS] || stage,
    count,
    percentage: stats.projects.total > 0 ? Math.round((count / stats.projects.total) * 100) : 0,
  }))

  // Track type distribution
  const trackTypeData = Object.entries(stats.tracks.by_type).map(([type, count]) => ({
    key: type,
    type: TRACK_TYPE_LABELS[type as keyof typeof TRACK_TYPE_LABELS] || type,
    count,
  }))

  // Project progress columns
  const progressColumns = [
    {
      title: '项目名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '当前阶段',
      dataIndex: 'current_stage',
      key: 'current_stage',
      render: (stage: string | null) => stage ? (
        <Tag color={stageColorMap[stage]}>
          {STAGE_LABELS[stage as keyof typeof STAGE_LABELS] || stage}
        </Tag>
      ) : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string, record: any) => {
        // Derive meaningful status from current_stage when status is always 'initiation'
        const stage = record.current_stage
        const stageStatusLabels: Record<string, string> = {
          initiation: '立项评审',
          route_dev: '路线开发中',
          optimization: '工艺优化中',
          pilot: '中试研究中',
          validation: '工艺验证中',
          filing: '申报准备中',
        }
        const stageStatusColors: Record<string, string> = {
          initiation: 'blue',
          route_dev: 'purple',
          optimization: 'orange',
          pilot: 'cyan',
          validation: 'green',
          filing: 'pink',
        }
        if (stage && stageStatusLabels[stage]) {
          return <Tag color={stageStatusColors[stage]}>{stageStatusLabels[stage]}</Tag>
        }
        const statusLabels: Record<string, string> = {
          initiation: '立项',
          active: '进行中',
          completed: '已完成',
          on_hold: '已暂停',
          terminated: '已终止',
        }
        const statusColors: Record<string, string> = {
          initiation: 'blue',
          active: 'green',
          completed: 'default',
          on_hold: 'orange',
          terminated: 'red',
        }
        return <Tag color={statusColors[status]}>{statusLabels[status] || status}</Tag>
      },
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (p: number) => <Progress percent={p} size="small" style={{ width: 120 }} />,
    },
    {
      title: '目标申报日期',
      dataIndex: 'target_filing_date',
      key: 'target_filing_date',
      render: (d: string | null) => d || '-',
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>研发统计</h1>
        <p style={{ color: '#666', margin: '4px 0 0 0' }}>研发模块数据概览和项目进度统计</p>
      </div>

      {/* Overview Cards */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={12} md={6}>
          <Link href="/research/projects" style={{ display: 'block' }}>
            <Card hoverable>
              <Statistic
                title="研发项目"
                value={stats.projects.total}
                prefix={<ProjectOutlined />}
                styles={{ content: { color: '#1677ff' } }}
              />
            </Card>
          </Link>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Link href="/research/research-tracks" style={{ display: 'block' }}>
            <Card hoverable>
              <Statistic
                title="研究项"
                value={stats.tracks.total}
                prefix={<ExperimentOutlined />}
                styles={{ content: { color: '#7b3ff2' } }}
              />
            </Card>
          </Link>
        </Col>
        <Col xs={12} sm={12} md={6}>
          <Link href="/research/deliverable-templates" style={{ display: 'block' }}>
            <Card hoverable>
              <Statistic
                title="交付物"
                value={stats.deliverables.total}
                prefix={<CheckCircleOutlined />}
                styles={{ content: { color: '#52c41a' } }}
              />
            </Card>
          </Link>
        </Col>
      </Row>

      {/* Distribution Charts */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          <Card title="项目阶段分布">
            <Table
              scroll={{ x: "max-content" }}
              dataSource={stageData}
              columns={[
                { title: '阶段', dataIndex: 'stage', key: 'stage' },
                { title: '数量', dataIndex: 'count', key: 'count' },
                {
                  title: '占比',
                  dataIndex: 'percentage',
                  key: 'percentage',
                  render: (p: number) => <Progress percent={p} size="small" />,
                },
              ]}
              rowKey="key"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="研究项类型分布">
            <Table
              scroll={{ x: "max-content" }}
              dataSource={trackTypeData}
              columns={[
                { title: '类型', dataIndex: 'type', key: 'type' },
                { title: '数量', dataIndex: 'count', key: 'count' },
              ]}
              rowKey="key"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      {/* Project Progress */}
      <Card title="项目进度">
        <Table
          scroll={{ x: "max-content" }}
          dataSource={progress}
          columns={progressColumns}
          rowKey="id"
          pagination={false}
          size="small"
        />
      </Card>
    </div>
  )
}
