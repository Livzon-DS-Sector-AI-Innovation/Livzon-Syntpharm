'use client'

import { useState, useEffect, useCallback } from 'react'
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
  SearchOutlined,
  ReloadOutlined,
  FilterOutlined,
  TrophyOutlined,
  WarningOutlined,
  MinusCircleOutlined,
  PlusCircleOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { Standard, STANDARD_STATUS_OPTIONS, STANDARD_TYPE_OPTIONS } from '@/types/static-data'
import {
  listStandard,
  createStandard,
  updateStandard,
  deleteStandard,
  adjustStandardQuantity,
} from '@/lib/static-data-api'
import './standard-style.css'

const { Search } = Input
const { Option } = Select

const STD_TYPE_META: Record<string, { label: string; color: string }> = {
  national: { label: '国家标准品', color: '#dc2626' },
  working: { label: '工作标准品', color: '#2563eb' },
  international: { label: '国际标准品', color: '#7c3aed' },
}

const STD_STATUS_META: Record<number, { label: string; color: string }> = {
  0: { label: '在用', color: '#10b981' },
  1: { label: '用完', color: '#6b7280' },
  2: { label: '过期', color: '#ef4444' },
  3: { label: '停用', color: '#f59e0b' },
}

export default function StandardPage() {
  const [data, setData] = useState<Standard[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')
  const [searchText, setSearchText] = useState('')
  const [typeFilter, setTypeFilter] = useState<string | 'all'>('all')
  const [statusFilter, setStatusFilter] = useState<number | 'all'>('all')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [editingRecord, setEditingRecord] = useState<Standard | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [form] = Form.useForm()
  const [stockDrawerOpen, setStockDrawerOpen] = useState(false)
  const [stockAdjustRecord, setStockAdjustRecord] = useState<Standard | null>(null)
  const [stockForm] = Form.useForm()

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, page_size: pageSize }
      if (searchText) {
        params.std_code = searchText
        params.std_name = searchText
      }
      if (typeFilter !== 'all') {
        params.std_type = typeFilter
      }
      if (statusFilter !== 'all') {
        params.std_status = statusFilter
      }
      const res = await listStandard(params)
      setData((res?.data ?? []) as Standard[])
      setTotal(res?.meta?.total ?? 0)
    } catch (e: any) {
      message.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchText, typeFilter, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const [statsData, setStatsData] = useState({ all: 0, active: 0, expired: 0, lowStock: 0, national: 0 })

  const fetchStats = useCallback(async () => {
    try {
      let allData: Standard[] = []
      let curPage = 1
      while (true) {
        const res = await listStandard({ page: curPage, page_size: 200 })
        const batch = (res?.data ?? []) as Standard[]
        allData = allData.concat(batch)
        if (allData.length >= (res?.meta?.total ?? 0) || batch.length === 0) break
        curPage++
      }
      let active = 0, expired = 0, lowStock = 0, national = 0
      const today = dayjs()
      allData.forEach(item => {
        if (item.std_status === 0) active++
        if (item.expire_date && dayjs(item.expire_date).isBefore(today)) expired++
        if (item.quantity <= item.min_stock) lowStock++
        if (item.std_type === 'national') national++
      })
      setStatsData({ all: allData.length, active, expired, lowStock, national })
    } catch (e) {
      console.error('stats fetch error:', e)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

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

  const handleReset = () => {
    setSearchText('')
    setTypeFilter('all')
    setStatusFilter('all')
    setPage(1)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteStandard(id)
      message.success('删除成功')
      fetchData()
      fetchStats()
    } catch (e: any) {
      message.error(e.message || '删除失败')
    }
  }

  const openCreate = () => {
    setIsNew(true)
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({ std_status: 0, quantity: 1, min_stock: 1, std_type: 'working' })
    setDrawerOpen(true)
  }

  const openDetail = (record: Standard) => {
    setIsNew(false)
    setEditingRecord(record)
    const toDay = (v: string | null) => (v ? dayjs(v) : undefined)
    form.setFieldsValue({
      ...record,
      produce_date: toDay(record.produce_date),
      expire_date: toDay(record.expire_date),
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setDrawerLoading(true)

      const dateFields = ['produce_date', 'expire_date']
      dateFields.forEach(f => {
        if (values[f] && typeof values[f].format === 'function') {
          values[f] = values[f].format('YYYY-MM-DD')
        }
      })

      if (isNew) {
        await createStandard(values)
        message.success('创建成功')
      } else if (editingRecord) {
        await updateStandard(editingRecord.id, values)
        message.success('更新成功')
      }
      setDrawerOpen(false)
      fetchData()
      fetchStats()
    } catch (e: any) {
      if (e.errorFields) return
      message.error(e.message || '保存失败')
    } finally {
      setDrawerLoading(false)
    }
  }

  const openStockAdjust = (record: Standard) => {
    setStockAdjustRecord(record)
    stockForm.resetFields()
    stockForm.setFieldsValue({ quantity: 0 })
    setStockDrawerOpen(true)
  }

  const handleStockAdjust = async () => {
    try {
      const values = await stockForm.validateFields()
      if (stockAdjustRecord) {
        await adjustStandardQuantity(stockAdjustRecord.id, values.quantity)
        message.success('数量调整成功')
        setStockDrawerOpen(false)
        fetchData()
        fetchStats()
      }
    } catch (e: any) {
      if (e.errorFields) return
      message.error(e.message || '调整失败')
    }
  }

  const columns: ColumnsType<Standard> = [
    {
      title: '编号',
      dataIndex: 'std_code',
      width: 110,
      fixed: 'left',
      render: (v, record) => (
        <a onClick={() => openDetail(record)} style={{ fontWeight: 600, color: '#7c3aed' }}>
          {v}
        </a>
      ),
    },
    { title: '名称', dataIndex: 'std_name', width: 160, ellipsis: true },
    {
      title: '类型',
      dataIndex: 'std_type',
      width: 110,
      render: v => {
        const meta = STD_TYPE_META[v]
        return meta ? <Tag color={meta.color}>{meta.label}</Tag> : v
      },
    },
    { title: '批号', dataIndex: 'batch_no', width: 100 },
    { title: 'CAS号', dataIndex: 'cas_no', width: 110 },
    {
      title: '纯度',
      dataIndex: 'purity',
      width: 80,
      render: v => (v ? `${v}%` : '-'),
    },
    {
      title: '有效期',
      dataIndex: 'expire_date',
      width: 110,
      render: v => {
        if (!v) return '-'
        const isExpired = dayjs(v).isBefore(dayjs())
        return <span style={{ color: isExpired ? '#ef4444' : undefined }}>{v}</span>
      },
    },
    {
      title: '库存',
      width: 100,
      render: (_, record) => {
        const isLow = record.quantity <= record.min_stock
        return (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ color: isLow ? '#ef4444' : '#7c3aed', fontWeight: 600 }}>
              {record.quantity}
            </span>
            <span style={{ color: '#64748b' }}>{record.unit_code}</span>
            {isLow && <WarningOutlined style={{ color: '#ef4444' }} />}
          </div>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'std_status',
      width: 80,
      render: v => {
        const meta = STD_STATUS_META[v]
        return meta ? <Tag color={meta.color}>{meta.label}</Tag> : v
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 140,
      fixed: 'right',
      render: (_, record) => (
        <Space size={2}>
          <Tooltip title="调整数量">
            <Button type="text" size="small" icon={<TrophyOutlined />} onClick={() => openStockAdjust(record)} />
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
    <div className="std-page">
      <div className="std-header">
        <div className="std-header-left">
          <div className="std-title">
            <span className="std-title-icon">🏆</span>
            <div>
              <h1>标准品管理</h1>
              <p>管理国家标准品、工作标准品与国际标准品的库存与有效期</p>
            </div>
          </div>
        </div>
        <div className="std-header-right">
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={openCreate} className="std-add-btn">
            新建标准品
          </Button>
        </div>
      </div>

      <div className="std-stats">
        <div className="stat-card stat-all" onClick={() => handleStatusFilter('all')}>
          <div className="stat-icon">📋</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.all}</div>
            <div className="stat-label">全部标准品</div>
          </div>
        </div>
        <div className="stat-card stat-active" onClick={() => handleStatusFilter(0)}>
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.active}</div>
            <div className="stat-label">在用</div>
          </div>
        </div>
        <div className="stat-card stat-national" onClick={() => handleTypeFilter('national')}>
          <div className="stat-icon">🇨🇳</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.national}</div>
            <div className="stat-label">国家标准品</div>
          </div>
        </div>
        <div className="stat-card stat-expired" onClick={() => handleStatusFilter(2)}>
          <div className="stat-icon">⚠️</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.expired}</div>
            <div className="stat-label">已过期</div>
          </div>
        </div>
        <div className="stat-card stat-low-stock" onClick={() => handleStatusFilter('all')}>
          <div className="stat-icon">📉</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.lowStock}</div>
            <div className="stat-label">库存不足</div>
          </div>
        </div>
      </div>

      <div className="std-toolbar">
        <div className="std-search-wrap">
          <Search
            placeholder="搜索编号或名称..."
            allowClear
            size="large"
            value={searchText}
            onChange={e => handleQuickSearch(e.target.value)}
            onSearch={handleQuickSearch}
            className="std-search"
          />
          <Select
            size="large"
            value={typeFilter}
            onChange={handleTypeFilter}
            style={{ width: 160, marginLeft: 12 }}
          >
            <Option value="all">全部类型</Option>
            {STANDARD_TYPE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        </div>
        <div className="std-toolbar-right">
          <Button icon={<FilterOutlined />} onClick={() => setShowAdvanced(!showAdvanced)} className={showAdvanced ? 'std-filter-active' : ''}>
            高级筛选
          </Button>          <Button icon={<ReloadOutlined />} onClick={() => { fetchData(); fetchStats() }}>
            刷新
          </Button>
          <Segmented
            value={viewMode}
            onChange={v => setViewMode(v as 'card' | 'table')}
            options={[
              { value: 'card', icon: <AppstoreOutlined /> },
              { value: 'table', icon: <UnorderedListOutlined /> },
            ]}
          />
        </div>
      </div>

      {viewMode === 'card' ? (
        <div>
          <div className="std-card-grid">
            {data.map((item, idx) => {
              const typeMeta = STD_TYPE_META[item.std_type]
              const statusMeta = STD_STATUS_META[item.std_status]
              const isExpired = item.expire_date && dayjs(item.expire_date).isBefore(dayjs())
              const isLowStock = item.quantity <= item.min_stock
              const stockPercent = item.min_stock > 0 ? Math.round((item.quantity / (item.min_stock * 2)) * 100) : 100
              return (
                <div
                  key={item.id}
                  className="std-card"
                  onClick={() => openDetail(item)}
                  style={{ animationDelay: `${idx * 0.03}s` }}
                >
                  <div className="std-card-type-bar" style={{ background: typeMeta?.color || '#94a3b8' }} />
                  <div className="std-card-body">
                    <div className="std-card-header">
                      <span className="std-card-code">{item.std_code}</span>
                      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                        <Tag color={typeMeta?.color} style={{ margin: 0 }}>
                          {typeMeta?.label}
                        </Tag>
                        {isExpired && <Tag color="#ef4444" style={{ margin: 0 }}>过期</Tag>}
                      </div>
                    </div>
                    <div className="std-card-name">{item.std_name}</div>
                    <div className="std-card-spec">
                      {item.batch_no}
                      {item.cas_no ? ` · CAS: ${item.cas_no}` : ''}
                    </div>
                    <div className="std-card-stock">
                      <div className="std-stock-label">
                        <span>库存</span>
                        <span className="std-stock-count" style={{ color: isLowStock ? '#ef4444' : '#7c3aed' }}>
                          {item.quantity} / {item.unit_code}
                        </span>
                      </div>
                      <div className="std-stock-bar">
                        <div
                          className="std-stock-fill"
                          style={{ width: `${Math.min(stockPercent, 100)}%`, background: isLowStock ? '#ef4444' : '#7c3aed' }}
                        />
                      </div>
                    </div>
                    <div className="std-card-info-grid">
                      <div className="std-card-info-item">
                        <div className="std-info-label">有效期</div>
                        <div className="std-info-value" style={{ color: isExpired ? '#ef4444' : undefined }}>
                          {item.expire_date || '-'}
                        </div>
                      </div>
                      <div className="std-card-info-item">
                        <div className="std-info-label">状态</div>
                        <div className="std-info-value">
                          <Tag color={statusMeta?.color} style={{ margin: 0, fontSize: 11 }}>
                            {statusMeta?.label}
                          </Tag>
                        </div>
                      </div>
                    </div>
                    <div className="std-card-actions" onClick={e => e.stopPropagation()}>
                      <Tooltip title="调整数量">
                        <Button type="text" size="small" icon={<TrophyOutlined />} onClick={() => openStockAdjust(item)} />
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
          <div className="std-pagination">
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
        <div className="std-table-wrap">
          <Table
            columns={columns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ x: 1100 }}
          />
          <div className="std-pagination">
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
        title={isNew ? '新建标准品' : '编辑标准品'}
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
        <Form form={form} layout="vertical" className="std-drawer-form">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="std_code" label="标准品编号" rules={[{ required: true, message: '请输入编号' }]}>
                <Input placeholder="如 STD24001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="std_name" label="标准品名称" rules={[{ required: true, message: '请输入名称' }]}>
                <Input placeholder="如 阿莫西林标准品" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="std_type" label="标准品类型" rules={[{ required: true, message: '请选择类型' }]}>
                <Select>
                  {STANDARD_TYPE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="batch_no" label="批号" rules={[{ required: true, message: '请输入批号' }]}>
                <Input placeholder="批号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="cas_no" label="CAS号">
                <Input placeholder="CAS号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="spec" label="规格">
                <Input placeholder="如 100mg/支" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="purity" label="纯度(%)">
                <InputNumber min={0} max={100} step={0.01} style={{ width: '100%' }} placeholder="如 99.5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="content" label="含量(%)">
                <InputNumber min={0} max={100} step={0.01} style={{ width: '100%' }} placeholder="如 99.8" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="quantity" label="库存数量" rules={[{ required: true, message: '请输入数量' }]}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="unit_code" label="单位" rules={[{ required: true, message: '请输入单位' }]}>
                <Input placeholder="如 支、mg" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="min_stock" label="最低库存" rules={[{ required: true, message: '请输入阈值' }]}>
                <InputNumber min={0} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="produce_date" label="生产日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="expire_date" label="有效期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="storage_cond_code" label="贮存条件" rules={[{ required: true, message: '请输入贮存条件' }]}>
                <Input placeholder="如 RT_2_8C" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="location" label="存放位置">
                <Input placeholder="如 冰箱A-1层" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="test_item" label="检测项目">
                <Input placeholder="如 含量测定" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="manufacturer" label="来源/厂家">
                <Input placeholder="如 中国药品生物制品检定所" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="std_status" label="状态" rules={[{ required: true }]}>
            <Select>
              {STANDARD_STATUS_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} placeholder="备注信息" maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Drawer>

      <Drawer
        title="调整数量"
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
          <Form.Item label="当前标准品">
            <div style={{ fontSize: 16, fontWeight: 500 }}>
              {stockAdjustRecord?.std_name} ({stockAdjustRecord?.std_code})
            </div>
            <div style={{ color: '#64748b', marginTop: 4 }}>
              当前数量: <span style={{ fontWeight: 600, color: '#7c3aed' }}>{stockAdjustRecord?.quantity}</span> {stockAdjustRecord?.unit_code}
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
