'use client'

import { useState, useEffect } from 'react'
import {
  Table,
  Button,
  Space,
  Card,
  Input,
  Select,
  DatePicker,
  Modal,
  Form,
  message,
  Tag,
  Popconfirm,
  Row,
  Col,
  Statistic,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  EditOutlined,
  FileWordOutlined,
  EyeOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  getReports,
  deleteReport,
  submitReport,
  getReportStatistics,
  getTemplates,
} from '@/actions/material-report'
import {
  ReportListItem,
  TemplateListItem,
  reportStatusLabels,
  reportStatusColors,
} from '@/types/material-report'

const { RangePicker } = DatePicker

export default function MaterialReportPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ReportListItem[]>([])
  const [pagination, setPagination] = useState({ total: 0, page: 1, pageSize: 20 })
  const [filters, setFilters] = useState<{
    status?: string
    template_id?: string
    start_date?: string
    end_date?: string
    keyword?: string
  }>({})
  const [templates, setTemplates] = useState<TemplateListItem[]>([])
  const [statistics, setStatistics] = useState({
    total_count: 0,
    draft_count: 0,
    completed_count: 0,
    approved_count: 0,
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [result, stats, templateResult] = await Promise.all([
        getReports({ ...filters, page: pagination.page, page_size: pagination.pageSize }),
        getReportStatistics(),
        getTemplates({ page: 1, page_size: 100 }),
      ])
      setData(result.data?.items || [])
      setPagination((prev) => ({ ...prev, total: result.data?.total || 0 }))
      setStatistics(stats.data || {})
      setTemplates(templateResult.data?.items || [])
    } catch (error) {
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [filters, pagination.page, pagination.pageSize])

  const handleDelete = async (id: string) => {
    try {
      await deleteReport(id)
      message.success('删除成功')
      fetchData()
    } catch {
      message.error('删除失败')
    }
  }

  const handleSubmit = async (id: string) => {
    try {
      await submitReport(id)
      message.success('提交成功')
      fetchData()
    } catch {
      message.error('提交失败')
    }
  }

  const handleSearch = (values: any) => {
    const [start_date, end_date] = values.dateRange || []
    setFilters({
      status: values.status,
      template_id: values.template_id,
      start_date: start_date?.format('YYYY-MM-DD'),
      end_date: end_date?.format('YYYY-MM-DD'),
      keyword: values.keyword,
    })
    setPagination((prev) => ({ ...prev, page: 1 }))
  }

  const columns: ColumnsType<ReportListItem> = [
    {
      title: '报告单编号',
      dataIndex: 'report_no',
      key: 'report_no',
      width: 150,
    },
    {
      title: '模板名称',
      dataIndex: 'template_name',
      key: 'template_name',
      width: 150,
    },
    {
      title: '报告标题',
      dataIndex: 'report_title',
      key: 'report_title',
      width: 200,
    },
    {
      title: '报告日期',
      dataIndex: 'report_date',
      key: 'report_date',
      width: 120,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={reportStatusColors[status]}>
          {reportStatusLabels[status] || status}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Link href={`/quality/material-report/${record.id}`}>
            <Button type="link" size="small" icon={<EyeOutlined />}>
              查看
            </Button>
          </Link>
          <Link href={`/quality/material-report/${record.id}?edit=true`}>
            <Button type="link" size="small" icon={<EditOutlined />}>
              编辑
            </Button>
          </Link>
          {record.status === 'draft' && (
            <>
              <Link href={`/quality/material-report/${record.id}?generate=true`}>
                <Button type="link" size="small" icon={<FileWordOutlined />}>
                  生成
                </Button>
              </Link>
              <Popconfirm
                title="确认提交？"
                onConfirm={() => handleSubmit(record.id)}
              >
                <Button type="link" size="small" danger>
                  提交
                </Button>
              </Popconfirm>
              <Popconfirm
                title="确认删除？"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="原料报告单管理"
        extra={
          <Space>
            <Link href="/quality/material-report/template">
              <Button icon={<SettingOutlined />}>
                模板管理
              </Button>
            </Link>
            <Link href="/quality/material-report/create">
              <Button type="primary" icon={<PlusOutlined />}>
                新建报告单
              </Button>
            </Link>
          </Space>
        }
      >
        {/* 统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Statistic title="总报告单数" value={statistics.total_count} />
          </Col>
          <Col span={6}>
            <Statistic title="草稿" value={statistics.draft_count} />
          </Col>
          <Col span={6}>
            <Statistic title="已完成" value={statistics.completed_count} />
          </Col>
          <Col span={6}>
            <Statistic title="已审批" value={statistics.approved_count} />
          </Col>
        </Row>

        {/* 筛选表单 */}
        <Form layout="inline" onFinish={handleSearch} style={{ marginBottom: 16 }}>
          <Form.Item name="keyword" label="搜索">
            <Input
              placeholder="报告单编号/标题"
              style={{ width: 200 }}
              allowClear
            />
          </Form.Item>
          <Form.Item name="template_id" label="模板">
            <Select
              placeholder="选择模板"
              style={{ width: 150 }}
              allowClear
              options={templates.map((t) => ({
                label: t.template_name,
                value: t.id,
              }))}
            />
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select
              placeholder="选择状态"
              style={{ width: 120 }}
              allowClear
              options={Object.entries(reportStatusLabels).map(([value, label]) => ({
                label,
                value,
              }))}
            />
          </Form.Item>
          <Form.Item name="dateRange" label="日期范围">
            <RangePicker />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>
              搜索
            </Button>
          </Form.Item>
        </Form>

        {/* 数据表格 */}
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            total: pagination.total,
            current: pagination.page,
            pageSize: pagination.pageSize,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => {
              setPagination({ ...pagination, page, pageSize })
            },
          }}
        />
      </Card>
    </div>
  )
}