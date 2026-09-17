'use client'

import { useState } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Form,
  Input,
  DatePicker,
  Select,
  Tag,
  message,
} from 'antd'
import {
  SearchOutlined,
  DownloadOutlined,
  EyeOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { useRouter } from 'next/navigation'

const API_BASE = '/api/v1'

interface TaskItem {
  task_id: number
  deviation_no: string
  creator: string
  auditor: string | null
  report_date: string
  original_file_path: string
  standard_file_path: string | null
  task_status: number
  create_time: string
}

const statusOptions = [
  { label: '待处理', value: 1 },
  { label: 'AI处理中', value: 2 },
  { label: '已生成', value: 3 },
  { label: '已完成', value: 4 },
]

const getStatusTag = (status: number) => {
  const colors: Record<number, string> = {
    1: 'default',
    2: 'processing',
    3: 'success',
    4: 'blue',
  }
  const labels: Record<number, string> = {
    1: '待处理',
    2: 'AI处理中',
    3: '已生成',
    4: '已完成',
  }
  return <Tag color={colors[status]}>{labels[status]}</Tag>
}

export default function HistoryPage() {
  const [form] = Form.useForm()
  const [data, setData] = useState<TaskItem[]>([])
  const [loading, setLoading] = useState(false)
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })
  const router = useRouter()

  const fetchData = async (page = 1, pageSize = 20) => {
    setLoading(true)
    try {
      const values = form.getFieldsValue()
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(pageSize))

      if (values.deviation_no) params.set('deviation_no', values.deviation_no)
      if (values.creator) params.set('creator', values.creator)
      if (values.task_status !== undefined) params.set('task_status', String(values.task_status))
      if (values.start_date) params.set('start_date', values.start_date.format('YYYY-MM-DD'))
      if (values.end_date) params.set('end_date', values.end_date.format('YYYY-MM-DD'))

      const response = await fetch(
        `${API_BASE}/quality/deviation-automation/tasks?${params.toString()}`
      )
      if (!response.ok) throw new Error('查询失败')

      const result = await response.json()
      setData(result.data.items)
      setPagination({
        ...pagination,
        current: page,
        pageSize,
        total: result.data.total,
      })
    } catch (error: any) {
      message.error(error.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = () => {
    fetchData(1, pagination.pageSize)
  }

  const handleReset = () => {
    form.resetFields()
    fetchData(1, pagination.pageSize)
  }

  const handleTableChange = (newPagination: any) => {
    fetchData(newPagination.current, newPagination.pageSize)
  }

  const handleView = (record: TaskItem) => {
    router.push(`/quality/deviation-automation/preview/${record.task_id}`)
  }

  const handleDownloadOriginal = (record: TaskItem) => {
    window.open(
      `${API_BASE}/quality/deviation-automation/tasks/${record.task_id}/download/original`,
      '_blank'
    )
  }

  const handleDownloadStandard = (record: TaskItem) => {
    if (!record.standard_file_path) {
      message.warning('标准报告文件尚未生成')
      return
    }
    window.open(
      `${API_BASE}/quality/deviation-automation/tasks/${record.task_id}/download/standard`,
      '_blank'
    )
  }

  const columns: ColumnsType<TaskItem> = [
    {
      title: '偏差编号',
      dataIndex: 'deviation_no',
      key: 'deviation_no',
      width: 150,
    },
    {
      title: '编制人',
      dataIndex: 'creator',
      key: 'creator',
      width: 100,
    },
    {
      title: '审核人',
      dataIndex: 'auditor',
      key: 'auditor',
      width: 100,
      render: (text) => text || '-',
    },
    {
      title: '编制日期',
      dataIndex: 'report_date',
      key: 'report_date',
      width: 120,
    },
    {
      title: '任务状态',
      dataIndex: 'task_status',
      key: 'task_status',
      width: 100,
      render: (status) => getStatusTag(status),
    },
    {
      title: '创建时间',
      dataIndex: 'create_time',
      key: 'create_time',
      width: 180,
      render: (text) => text ? dayjs(text).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleView(record)}
          >
            预览
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadOriginal(record)}
          >
            原始
          </Button>
          <Button
            type="link"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => handleDownloadStandard(record)}
            disabled={!record.standard_file_path}
          >
            标准
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card title="历史任务查询">
        {/* 查询条件 */}
        <Form form={form} layout="inline" style={{ marginBottom: 16 }}>
          <Form.Item name="deviation_no" label="偏差编号">
            <Input placeholder="请输入" style={{ width: 150 }} />
          </Form.Item>
          <Form.Item name="creator" label="编制人">
            <Input placeholder="请输入" style={{ width: 120 }} />
          </Form.Item>
          <Form.Item name="task_status" label="任务状态">
            <Select
              placeholder="请选择"
              style={{ width: 120 }}
              allowClear
              options={statusOptions}
            />
          </Form.Item>
          <Form.Item name="start_date" label="开始日期">
            <DatePicker />
          </Form.Item>
          <Form.Item name="end_date" label="结束日期">
            <DatePicker />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button onClick={handleReset}>重置</Button>
            </Space>
          </Form.Item>
        </Form>

        {/* 数据列表 */}
        <Table
          columns={columns}
          dataSource={data}
          rowKey="task_id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
          }}
          onChange={handleTableChange}
        />
      </Card>
    </div>
  )
}
