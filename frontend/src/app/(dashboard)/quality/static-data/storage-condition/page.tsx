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
  Drawer,
  Row,
  Col,
  InputNumber,
  Segmented,
  Pagination,
  Tooltip,
  Space,
  Empty,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ReloadOutlined,
  FilterOutlined,
  DatabaseOutlined,
  FireOutlined,
  CheckCircleOutlined,
  StopOutlined,
  DashboardOutlined,
  CloudOutlined,
} from '@ant-design/icons'
import { StorageCondition, Status0Or1 } from '@/types/static-data'
import {
  listStorageCondition,
  createStorageCondition,
  updateStorageCondition,
  deleteStorageCondition,
} from '@/lib/static-data-api'
import './storage-condition-style.css'

const { Search } = Input

const STATUS_META: Record<number, { label: string; color: string }> = {
  0: { label: '启用', color: '#10b981' },
  1: { label: '停用', color: '#94a3b8' },
}

export default function StorageConditionPage() {
  const [data, setData] = useState<StorageCondition[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [total, setTotal] = useState(0)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('card')
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<number | 'all'>('all')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerLoading, setDrawerLoading] = useState(false)
  const [editingRecord, setEditingRecord] = useState<StorageCondition | null>(null)
  const [isNew, setIsNew] = useState(false)
  const [form] = Form.useForm()

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { page, page_size: pageSize }
      if (searchText) {
        params.cond_code = searchText
        params.cond_name = searchText
      }
      if (statusFilter !== 'all') {
        params.status = statusFilter
      }
      const res = await listStorageCondition(params)
      setData((res?.data ?? []) as StorageCondition[])
      setTotal(res?.meta?.total ?? 0)
    } catch (e: any) {
      message.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, searchText, statusFilter])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const [statsData, setStatsData] = useState({ all: 0, enabled: 0, disabled: 0, withTemp: 0 })

  const fetchStats = useCallback(async () => {
    try {
      const [allRes, enabledRes, disabledRes] = await Promise.all([
        listStorageCondition({ page: 1, page_size: 1 }),
        listStorageCondition({ page: 1, page_size: 1, status: 0 }),
        listStorageCondition({ page: 1, page_size: 1, status: 1 }),
      ])
      const allCount = allRes?.meta?.total ?? 0
      const enabledCount = enabledRes?.meta?.total ?? 0
      const disabledCount = disabledRes?.meta?.total ?? 0
      // 拉取所有数据计算有温度要求的数量（数据量不会很大）
      const allItemsRes = await listStorageCondition({ page: 1, page_size: 200 })
      const items = (allItemsRes?.data ?? []) as StorageCondition[]
      const withTempCount = items.filter(
        (x) => x.temp_min !== null && x.temp_min !== undefined,
      ).length
      setStatsData({
        all: allCount,
        enabled: enabledCount,
        disabled: disabledCount,
        withTemp: withTempCount,
      })
    } catch (e) {
      // 忽略统计错误
    }
  }, [])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  const handleStatusFilter = (status: number | 'all') => {
    setStatusFilter(status)
    setPage(1)
  }

  const handleSearch = (value: string) => {
    setSearchText(value)
    setPage(1)
  }

  const openCreate = () => {
    setIsNew(true)
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({
      status: 0,
      temp_min: null,
      temp_max: null,
    })
    setDrawerOpen(true)
  }

  const openEdit = (record: StorageCondition) => {
    setIsNew(false)
    setEditingRecord(record)
    form.setFieldsValue({
      cond_code: record.cond_code,
      cond_name: record.cond_name,
      temp_min: record.temp_min,
      temp_max: record.temp_max,
      humidity: record.humidity,
      remark: record.remark,
      status: record.status,
    })
    setDrawerOpen(true)
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setDrawerLoading(true)
      if (isNew) {
        await createStorageCondition({ ...values, create_by: 0 })
        message.success('创建成功')
      } else if (editingRecord) {
        await updateStorageCondition(editingRecord.id, values)
        message.success('更新成功')
      }
      setDrawerOpen(false)
      fetchData()
      fetchStats()
    } catch (e: any) {
      if (e?.errorFields) return // 表单校验错误
      message.error(e.message || '操作失败')
    } finally {
      setDrawerLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteStorageCondition(id)
      message.success('删除成功')
      fetchData()
      fetchStats()
    } catch (e: any) {
      message.error(e.message || '删除失败')
    }
  }

  const handleToggleStatus = async (record: StorageCondition) => {
    try {
      const newStatus: Status0Or1 = record.status === 0 ? 1 : 0
      await updateStorageCondition(record.id, { status: newStatus })
      message.success(newStatus === 0 ? '已启用' : '已停用')
      fetchData()
      fetchStats()
    } catch (e: any) {
      message.error(e.message || '操作失败')
    }
  }

  const formatTemp = (min: number | null | undefined, max: number | null | undefined) => {
    if ((min === null || min === undefined) && (max === null || max === undefined)) {
      return '常温'
    }
    const minStr = min !== null && min !== undefined ? `${min}` : '-'
    const maxStr = max !== null && max !== undefined ? `${max}` : '-'
    return `${minStr} ~ ${maxStr}`
  }

  const columns: ColumnsType<StorageCondition> = [
    {
      title: '编码',
      dataIndex: 'cond_code',
      key: 'cond_code',
      width: 140,
      render: (text: string) => (
        <span style={{ color: '#f59e0b', fontWeight: 600 }}>{text}</span>
      ),
    },
    {
      title: '名称',
      dataIndex: 'cond_name',
      key: 'cond_name',
      width: 200,
      render: (text: string) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: '温度范围 (℃)',
      key: 'temp',
      width: 160,
      render: (_: any, record: StorageCondition) => {
        const hasTemp =
          (record.temp_min !== null && record.temp_min !== undefined) ||
          (record.temp_max !== null && record.temp_max !== undefined)
        return hasTemp ? (
          <Tag color="orange">{formatTemp(record.temp_min, record.temp_max)}</Tag>
        ) : (
          <span style={{ color: '#94a3b8' }}>常温</span>
        )
      },
    },
    {
      title: '湿度要求',
      dataIndex: 'humidity',
      key: 'humidity',
      width: 140,
      render: (text: string | null) =>
        text ? <Tag color="blue">{text}</Tag> : <span style={{ color: '#cbd5e1' }}>-</span>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: number) => {
        const meta = STATUS_META[status]
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      ellipsis: true,
      render: (text: string | null) =>
        text ? <span style={{ color: '#64748b' }}>{text}</span> : <span style={{ color: '#cbd5e1' }}>-</span>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 180,
      fixed: 'right',
      render: (_: any, record: StorageCondition) => (
        <Space>
          <Tooltip title="编辑">
            <Button type="text" icon={<EditOutlined />} onClick={() => openEdit(record)} />
          </Tooltip>
          <Tooltip title={record.status === 0 ? '停用' : '启用'}>
            <Button
              type="text"
              icon={record.status === 0 ? <StopOutlined /> : <CheckCircleOutlined />}
              onClick={() => handleToggleStatus(record)}
              style={{ color: record.status === 0 ? '#94a3b8' : '#10b981' }}
            />
          </Tooltip>
          <Popconfirm
            title="确认删除"
            description={`确定要删除「${record.cond_name}」吗？`}
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除">
              <Button type="text" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="sc-page">
      <div className="sc-header">
        <div className="sc-header-left">
          <div className="sc-title">
            <DatabaseOutlined className="sc-title-icon" />
            <div>
              <h1>贮存条件管理</h1>
              <p>维护物料、试剂、样品等贮存环境条件字典</p>
            </div>
          </div>
        </div>
        <div className="sc-header-right">
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={openCreate}
            className="sc-add-btn"
            size="large"
          >
            新建贮存条件
          </Button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="sc-stats">
        <div className="stat-card stat-all" onClick={() => handleStatusFilter('all')}>
          <DashboardOutlined className="stat-icon" style={{ color: '#f59e0b' }} />
          <div className="stat-info">
            <div className="stat-num">{statsData.all}</div>
            <div className="stat-label">全部条件</div>
          </div>
        </div>
        <div className="stat-card stat-enabled" onClick={() => handleStatusFilter(0)}>
          <CheckCircleOutlined className="stat-icon" style={{ color: '#10b981' }} />
          <div className="stat-info">
            <div className="stat-num">{statsData.enabled}</div>
            <div className="stat-label">启用中</div>
          </div>
        </div>
        <div className="stat-card stat-disabled" onClick={() => handleStatusFilter(1)}>
          <StopOutlined className="stat-icon" style={{ color: '#94a3b8' }} />
          <div className="stat-info">
            <div className="stat-num">{statsData.disabled}</div>
            <div className="stat-label">已停用</div>
          </div>
        </div>
        <div className="stat-card stat-temp">
          <FireOutlined className="stat-icon" style={{ color: '#06b6d4' }} />
          <div className="stat-info">
            <div className="stat-num">{statsData.withTemp}</div>
            <div className="stat-label">有温度要求</div>
          </div>
        </div>
      </div>

      {/* 工具栏 */}
      <div className="sc-toolbar">
        <div className="sc-search-wrap">
          <Search
            placeholder="搜索编码或名称..."
            allowClear
            onSearch={handleSearch}
            className="sc-search"
            size="large"
          />
          <Button
            icon={<FilterOutlined />}
            onClick={() => handleStatusFilter('all')}
            className={statusFilter === 'all' ? 'sc-filter-active' : ''}
          >
            全部
          </Button>
          <Button
            icon={<CheckCircleOutlined />}
            onClick={() => handleStatusFilter(0)}
            className={statusFilter === 0 ? 'sc-filter-active' : ''}
          >
            启用
          </Button>
          <Button
            icon={<StopOutlined />}
            onClick={() => handleStatusFilter(1)}
            className={statusFilter === 1 ? 'sc-filter-active' : ''}
          >
            停用
          </Button>
        </div>
        <div className="sc-toolbar-right">
          <Segmented
            options={[
              { label: '卡片', value: 'card' },
              { label: '表格', value: 'table' },
            ]}
            value={viewMode}
            onChange={(value) => setViewMode(value as 'card' | 'table')}
          />
          <Button icon={<ReloadOutlined />} onClick={fetchData}>
            刷新
          </Button>
        </div>
      </div>

      {/* 卡片视图 */}
      {viewMode === 'card' ? (
        data.length === 0 && !loading ? (
          <div className="sc-table-wrap">
            <Empty description="暂无数据" />
          </div>
        ) : (
          <div className="sc-card-grid">
            {data.map((record, index) => {
              const meta = STATUS_META[record.status]
              const hasTemp =
                (record.temp_min !== null && record.temp_min !== undefined) ||
                (record.temp_max !== null && record.temp_max !== undefined)
              return (
                <div
                  className="sc-card"
                  key={record.id}
                  style={{ animationDelay: `${index * 0.04}s` }}
                  onClick={() => openEdit(record)}
                >
                  <div
                    className="sc-card-status-bar"
                    style={{ background: record.status === 0 ? meta.color : '#cbd5e1' }}
                  />
                  <div className="sc-card-body">
                    <div className="sc-card-header">
                      <span className="sc-card-code">{record.cond_code}</span>
                      <Tag color={record.status === 0 ? 'success' : 'default'}>
                        {meta.label}
                      </Tag>
                    </div>
                    <div className="sc-card-name">{record.cond_name}</div>

                    <div className="sc-card-temp">
                      <FireOutlined className="sc-card-temp-icon" />
                      <span className="sc-card-temp-value">
                        {formatTemp(record.temp_min, record.temp_max)}
                      </span>
                      <span className="sc-card-temp-unit">°C</span>
                    </div>

                    <div className="sc-card-info-grid">
                      <div className="sc-card-info-item">
                        <span className="sc-info-label">
                          <CloudOutlined /> 湿度
                        </span>
                        <span className="sc-info-value">
                          {record.humidity || '无要求'}
                        </span>
                      </div>
                      <div className="sc-card-info-item">
                        <span className="sc-info-label">编码</span>
                        <span className="sc-info-value">{record.cond_code}</span>
                      </div>
                    </div>

                    {record.remark && <div className="sc-card-remark">{record.remark}</div>}

                    <div className="sc-card-actions" onClick={(e) => e.stopPropagation()}>
                      <Tooltip title="编辑">
                        <Button
                          type="text"
                          icon={<EditOutlined />}
                          onClick={() => openEdit(record)}
                        />
                      </Tooltip>
                      <Tooltip title={record.status === 0 ? '停用' : '启用'}>
                        <Button
                          type="text"
                          icon={record.status === 0 ? <StopOutlined /> : <CheckCircleOutlined />}
                          onClick={() => handleToggleStatus(record)}
                          style={{ color: record.status === 0 ? '#94a3b8' : '#10b981' }}
                        />
                      </Tooltip>
                      <Popconfirm
                        title="确认删除"
                        description={`确定要删除「${record.cond_name}」吗？`}
                        onConfirm={() => handleDelete(record.id)}
                        okText="确定"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <Tooltip title="删除">
                          <Button type="text" danger icon={<DeleteOutlined />} />
                        </Tooltip>
                      </Popconfirm>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )
      ) : (
        <div className="sc-table-wrap">
          <Table
            columns={columns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            pagination={false}
            scroll={{ x: 1100 }}
            size="middle"
          />
        </div>
      )}

      <div className="sc-pagination">
        <Pagination
          current={page}
          pageSize={pageSize}
          total={total}
          showSizeChanger
          showQuickJumper
          showTotal={(t) => `共 ${t} 条`}
          onChange={(p, ps) => {
            setPage(p)
            setPageSize(ps)
          }}
        />
      </div>

      {/* 新建/编辑 Drawer */}
      <Drawer
        title={isNew ? '新建贮存条件' : '编辑贮存条件'}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width={520}
        destroyOnClose
        extra={
          <Space>
            <Button onClick={() => setDrawerOpen(false)}>取消</Button>
            <Button
              type="primary"
              loading={drawerLoading}
              onClick={handleSubmit}
              className="sc-add-btn"
            >
              保存
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          className="sc-drawer-form"
          initialValues={{ status: 0 }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="cond_code"
                label="条件编码"
                rules={[
                  { required: true, message: '请输入条件编码' },
                  { max: 50, message: '编码长度不能超过50' },
                ]}
              >
                <Input placeholder="如 SC001" disabled={!isNew} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="cond_name"
                label="条件名称"
                rules={[
                  { required: true, message: '请输入条件名称' },
                  { max: 100, message: '名称长度不能超过100' },
                ]}
              >
                <Input placeholder="如 2-8℃冷藏" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="temp_min" label="最低温度 (℃)">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="-30"
                  min={-100}
                  max={200}
                  step={0.5}
                  precision={2}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="temp_max" label="最高温度 (℃)">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="40"
                  min={-100}
                  max={200}
                  step={0.5}
                  precision={2}
                />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="humidity"
            label="湿度要求"
            tooltip="如：≤60%RH、30-65%RH 等"
          >
            <Input placeholder="如 ≤60%RH" maxLength={50} />
          </Form.Item>

          <Form.Item name="status" label="状态">
            <Segmented
              style={{ width: '100%' }}
              options={[
                { label: '✅ 启用', value: 0 },
                { label: '⛔ 停用', value: 1 },
              ]}
            />
          </Form.Item>

          <Form.Item name="remark" label="备注">
            <Input.TextArea
              rows={4}
              placeholder="补充说明..."
              maxLength={500}
              showCount
            />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}
