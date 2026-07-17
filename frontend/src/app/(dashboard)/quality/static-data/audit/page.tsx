'use client'

import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Select,
  DatePicker,
  Button,
  Space,
  Row,
  Col,
  Modal,
  Tag,
  Typography,
  message,
  Spin,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { SearchOutlined, EyeOutlined, SyncOutlined, ExportOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { listAuditLogs, getAuditModules, AuditLogItem } from '@/actions/static-data'

const { RangePicker } = DatePicker
const { Text, Paragraph } = Typography

const API = '/api/v1'

// 模块名称映射
const MODULE_LABELS: Record<string, string> = {
  'storage-condition': '贮存条件',
  'unit': '计量单位',
  'test-item': '检验项目',
  'equipment': '检测设备',
  'chrom-column': '色谱柱',
  'medium': '培养基',
  'reagent': '试剂',
  'standard-material': '标准物质',
  'material-standard': '物料质量标准',
  'product-standard': '产品质量标准',
}

const OPERATE_TYPE_COLORS: Record<string, string> = {
  CREATE: 'green',
  UPDATE: 'blue',
  DELETE: 'red',
  TOGGLE_STATUS: 'orange',
}

const OPERATE_TYPE_LABELS: Record<string, string> = {
  CREATE: '新建',
  UPDATE: '修改',
  DELETE: '删除',
  TOGGLE_STATUS: '切换状态',
}

export default function AuditLogPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<AuditLogItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [moduleOptions, setModuleOptions] = useState<{ label: string; value: string }[]>([])
  const [selectedModule, setSelectedModule] = useState<string | undefined>(undefined)
  const [selectedOperateType, setSelectedOperateType] = useState<string | undefined>(undefined)
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [detailVisible, setDetailVisible] = useState(false)
  const [detailRecord, setDetailRecord] = useState<AuditLogItem | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // 加载模块列表
  useEffect(() => {
    getAuditModules().then(res => {
      if (res.code === 0) {
        setModuleOptions(res.data.map((m: any) => ({
          label: MODULE_LABELS[m.module_type] || m.module_type,
          value: m.module_type,
        })))
      }
    }).catch(() => {})
  }, [])

  // 加载审计日志
  const loadData = async () => {
    setLoading(true)
    try {
      const [startDate, endDate] = dateRange
        ? [dateRange[0].format('YYYY-MM-DD'), dateRange[1].format('YYYY-MM-DD')]
        : [undefined, undefined]

      const res = await listAuditLogs({
        page,
        page_size: pageSize,
        module_type: selectedModule,
        operate_type: selectedOperateType,
        start_date: startDate,
        end_date: endDate,
      })

      if (res.code === 0) {
        setData(res.data)
        setTotal(res.meta?.total || 0)
      } else {
        message.error(res.message || '加载失败')
      }
    } catch (e: any) {
      message.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [page, pageSize, selectedModule, selectedOperateType, dateRange])

  // 查看详情
  const handleViewDetail = async (record: AuditLogItem) => {
    setDetailRecord(record)
    setDetailVisible(true)
  }

  // 导出
  const handleExport = async () => {
    try {
      const [startDate, endDate] = dateRange
        ? [dateRange[0].format('YYYY-MM-DD'), dateRange[1].format('YYYY-MM-DD')]
        : ['', '']

      const params = new URLSearchParams()
      if (selectedModule) params.set('module_type', selectedModule)
      if (selectedOperateType) params.set('operate_type', selectedOperateType)
      if (startDate) params.set('start_date', startDate)
      if (endDate) params.set('end_date', endDate)

      const res = await fetch(`${API}/quality/static-data/audit/export?${params}`, {
        headers: { 'Authorization': 'Bearer dummy' },
      })
      if (!res.ok) throw new Error('导出失败')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `审计日志_${dayjs().format('YYYYMMDDHHmmss')}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
      message.success('导出成功')
    } catch (e: any) {
      message.error(e.message || '导出失败，请稍后重试')
    }
  }

  const columns: ColumnsType<AuditLogItem> = [
    {
      title: '序号',
      key: 'index',
      width: 60,
      render: (_, __, index) => (page - 1) * pageSize + index + 1,
    },
    {
      title: '模块',
      dataIndex: 'module_type',
      key: 'module_type',
      width: 130,
      render: (val) => MODULE_LABELS[val] || val,
    },
    {
      title: '记录编码',
      dataIndex: 'record_code',
      key: 'record_code',
      width: 150,
      render: (val) => val || '-',
    },
    {
      title: '操作类型',
      dataIndex: 'operate_type',
      key: 'operate_type',
      width: 100,
      render: (val) => (
        <Tag color={OPERATE_TYPE_COLORS[val] || 'default'}>
          {OPERATE_TYPE_LABELS[val] || val}
        </Tag>
      ),
    },
    {
      title: '操作人ID',
      dataIndex: 'operate_by',
      key: 'operate_by',
      width: 100,
    },
    {
      title: '操作时间',
      dataIndex: 'operate_time',
      key: 'operate_time',
      width: 170,
      render: (val) => val ? dayjs(val).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '变更摘要',
      dataIndex: 'change_summary',
      key: 'change_summary',
      ellipsis: true,
      render: (val) => val || '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button
          type="link"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          详情
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card title="变更审计日志" extra={
        <Space>
          <Button icon={<ExportOutlined />} onClick={handleExport}>导出</Button>
          <Button icon={<SyncOutlined />} onClick={loadData}>刷新</Button>
        </Space>
      }>
        {/* 筛选区 */}
        <div style={{ marginBottom: 16 }}>
          <Row gutter={12} align="middle" style={{ rowGap: 8 }}>
            <Col>
              <Select
                allowClear
                placeholder="选择模块"
                style={{ width: 150 }}
                options={moduleOptions}
                value={selectedModule}
                onChange={(val) => { setSelectedModule(val); setPage(1) }}
              />
            </Col>
            <Col>
              <Select
                allowClear
                placeholder="操作类型"
                style={{ width: 120 }}
                value={selectedOperateType}
                onChange={(val) => { setSelectedOperateType(val); setPage(1) }}
              >
                <Select.Option value="CREATE">新建</Select.Option>
                <Select.Option value="UPDATE">修改</Select.Option>
                <Select.Option value="DELETE">删除</Select.Option>
                <Select.Option value="TOGGLE_STATUS">切换状态</Select.Option>
              </Select>
            </Col>
            <Col>
              <RangePicker
                value={dateRange}
                onChange={(dates) => { setDateRange(dates as any); setPage(1) }}
                format="YYYY-MM-DD"
                placeholder={['开始日期', '结束日期']}
              />
            </Col>
            <Col>
              <Button type="primary" icon={<SearchOutlined />} onClick={loadData}>
                查询
              </Button>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => { setPage(p); setPageSize(ps) },
          }}
          scroll={{ x: 900 }}
          size="small"
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="审计日志详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={
          <Button type="primary" onClick={() => setDetailVisible(false)}>
            关闭
          </Button>
        }
        width={700}
      >
        {detailRecord && (
          <div>
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={12}>
                <Text strong>模块：</Text>
                <Text>{MODULE_LABELS[detailRecord.module_type] || detailRecord.module_type}</Text>
              </Col>
              <Col span={12}>
                <Text strong>操作类型：</Text>
                <Tag color={OPERATE_TYPE_COLORS[detailRecord.operate_type]}>
                  {OPERATE_TYPE_LABELS[detailRecord.operate_type]}
                </Tag>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={12}>
                <Text strong>记录ID：</Text>
                <Text>{detailRecord.record_id}</Text>
              </Col>
              <Col span={12}>
                <Text strong>记录编码：</Text>
                <Text>{detailRecord.record_code || '-'}</Text>
              </Col>
            </Row>
            <Row gutter={16} style={{ marginBottom: 12 }}>
              <Col span={12}>
                <Text strong>操作人ID：</Text>
                <Text>{detailRecord.operate_by}</Text>
              </Col>
              <Col span={12}>
                <Text strong>操作时间：</Text>
                <Text>{detailRecord.operate_time ? dayjs(detailRecord.operate_time).format('YYYY-MM-DD HH:mm:ss') : '-'}</Text>
              </Col>
            </Row>
            <div style={{ marginBottom: 12 }}>
              <Text strong>变更摘要：</Text>
              <Paragraph type="secondary">{detailRecord.change_summary || '无'}</Paragraph>
            </div>

            <Row gutter={16}>
              <Col span={12}>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>变更前：</Text>
                <div style={{
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  maxHeight: 300,
                  overflow: 'auto',
                  fontFamily: 'monospace',
                  fontSize: 12,
                }}>
                  {detailRecord.old_value
                    ? <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                        {JSON.stringify(JSON.parse(detailRecord.old_value), null, 2)}
                      </pre>
                    : <Text type="secondary">无</Text>
                  }
                </div>
              </Col>
              <Col span={12}>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>变更后：</Text>
                <div style={{
                  background: '#f5f5f5',
                  padding: 12,
                  borderRadius: 4,
                  maxHeight: 300,
                  overflow: 'auto',
                  fontFamily: 'monospace',
                  fontSize: 12,
                }}>
                  {detailRecord.new_value
                    ? <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                        {JSON.stringify(JSON.parse(detailRecord.new_value), null, 2)}
                      </pre>
                    : <Text type="secondary">无</Text>
                  }
                </div>
              </Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  )
}
