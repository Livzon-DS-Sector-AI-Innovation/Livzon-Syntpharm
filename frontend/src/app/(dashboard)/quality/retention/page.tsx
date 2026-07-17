'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Card,
  Row,
  Col,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  HistoryOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  SampleRetentionLedger,
  RetentionStatus,
  RetentionStatusLabels,
  RetentionStatusColors,
  RetentionLedgerFilter,
  RetentionLedgerListResponse,
} from '@/types/sampling'
import { getRetentionLedger } from '@/actions/quality'

const { Text } = Typography

// 初始筛选条件
const initialFilters: RetentionLedgerFilter = {
  order_no: '',
  sample_no: '',
  material_code: '',
  material_name: '',
  retention_status: undefined,
}

export default function RetentionLedgerPage() {
  // 状态
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<SampleRetentionLedger[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<RetentionLedgerFilter>(initialFilters)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getRetentionLedger({
        ...filters,
        page,
        page_size: pageSize,
      })
      // 后端返回格式: {items, total, page, page_size}
      if (response.code === 200 || response.code === 0) {
        const data = response.data as RetentionLedgerListResponse
        setData(data?.items || [])
        setTotal(data?.total || 0)
      }
    } catch (error) {
      console.error('加载数据失败', error)
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 筛选
  const handleSearch = () => {
    setPage(1)
    loadData()
  }

  // 重置筛选
  const handleReset = () => {
    setFilters(initialFilters)
    setPage(1)
    loadData()
  }

  // 表格列定义
  const columns: ColumnsType<SampleRetentionLedger> = [
    {
      title: '取样单号',
      dataIndex: 'order_no',
      key: 'order_no',
      width: 150,
    },
    {
      title: '样品编号',
      dataIndex: 'sample_no',
      key: 'sample_no',
      width: 150,
    },
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 120,
    },
    {
      title: '物料名称',
      dataIndex: 'material_name',
      key: 'material_name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '批次号',
      dataIndex: 'batch_no',
      key: 'batch_no',
      width: 120,
    },
    {
      title: '留样份数',
      dataIndex: 'retention_count',
      key: 'retention_count',
      width: 80,
    },
    {
      title: '存放位置',
      dataIndex: 'retention_location',
      key: 'retention_location',
      width: 150,
      ellipsis: true,
    },
    {
      title: '留样日期',
      dataIndex: 'retention_date',
      key: 'retention_date',
      width: 120,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD') : '-',
    },
    {
      title: '有效期',
      dataIndex: 'expiry_date',
      key: 'expiry_date',
      width: 120,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD') : '-',
    },
    {
      title: '状态',
      dataIndex: 'retention_status',
      key: 'retention_status',
      width: 100,
      render: (value: RetentionStatus) => (
        <Tag color={RetentionStatusColors[value]}>
          {RetentionStatusLabels[value]}
        </Tag>
      ),
    },
    {
      title: '处置日期',
      dataIndex: 'disposal_date',
      key: 'disposal_date',
      width: 120,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD') : '-',
    },
    {
      title: '处置方式',
      dataIndex: 'disposal_method',
      key: 'disposal_method',
      width: 100,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-',
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card>
        {/* 筛选区域 */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Input
                placeholder="取样单号"
                value={filters.order_no}
                onChange={(e) => setFilters({ ...filters, order_no: e.target.value || undefined })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="样品编号"
                value={filters.sample_no}
                onChange={(e) => setFilters({ ...filters, sample_no: e.target.value || undefined })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="物料编码"
                value={filters.material_code}
                onChange={(e) => setFilters({ ...filters, material_code: e.target.value || undefined })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="物料名称"
                value={filters.material_name}
                onChange={(e) => setFilters({ ...filters, material_name: e.target.value || undefined })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="状态"
                value={filters.retention_status}
                onChange={(value) => setFilters({ ...filters, retention_status: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(RetentionStatusLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4} style={{ textAlign: 'right' }}>
              <Space>
                <Button type="primary" onClick={handleSearch}>查询</Button>
                <Button onClick={handleReset}>重置</Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1500 }}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </Card>
    </div>
  )
}
