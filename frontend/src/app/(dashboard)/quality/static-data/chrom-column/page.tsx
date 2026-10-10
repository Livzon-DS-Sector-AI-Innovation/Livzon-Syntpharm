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
  Upload,
  Drawer,
  Row,
  Col,
  InputNumber,
  Select,
  Segmented,
  Pagination,
  Dropdown,
  Tooltip,
  Progress,
  Space,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps, MenuProps } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UploadOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  MoreOutlined,
  FilterOutlined,
  FileExcelOutlined,
  PlayCircleOutlined,
  ClockCircleOutlined,
  PauseCircleOutlined,
  CloseCircleOutlined,
  RiseOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { ChromColumn, CHROM_COLUMN_STATUS_OPTIONS, CHROM_COLUMN_CATEGORY_OPTIONS } from '@/types/static-data'
import {
  createChromColumn,
  updateChromColumn,
  deleteChromColumn,
  incrementChromColumnUsage,
} from '@/actions/static-data'
import {
  listChromColumn,
  downloadChromColumnTemplate,
  batchImportChromColumn,
} from '@/lib/api/client/static-data-api'
import './chrom-column-style.css'

const { Search } = Input
const { Option } = Select

const STATUS_META: Record<number, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  0: { label: '在用', color: '#3b82f6', bg: '#eff6ff', icon: <PlayCircleOutlined /> },
  1: { label: '待清洗', color: '#f59e0b', bg: '#fffbeb', icon: <ClockCircleOutlined /> },
  2: { label: '封存', color: '#8b5cf6', bg: '#f5f3ff', icon: <PauseCircleOutlined /> },
  3: { label: '报废', color: '#ef4444', bg: '#fef2f2', icon: <CloseCircleOutlined /> },
}

const getUsageLevel = (used: number, max: number): 'low' | 'mid' | 'high' | 'critical' => {
  if (max <= 0) return 'low'
  const ratio = used / max
  if (ratio < 0.5) return 'low'
  if (ratio < 0.8) return 'mid'
  if (ratio < 1) return 'high'
  return 'critical'
}

export default function ChromColumnPage() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<number | 'all'>('all')
  const [categoryFilter, setCategoryFilter] = useState<number | 'all'>('all')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [editingRecord, setEditingRecord] = useState<ChromColumn | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [form] = Form.useForm()
  const [advancedForm] = Form.useForm()
  const queryClient = useQueryClient()

  const queryParams = useCallback((): Record<string, unknown> => {
    const params: Record<string, unknown> = { page, page_size: pageSize }
    if (searchText) {
      params.col_code = searchText
      params.col_type = searchText
    }
    if (statusFilter !== 'all') {
      params.col_status = statusFilter
    }
    if (categoryFilter !== 'all') {
      params.column_category = categoryFilter
    }
    const adv = advancedForm.getFieldsValue()
    if (adv.manufacturer) params.manufacturer = adv.manufacturer
    if (adv.spec) params.spec = adv.spec
    return params
  }, [page, pageSize, searchText, statusFilter, categoryFilter, advancedForm])

  const { data: queryResult, isLoading: loading, refetch } = useQuery({
    queryKey: ['chrom-column-list', page, pageSize, searchText, statusFilter, categoryFilter],
    queryFn: async () => {
      const params = queryParams()
      const res = await listChromColumn(params)
      return { items: (res?.data ?? []) as ChromColumn[], total: res?.meta?.total ?? 0 }
    },
  })

  const data = queryResult?.items || []
  const total = queryResult?.total || 0

  const { data: statsData = { all: 0, active: 0, cleaning: 0, sealed: 0, scrapped: 0 } } = useQuery({
    queryKey: ['chrom-column-stats', categoryFilter],
    queryFn: async () => {
      let allData: ChromColumn[] = []
      let curPage = 1
      while (true) {
        const params: Record<string, unknown> = { page: curPage, page_size: 200 }
        if (categoryFilter !== 'all') {
          params.column_category = categoryFilter
        }
        const res = await listChromColumn(params)
        const batch = (res?.data ?? []) as ChromColumn[]
        allData = allData.concat(batch)
        if (allData.length >= (res?.meta?.total ?? 0) || batch.length === 0) break
        curPage++
      }
      let active = 0, cleaning = 0, sealed = 0, scrapped = 0
      allData.forEach(item => {
        if (item.col_status === 0) active++
        if (item.col_status === 1) cleaning++
        if (item.col_status === 2) sealed++
        if (item.col_status === 3) scrapped++
      })
      return { all: allData.length, active, cleaning, sealed, scrapped }
    },
  })

  const handleQuickSearch = (val: string) => {
    setSearchText(val)
    setPage(1)
  }

  const handleStatusFilter = (val: number | 'all') => {
    setStatusFilter(val)
    setPage(1)
  }

  const handleCategoryFilter = (val: number | 'all') => {
    setCategoryFilter(val)
    setPage(1)
  }

  const handleAdvancedSearch = () => {
    setPage(1)
  }

  const handleReset = () => {
    setSearchText('')
    setStatusFilter('all')
    setCategoryFilter('all')
    advancedForm.resetFields()
    setPage(1)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteChromColumn(id)
      message.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['chrom-column-list'] })
      queryClient.invalidateQueries({ queryKey: ['chrom-column-stats'] })
    } catch (e: unknown) {
      message.error((e instanceof Error ? e.message : '删除失败'))
    }
  }

  const handleIncrementUsage = async (id: number) => {
    try {
      await incrementChromColumnUsage(id)
      message.success('使用次数+1')
      queryClient.invalidateQueries({ queryKey: ['chrom-column-list'] })
      queryClient.invalidateQueries({ queryKey: ['chrom-column-stats'] })
    } catch (e: unknown) {
      message.error((e as Error).message || '操作失败')
    }
  }

  const openCreate = () => {
    setIsNew(true)
    setEditingRecord(null)
    form.resetFields()
    const defaultCat = categoryFilter === 'all' ? 0 : categoryFilter
    form.setFieldsValue({ col_status: 0, used_times: 0, max_use_times: 100, column_category: defaultCat })
    setDrawerOpen(true)
  }

  const openDetail = (record: ChromColumn) => {
    setIsNew(false)
    setEditingRecord(record)
    const toDay = (v: string | null) => v ? dayjs(v) : undefined
    form.setFieldsValue({
      ...record,
      purchase_date: toDay(record.purchase_date),
      use_start_date: toDay(record.use_start_date),
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setDrawerLoading(true)

      const dateFields = ['purchase_date', 'use_start_date']
      dateFields.forEach(f => {
        if (values[f] && typeof values[f].format === 'function') {
          values[f] = values[f].format('YYYY-MM-DD')
        }
      })

      if (isNew) {
        await createChromColumn(values)
        message.success('创建成功')
      } else if (editingRecord) {
        await updateChromColumn(editingRecord.id, values)
        message.success('更新成功')
      }
      setDrawerOpen(false)
      queryClient.invalidateQueries({ queryKey: ['chrom-column-list'] })
      queryClient.invalidateQueries({ queryKey: ['chrom-column-stats'] })
    } catch (e: unknown) {
      if (e && typeof e === "object" && "errorFields" in e) return
      message.error((e instanceof Error ? e.message : '保存失败'))
    } finally {
      setDrawerLoading(false)
    }
  }

  const handleTemplateDownload = async () => {
    try {
      await downloadChromColumnTemplate()
      message.success('模板下载成功')
    } catch (e: unknown) {
      message.error((e as Error).message || '模板下载失败')
    }
  }

  const handleImport = async (file: File) => {
    try {
      const res = await batchImportChromColumn(file)
      message.success(res.message || '导入成功')
      queryClient.invalidateQueries({ queryKey: ['chrom-column-list'] })
      queryClient.invalidateQueries({ queryKey: ['chrom-column-stats'] })
    } catch (e: unknown) {
      message.error((e instanceof Error ? e.message : '导入失败'))
    }
    return false
  }

  const uploadProps: UploadProps = {
    accept: '.xlsx,.xls',
    showUploadList: false,
    beforeUpload: handleImport,
  }

  const moreMenu: MenuProps['items'] = [
    {
      key: 'template',
      icon: <FileExcelOutlined />,
      label: '下载导入模板',
      onClick: handleTemplateDownload,
    },
    {
      key: 'import',
      icon: <UploadOutlined />,
      label: (
        <Upload {...uploadProps}>
          <span style={{ display: 'block' }}>批量导入</span>
        </Upload>
      ),
    },
  ]

  const columns: ColumnsType<ChromColumn> = [
    {
      title: '编号',
      dataIndex: 'col_code',
      width: 120,
      fixed: 'left',
      render: (v, record) => (
        <a onClick={() => openDetail(record)} style={{ fontWeight: 600, color: '#2563eb' }}>
          {v}
        </a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'column_category',
      width: 100,
      render: v => v === 1 ? (
        <Tag color="#f97316">气相</Tag>
      ) : (
        <Tag color="#3b82f6">液相</Tag>
      ),
    },
    { title: '填料', dataIndex: 'col_type', width: 140, ellipsis: true },
    { title: '规格', dataIndex: 'spec', width: 140, ellipsis: true },
    { title: '厂家', dataIndex: 'manufacturer', width: 140, ellipsis: true },
    { title: '序列号', dataIndex: 'serial_no', width: 140 },
    {
      title: '采购日期',
      dataIndex: 'purchase_date',
      width: 110,
    },
    {
      title: '使用次数',
      width: 160,
      render: (_, record) => {
        const level = getUsageLevel(record.used_times, record.max_use_times)
        const colorMap = { low: '#10b981', mid: '#3b82f6', high: '#f59e0b', critical: '#ef4444' }
        const percent = record.max_use_times > 0 ? Math.round((record.used_times / record.max_use_times) * 100) : 0
        return (
          <div style={{ minWidth: 120 }}>
            <Progress
              percent={percent}
              size="small"
              strokeColor={colorMap[level]}
              format={() => `${record.used_times}/${record.max_use_times}`}
            />
          </div>
        )
      },
    },
    { title: '存放位置', dataIndex: 'location', width: 100, ellipsis: true },
    {
      title: '状态',
      dataIndex: 'col_status',
      width: 100,
      render: v => {
        const meta = STATUS_META[v]
        return meta ? (
          <Tag color={meta.color} style={{ fontSize: 12, padding: '2px 10px', borderRadius: 4 }}>
            {meta.icon} {meta.label}
          </Tag>
        ) : v
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_, record) => (
        <Space size={2}>
          <Tooltip title="使用+1">
            <Button
              type="text"
              size="small"
              icon={<RiseOutlined />}
              onClick={() => handleIncrementUsage(record.id)}
              disabled={record.col_status !== 0}
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
    <div className="cc-page">
      <div className="cc-header">
        <div className="cc-header-left">
          <div className="cc-title">
            <span className="cc-title-icon">🧪</span>
            <div>
              <h1>色谱柱管理</h1>
              <p>管理 HPLC/GC 色谱柱库存、使用次数与状态</p>
            </div>
          </div>
        </div>
        <div className="cc-header-right">
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={openCreate} className="cc-add-btn">
            新建色谱柱
          </Button>
          <Dropdown menu={{ items: moreMenu }} placement="bottomRight">
            <Button size="large" icon={<MoreOutlined />} />
          </Dropdown>
        </div>
      </div>

      <div className="cc-stats">
        <div className="stat-card stat-all" onClick={() => handleStatusFilter('all')}>
          <div className="stat-icon">📋</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.all}</div>
            <div className="stat-label">全部色谱柱</div>
          </div>
        </div>
        <div className="stat-card stat-active" onClick={() => handleStatusFilter(0)}>
          <div className="stat-icon">▶️</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.active}</div>
            <div className="stat-label">在用</div>
          </div>
        </div>
        <div className="stat-card stat-cleaning" onClick={() => handleStatusFilter(1)}>
          <div className="stat-icon">🧼</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.cleaning}</div>
            <div className="stat-label">待清洗</div>
          </div>
        </div>
        <div className="stat-card stat-sealed" onClick={() => handleStatusFilter(2)}>
          <div className="stat-icon">📦</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.sealed}</div>
            <div className="stat-label">封存</div>
          </div>
        </div>
        <div className="stat-card stat-scrapped" onClick={() => handleStatusFilter(3)}>
          <div className="stat-icon">🗑️</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.scrapped}</div>
            <div className="stat-label">报废</div>
          </div>
        </div>
      </div>

      <div className="cc-category-bar">
        <Segmented
          value={categoryFilter === 'all' ? 'all' : String(categoryFilter)}
          onChange={v => handleCategoryFilter(v as number | 'all')}
          options={[
            { value: 'all', label: '全部' },
            { value: '0', label: '液相色谱柱' },
            { value: '1', label: '气相色谱柱' },
          ]}
          size="large"
        />
      </div>

      <div className="cc-toolbar">
        <div className="cc-search-wrap">
          <Search
            placeholder="搜索编号或类型..."
            allowClear
            size="large"
            value={searchText}
            onChange={e => handleQuickSearch(e.target.value)}
            onSearch={handleQuickSearch}
            className="cc-search"
          />
        </div>
        <div className="cc-toolbar-right">
          <Button
            icon={<FilterOutlined />}
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={showAdvanced ? 'cc-filter-active' : ''}
          >
            高级筛选
          </Button>
          <Button icon={<ReloadOutlined />} onClick={() => { refetch(); queryClient.invalidateQueries({ queryKey: ['chrom-column-stats'] }) }}>
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

      {showAdvanced && (
        <div className="cc-advanced">
          <Form form={advancedForm} layout="vertical">
            <Row gutter={16}>
              <Col span={6}>
                <Form.Item name="manufacturer" label="生产厂家">
                  <Input placeholder="输入厂家名称" allowClear />
                </Form.Item>
              </Col>
              <Col span={6}>
                <Form.Item name="spec" label="规格参数">
                  <Input placeholder="输入规格" allowClear />
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
          <div className="cc-card-grid">
            {data.map((item, idx) => {
              const meta = STATUS_META[item.col_status]
              const level = getUsageLevel(item.used_times, item.max_use_times)
              const colorMap = { low: '#10b981', mid: '#3b82f6', high: '#f59e0b', critical: '#ef4444' }
              const percent = item.max_use_times > 0 ? Math.round((item.used_times / item.max_use_times) * 100) : 0
              return (
                <div
                  key={item.id}
                  className="cc-card"
                  onClick={() => openDetail(item)}
                  style={{ animationDelay: `${idx * 0.03}s` }}
                >
                  <div className="cc-card-status-bar" style={{ background: meta?.color || '#94a3b8' }} />
                  <div className="cc-card-body">
                    <div className="cc-card-header">
                      <span className="cc-card-code">{item.col_code}</span>
                      <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                        <Tag color={item.column_category === 1 ? '#f97316' : '#3b82f6'} style={{ margin: 0 }}>
                          {item.column_category === 1 ? '气相' : '液相'}
                        </Tag>
                        <Tag color={meta?.color} className="cc-card-status-tag" style={{ margin: 0 }}>
                          {meta?.icon} {meta?.label}
                        </Tag>
                      </div>
                    </div>
                    <div className="cc-card-type">{item.col_type}</div>
                    <div className="cc-card-spec">{item.spec}</div>
                    <div className="cc-card-usage">
                      <div className="cc-usage-label">
                        <span>使用次数</span>
                        <span className="cc-usage-count">{item.used_times} / {item.max_use_times}</span>
                      </div>
                      <div className="cc-usage-bar">
                        <div
                          className="cc-usage-fill"
                          style={{ width: `${percent}%`, background: colorMap[level] }}
                        />
                      </div>
                    </div>
                    <div className="cc-card-info-grid">
                      <div className="cc-card-info-item">
                        <div className="cc-info-label">厂家</div>
                        <div className="cc-info-value" title={item.manufacturer}>{item.manufacturer}</div>
                      </div>
                      <div className="cc-card-info-item">
                        <div className="cc-info-label">位置</div>
                        <div className="cc-info-value" title={item.location}>{item.location}</div>
                      </div>
                    </div>
                    <div className="cc-card-actions" onClick={e => e.stopPropagation()}>
                      <Button
                        type="primary"
                        size="small"
                        icon={<RiseOutlined />}
                        onClick={() => handleIncrementUsage(item.id)}
                        disabled={item.col_status !== 0}
                        className="cc-use-btn"
                      >
                        使用+1
                      </Button>
                      <Button size="small" icon={<EditOutlined />} onClick={() => openDetail(item)}>
                        编辑
                      </Button>
                    </div>
                  </div>
                </div>
              )
            })}
            {!loading && data.length === 0 && (
              <div className="cc-empty">暂无数据</div>
            )}
          </div>
          <div className="cc-card-pagination">
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
        <div className="cc-table-wrap">
          <Table
            columns={columns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            scroll={{ x: 1200 }}
            pagination={{
              current: page,
              pageSize,
              total,
              onChange: (p, ps) => { setPage(p); setPageSize(ps) },
              showSizeChanger: true,
              showTotal: t => `共 ${t} 条`,
            }}
          />
        </div>
      )}

      <Drawer
        title={isNew ? '新建色谱柱' : '编辑色谱柱'}
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
        <Form form={form} layout="vertical" className="cc-drawer-form">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="col_code"
                label="色谱柱编号"
                rules={[{ required: true, message: '请输入编号' }]}
              >
                <Input placeholder="如 LC24001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="column_category"
                label="柱类型"
                rules={[{ required: true, message: '请选择柱类型' }]}
              >
                <Select>
                  {CHROM_COLUMN_CATEGORY_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="col_type"
                label="固定相类型"
                rules={[{ required: true, message: '请输入类型' }]}
              >
                <Input placeholder="如 C18, C8, Silica" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="spec"
                label="规格参数"
                rules={[{ required: true, message: '请输入规格' }]}
              >
                <Input placeholder="如 4.6*250mm 5um" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="manufacturer"
                label="生产厂家"
                rules={[{ required: true, message: '请输入厂家' }]}
              >
                <Input placeholder="如 安捷伦/月旭科技" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="serial_no"
                label="原厂序列号"
                rules={[{ required: true, message: '请输入序列号' }]}
              >
                <Input placeholder="原厂序列号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="purchase_date"
                label="采购日期"
                rules={[{ required: true, message: '请选择日期' }]}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="use_start_date" label="启用日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="col_status"
                label="状态"
                rules={[{ required: true, message: '请选择状态' }]}
              >
                <Select>
                  {CHROM_COLUMN_STATUS_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="max_use_times"
                label="最大使用次数"
                rules={[{ required: true, message: '请输入最大次数' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="used_times" label="已使用次数">
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
                <Input placeholder="如 ROOM_TEMP" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="location"
                label="存放位置"
                rules={[{ required: true, message: '请输入位置' }]}
              >
                <Input placeholder="存放位置" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="apply_method" label="适用检测方法">
            <Input.TextArea rows={3} placeholder="适用的检测方法或项目" maxLength={500} showCount />
          </Form.Item>
          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={3} placeholder="备注信息" maxLength={500} showCount />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
