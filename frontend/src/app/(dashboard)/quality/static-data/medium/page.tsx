'use client'

import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Table,
  Button,
  Input,
  Form,
  Tag,
  message,
  Popconfirm,
  DatePicker,
  Drawer,
  Row,
  Col,
  InputNumber,
  Select,
  Segmented,
  Pagination,
  Tooltip,
  Space,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FilterOutlined,
  ExperimentOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  MinusCircleOutlined,
  PlusCircleOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { Medium, MEDIUM_TYPE_OPTIONS, MEDIUM_VERIFY_STATUS_OPTIONS } from '@/types/static-data'
import {
  listMedium,
  createMedium,
  updateMedium,
  deleteMedium,
  adjustMediumStock,
} from '@/lib/api/client/static-data-api'
import './medium-style.css'

const { Search } = Input
const { Option } = Select

const MEDIUM_TYPE_META: Record<string, { label: string; color: string }> = {
  '干粉培养基': { label: '干粉', color: '#10b981' },
  '颗粒培养基': { label: '颗粒', color: '#3b82f6' },
  '液体培养基': { label: '液体', color: '#06b6d4' },
  '显色培养基': { label: '显色', color: '#f59e0b' },
  '环境监测培养基': { label: '环境', color: '#8b5cf6' },
}

const VERIFY_STATUS_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  '待验证': { label: '待验证', color: '#f59e0b', icon: <ClockCircleOutlined /> },
  '已验证': { label: '已验证', color: '#10b981', icon: <CheckCircleOutlined /> },
  '验证失败': { label: '失败', color: '#ef4444', icon: <WarningOutlined /> },
}

export default function MediumPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<number | 'all'>('all')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [editingRecord, setEditingRecord] = useState<Medium | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [form] = Form.useForm()
  const [advancedForm] = Form.useForm()
  const [stockDrawerOpen, setStockDrawerOpen] = useState(false)
  const [stockAdjustRecord, setStockAdjustRecord] = useState<Medium | null>(null)
  const [stockForm] = Form.useForm()
  const queryClient = useQueryClient()

  const queryParams = useCallback((): Record<string, unknown> => {
    const params: Record<string, unknown> = { page, page_size: pageSize }
    if (searchText) {
      params.medium_code = searchText
      params.medium_name = searchText
    }
    if (typeFilter !== 'all') {
      params.medium_type = typeFilter
    }
    if (statusFilter !== 'all') {
      params.status = statusFilter
    }
    const adv = advancedForm.getFieldsValue()
    if (adv.manufacturer) params.manufacturer = adv.manufacturer
    return params
  }, [page, pageSize, searchText, typeFilter, statusFilter, advancedForm])

  const { data: queryResult, isLoading: loading, refetch: fetchData } = useQuery({
    queryKey: ['medium-list', page, pageSize, searchText, typeFilter, statusFilter],
    queryFn: async () => {
      const params = queryParams()
      const res = await listMedium(params)
      return { items: (res?.data ?? []) as Medium[], total: res?.meta?.total ?? 0 }
    },
  })

  const data = queryResult?.items || []
  const total = queryResult?.total || 0

  const { data: statsData = { all: 0, verified: 0, pending: 0, expired: 0, lowStock: 0 }, refetch: fetchStats } = useQuery({
    queryKey: ['medium-stats', typeFilter],
    queryFn: async () => {
      let allData: Medium[] = []
      let curPage = 1
      while (true) {
        const params: Record<string, unknown> = { page: curPage, page_size: 200 }
        if (typeFilter !== 'all') {
          params.medium_type = typeFilter
        }
        const res = await listMedium(params)
        const batch = (res?.data ?? []) as Medium[]
        allData = allData.concat(batch)
        if (allData.length >= (res?.meta?.total ?? 0) || batch.length === 0) break
        curPage++
      }
      let verified = 0, pending = 0, expired = 0, lowStock = 0
      const today = dayjs()
      allData.forEach(item => {
        if (item.verify_status === '已验证') verified++
        if (item.verify_status === '待验证') pending++
        if (dayjs(item.expire_date).isBefore(today)) expired++
        if (item.stock_num <= item.min_stock) lowStock++
      })
      return { all: allData.length, verified, pending, expired, lowStock }
    },
  })

  const handleQuickSearch = (val: string) => {
    setSearchText(val)
    setPage(1)
  }

  const handleTypeFilter = (val: string | 'all') => {
    setTypeFilter(val)
    setPage(1)
  }

  const handleStatusFilter = (val: number | 'all') => {
    setStatusFilter(val)
    setPage(1)
  }

  const handleAdvancedSearch = () => {
    setPage(1)
    fetchData()
  }

  const handleReset = () => {
    setSearchText('')
    setTypeFilter('all')
    setStatusFilter('all')
    advancedForm.resetFields()
    setPage(1)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteMedium(id)
      message.success('删除成功')
      fetchData()
      fetchStats()
    } catch (e: unknown) {
      message.error((e instanceof Error ? e.message : '删除失败'))
    }
  }

  const openCreate = () => {
    setIsNew(true)
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({ status: 0, stock_num: 0, min_stock: 10, verify_status: '待验证' })
    setDrawerOpen(true)
  }

  const openDetail = (record: Medium) => {
    setIsNew(false)
    setEditingRecord(record)
    const toDay = (v: string | null) => v ? dayjs(v) : undefined
    form.setFieldsValue({
      ...record,
      expire_date: toDay(record.expire_date),
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setDrawerLoading(true)

      const dateFields = ['expire_date']
      dateFields.forEach(f => {
        if (values[f] && typeof values[f].format === 'function') {
          values[f] = values[f].format('YYYY-MM-DD')
        }
      })

      if (isNew) {
        await createMedium(values)
        message.success('创建成功')
      } else if (editingRecord) {
        await updateMedium(editingRecord.id, values)
        message.success('更新成功')
      }
      setDrawerOpen(false)
      fetchData()
      fetchStats()
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      message.error((e instanceof Error ? e.message : '保存失败'))
    } finally {
      setDrawerLoading(false)
    }
  }

  const openStockAdjust = (record: Medium) => {
    setStockAdjustRecord(record)
    stockForm.resetFields()
    stockForm.setFieldsValue({ quantity: 0 })
    setStockDrawerOpen(true)
  }

  const handleStockAdjust = async () => {
    try {
      const values = await stockForm.validateFields()
      if (stockAdjustRecord) {
        await adjustMediumStock(stockAdjustRecord.id, values.quantity)
        message.success('库存调整成功')
        setStockDrawerOpen(false)
        fetchData()
        fetchStats()
      }
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      message.error((e instanceof Error ? e.message : '调整失败'))
    }
  }

  const columns: ColumnsType<Medium> = [
    {
      title: '编号',
      dataIndex: 'medium_code',
      width: 100,
      fixed: 'left',
      render: (v, record) => (
        <a onClick={() => openDetail(record)} style={{ fontWeight: 600, color: '#10b981' }}>
          {v}
        </a>
      ),
    },
    { title: '名称', dataIndex: 'medium_name', width: 140, ellipsis: true },
    {
      title: '类型',
      dataIndex: 'medium_type',
      width: 100,
      render: v => {
        const meta = MEDIUM_TYPE_META[v]
        return meta ? (
          <Tag color={meta.color}>{meta.label}</Tag>
        ) : v
      },
    },
    { title: '厂家', dataIndex: 'manufacturer', width: 100, ellipsis: true },
    { title: '批号', dataIndex: 'batch_no', width: 100 },
    {
      title: '有效期',
      dataIndex: 'expire_date',
      width: 110,
      render: v => {
        const isExpired = dayjs(v).isBefore(dayjs())
        return (
          <span style={{ color: isExpired ? '#ef4444' : undefined }}>
            {v}
          </span>
        )
      },
    },
    {
      title: '验证状态',
      dataIndex: 'verify_status',
      width: 100,
      render: v => {
        const meta = VERIFY_STATUS_META[v]
        return meta ? (
          <Tag color={meta.color}>
            {meta.icon} {meta.label}
          </Tag>
        ) : v
      },
    },
    {
      title: '库存',
      width: 120,
      render: (_, record) => {
        const isLow = record.stock_num <= record.min_stock
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ color: isLow ? '#ef4444' : '#10b981', fontWeight: 600 }}>
              {record.stock_num}
            </span>
            <span style={{ color: '#64748b' }}>/ {record.unit_code}</span>
            {isLow && <WarningOutlined style={{ color: '#ef4444' }} />}
          </div>
        )
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      fixed: 'right',
      render: (_, record) => (
        <Space size={2}>
          <Tooltip title="调整库存">
            <Button
              type="text"
              size="small"
              icon={<ExperimentOutlined />}
              onClick={() => openStockAdjust(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openDetail(record)} />
          </Tooltip>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="确定" cancelText="取消">
            <Tooltip title="删除">
              <Button type="text" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="medium-page">
      <div className="medium-header">
        <div className="medium-header-left">
          <div className="medium-title">
            <span className="medium-title-icon">🧫</span>
            <div>
              <h1>培养基管理</h1>
              <p>管理微生物培养基库存、有效期与验证状态</p>
            </div>
          </div>
        </div>
        <div className="medium-header-right">
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={openCreate} className="medium-add-btn">
            新建培养基
          </Button>
        </div>
      </div>

      <div className="medium-stats">
        <div className="stat-card stat-all" onClick={() => handleStatusFilter('all')}>
          <div className="stat-icon">🧪</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.all}</div>
            <div className="stat-label">全部培养基</div>
          </div>
        </div>
        <div className="stat-card stat-verified" onClick={() => handleTypeFilter('all')}>
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.verified}</div>
            <div className="stat-label">已验证</div>
          </div>
        </div>
        <div className="stat-card stat-pending" onClick={() => handleTypeFilter('all')}>
          <div className="stat-icon">⏳</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.pending}</div>
            <div className="stat-label">待验证</div>
          </div>
        </div>
        <div className="stat-card stat-expired" onClick={() => handleTypeFilter('all')}>
          <div className="stat-icon">⚠️</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.expired}</div>
            <div className="stat-label">已过期</div>
          </div>
        </div>
        <div className="stat-card stat-low-stock" onClick={() => handleTypeFilter('all')}>
          <div className="stat-icon">📉</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.lowStock}</div>
            <div className="stat-label">库存不足</div>
          </div>
        </div>
      </div>

      <div className="medium-toolbar">
        <div className="medium-search-wrap">
          <Search
            placeholder="搜索编号或名称..."
            allowClear
            size="large"
            value={searchText}
            onChange={e => handleQuickSearch(e.target.value)}
            onSearch={handleQuickSearch}
            className="medium-search"
          />
          <Select
            size="large"
            value={typeFilter}
            onChange={handleTypeFilter}
            style={{ width: 160, marginLeft: 12 }}
          >
            <Option value="all">全部类型</Option>
            {MEDIUM_TYPE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        </div>
        <div className="medium-toolbar-right">
          <Button
            icon={<FilterOutlined />}
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={showAdvanced ? 'medium-filter-active' : ''}
          >
            高级筛选
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { fetchData(); fetchStats() }}>
            刷新
          </Button>
          <Segmented
            value={viewMode}
            onChange={v => setViewMode(v as 'card' | 'table')}
            options={[
              { value: 'card', icon: <ExperimentOutlined /> },
              { value: 'table', icon: <ExperimentOutlined /> },
            ]}
          />
        </div>
      </div>

      {showAdvanced && (
        <div className="medium-advanced">
          <Form form={advancedForm} layout="vertical">
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="manufacturer" label="生产厂家">
                  <Input placeholder="输入厂家名称" allowClear />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item label=" " colon={false}>
                  <Space>
                    <Button type="primary" onClick={handleAdvancedSearch}>查询</Button>
                    <Button onClick={handleReset}>重置</Button>
                  </Space>
                </Form.Item>
              </Col>
            </Row>
          </Form>
        </div>
      )}

      {viewMode === 'card' ? (
        <div>
          <div className="medium-card-grid">
            {data.map((item, idx) => {
              const typeMeta = MEDIUM_TYPE_META[item.medium_type]
              const verifyMeta = VERIFY_STATUS_META[item.verify_status]
              const isExpired = dayjs(item.expire_date).isBefore(dayjs())
              const isLowStock = item.stock_num <= item.min_stock
              const stockPercent = item.min_stock > 0 ? Math.round((item.stock_num / (item.min_stock * 2)) * 100) : 100
              return (
                <div
                  key={item.id}
                  className="medium-card"
                  onClick={() => openDetail(item)}
                  style={{ animationDelay: `${idx * 0.03}s` }}
                >
                  <div className="medium-card-type-bar" style={{ background: typeMeta?.color || '#94a3b8' }} />
                  <div className="medium-card-body">
                    <div className="medium-card-header">
                      <span className="medium-card-code">{item.medium_code}</span>
                      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                        <Tag color={typeMeta?.color} style={{ margin: 0 }}>
                          {typeMeta?.label}
                        </Tag>
                        {isExpired && (
                          <Tag color="#ef4444" style={{ margin: 0 }}>过期</Tag>
                        )}
                      </div>
                    </div>
                    <div className="medium-card-name">{item.medium_name}</div>
                    <div className="medium-card-spec">{item.batch_no} · {item.manufacturer}</div>
                    <div className="medium-card-stock">
                      <div className="medium-stock-label">
                        <span>库存</span>
                        <span className="medium-stock-count" style={{ color: isLowStock ? '#ef4444' : '#10b981' }}>
                          {item.stock_num} / {item.unit_code}
                        </span>
                      </div>
                      <div className="medium-stock-bar">
                        <div
                          className="medium-stock-fill"
                          style={{ width: `${Math.min(stockPercent, 100)}%`, background: isLowStock ? '#ef4444' : '#10b981' }}
                        />
                      </div>
                    </div>
                    <div className="medium-card-info-grid">
                      <div className="medium-card-info-item">
                        <div className="medium-info-label">有效期</div>
                        <div className="medium-info-value" style={{ color: isExpired ? '#ef4444' : undefined }}>
                          {item.expire_date}
                        </div>
                      </div>
                      <div className="medium-card-info-item">
                        <div className="medium-info-label">验证</div>
                        <div className="medium-info-value">
                          <Tag color={verifyMeta?.color} style={{ margin: 0, fontSize: 11 }}>
                            {verifyMeta?.label}
                          </Tag>
                        </div>
                      </div>
                    </div>
                    <div className="medium-card-actions" onClick={e => e.stopPropagation()}>
                      <Tooltip title="调整库存">
                        <Button
                          type="text"
                          size="small"
                          icon={<ExperimentOutlined />}
                          onClick={() => openStockAdjust(item)}
                        />
                      </Tooltip>
                      <Tooltip title="编辑">
                        <Button type="text" size="small" icon={<EditOutlined />} onClick={() => openDetail(item)} />
                      </Tooltip>
                      <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)} okText="确定" cancelText="取消">
                        <Tooltip title="删除">
                          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                        </Tooltip>
                      </Popconfirm>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          <div className="medium-pagination">
            <Pagination
              current={page}
              pageSize={pageSize}
              total={total}
              onChange={(p, ps) => { setPage(p); setPageSize(ps) }}
              showSizeChanger
              showTotal={t => `共 ${t} 条`}
            />
          </div>
        </div>
      ) : (
        <div className="medium-table-wrap">
          <Table
            columns={columns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ x: 1000 }}
          />
          <div className="medium-pagination">
            <Pagination
              current={page}
              pageSize={pageSize}
              total={total}
              onChange={(p, ps) => { setPage(p); setPageSize(ps) }}
              showSizeChanger
              showTotal={t => `共 ${t} 条`}
            />
          </div>
        </div>
      )}

      <Drawer
        title={isNew ? '新建培养基' : '编辑培养基'}
        placement="right"
        width={560}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleSave} loading={drawerLoading}>
              保存
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical" className="medium-drawer-form">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="medium_code"
                label="培养基编号"
                rules={[{ required: true, message: '请输入编号' }]}
              >
                <Input placeholder="如 MJ24001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="medium_name"
                label="培养基名称"
                rules={[{ required: true, message: '请输入名称' }]}
              >
                <Input placeholder="如 TSA培养基" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="medium_type"
                label="培养基类型"
                rules={[{ required: true, message: '请选择类型' }]}
              >
                <Select>
                  {MEDIUM_TYPE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="manufacturer"
                label="生产厂家"
                rules={[{ required: true, message: '请输入厂家' }]}
              >
                <Input placeholder="生产厂家名称" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="batch_no"
                label="批号"
                rules={[{ required: true, message: '请输入批号' }]}
              >
                <Input placeholder="批号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="spec"
                label="规格"
                rules={[{ required: true, message: '请输入规格' }]}
              >
                <Input placeholder="如 500g/瓶" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="expire_date"
                label="有效期"
                rules={[{ required: true, message: '请选择日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="verify_status"
                label="验证状态"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select>
                  {MEDIUM_VERIFY_STATUS_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item
                name="stock_num"
                label="库存数量"
                rules={[{ required: true, message: '请输入数量' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="unit_code"
                label="单位"
                rules={[{ required: true, message: '请输入单位' }]}
              >
                <Input placeholder="如 瓶、g" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="min_stock"
                label="最低库存"
                rules={[{ required: true, message: '请输入阈值' }]}
              >
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="storage_cond_code"
                label="贮存条件编码"
                rules={[{ required: true, message: '请输入贮存条件' }]}
              >
                <Input placeholder="如 RT_2_8C" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="config_method" label="配制方法">
                <Input placeholder="配制方法说明" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} placeholder="备注信息" maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Drawer>

      <Drawer
        title="调整库存"
        placement="right"
        size={400}
        open={stockDrawerOpen}
        onClose={() => setStockDrawerOpen(false)}
        extra={
          <Space>
            <Button onClick={() => setStockDrawerOpen(false)}>取消</Button>
            <Button type="primary" onClick={handleStockAdjust}>
              确认调整
            </Button>
          </Space>
        }
      >
        <Form form={stockForm} layout="vertical">
          <Form.Item label="当前培养基">
            <div style={{ fontSize: 16, fontWeight: 500 }}>
              {stockAdjustRecord?.medium_name} ({stockAdjustRecord?.medium_code})
            </div>
            <div style={{ color: '#64748b', marginTop: 4 }}>
              当前库存: <span style={{ fontWeight: 600, color: '#10b981' }}>{stockAdjustRecord?.stock_num}</span> {stockAdjustRecord?.unit_code}
            </div>
          </Form.Item>
          <Form.Item
            name="quantity"
            label="调整数量"
            rules={[{ required: true, message: '请输入数量' }]}
            extra="正数为入库，负数为出库"
          >
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
            <Button icon={<PlusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity: stockForm.getFieldValue('quantity') + 10 })}>
              +10
            </Button>
            <Button icon={<PlusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity: stockForm.getFieldValue('quantity') + 1 })}>
              +1
            </Button>
            <Button icon={<MinusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity: stockForm.getFieldValue('quantity') - 1 })}>
              -1
            </Button>
            <Button icon={<MinusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity: stockForm.getFieldValue('quantity') - 10 })}>
              -10
            </Button>
          </div>
        </Form>
      </Drawer>
    </div>
  )
}