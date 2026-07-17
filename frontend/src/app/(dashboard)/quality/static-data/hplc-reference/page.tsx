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
  Upload,
  Drawer,
  Row,
  Col,
  InputNumber,
  Switch,
  Select,
  Segmented,
  Pagination,
  Dropdown,
  Tooltip,
  Space,
  Alert,
  Empty,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps, MenuProps } from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  UploadOutlined,
  DownloadOutlined,
  AppstoreOutlined,
  UnorderedListOutlined,
  MoreOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  DisconnectOutlined,
  FilterOutlined,
  FileExcelOutlined,
  SettingOutlined,
  PlusCircleOutlined,
  MinusCircleOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { HplcReference, HplcReferenceUsage, HPLC_REF_STATUS_OPTIONS, HPLC_REF_SPEC_UNIT_OPTIONS } from '@/types/static-data'
import {
  createHplcReference,
  updateHplcReference,
  deleteHplcReference,
} from '@/actions/static-data'
import {
  listHplcReference,
  downloadHplcReferenceTemplate,
  batchImportHplcReference,
  adjustHplcReferenceQuantity,
  useHplcReference,
  getHplcReferenceUsageHistory,
  getHplcReferencesNeedRecal,
} from '@/lib/static-data-api'
import './hplc-style.css'

const { RangePicker } = DatePicker
const { Search } = Input

const STATUS_META: Record<number, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
  0: { label: '在用', color: '#10b981', bg: '#ecfdf5', icon: <CheckCircleOutlined /> },
  1: { label: '用完', color: '#3b82f6', bg: '#eff6ff', icon: <DisconnectOutlined /> },
  2: { label: '过期', color: '#ef4444', bg: '#fef2f2', icon: <ExclamationCircleOutlined /> },
  3: { label: '报废', color: '#f97316', bg: '#fff7ed', icon: <ExclamationCircleOutlined /> },
}

const calcDaysRemaining = (expireDate: string | null): number | null => {
  if (!expireDate) return null
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const exp = new Date(expireDate)
  exp.setHours(0, 0, 0, 0)
  return Math.ceil((exp.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

const getExpiryBadge = (days: number | null, status: number) => {
  if (status !== 0) return null
  if (days === null) return null
  if (days < 0) return { text: `已过期 ${Math.abs(days)} 天`, color: 'error', bg: '#fef2f2' }
  if (days <= 30) return { text: `剩 ${days} 天`, color: 'warning', bg: '#fffbeb' }
  if (days <= 90) return { text: `剩 ${days} 天`, color: 'processing', bg: '#eff6ff' }
  return { text: `剩 ${days} 天`, color: 'success', bg: '#ecfdf5' }
}

export default function HplcReferencePage() {
  const [data, setData] = useState<HplcReference[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<number | 'all'>('all')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [editingRecord, setEditingRecord] = useState<HplcReference | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [form] = Form.useForm()
  const [advancedForm] = Form.useForm()
  const [stockDrawerOpen, setStockDrawerOpen] = useState(false)
  const [stockAdjustRecord, setStockAdjustRecord] = useState<HplcReference | null>(null)
  const [stockForm] = Form.useForm()
  // 领用相关状态
  const [usageDrawerOpen, setUsageDrawerOpen] = useState(false)
  const [usageRecord, setUsageRecord] = useState<HplcReference | null>(null)
  const [usageForm] = Form.useForm()
  // 领用历史相关状态
  const [usageHistoryOpen, setUsageHistoryOpen] = useState(false)
  const [usageHistoryRecord, setUsageHistoryRecord] = useState<HplcReference | null>(null)
  const [usageHistoryData, setUsageHistoryData] = useState<HplcReferenceUsage[]>([])
  const [usageHistoryLoading, setUsageHistoryLoading] = useState(false)
  const [usageHistoryTotal, setUsageHistoryTotal] = useState(0)
  const [usageHistoryPage, setUsageHistoryPage] = useState(1)
  // 复标提醒
  const [recalAlertCount, setRecalAlertCount] = useState(0)
  const [recalAlertVisible, setRecalAlertVisible] = useState(false)
  const [recalList, setRecalList] = useState<HplcReference[]>([])

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, page_size: pageSize }
      if (searchText) {
        params.ref_name = searchText
        params.ref_code = searchText
      }
      if (statusFilter !== 'all') {
        params.ref_status = statusFilter
      }
      const adv = advancedForm.getFieldsValue()
      if (adv.cas_no) params.cas_no = adv.cas_no
      if (adv.expire_start) params.expire_start = adv.expire_start
      if (adv.expire_end) params.expire_end = adv.expire_end
      const res = await listHplcReference(params)
      setData((res?.data ?? []) as HplcReference[])
      setTotal(res?.meta?.total ?? 0)
    } catch (e: any) {
      message.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchText, statusFilter, advancedForm])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const [statsData, setStatsData] = useState({ all: 0, active: 0, usedUp: 0, expired: 0 })

  const fetchStats = useCallback(async () => {
    try {
      let allData: HplcReference[] = []
      let curPage = 1
      while (true) {
        const res = await listHplcReference({ page: curPage, page_size: 200 })
        const batch = (res?.data ?? []) as HplcReference[]
        allData = allData.concat(batch)
        if (allData.length >= (res?.meta?.total ?? 0) || batch.length === 0) break
        curPage++
      }
      let active = 0, usedUp = 0, expired = 0
      allData.forEach(item => {
        if (item.ref_status === 0) active++
        if (item.ref_status === 1) usedUp++
        if (item.ref_status === 2) expired++
      })
      setStatsData({ all: allData.length, active, usedUp, expired })
    } catch (e) {
      console.error('stats fetch error:', e)
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  // 复标提醒：拉取需要复标的对照品列表
  const fetchRecalAlerts = useCallback(async () => {
    try {
      const res: any = await getHplcReferencesNeedRecal()
      const list = (res?.data ?? []) as HplcReference[]
      setRecalList(list)
      setRecalAlertCount(list.length)
      setRecalAlertVisible(list.length > 0)
    } catch (e) {
      console.error('fetch recal alerts error:', e)
    }
  }, [])

  useEffect(() => {
    fetchRecalAlerts()
  }, [fetchRecalAlerts])

  // 打开领用 Drawer
  const openUsage = (record: HplcReference) => {
    setUsageRecord(record)
    usageForm.resetFields()
    const unit = record.remaining_unit || 'mg'
    usageForm.setFieldsValue({
      usage_amount: 0,
      usage_unit: unit,
      usage_person: '',
      usage_purpose: '',
      remark: '',
    })
    setUsageDrawerOpen(true)
  }

  // 提交领用
  const handleUsageSubmit = async () => {
    try {
      const values = await usageForm.validateFields()
      if (!usageRecord) return
      await useHplcReference(usageRecord.id, {
        usage_amount: Number(values.usage_amount),
        usage_unit: values.usage_unit || 'mg',
        usage_person: values.usage_person || undefined,
        usage_purpose: values.usage_purpose || undefined,
        remark: values.remark || undefined,
      })
      message.success('领用成功')
      setUsageDrawerOpen(false)
      fetchData()
      fetchStats()
      fetchRecalAlerts()
    } catch (e: any) {
      if (e.errorFields) return
      message.error(e.message || '领用失败')
    }
  }

  // 拉取领用历史
  const fetchUsageHistory = useCallback(async (refId: number, p = 1) => {
    setUsageHistoryLoading(true)
    try {
      const res: any = await getHplcReferenceUsageHistory(refId, p, 20)
      setUsageHistoryData((res?.data ?? []) as HplcReferenceUsage[])
      setUsageHistoryTotal(res?.meta?.total ?? 0)
      setUsageHistoryPage(p)
    } catch (e: any) {
      message.error(e.message || '加载领用历史失败')
    } finally {
      setUsageHistoryLoading(false)
    }
  }, [])

  // 打开领用历史 Drawer
  const openUsageHistory = (record: HplcReference) => {
    setUsageHistoryRecord(record)
    setUsageHistoryPage(1)
    setUsageHistoryOpen(true)
    fetchUsageHistory(record.id, 1)
  }

  const handleQuickSearch = (val: string) => {
    setSearchText(val)
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
    setStatusFilter('all')
    advancedForm.resetFields()
    setPage(1)
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteHplcReference(id)
      message.success('删除成功')
      fetchData()
      fetchStats()
    } catch (e: any) {
      message.error(e.message || '删除失败')
    }
  }

  const openStockAdjust = (record: HplcReference) => {
    setStockAdjustRecord(record)
    stockForm.resetFields()
    stockForm.setFieldsValue({ quantity_change: 0 })
    setStockDrawerOpen(true)
  }

  const handleStockAdjust = async () => {
    try {
      const values = await stockForm.validateFields()
      if (stockAdjustRecord) {
        await adjustHplcReferenceQuantity(stockAdjustRecord.id, values.quantity_change)
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

  const openCreate = () => {
    setIsNew(true)
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({
      ref_status: 0,
      has_coa: false,
      spec_unit: 'mg',
      remaining_unit: 'mg',
      quantity: 1,
      total_amount: 0,
      remaining_amount: 0,
      recal_threshold: 0,
    })
    setDrawerOpen(true)
  }

  const openDetail = (record: HplcReference) => {
    setIsNew(false)
    setEditingRecord(record)
    const toDay = (v: string | null) => v ? dayjs(v) : undefined
    form.setFieldsValue({
      ...record,
      arrival_date: toDay(record.arrival_date),
      produce_date: toDay(record.produce_date),
      expire_date: toDay(record.expire_date),
      open_date: toDay(record.open_date),
    })
    setDrawerOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setDrawerLoading(true)

      const dateFields = ['arrival_date', 'produce_date', 'expire_date', 'open_date']
      dateFields.forEach(f => {
        if (values[f] && typeof values[f].format === 'function') {
          values[f] = values[f].format('YYYY-MM-DD')
        }
      })

      if (isNew) {
        await createHplcReference(values)
        message.success('创建成功')
      } else if (editingRecord) {
        await updateHplcReference(editingRecord.id, values)
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

  const handleTemplateDownload = async () => {
    try {
      await downloadHplcReferenceTemplate()
      message.success('模板下载成功')
    } catch (e: any) {
      message.error(e.message || '模板下载失败')
    }
  }

  const handleImport = async (file: File) => {
    try {
      const res = await batchImportHplcReference(file)
      message.success(res.message || '导入成功')
      setImportModalOpen(false)
      fetchData()
    } catch (e: any) {
      message.error(e.message || '导入失败')
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
      label: '批量导入',
      onClick: () => setImportModalOpen(true),
    },
  ]

  const columns: ColumnsType<HplcReference> = [
    {
      title: '编号',
      dataIndex: 'ref_code',
      width: 120,
      fixed: 'left',
      render: (v, record) => (
        <a onClick={() => openDetail(record)} style={{ fontWeight: 600, color: '#0f766e' }}>
          {v}
        </a>
      ),
    },
    { title: '名称', dataIndex: 'ref_name', width: 200, ellipsis: true },
    { title: 'CAS号', dataIndex: 'cas_no', width: 120 },
    {
      title: '规格',
      key: 'spec',
      width: 100,
      render: (_, record) => {
        if (!record.spec) return '-'
        return `${record.spec}${record.spec_unit || ''}`
      },
    },
    {
      title: '纯度(%)',
      dataIndex: 'purity',
      width: 90,
      render: v => v ? Number(v).toFixed(2) : '-',
    },
    {
      title: '瓶数',
      dataIndex: 'quantity',
      width: 70,
      render: v => v ?? '-',
    },
    {
      title: '剩余量',
      key: 'remaining',
      width: 160,
      render: (_, record) => {
        const remaining = Number(record.remaining_amount ?? 0)
        const total = Number(record.total_amount ?? 0)
        const unit = record.remaining_unit || 'mg'
        const threshold = Number(record.recal_threshold ?? 0)
        const percent = total > 0 ? Math.max(0, Math.min(100, (remaining / total) * 100)) : 0
        const needRecal = threshold > 0 && remaining <= threshold
        const color = needRecal ? '#ef4444' : percent < 30 ? '#f59e0b' : '#10b981'
        return (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <span style={{ fontWeight: 600, color }}>{remaining.toFixed(2)} {unit}</span>
              {needRecal && (
                <Tag color="red" style={{ fontSize: 10, margin: 0, padding: '0 4px' }}>需复标</Tag>
              )}
            </div>
            {total > 0 && (
              <div style={{ width: '100%', height: 6, background: '#e5e7eb', borderRadius: 3, overflow: 'hidden' }}>
                <div style={{ width: `${percent}%`, height: '100%', background: color, transition: 'width 0.3s' }} />
              </div>
            )}
          </div>
        )
      },
    },
    {
      title: '有效期至',
      dataIndex: 'expire_date',
      width: 120,
      render: (v, record) => {
        const days = calcDaysRemaining(v)
        const badge = getExpiryBadge(days, record.ref_status)
        return (
          <div>
            <div style={{ fontSize: 13 }}>{v || '-'}</div>
            {badge && (
              <Tag color={badge.color} style={{ marginTop: 2, fontSize: 11, padding: '0 6px' }}>
                {badge.text}
              </Tag>
            )}
          </div>
        )
      },
    },
    {
      title: '存放位置',
      dataIndex: 'location',
      width: 100,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'ref_status',
      width: 90,
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
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <Tooltip title="领用">
            <Button
              type="text"
              size="small"
              icon={<ExperimentOutlined />}
              onClick={() => openUsage(record)}
              style={{ color: '#0f766e' }}
            />
          </Tooltip>
          <Tooltip title="领用历史">
            <Button
              type="text"
              size="small"
              icon={<HistoryOutlined />}
              onClick={() => openUsageHistory(record)}
            />
          </Tooltip>
          <Tooltip title="调整数量">
            <Button
              type="text"
              size="small"
              icon={<PlusCircleOutlined />}
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
        </div>
      ),
    },
  ]

  return (
    <div className="hplc-page">
      <div className="hplc-header">
        <div className="hplc-header-left">
          <div className="hplc-title">
            <span className="hplc-title-icon">⚗️</span>
            <div>
              <h1>液相对照品</h1>
              <p>管理 HPLC 对照品库存与有效期</p>
            </div>
          </div>
        </div>
        <div className="hplc-header-right">
          <Button type="primary" size="large" icon={<PlusOutlined />} onClick={openCreate} className="hplc-add-btn">
            新建对照品
          </Button>
          <Dropdown menu={{ items: moreMenu }} placement="bottomRight">
            <Button size="large" icon={<MoreOutlined />} />
          </Dropdown>
        </div>
      </div>

      <div className="hplc-stats">
        <div className="stat-card stat-all" onClick={() => handleStatusFilter('all')}>
          <div className="stat-icon">📋</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.all}</div>
            <div className="stat-label">全部对照品</div>
          </div>
        </div>
        <div className="stat-card stat-active" onClick={() => handleStatusFilter(0)}>
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.active}</div>
            <div className="stat-label">在用</div>
          </div>
        </div>
        <div className="stat-card stat-soon" onClick={() => handleStatusFilter(1)}>
          <div className="stat-icon">📦</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.usedUp}</div>
            <div className="stat-label">用完</div>
          </div>
        </div>
        <div className="stat-card stat-expired" onClick={() => handleStatusFilter(2)}>
          <div className="stat-icon">⚠️</div>
          <div className="stat-info">
            <div className="stat-num">{statsData.expired}</div>
            <div className="stat-label">已过期</div>
          </div>
        </div>
      </div>

      {recalAlertVisible && (
        <Alert
          type="error"
          showIcon
          icon={<WarningOutlined />}
          style={{ marginBottom: 16, borderLeft: '4px solid #ef4444' }}
          message={
            <span>
              <strong>复标提醒：</strong>
              当前有 <strong style={{ color: '#ef4444' }}>{recalAlertCount}</strong> 个对照品剩余量低于复标阈值，请及时处理。
            </span>
          }
          description={
            <div style={{ marginTop: 8 }}>
              {recalList.slice(0, 5).map(r => (
                <Tag
                  key={r.id}
                  color="red"
                  style={{ marginBottom: 4, cursor: 'pointer' }}
                  onClick={() => openDetail(r)}
                >
                  {r.ref_code} - {r.ref_name}
                  （剩余 {Number(r.remaining_amount ?? 0).toFixed(2)} {r.remaining_unit || 'mg'} / 阈值 {Number(r.recal_threshold ?? 0).toFixed(2)}）
                </Tag>
              ))}
              {recalList.length > 5 && (
                <Tag color="default" style={{ marginBottom: 4 }}>
                  ...等共 {recalList.length} 项
                </Tag>
              )}
            </div>
          }
          closable
          onClose={() => setRecalAlertVisible(false)}
        />
      )}

      <div className="hplc-toolbar">
        <div className="hplc-search-wrap">
          <Search
            placeholder="搜索编号或名称..."
            allowClear
            size="large"
            value={searchText}
            onChange={e => handleQuickSearch(e.target.value)}
            onSearch={handleQuickSearch}
            className="hplc-search"
          />
        </div>
        <div className="hplc-toolbar-right">
          <Button
            icon={<FilterOutlined />}
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={showAdvanced ? 'hplc-filter-active' : ''}
          >
            高级筛选
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
        <div className="hplc-advanced">
          <Form form={advancedForm} layout="inline" onFinish={handleAdvancedSearch} size="middle">
            <Form.Item name="cas_no" label="CAS号">
              <Input placeholder="CAS号" style={{ width: 140 }} allowClear />
            </Form.Item>
            <Form.Item name="expire_range" label="有效期范围">
              <RangePicker format="YYYY-MM-DD" style={{ width: 260 }}
                onChange={(_, dateStrings) => {
                  advancedForm.setFieldsValue({
                    expire_start: dateStrings[0] || undefined,
                    expire_end: dateStrings[1] || undefined,
                  })
                }}
              />
            </Form.Item>
            <Form.Item name="expire_start" hidden><Input /></Form.Item>
            <Form.Item name="expire_end" hidden><Input /></Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" icon={<SearchOutlined />}>应用筛选</Button>
            </Form.Item>
            <Form.Item>
              <Button onClick={handleReset} icon={<ReloadOutlined />}>重置</Button>
            </Form.Item>
          </Form>
        </div>
      )}

      <div className="hplc-status-chips">
        <Tag
          className={`chip ${statusFilter === 'all' ? 'chip-active' : ''}`}
          onClick={() => handleStatusFilter('all')}
        >
          全部
        </Tag>
        {HPLC_REF_STATUS_OPTIONS.map(opt => (
          <Tag
            key={opt.value}
            className={`chip chip-${opt.value} ${statusFilter === opt.value ? 'chip-active' : ''}`}
            onClick={() => handleStatusFilter(opt.value)}
          >
            {opt.label}
          </Tag>
        ))}
      </div>

      {viewMode === 'card' ? (
        <div>
        <div className="hplc-card-grid">
          {loading ? (
            <div className="hplc-loading">加载中...</div>
          ) : data.length === 0 ? (
            <div className="hplc-empty">
              <div style={{ fontSize: 48, marginBottom: 16 }}>🔬</div>
              <div style={{ fontSize: 16, color: '#64748b' }}>暂无对照品数据</div>
              <Button type="primary" icon={<PlusOutlined />} onClick={openCreate} style={{ marginTop: 16 }}>
                新建第一个对照品
              </Button>
            </div>
          ) : (
            data.map((item, idx) => {
              const meta = STATUS_META[item.ref_status]
              const days = calcDaysRemaining(item.expire_date)
              const badge = getExpiryBadge(days, item.ref_status)
              const remaining = Number(item.remaining_amount ?? 0)
              const totalAmt = Number(item.total_amount ?? 0)
              const remUnit = item.remaining_unit || 'mg'
              const threshold = Number(item.recal_threshold ?? 0)
              const pct = totalAmt > 0 ? Math.max(0, Math.min(100, (remaining / totalAmt) * 100)) : 0
              // 动态计算：剩余量 <= 阈值 时需要复标（忽略后端可能过期的 need_recal 标记）
              const needRecal = threshold > 0 && remaining <= threshold
              const barColor = needRecal ? '#ef4444' : pct < 30 ? '#f59e0b' : '#10b981'
              const hasStock = totalAmt > 0 || remaining > 0 || threshold > 0
              const thresholdPct = totalAmt > 0 && threshold > 0 ? Math.max(0, Math.min(100, (threshold / totalAmt) * 100)) : 0
              return (
                <div
                  key={item.id}
                  className="hplc-card"
                  style={{
                    animationDelay: `${idx * 0.03}s`,
                    ...(needRecal ? {
                      borderColor: '#ef4444',
                      boxShadow: '0 0 0 2px rgba(239, 68, 68, 0.15), 0 8px 24px rgba(239, 68, 68, 0.12)',
                    } : {}),
                  }}
                  onClick={() => openDetail(item)}
                >
                  <div className="hplc-card-status-bar" style={{ background: needRecal ? '#ef4444' : (meta?.color || '#999') }} />
                  <div className="hplc-card-body">
                    <div className="hplc-card-header">
                      <span className="hplc-card-code">{item.ref_code}</span>
                      <div className="hplc-card-tags">
                        {needRecal && (
                          <Tag color="red" className="hplc-card-coa-tag" style={{ fontSize: 10 }}>
                            <WarningOutlined /> 需复标
                          </Tag>
                        )}
                        {item.has_coa && (
                          <Tag color="green" className="hplc-card-coa-tag">
                            <FileExcelOutlined /> COA
                          </Tag>
                        )}
                        <Tag color={meta?.color} className="hplc-card-status-tag">
                          {meta?.label}
                        </Tag>
                      </div>
                    </div>
                    <div className="hplc-card-name" title={item.ref_name}>{item.ref_name}</div>
                    {item.cas_no && <div className="hplc-card-meta">CAS: {item.cas_no}</div>}
                    <div className="hplc-card-info-row">
                      <div className="hplc-card-info-item">
                        <span className="info-label">规格</span>
                        <span className="info-value">
                          {item.spec ? `${item.spec}${item.spec_unit || ''}` : '-'}
                        </span>
                      </div>
                      <div className="hplc-card-info-item">
                        <span className="info-label">纯度</span>
                        <span className="info-value">{item.purity ? Number(item.purity).toFixed(2) + '%' : '-'}</span>
                      </div>
                      <div className="hplc-card-info-item">
                        <span className="info-label">瓶数</span>
                        <span className="info-value">{item.quantity ?? '-'}</span>
                      </div>
                    </div>
                    <div style={{
                      marginTop: 10,
                      padding: '10px 12px',
                      background: needRecal ? '#fef2f2' : '#f8fafc',
                      borderRadius: 8,
                      border: `1px solid ${needRecal ? '#fecaca' : '#e2e8f0'}`,
                    }}>
                      {hasStock ? (
                        <>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                            <span style={{ fontSize: 12, color: '#64748b' }}>剩余量</span>
                            <span style={{ fontWeight: 600, color: barColor, fontSize: 13 }}>
                              {remaining.toFixed(2)} {remUnit}
                              {totalAmt > 0 && (
                                <span style={{ color: '#94a3b8', fontWeight: 400, marginLeft: 4 }}>
                                  / {totalAmt.toFixed(2)}
                                </span>
                              )}
                            </span>
                          </div>
                          {totalAmt > 0 && (
                            <div style={{ marginBottom: 4, position: 'relative' }}>
                              <div style={{ width: '100%', height: 10, background: '#e5e7eb', borderRadius: 5, overflow: 'hidden', position: 'relative' }}>
                                <div style={{ width: `${pct}%`, height: '100%', background: barColor, transition: 'width 0.3s' }} />
                                {threshold > 0 && thresholdPct > 0 && (
                                  <div style={{
                                    position: 'absolute',
                                    top: -2,
                                    bottom: -2,
                                    left: `${thresholdPct}%`,
                                    width: 2,
                                    background: '#ef4444',
                                    boxShadow: '0 0 0 1px rgba(255,255,255,0.8)',
                                    zIndex: 2,
                                  }} title={`阈值: ${threshold} ${remUnit}`} />
                                )}
                              </div>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3, fontSize: 10, color: '#94a3b8' }}>
                                <span style={{ color: barColor, fontWeight: 600 }}>{pct.toFixed(0)}%</span>
                                <span>阈值 {threshold.toFixed(2)} {remUnit}</span>
                              </div>
                            </div>
                          )}
                          {needRecal && (
                            <div style={{
                              marginTop: 8,
                              padding: '6px 10px',
                              background: '#fee2e2',
                              border: '1px solid #ef4444',
                              borderRadius: 6,
                              display: 'flex',
                              alignItems: 'center',
                              gap: 6,
                              fontSize: 12,
                              color: '#991b1b',
                              fontWeight: 600,
                            }}>
                              <WarningOutlined style={{ color: '#ef4444', fontSize: 14 }} />
                              <span>剩余量低于复标阈值，需立即复标</span>
                            </div>
                          )}
                        </>
                      ) : (
                        <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6, textAlign: 'center' }}>
                          未设置精细库存，请在详情中填写总量/剩余量
                        </div>
                      )}
                      <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
                        <Button
                          size="small"
                          type="primary"
                          icon={<ExperimentOutlined />}
                          style={{ flex: 1, fontSize: 12 }}
                          onClick={(e) => { e.stopPropagation(); openUsage(item); }}
                        >
                          领用
                        </Button>
                        <Button
                          size="small"
                          icon={<PlusCircleOutlined />}
                          style={{ flex: 1, fontSize: 12 }}
                          onClick={(e) => { e.stopPropagation(); openStockAdjust(item); }}
                        >
                          调整
                        </Button>
                        <Button
                          size="small"
                          icon={<HistoryOutlined />}
                          style={{ fontSize: 12 }}
                          onClick={(e) => { e.stopPropagation(); openUsageHistory(item); }}
                        >
                          历史
                        </Button>
                      </div>
                    </div>
                    <div className="hplc-card-footer">
                      <div className="hplc-card-expiry">
                        <ClockCircleOutlined />
                        <span>{item.expire_date || '无有效期'}</span>
                        {badge && (
                          <Tag color={badge.color} className="expiry-badge">
                            {badge.text}
                          </Tag>
                        )}
                      </div>
                      <div className="hplc-card-loc" title={item.location || ''}>
                        {item.location || '未设位置'}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
        <div className="hplc-card-pagination">
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            showSizeChanger
            showQuickJumper
            showTotal={t => `共 ${t} 条`}
            onChange={(p, ps) => { setPage(p); setPageSize(ps) }}
          />
        </div>
        </div>
      ) : (
        <div className="hplc-table-wrap">
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
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: t => `共 ${t} 条`,
              onChange: (p, ps) => { setPage(p); setPageSize(ps) },
            }}
          />
        </div>
      )}

      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 20 }}>⚗️</span>
            <span style={{ fontSize: 18, fontWeight: 600 }}>
              {isNew ? '新建对照品' : editingRecord?.ref_name || '对照品详情'}
            </span>
          </div>
        }
        placement="right"
        size={680}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        destroyOnHidden
        extra={
          <div style={{ display: 'flex', gap: 8 }}>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button type="primary" loading={drawerLoading} onClick={handleSave}>
              {isNew ? '创建' : '保存'}
            </Button>
          </div>
        }
      >
        {editingRecord && !isNew && (
          <div className="hplc-drawer-summary">
            <div className="summary-row">
              <span className="summary-label">编号</span>
              <span className="summary-code">{editingRecord.ref_code}</span>
            </div>
            <div className="summary-row">
              <span className="summary-label">状态</span>
              <Tag color={STATUS_META[editingRecord.ref_status]?.color}>
                {STATUS_META[editingRecord.ref_status]?.label}
              </Tag>
            </div>
          </div>
        )}

        <Form form={form} layout="vertical" size="middle" className="hplc-drawer-form">
          <div className="form-section">
            <div className="form-section-title">基本信息</div>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="ref_code" label="对照品编号" rules={[{ required: true, message: '请输入编号' }]}>
                  <Input placeholder="如：REF0001" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="ref_name" label="对照品名称" rules={[{ required: true, message: '请输入名称' }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="project_name" label="检测项目"><Input /></Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="cas_no" label="CAS号"><Input /></Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="internal_batch" label="厂内批号"><Input /></Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="cat_no" label="供应商货号"><Input /></Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="manufacturer" label="供应商/来源"><Input /></Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="manufacturer_batch" label="厂家批号"><Input /></Form.Item>
              </Col>
            </Row>
          </div>

          <div className="form-section">
            <div className="form-section-title">质量与数量</div>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="spec" label="规格/瓶"><Input placeholder="如：100" /></Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="spec_unit" label="规格单位">
                  <Select options={HPLC_REF_SPEC_UNIT_OPTIONS} placeholder="选择单位" allowClear />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="quantity" label="瓶数">
                  <InputNumber style={{ width: '100%' }} min={0} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="purity" label="纯度(%)">
                  <InputNumber precision={4} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="content" label="含量(%)">
                  <InputNumber precision={4} style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="stock_status" label="库存状态"><Input /></Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="location" label="存放位置"><Input /></Form.Item>
              </Col>
            </Row>
          </div>

          <div className="form-section">
            <div className="form-section-title">
              精细库存管理（按 mg/g 计量）
              <Button
                size="small"
                type="link"
                onClick={() => {
                  const spec = form.getFieldValue('spec')
                  const unit = form.getFieldValue('spec_unit') || 'mg'
                  const qty = form.getFieldValue('quantity') || 0
                  const specNum = parseFloat(spec) || 0
                  const total = specNum * qty
                  form.setFieldsValue({
                    total_amount: total,
                    remaining_amount: form.getFieldValue('remaining_amount') ?? total,
                    remaining_unit: unit,
                  })
                  message.info(`已按 ${specNum}${unit} × ${qty}瓶 计算总量 = ${total}${unit}`)
                }}
              >
                按规格×瓶数自动计算
              </Button>
            </div>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="total_amount" label="总量">
                  <InputNumber precision={2} style={{ width: '100%' }} min={0} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="remaining_amount" label="剩余量">
                  <InputNumber precision={2} style={{ width: '100%' }} min={0} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="remaining_unit" label="剩余单位">
                  <Select options={HPLC_REF_SPEC_UNIT_OPTIONS} allowClear />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item
                  name="recal_threshold"
                  label="复标阈值"
                  extra="剩余量低于此值时提醒复标"
                >
                  <InputNumber precision={2} style={{ width: '100%' }} min={0} />
                </Form.Item>
              </Col>
            </Row>
          </div>

          <div className="form-section">
            <div className="form-section-title">日期与有效期</div>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="arrival_date" label="到货日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="produce_date" label="生产/标定日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="expire_date" label="有效期至">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="recal_cycle_days" label="复标周期(天)">
                  <InputNumber style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="open_date" label="开瓶日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="open_expire_days" label="开瓶有效期(天)">
                  <InputNumber style={{ width: '100%' }} />
                </Form.Item>
              </Col>
            </Row>
          </div>

          <div className="form-section">
            <div className="form-section-title">其他信息</div>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="handover_no" label="交接单号"><Input /></Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="has_coa" label="是否有COA" valuePropName="checked" initialValue={false}>
                  <Switch />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="ref_status" label="状态" initialValue={0}>
                  <Select options={HPLC_REF_STATUS_OPTIONS} />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item name="remark" label="备注">
              <Input.TextArea rows={3} />
            </Form.Item>
          </div>
        </Form>
      </Drawer>

      <Drawer
        title="批量导入"
        placement="right"
        size={480}
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        destroyOnHidden
      >
        <div style={{ marginBottom: 24 }}>
          <p style={{ color: '#64748b', marginBottom: 12 }}>
            请下载模板后按格式填写，再上传 Excel 文件。
          </p>
          <Button icon={<DownloadOutlined />} onClick={handleTemplateDownload} block>
            下载导入模板
          </Button>
        </div>
        <Upload.Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <UploadOutlined style={{ fontSize: 48, color: '#0f766e' }} />
          </p>
          <p className="ant-upload-text" style={{ fontSize: 16 }}>点击或拖拽文件上传</p>
          <p className="ant-upload-hint">支持 .xlsx, .xls 格式</p>
        </Upload.Dragger>
      </Drawer>

      <Drawer
        title="调整数量"
        placement="right"
        size={400}
        open={stockDrawerOpen}
        onClose={() => setStockDrawerOpen(false)}
        destroyOnHidden
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
          <Form.Item label="对照品">
            <div style={{ fontSize: 16, fontWeight: 500 }}>
              {stockAdjustRecord?.ref_name} ({stockAdjustRecord?.ref_code})
            </div>
            <div style={{ color: '#64748b', marginTop: 4 }}>
              当前数量: <span style={{ fontWeight: 600, color: '#10b981' }}>{stockAdjustRecord?.quantity ?? 0}</span>
            </div>
          </Form.Item>
          <Form.Item
            name="quantity_change"
            label="调整数量"
            rules={[{ required: true, message: '请输入数量' }]}
            extra="正数为入库，负数为出库"
          >
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <Button icon={<PlusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity_change: (stockForm.getFieldValue('quantity_change') || 0) + 10 })}>
              +10
            </Button>
            <Button icon={<PlusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity_change: (stockForm.getFieldValue('quantity_change') || 0) + 1 })}>
              +1
            </Button>
            <Button icon={<MinusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity_change: (stockForm.getFieldValue('quantity_change') || 0) - 1 })}>
              -1
            </Button>
            <Button icon={<MinusCircleOutlined />} onClick={() => stockForm.setFieldsValue({ quantity_change: (stockForm.getFieldValue('quantity_change') || 0) - 10 })}>
              -10
            </Button>
          </div>
        </Form>
      </Drawer>

      {/* 领用 Drawer */}
      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <ExperimentOutlined style={{ color: '#0f766e' }} />
            <span>领用对照品</span>
          </div>
        }
        placement="right"
        size={480}
        open={usageDrawerOpen}
        onClose={() => setUsageDrawerOpen(false)}
        destroyOnHidden
        extra={
          <Space>
            <Button onClick={() => setUsageDrawerOpen(false)}>取消</Button>
            <Button type="primary" icon={<ExperimentOutlined />} onClick={handleUsageSubmit}>
              确认领用
            </Button>
          </Space>
        }
      >
        {usageRecord && (
          <>
            <div style={{ padding: '12px 16px', background: '#f0fdf4', borderRadius: 8, marginBottom: 16, border: '1px solid #bbf7d0' }}>
              <div style={{ fontWeight: 600, fontSize: 15, color: '#0f766e' }}>
                {usageRecord.ref_name}
                <span style={{ fontWeight: 400, color: '#64748b', marginLeft: 8, fontSize: 13 }}>
                  ({usageRecord.ref_code})
                </span>
              </div>
              <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 13 }}>
                <div>
                  <span style={{ color: '#64748b' }}>当前剩余：</span>
                  <span style={{ fontWeight: 600, color: '#10b981' }}>
                    {Number(usageRecord.remaining_amount ?? 0).toFixed(2)} {usageRecord.remaining_unit || 'mg'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#64748b' }}>总量：</span>
                  <span style={{ fontWeight: 600 }}>
                    {Number(usageRecord.total_amount ?? 0).toFixed(2)} {usageRecord.remaining_unit || 'mg'}
                  </span>
                </div>
              </div>
              {Number(usageRecord.recal_threshold ?? 0) > 0 && Number(usageRecord.remaining_amount ?? 0) <= Number(usageRecord.recal_threshold ?? 0) && (
                <div style={{ marginTop: 8, color: '#ef4444', fontSize: 12 }}>
                  <WarningOutlined /> 当前剩余量已低于复标阈值 {Number(usageRecord.recal_threshold).toFixed(2)}，领用后请尽快复标
                </div>
              )}
            </div>

            <Form form={usageForm} layout="vertical">
              <Row gutter={16}>
                <Col span={14}>
                  <Form.Item
                    name="usage_amount"
                    label="领用量"
                    rules={[
                      { required: true, message: '请输入领用量' },
                      {
                        validator: async (_, value) => {
                          if (value && usageRecord && Number(value) > Number(usageRecord.remaining_amount ?? 0)) {
                            return Promise.reject(new Error(`领用量不能超过剩余量 ${Number(usageRecord.remaining_amount).toFixed(2)}`))
                          }
                        },
                      },
                    ]}
                  >
                    <InputNumber precision={2} style={{ width: '100%' }} min={0.01} placeholder="领用量" />
                  </Form.Item>
                </Col>
                <Col span={10}>
                  <Form.Item name="usage_unit" label="单位">
                    <Select options={HPLC_REF_SPEC_UNIT_OPTIONS} />
                  </Form.Item>
                </Col>
              </Row>
              <Form.Item name="usage_person" label="领用人">
                <Input placeholder="请输入领用人姓名" />
              </Form.Item>
              <Form.Item name="usage_purpose" label="领用用途/项目">
                <Input placeholder="如：XX产品含量测定、方法验证等" />
              </Form.Item>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={3} placeholder="其他需要记录的信息" />
              </Form.Item>
            </Form>

            <div style={{ marginTop: 16, padding: '12px 16px', background: '#fef3c7', borderRadius: 6, border: '1px solid #fde68a' }}>
              <div style={{ fontSize: 12, color: '#92400e', marginBottom: 4 }}>
                <ExclamationCircleOutlined /> 领用提示
              </div>
              <ul style={{ fontSize: 12, color: '#78350f', paddingLeft: 16, margin: 0 }}>
                <li>领用将按 mg/g 扣减剩余量</li>
                <li>剩余量低于复标阈值时将自动标记为"需复标"</li>
                <li>每次领用都会记录到领用历史中</li>
              </ul>
            </div>
          </>
        )}
      </Drawer>

      {/* 领用历史 Drawer */}
      <Drawer
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <HistoryOutlined style={{ color: '#0f766e' }} />
            <span>领用历史记录</span>
          </div>
        }
        placement="right"
        size={720}
        open={usageHistoryOpen}
        onClose={() => setUsageHistoryOpen(false)}
        destroyOnHidden
      >
        {usageHistoryRecord && (
          <>
            <div style={{ padding: '12px 16px', background: '#f8fafc', borderRadius: 8, marginBottom: 16, border: '1px solid #e2e8f0' }}>
              <div style={{ fontWeight: 600, fontSize: 15 }}>
                {usageHistoryRecord.ref_name}
                <span style={{ fontWeight: 400, color: '#64748b', marginLeft: 8, fontSize: 13 }}>
                  ({usageHistoryRecord.ref_code})
                </span>
              </div>
              <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 13 }}>
                <div>
                  <span style={{ color: '#64748b' }}>当前剩余：</span>
                  <span style={{ fontWeight: 600, color: '#10b981' }}>
                    {Number(usageHistoryRecord.remaining_amount ?? 0).toFixed(2)} {usageHistoryRecord.remaining_unit || 'mg'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#64748b' }}>总量：</span>
                  <span style={{ fontWeight: 600 }}>
                    {Number(usageHistoryRecord.total_amount ?? 0).toFixed(2)} {usageHistoryRecord.remaining_unit || 'mg'}
                  </span>
                </div>
                <div>
                  <span style={{ color: '#64748b' }}>复标阈值：</span>
                  <span style={{ fontWeight: 600, color: Number(usageHistoryRecord.recal_threshold ?? 0) > 0 ? '#f59e0b' : '#94a3b8' }}>
                    {Number(usageHistoryRecord.recal_threshold ?? 0).toFixed(2) || '未设'}
                  </span>
                </div>
              </div>
            </div>

            <Table
              size="small"
              rowKey="id"
              loading={usageHistoryLoading}
              dataSource={usageHistoryData}
              pagination={{
                current: usageHistoryPage,
                pageSize: 20,
                total: usageHistoryTotal,
                showSizeChanger: false,
                showTotal: t => `共 ${t} 条领用记录`,
                onChange: (p) => fetchUsageHistory(usageHistoryRecord.id, p),
              }}
              columns={[
                {
                  title: '领用日期',
                  dataIndex: 'usage_date',
                  width: 110,
                  render: v => v || '-',
                },
                {
                  title: '领用量',
                  dataIndex: 'usage_amount',
                  width: 110,
                  render: (v, r: HplcReferenceUsage) => (
                    <span style={{ fontWeight: 600, color: '#0f766e' }}>
                      {Number(v).toFixed(2)} {r.usage_unit || 'mg'}
                    </span>
                  ),
                },
                {
                  title: '领用后剩余',
                  dataIndex: 'remaining_after',
                  width: 110,
                  render: v => (
                    <span style={{ color: '#64748b' }}>{Number(v ?? 0).toFixed(2)}</span>
                  ),
                },
                {
                  title: '领用人',
                  dataIndex: 'usage_person',
                  width: 100,
                  render: v => v || '-',
                },
                {
                  title: '用途',
                  dataIndex: 'usage_purpose',
                  ellipsis: true,
                  render: v => v || '-',
                },
                {
                  title: '备注',
                  dataIndex: 'remark',
                  ellipsis: true,
                  render: v => v || '-',
                },
              ]}
              locale={{ emptyText: <Empty description="暂无领用记录" /> }}
            />
          </>
        )}
      </Drawer>
    </div>
  )
}
