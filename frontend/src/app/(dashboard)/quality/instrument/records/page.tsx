'use client'

import { useState, useCallback, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Drawer,
  Form,
  DatePicker,
  message,
  Popconfirm,
  Empty,
  Spin,
} from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  AppstoreOutlined,
  TableOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  getCalibrationRecords,
  getCalibrationRecord,
  createCalibrationRecord,
  updateCalibrationRecord,
  deleteCalibrationRecord,
  getInstruments,
} from '@/actions/instrument'
import type {
  CalibrationRecordListItem,
  CalibrationRecordFilter,
  CalibrationRecordCreate,
  CalibrationRecordUpdate,
  InstrumentListItem,
  CalibrationMethod,
  CalibrationResult,
  RecordStatus,
} from '@/types/instrument'
import '../instrument-style.css'

const methodOptions = [
  { value: 'external', label: '外委校准' },
  { value: 'internal', label: '内部校准' },
]

const resultOptions = [
  { value: 'qualified', label: '合格' },
  { value: 'unqualified', label: '不合格' },
  { value: 'limited', label: '限用' },
]

const validPeriodOptions = [
  { value: 6, label: '半年' },
  { value: 12, label: '一年' },
]

const statusOptions = [
  { value: 'active', label: '已启用' },
  { value: 'inactive', label: '已停用' },
]

const resultColorMap: Record<string, string> = {
  qualified: 'success',
  unqualified: 'error',
  limited: 'warning',
}

const statusColorMap: Record<string, string> = {
  active: 'success',
  inactive: 'default',
}

const methodColorMap: Record<string, string> = {
  external: 'blue',
  internal: 'green',
}

export default function CalibrationRecordsPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<CalibrationRecordListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [viewMode, setViewMode] = useState<'card' | 'table'>('table')
  const [isMobile, setIsMobile] = useState(false)

  const [filters, setFilters] = useState<{
    instrument_id?: string
    calibration_no?: string
    calibration_result?: string
    status?: string
    calibration_method?: string
  }>({})

  const [createDrawerVisible, setCreateDrawerVisible] = useState(false)
  const [editDrawerVisible, setEditDrawerVisible] = useState(false)
  const [editRecord, setEditRecord] = useState<CalibrationRecordListItem | null>(null)
  const [submitLoading, setSubmitLoading] = useState(false)

  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()

  const [instruments, setInstruments] = useState<InstrumentListItem[]>([])
  const [instrumentsLoading, setInstrumentsLoading] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => {
      setIsMobile(mq.matches)
      setViewMode(mq.matches ? 'card' : 'table')
    }
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  const loadInstruments = useCallback(async () => {
    setInstrumentsLoading(true)
    try {
      const response = await getInstruments({ page: 1, page_size: 1000 })
      const items = response.items || []
      console.log('仪器列表加载完成:', items.length, '条')
      setInstruments(items)
    } catch (error) {
      console.error('加载仪器列表失败', error)
      message.error('加载仪器列表失败')
    } finally {
      setInstrumentsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadInstruments()
  }, [loadInstruments])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params: CalibrationRecordFilter = { page, page_size: pageSize }
      if (filters.instrument_id) params.instrument_id = filters.instrument_id
      if (filters.calibration_no) params.calibration_no = filters.calibration_no
      if (filters.calibration_result) params.calibration_result = filters.calibration_result as CalibrationResult
      if (filters.status) params.status = filters.status as RecordStatus
      if (filters.calibration_method) params.calibration_method = filters.calibration_method as CalibrationMethod

      const response = await getCalibrationRecords(params)
      setData(response.items || [])
      setTotal(response.total || 0)
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filters])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSearch = () => { setPage(1); loadData() }
  const handleReset = () => { setFilters({}); setPage(1) }

  const handleCreate = () => {
    createForm.resetFields()
    createForm.setFieldsValue({
      calibration_date: dayjs(),
      calibration_method: 'external',
      calibration_result: 'qualified',
      valid_period: 12,
      is_scheduled: false,
    })
    setCreateDrawerVisible(true)
  }

  const handleEdit = async (record: CalibrationRecordListItem) => {
    try {
      const response = await getCalibrationRecord(record.id)
      setEditRecord({
        ...response,
        instrument_no: record.instrument_no,
        instrument_name: record.instrument_name,
      })

      let valid_period = 12
      if (response.valid_from && response.valid_until) {
        const from = dayjs(response.valid_from)
        const until = dayjs(response.valid_until)
        valid_period = until.diff(from, 'month')
      }

      editForm.setFieldsValue({
        ...response,
        calibration_date: dayjs(response.calibration_date),
        calibration_end_date: response.calibration_end_date ? dayjs(response.calibration_end_date) : null,
        valid_from: response.valid_from ? dayjs(response.valid_from) : null,
        valid_until: response.valid_until ? dayjs(response.valid_until) : null,
        scheduled_date: response.scheduled_date ? dayjs(response.scheduled_date) : null,
        valid_period: valid_period,
      })
      setEditDrawerVisible(true)
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteCalibrationRecord(id)
      message.success('删除成功')
      loadData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const generateCalibrationNo = () => {
    return `CAL${dayjs().format('YYYYMMDDHHmmss')}`
  }

  const handleCreateSubmit = async () => {
    try {
      const values = await createForm.validateFields()
      const validFrom = values.calibration_date.format('YYYY-MM-DD')
      const validUntil = values.calibration_date.add(values.valid_period, 'month').format('YYYY-MM-DD')

      const submitData: CalibrationRecordCreate = {
        instrument_id: values.instrument_id,
        calibration_no: values.calibration_no || generateCalibrationNo(),
        calibration_date: values.calibration_date.format('YYYY-MM-DD'),
        calibration_end_date: values.calibration_end_date?.format('YYYY-MM-DD'),
        calibration_method: values.calibration_method,
        calibration_agency: values.calibration_agency,
        calibrator_name: values.calibrator_name,
        certificate_no: values.certificate_no,
        calibration_result: values.calibration_result,
        result_reason: values.result_reason,
        valid_from: validFrom,
        valid_until: validUntil,
        is_scheduled: values.is_scheduled,
        scheduled_date: values.scheduled_date?.format('YYYY-MM-DD'),
        remark: values.remark,
      }
      setSubmitLoading(true)
      await createCalibrationRecord(submitData)
      message.success('创建成功')
      setCreateDrawerVisible(false)
      loadData()
    } catch (error) {
      message.error('创建失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const handleEditSubmit = async () => {
    if (!editRecord) return
    try {
      const values = await editForm.validateFields()
      const validFrom = values.calibration_date?.format('YYYY-MM-DD')
      const validUntil = values.calibration_date?.add(values.valid_period, 'month').format('YYYY-MM-DD')

      const submitData: CalibrationRecordUpdate = {
        calibration_date: values.calibration_date?.format('YYYY-MM-DD'),
        calibration_end_date: values.calibration_end_date?.format('YYYY-MM-DD'),
        calibration_method: values.calibration_method,
        calibration_agency: values.calibration_agency,
        calibrator_name: values.calibrator_name,
        certificate_no: values.certificate_no,
        calibration_result: values.calibration_result,
        result_reason: values.result_reason,
        valid_from: validFrom,
        valid_until: validUntil,
        is_scheduled: values.is_scheduled,
        scheduled_date: values.scheduled_date?.format('YYYY-MM-DD'),
        remark: values.remark,
        is_active: values.is_active,
      }
      setSubmitLoading(true)
      await updateCalibrationRecord(editRecord.id, submitData)
      message.success('更新成功')
      setEditDrawerVisible(false)
      loadData()
    } catch (error) {
      message.error('更新失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  const columns = [
    { title: '校准单据编号', dataIndex: 'calibration_no', key: 'calibration_no', width: 150 },
    { title: '仪器编号', dataIndex: 'instrument_no', key: 'instrument_no', width: 100 },
    { title: '仪器名称', dataIndex: 'instrument_name', key: 'instrument_name', width: 120, ellipsis: true },
    { title: '校准日期', dataIndex: 'calibration_date', key: 'calibration_date', width: 110, render: (value: string) => dayjs(value).format('YYYY-MM-DD') },
    { title: '校准方式', dataIndex: 'calibration_method', key: 'calibration_method', width: 90, render: (value: string) => <Tag color={methodColorMap[value]}>{methodOptions.find(o => o.value === value)?.label || value}</Tag> },
    { title: '校准结论', dataIndex: 'calibration_result', key: 'calibration_result', width: 80, render: (value: CalibrationResult) => <Tag color={resultColorMap[value]}>{resultOptions.find(o => o.value === value)?.label}</Tag> },
    { title: '证书编号', dataIndex: 'certificate_no', key: 'certificate_no', width: 120, ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80, render: (value: RecordStatus) => <Tag color={statusColorMap[value]}>{statusOptions.find(o => o.value === value)?.label}</Tag> },
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: unknown, record: CalibrationRecordListItem) => (
        <Space size="small">
          <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const renderCard = (item: CalibrationRecordListItem) => (
    <div key={item.id} className="record-card">
      <div className="record-card-header">
        <div className="record-card-no">{item.calibration_no}</div>
        <Tag color={statusColorMap[item.status]}>{statusOptions.find(o => o.value === item.status)?.label}</Tag>
      </div>
      <div className="record-card-body">
        <div className="record-card-item">
          <div className="record-card-item-label">仪器</div>
          <div className="record-card-item-value">{item.instrument_no} - {item.instrument_name}</div>
        </div>
        <div className="record-card-item">
          <div className="record-card-item-label">校准日期</div>
          <div className="record-card-item-value">{dayjs(item.calibration_date).format('YYYY-MM-DD')}</div>
        </div>
        <div className="record-card-item">
          <div className="record-card-item-label">方式</div>
          <div className="record-card-item-value"><Tag color={methodColorMap[item.calibration_method]}>{methodOptions.find(o => o.value === item.calibration_method)?.label}</Tag></div>
        </div>
        <div className="record-card-item">
          <div className="record-card-item-label">结论</div>
          <div className="record-card-item-value"><Tag color={resultColorMap[item.calibration_result]}>{resultOptions.find(o => o.value === item.calibration_result)?.label}</Tag></div>
        </div>
        <div className="record-card-item">
          <div className="record-card-item-label">证书编号</div>
          <div className="record-card-item-value">{item.certificate_no || '-'}</div>
        </div>
        <div className="record-card-item">
          <div className="record-card-item-label">有效期至</div>
          <div className="record-card-item-value">{item.valid_until ? dayjs(item.valid_until).format('YYYY-MM-DD') : '-'}</div>
        </div>
      </div>
      <div className="record-card-footer">
        <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(item)}>编辑</Button>
        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(item.id)}>
          <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </div>
    </div>
  )

  return (
    <div className="instrument-page">
      <div className="instrument-toolbar">
        <div>
          <h1 style={{ fontSize: isMobile ? '18px' : '24px', fontWeight: 700, margin: 0, color: '#1f2937' }}>校准记录</h1>
          <p style={{ fontSize: isMobile ? '12px' : '14px', color: '#6b7280', margin: '4px 0 0 0' }}>管理仪器校准记录，追踪校准周期</p>
        </div>
        <Space wrap size={8}>
          {!isMobile && (
            <Space>
              <Button
                type={viewMode === 'table' ? 'primary' : 'default'}
                icon={<TableOutlined />}
                onClick={() => setViewMode('table')}
                size="small"
              >表格</Button>
              <Button
                type={viewMode === 'card' ? 'primary' : 'default'}
                icon={<AppstoreOutlined />}
                onClick={() => setViewMode('card')}
                size="small"
              >卡片</Button>
            </Space>
          )}
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading} size={isMobile ? 'small' : 'middle'}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate} size={isMobile ? 'small' : 'middle'}>新增记录</Button>
        </Space>
      </div>

      <Card style={{ borderRadius: 12, border: '1px solid #e5e7eb', marginBottom: 16 }}>
        <div className="records-search-area">
          <Input
            placeholder="校准单据编号"
            value={filters.calibration_no}
            onChange={(e) => setFilters({ ...filters, calibration_no: e.target.value || undefined })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '150px' }}
            onPressEnter={handleSearch}
          />
          <Select
            placeholder="校准方式"
            value={filters.calibration_method}
            onChange={(value) => setFilters({ ...filters, calibration_method: value })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '120px' }}
          >
            {methodOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}
          </Select>
          <Select
            placeholder="校准结论"
            value={filters.calibration_result}
            onChange={(value) => setFilters({ ...filters, calibration_result: value })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '120px' }}
          >
            {resultOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}
          </Select>
          <Select
            placeholder="状态"
            value={filters.status}
            onChange={(value) => setFilters({ ...filters, status: value })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '120px' }}
          >
            {statusOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}
          </Select>
          <Space>
            <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch} size={isMobile ? 'small' : 'middle'}>查询</Button>
            <Button icon={<ReloadOutlined />} onClick={handleReset} size={isMobile ? 'small' : 'middle'}>重置</Button>
          </Space>
        </div>
      </Card>

      <Spin spinning={loading}>
        {viewMode === 'table' ? (
          <Card style={{ borderRadius: 12, border: '1px solid #e5e7eb' }}>
            <Table
              columns={columns}
              dataSource={data}
              rowKey="id"
              scroll={{ x: 1100 }}
              pagination={{
                current: page, pageSize, total,
                showSizeChanger: !isMobile,
                showQuickJumper: !isMobile,
                showTotal: (t) => `共 ${t} 条`,
                onChange: (p, ps) => { setPage(p); setPageSize(ps) },
                simple: isMobile,
              }}
            />
          </Card>
        ) : (
          <>
            <div className="records-card-grid">
              {data.length > 0 ? data.map(renderCard) : (
                <div className="empty-state"><Empty description="暂无校准记录" /></div>
              )}
            </div>
            <div className="pagination-mobile">
              <span style={{ color: '#6b7280', fontSize: 13 }}>共 {total} 条</span>
              <Space>
                <Button disabled={page === 1} onClick={() => setPage(page - 1)}>上一页</Button>
                <span style={{ color: '#1f2937', fontWeight: 500 }}>{page}</span>
                <Button disabled={page * pageSize >= total} onClick={() => setPage(page + 1)}>下一页</Button>
              </Space>
            </div>
          </>
        )}
      </Spin>

      <Drawer
        title="新增校准记录"
        open={createDrawerVisible}
        onClose={() => setCreateDrawerVisible(false)}
        width={isMobile ? '100%' : 800}
        className="instrument-drawer"
        styles={{ body: { paddingBottom: 80 } }}
      >
        <Form form={createForm} layout="vertical">
          <Form.Item name="instrument_id" label="关联仪器" rules={[{ required: true }]}>
            <Select 
              placeholder={instrumentsLoading ? '加载中...' : '请选择仪器'} 
              showSearch 
              optionFilterProp="children"
              loading={instrumentsLoading}
              filterOption={(input, option) => 
                option?.children?.toString().toLowerCase().includes(input.toLowerCase()) ?? false
              }
            >
              {instruments.map((inst) => (
                <Select.Option key={inst.id} value={inst.id}>{inst.instrument_no} - {inst.instrument_name}</Select.Option>
              ))}
              {!instrumentsLoading && instruments.length === 0 && (
                <Select.Option value="" disabled>暂无仪器数据，请先添加仪器</Select.Option>
              )}
            </Select>
          </Form.Item>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item name="calibration_no" label="校准单据编号">
              <Input placeholder="不填则自动生成" />
            </Form.Item>
            <Form.Item name="calibration_date" label="校准日期" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
            <Form.Item name="calibration_method" label="校准方式" rules={[{ required: true }]}>
              <Select placeholder="请选择">{methodOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
            <Form.Item name="calibration_result" label="校准结论" rules={[{ required: true }]}>
              <Select placeholder="请选择">{resultOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
            <Form.Item name="valid_period" label="有效期" rules={[{ required: true }]}>
              <Select placeholder="请选择">{validPeriodOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item name="calibration_agency" label="校准机构">
              <Input placeholder="请输入校准机构" />
            </Form.Item>
            <Form.Item name="calibrator_name" label="校准人员">
              <Input placeholder="请输入校准人员" />
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item name="certificate_no" label="证书编号">
              <Input placeholder="请输入证书编号" />
            </Form.Item>
            <Form.Item name="calibration_end_date" label="校准结束日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Form.Item name="result_reason" label="结论说明">
            <Input.TextArea rows={2} placeholder="请输入结论说明" />
          </Form.Item>

          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>
        </Form>

        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, background: '#fff', borderTop: '1px solid #e5e7eb' }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setCreateDrawerVisible(false)}>取消</Button>
            <Button type="primary" onClick={handleCreateSubmit} loading={submitLoading}>创建</Button>
          </Space>
        </div>
      </Drawer>

      <Drawer
        title="编辑校准记录"
        open={editDrawerVisible}
        onClose={() => setEditDrawerVisible(false)}
        width={isMobile ? '100%' : 800}
        className="instrument-drawer"
        styles={{ body: { paddingBottom: 80 } }}
      >
        <Form form={editForm} layout="vertical">
          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item label="关联仪器">
              <Input value={editRecord?.instrument_name} disabled />
            </Form.Item>
            <Form.Item label="校准单据编号">
              <Input value={editRecord?.calibration_no} disabled />
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item name="calibration_date" label="校准日期" rules={[{ required: true }]}>
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="valid_period" label="有效期" rules={[{ required: true }]}>
              <Select placeholder="请选择">{validPeriodOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
            <Form.Item name="calibration_method" label="校准方式" rules={[{ required: true }]}>
              <Select placeholder="请选择">{methodOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
            <Form.Item name="calibration_result" label="校准结论" rules={[{ required: true }]}>
              <Select placeholder="请选择">{resultOptions.map((opt) => <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
            <Form.Item name="is_active" label="状态">
              <Select placeholder="请选择">{statusOptions.map((opt) => <Select.Option key={opt.value} value={opt.value === 'active'}>{opt.label}</Select.Option>)}</Select>
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item name="calibration_agency" label="校准机构">
              <Input placeholder="请输入校准机构" />
            </Form.Item>
            <Form.Item name="calibrator_name" label="校准人员">
              <Input placeholder="请输入校准人员" />
            </Form.Item>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
            <Form.Item name="certificate_no" label="证书编号">
              <Input placeholder="请输入证书编号" />
            </Form.Item>
            <Form.Item name="calibration_end_date" label="校准结束日期">
              <DatePicker style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Form.Item name="result_reason" label="结论说明">
            <Input.TextArea rows={2} placeholder="请输入结论说明" />
          </Form.Item>

          <Form.Item name="remark" label="备注">
            <Input.TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>
        </Form>

        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, background: '#fff', borderTop: '1px solid #e5e7eb' }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => setEditDrawerVisible(false)}>取消</Button>
            <Button type="primary" onClick={handleEditSubmit} loading={submitLoading}>保存</Button>
          </Space>
        </div>
      </Drawer>
    </div>
  )
}