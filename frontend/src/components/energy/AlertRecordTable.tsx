'use client'

import { Table, Tag, Space, Button, Empty } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import type { TableColumnsType } from 'antd'
import { AlertRecord, AlertLevel, EnergyType } from '@/types/energy'
import { energyTypeLabels } from './constants'

interface AlertRecordTableProps {
  data: AlertRecord[]
  loading?: boolean
  total?: number
  page: number
  pageSize: number
  onPageChange: (page: number, pageSize: number) => void
  onRefresh: () => void
  onProcess: (record: AlertRecord) => void
}

const alertLevelLabels: Record<AlertLevel, { text: string; color: string }> = {
  info: { text: '提示', color: 'blue' },
  warning: { text: '警告', color: 'orange' },
  critical: { text: '严重', color: 'red' },
  emergency: { text: '紧急', color: 'magenta' },
}

const statusLabels: Record<string, { text: string; color: string; icon: React.ReactNode }> = {
  pending: { text: '待处理', color: 'orange', icon: <ClockCircleOutlined /> },
  processed: { text: '已处理', color: 'green', icon: <CheckCircleOutlined /> },
  ignored: { text: '已忽略', color: 'default', icon: null },
}

export function AlertRecordTable({
  data,
  loading = false,
  total = 0,
  page,
  pageSize,
  onPageChange,
  onRefresh: _onRefresh,
  onProcess,
}: AlertRecordTableProps) {
  const columns: TableColumnsType<AlertRecord> = [
    {
      title: '预警时间',
      dataIndex: 'alert_time',
      key: 'alert_time',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '能源类型',
      dataIndex: 'energy_type',
      key: 'energy_type',
      width: 100,
      render: (type: EnergyType) => {
        const { text, color } = energyTypeLabels[type]
        return <Tag color={color}>{text}</Tag>
      },
    },
    {
      title: '预警等级',
      dataIndex: 'alert_level',
      key: 'alert_level',
      width: 100,
      render: (level: AlertLevel) => {
        const { text, color } = alertLevelLabels[level]
        return <Tag color={color}>{text}</Tag>
      },
    },
    {
      title: '触发值',
      key: 'trigger',
      width: 150,
      render: (_, record) => (
        <span>
          {record.trigger_value} {record.unit}
        </span>
      ),
    },
    {
      title: '阈值',
      key: 'threshold',
      width: 150,
      render: (_, record) => (
        <span>
          {record.threshold_value} {record.unit}
        </span>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const { text, color, icon } = statusLabels[status]
        return (
          <Tag color={color} icon={icon}>
            {text}
          </Tag>
        )
      },
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space>
          {record.status === 'pending' && (
            <Button type="link" onClick={() => onProcess(record)}>
              处理
            </Button>
          )}
        </Space>
      ),
    },
  ]

  const emptyState = (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <div style={{ color: '#999', fontSize: 14 }}>
          <p>暂无预警记录</p>
          <p style={{ fontSize: 12 }}>请点击&quot;导入数据&quot;从飞书表格导入数据，系统将自动检查并生成预警记录</p>
        </div>
      }
    />
  )

  return (
    <Table
      columns={columns}
      dataSource={data}
      loading={loading}
      rowKey="id"
      locale={{ emptyText: emptyState }}
      pagination={{
        current: page,
        pageSize,
        total,
        showSizeChanger: true,
        showQuickJumper: true,
        showTotal: (total) => `共 ${total} 条`,
        onChange: (p, s) => {
          if (s !== pageSize) {
            onPageChange(1, s)
          } else {
            onPageChange(p, s)
          }
        },
      }}
    />
  )
}
