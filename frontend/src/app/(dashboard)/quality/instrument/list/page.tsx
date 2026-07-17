'use client'

import { useState, useCallback, useEffect, useRef } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Tag,
  Empty,
  Spin,
  message,
  Modal,
  Form,
  DatePicker,
  Descriptions,
  Typography,
  Row,
  Col,
  Drawer,
  Divider,
  InputNumber,
} from 'antd'
import type { TableColumnsType } from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  ReloadOutlined,
  EditOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  AppstoreOutlined,
  TableOutlined,
  DownOutlined,
  UpOutlined,
  SaveOutlined,
  CameraOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useRouter } from 'next/navigation'
import {
  getInstruments,
  getCalibrationRules,
  getCalibrationRecords,
  createCalibrationRecord,
  getCalibrationRule,
  createInstrument,
  createCalibrationRule,
  recognizeInstrumentLabel,
} from '@/actions/instrument'
import type {
  InstrumentListItem,
  InstrumentFilter,
  InstrumentCategory,
  CalibrationRule,
  CalibrationRecordListItem,
  CalibrationRecordCreate,
  InstrumentCreate,
  CalibrationRuleCreate,
  AIRecognizedInstrumentInfo,
} from '@/types/instrument'
import '../instrument-style.css'

const { Text } = Typography

const categoryOptions = [
  { value: 'physicochemical', label: '理化' },
  { value: 'chromatography', label: '色谱' },
  { value: 'microbiology', label: '微生物' },
  { value: 'balance', label: '天平' },
  { value: 'oven', label: '烘箱' },
  { value: 'other', label: '其他' },
]

const methodOptions: Record<string, string> = {
  external: '外委校准',
  internal: '内部校准',
}

const unitOptions = [
  { value: 'month', label: '月' },
  { value: 'year', label: '年' },
]

const resultOptions: Record<string, { label: string; color: string }> = {
  qualified: { label: '合格', color: 'success' },
  unqualified: { label: '不合格', color: 'error' },
  limited: { label: '限用', color: 'warning' },
}

interface ExpandedRecord {
  instrument: InstrumentListItem
  rules: CalibrationRule[]
  recordsMap: Map<string, CalibrationRecordListItem[]>
}

function ExpandedRow({ record, onRefresh, isMobile }: { record: ExpandedRecord; onRefresh?: () => void; isMobile?: boolean }) {
  const [loading, setLoading] = useState(false)
  const [rules, setRules] = useState<CalibrationRule[]>([])
  const [recordsMap, setRecordsMap] = useState<Map<string, CalibrationRecordListItem[]>>(new Map())
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [selectedRule, setSelectedRule] = useState<CalibrationRule | null>(null)
  const [createForm] = Form.useForm()
  const [submitLoading, setSubmitLoading] = useState(false)

  useEffect(() => {
    loadCalibrationData(record.instrument.id)
  }, [record.instrument.id])

  const loadCalibrationData = async (instrumentId: string) => {
    setLoading(true)
    try {
      const rulesData = await getCalibrationRules(instrumentId)
      setRules(rulesData)

      const records = new Map<string, CalibrationRecordListItem[]>()
      const allRecordsData = await getCalibrationRecords({ instrument_id: instrumentId })
      const allRecords = allRecordsData.items || []

      for (const rule of rulesData) {
        const ruleRecords = allRecords.filter(r => r.rule_id === rule.id)
        records.set(rule.id, ruleRecords)
      }
      const ungroupedRecords = allRecords.filter(r => !r.rule_id)
      if (ungroupedRecords.length > 0) {
        records.set('ungrouped', ungroupedRecords)
      }
      setRecordsMap(records)
    } catch (err) {
      console.error('加载校准数据失败', err)
    } finally {
      setLoading(false)
    }
  }

  const generateCalibrationNo = () => {
    const now = dayjs()
    const no = `CAL${now.format('YYYYMMDDHHmmss')}`
    return no
  }

  const handleOpenCreate = (rule: CalibrationRule) => {
    setSelectedRule(rule)
    createForm.resetFields()
    createForm.setFieldsValue({
      calibration_date: dayjs(),
      calibration_method: rule.calibration_method,
      calibration_result: 'qualified',
      valid_period: rule.calibration_cycle || 12,
    })
    setCreateModalVisible(true)
  }

  const handleCreateSubmit = async () => {
    if (!selectedRule) return
    try {
      const values = await createForm.validateFields()
      const validFrom = values.calibration_date.format('YYYY-MM-DD')
      const validUntil = values.calibration_date.add(values.valid_period, 'month').format('YYYY-MM-DD')

      const submitData: CalibrationRecordCreate = {
        instrument_id: record.instrument.id,
        rule_id: selectedRule.id,
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
        remark: values.remark,
      }
      setSubmitLoading(true)
      await createCalibrationRecord(submitData)
      message.success('创建成功')
      setCreateModalVisible(false)
      loadCalibrationData(record.instrument.id)
      onRefresh?.()
    } catch (error) {
      message.error('创建失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  if (loading) {
    return <Spin size="small" style={{ padding: 16, display: 'block', textAlign: 'center' }} />
  }

  if (rules.length === 0 && !recordsMap.get('ungrouped')?.length) {
    return (
      <div className="empty-state">
        <Empty description="暂无校准规则" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </div>
    )
  }

  const recordColumns = [
    {
      title: '校准日期',
      dataIndex: 'calibration_date',
      width: 110,
      render: (v: string) => v ? dayjs(v).format('YYYY-MM-DD') : '-',
    },
    {
      title: '有效期至',
      dataIndex: 'valid_until',
      width: 140,
      render: (v: string) => {
        if (!v) return '-'
        const isOverdue = dayjs(v).isBefore(dayjs())
        return (
          <Space size={4}>
            <Text type={isOverdue ? 'danger' : undefined}>
              {dayjs(v).format('YYYY-MM-DD')}
            </Text>
            {isOverdue && <Tag color="red" style={{ margin: 0 }}>已超期</Tag>}
          </Space>
        )
      },
    },
    {
      title: '校准结果',
      dataIndex: 'calibration_result',
      width: 90,
      render: (v: string) => {
        const opt = resultOptions[v]
        return opt ? <Tag color={opt.color}>{opt.label}</Tag> : v
      },
    },
    {
      title: '证书编号',
      dataIndex: 'certificate_no',
      width: 150,
      ellipsis: true,
    },
    {
      title: '校准方法',
      dataIndex: 'calibration_method',
      width: 100,
      render: (v: string) => methodOptions[v] || v,
    },
  ]

  return (
    <>
      <div style={{ padding: '4px 0' }}>
        {rules.map((rule) => {
          const ruleRecords = recordsMap.get(rule.id) || []

          return (
            <div
              key={rule.id}
              className="ins-card"
              style={{ marginBottom: 12, padding: 12, background: '#f8fafc' }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 8,
                  gap: 12,
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <Space wrap size={[16, 4]}>
                    <Text strong style={{ fontSize: 13 }}>
                      {methodOptions[rule.calibration_method] || rule.calibration_method}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      周期: {rule.calibration_cycle} {rule.calibration_unit}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      机构: {rule.calibration_agency || '-'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      校准员: {rule.internal_calibrator_name || '-'}
                    </Text>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      预警: {rule.warning_days} 天
                    </Text>
                    {rule.is_active ? (
                      <Tag color="success" icon={<CheckCircleOutlined />} style={{ margin: 0 }}>启用</Tag>
                    ) : (
                      <Tag color="default" icon={<CloseCircleOutlined />} style={{ margin: 0 }}>停用</Tag>
                    )}
                  </Space>
                </div>
                <Button
                  type="primary"
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => handleOpenCreate(rule)}
                >
                  新增记录
                </Button>
              </div>

              {ruleRecords.length > 0 ? (
                isMobile ? (
                  <div className="calibration-record-list">
                    {ruleRecords.map((r) => (
                      <div key={r.id || r.calibration_no} className="calibration-record-item">
                        <div className="calibration-record-header">
                          <span className="calibration-record-date">{r.calibration_date ? dayjs(r.calibration_date).format('YYYY-MM-DD') : '-'}</span>
                          <Tag color={resultOptions[r.calibration_result]?.color || 'default'}>{resultOptions[r.calibration_result]?.label || r.calibration_result}</Tag>
                        </div>
                        <div className="calibration-record-body">
                          <div className="calibration-record-row">
                            <span className="calibration-record-label">有效期至</span>
                            <span className={dayjs(r.valid_until).isBefore(dayjs()) ? 'calibration-record-value danger' : 'calibration-record-value'}>
                              {r.valid_until ? dayjs(r.valid_until).format('YYYY-MM-DD') : '-'}
                              {dayjs(r.valid_until).isBefore(dayjs()) && <span className="calibration-record-tag">已超期</span>}
                            </span>
                          </div>
                          {r.certificate_no && (
                            <div className="calibration-record-row">
                              <span className="calibration-record-label">证书编号</span>
                              <span className="calibration-record-value">{r.certificate_no}</span>
                            </div>
                          )}
                          <div className="calibration-record-row">
                            <span className="calibration-record-label">校准方法</span>
                            <span className="calibration-record-value">{methodOptions[r.calibration_method] || r.calibration_method}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Table
                    size="small"
                    pagination={false}
                    dataSource={ruleRecords.map((r, i) => ({ ...r, key: r.id || i }))}
                    columns={recordColumns}
                    style={{ marginTop: 8 }}
                  />
                )
              ) : (
                <Text type="secondary" style={{ display: 'block', padding: '8px 0', fontSize: 12 }}>
                  暂无校准记录
                </Text>
              )}
            </div>
          )
        })}

        {recordsMap.get('ungrouped')?.length ? (
          <div className="ins-card" style={{ marginBottom: 12, padding: 12, background: '#f8fafc' }}>
            <div style={{ marginBottom: 8 }}>
              <Text strong style={{ fontSize: 13 }}>其他校准记录（未关联规则）</Text>
            </div>
            {isMobile ? (
              <div className="calibration-record-list">
                {recordsMap.get('ungrouped')?.map((r) => (
                  <div key={r.id || r.calibration_no} className="calibration-record-item">
                    <div className="calibration-record-header">
                      <span className="calibration-record-date">{r.calibration_date ? dayjs(r.calibration_date).format('YYYY-MM-DD') : '-'}</span>
                      <Tag color={resultOptions[r.calibration_result]?.color || 'default'}>{resultOptions[r.calibration_result]?.label || r.calibration_result}</Tag>
                    </div>
                    <div className="calibration-record-body">
                      <div className="calibration-record-row">
                        <span className="calibration-record-label">有效期至</span>
                        <span className={dayjs(r.valid_until).isBefore(dayjs()) ? 'calibration-record-value danger' : 'calibration-record-value'}>
                          {r.valid_until ? dayjs(r.valid_until).format('YYYY-MM-DD') : '-'}
                          {dayjs(r.valid_until).isBefore(dayjs()) && <span className="calibration-record-tag">已超期</span>}
                        </span>
                      </div>
                      {r.certificate_no && (
                        <div className="calibration-record-row">
                          <span className="calibration-record-label">证书编号</span>
                          <span className="calibration-record-value">{r.certificate_no}</span>
                        </div>
                      )}
                      <div className="calibration-record-row">
                        <span className="calibration-record-label">校准方法</span>
                        <span className="calibration-record-value">{methodOptions[r.calibration_method] || r.calibration_method}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Table
                size="small"
                pagination={false}
                dataSource={recordsMap.get('ungrouped')?.map((r, i) => ({ ...r, key: r.id || i }))}
                columns={recordColumns}
              />
            )}
          </div>
        ) : null}
      </div>

      <Modal
        title={`新增校准记录 - ${selectedRule?.calibration_method === 'external' ? '外委校准' : '内部校准'}`}
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        width={720}
        destroyOnHidden
        onOk={handleCreateSubmit}
        confirmLoading={submitLoading}
        okText="创建"
        cancelText="取消"
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="calibration_no" label="校准单据编号">
                <Input placeholder="不填则自动生成" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="calibration_date" label="校准日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="valid_period" label="有效期（月）" rules={[{ required: true }]}>
                <Input type="number" placeholder="请输入月数" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="calibration_method" label="校准方式" rules={[{ required: true }]}>
                <Select placeholder="请选择">
                  <Select.Option value="external">外委校准</Select.Option>
                  <Select.Option value="internal">内部校准</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="calibration_result" label="校准结论" rules={[{ required: true }]}>
                <Select placeholder="请选择">
                  <Select.Option value="qualified">合格</Select.Option>
                  <Select.Option value="unqualified">不合格</Select.Option>
                  <Select.Option value="limited">限用</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="calibration_agency" label="校准机构">
                <Input placeholder="请输入校准机构" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="calibrator_name" label="校准人员">
                <Input placeholder="请输入校准人员" />
              </Form.Item>
            </Col>
            <Col xs={24} sm={12}>
              <Form.Item name="certificate_no" label="证书编号">
                <Input placeholder="请输入证书编号" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col xs={24} sm={12}>
              <Form.Item name="calibration_end_date" label="校准结束日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="result_reason" label="结论说明">
                <Input.TextArea rows={2} placeholder="请输入结论说明" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={2} placeholder="请输入备注" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </>
  )
}

export default function InstrumentListPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<InstrumentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [expandedRowKeys, setExpandedRowKeys] = useState<string[]>([])
  const [isMobile, setIsMobile] = useState(false)
  const [viewMode, setViewMode] = useState<'table' | 'card'>('table')
  const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set())

  const [createDrawerVisible, setCreateDrawerVisible] = useState(false)
  const [createLoading, setCreateLoading] = useState(false)
  const [createForm] = Form.useForm()
  const [ruleForm] = Form.useForm()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [uploading, setUploading] = useState(false)
  const [recognizing, setRecognizing] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [recognizedData, setRecognizedData] = useState<AIRecognizedInstrumentInfo | null>(null)
  const [recognitionError, setRecognitionError] = useState<string | null>(null)

  const [filters, setFilters] = useState<{
    instrument_no?: string
    instrument_name?: string
    category?: string
  }>({})

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

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: InstrumentFilter = {
        page,
        page_size: pageSize,
      }
      if (filters.instrument_no) params.instrument_no = filters.instrument_no
      if (filters.instrument_name) params.instrument_name = filters.instrument_name
      if (filters.category) params.category = filters.category as InstrumentCategory

      const response = await getInstruments(params)
      setData(response.items || [])
      setTotal(response.total || 0)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '加载数据失败，请检查后端服务'
      setError(errorMsg)
      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, filters])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSearch = () => {
    setPage(1)
    loadData()
  }

  const handleReset = () => {
    setFilters({})
    setPage(1)
  }

  const toggleCardExpand = (id: string) => {
    setExpandedCards(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      message.error('请上传图片文件')
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      message.error('图片大小不能超过 10MB')
      return
    }

    setRecognitionError(null)
    setRecognizedData(null)

    const objectUrl = URL.createObjectURL(file)
    setPreviewUrl(objectUrl)

    setUploading(true)
    setRecognizing(true)

    try {
      const result = await recognizeInstrumentLabel(file)
      setRecognizedData(result)

      const formValues: Record<string, unknown> = {}
      const ruleValues: Record<string, unknown> = {}

      if (result.instrument_name) formValues.instrument_name = result.instrument_name
      if (result.model) formValues.model = result.model
      if (result.serial_no) formValues.serial_no = result.serial_no
      if (result.manufacturer) formValues.manufacturer = result.manufacturer
      if (result.last_calibration_date && dayjs(result.last_calibration_date).isValid()) {
        ruleValues.last_calibration_date = dayjs(result.last_calibration_date)
      }
      if (result.next_calibration_date && dayjs(result.next_calibration_date).isValid()) {
        ruleValues.next_calibration_date = dayjs(result.next_calibration_date)
      }
      if (result.calibration_agency) ruleValues.calibration_agency = result.calibration_agency

      if (Object.keys(formValues).length > 0) createForm.setFieldsValue(formValues)
      if (Object.keys(ruleValues).length > 0) ruleForm.setFieldsValue(ruleValues)

      message.success('识别完成，请核对结果')
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : '识别失败'
      setRecognitionError(errorMsg)
      message.error(errorMsg)
    } finally {
      setUploading(false)
      setRecognizing(false)
    }
  }

  const handleResetRecognition = () => {
    setPreviewUrl(null)
    setRecognizedData(null)
    setRecognitionError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleCreateSubmit = async () => {
    try {
      const values = await createForm.validateFields()
      const ruleValues = await ruleForm.validateFields()

      const instrumentData: InstrumentCreate = {
        instrument_no: values.instrument_no,
        instrument_name: values.instrument_name,
        model: values.model,
        serial_no: values.serial_no,
        manufacturer: values.manufacturer,
        location: values.location,
        category: values.category,
        manufacture_date: values.manufacture_date?.format('YYYY-MM-DD'),
        responsible_name: values.responsible_name,
        is_active: true,
        remark: values.remark,
      }

      setCreateLoading(true)

      const result = await createInstrument(instrumentData)

      if (ruleValues.calibration_method) {
        const ruleData: CalibrationRuleCreate = {
          instrument_id: result.id,
          calibration_method: ruleValues.calibration_method,
          calibration_cycle: ruleValues.calibration_cycle,
          calibration_unit: ruleValues.calibration_unit,
          last_calibration_date: ruleValues.last_calibration_date?.format('YYYY-MM-DD'),
          next_calibration_date: ruleValues.next_calibration_date?.format('YYYY-MM-DD'),
          calibration_agency: ruleValues.calibration_agency,
          internal_calibrator_name: ruleValues.internal_calibrator_name,
          warning_days: ruleValues.warning_days || 7,
          is_active: true,
        }
        await createCalibrationRule(ruleData)
      }

      message.success('创建成功')
      setCreateDrawerVisible(false)
      createForm.resetFields()
      ruleForm.resetFields()
      handleResetRecognition()
      loadData()
    } catch (error) {
      message.error('创建失败')
    } finally {
      setCreateLoading(false)
    }
  }

  const handleCreate = () => {
    createForm.resetFields()
    ruleForm.resetFields()
    handleResetRecognition()
    setCreateDrawerVisible(true)
  }

  const columns: TableColumnsType<InstrumentListItem> = [
    {
      title: '仪器编号',
      dataIndex: 'instrument_no',
      key: 'instrument_no',
      width: 130,
      render: (value: string) => (
        <Text style={{ fontFamily: 'SF Mono, Monaco, Cascadia Code, monospace', fontWeight: 600, color: '#4f46e5' }}>
          {value}
        </Text>
      ),
    },
    {
      title: '仪器名称',
      dataIndex: 'instrument_name',
      key: 'instrument_name',
      width: 160,
      ellipsis: true,
      render: (value: string) => <Text strong>{value}</Text>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 90,
      render: (value: string) => {
        const label = categoryOptions.find(o => o.value === value)?.label || value
        return <Tag color="blue">{label}</Tag>
      },
    },
    {
      title: '负责人',
      dataIndex: 'responsible_name',
      key: 'responsible_name',
      width: 100,
      render: (value: string) => value || '-',
    },
    {
      title: '下次校准',
      dataIndex: 'next_calibration_date',
      key: 'next_calibration_date',
      width: 120,
      render: (value: string) => {
        if (!value) return <Text type="secondary">-</Text>
        const isOverdue = dayjs(value).isBefore(dayjs())
        return (
          <Text type={isOverdue ? 'danger' : undefined} style={{ fontWeight: isOverdue ? 600 : 400 }}>
            {dayjs(value).format('YYYY-MM-DD')}
          </Text>
        )
      },
    },
    {
      title: '超期',
      dataIndex: 'is_overdue',
      key: 'is_overdue',
      width: 80,
      render: (value: boolean) => value ? <Tag color="red">是</Tag> : <Tag color="green">否</Tag>,
    },
    {
      title: '启用',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      render: (value: boolean) => value ? (
        <Tag color="success" icon={<CheckCircleOutlined />}>是</Tag>
      ) : (
        <Tag icon={<CloseCircleOutlined />}>否</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: InstrumentListItem) => (
        <Button
          type="link"
          size="small"
          icon={<EditOutlined />}
          onClick={() => router.push(`/quality/instrument/list/edit?id=${record.id}`)}
        >
          编辑
        </Button>
      ),
    },
  ]

  const renderInstrumentCard = (item: InstrumentListItem) => {
    const isExpanded = expandedCards.has(item.id)
    const isOverdue = item.is_overdue
    const nextDate = item.next_calibration_date
    const categoryLabel = categoryOptions.find(o => o.value === item.category)?.label || item.category || '-'

    return (
      <div key={item.id} className="instrument-card" style={{ marginBottom: 12 }}>
        <div className="instrument-card-header">
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="instrument-card-title">{item.instrument_name}</div>
            <div className="instrument-card-no">{item.instrument_no}</div>
          </div>
          <Space size={4} wrap>
            {isOverdue && <Tag color="red">超期</Tag>}
            {item.is_active ? (
              <Tag color="success">启用</Tag>
            ) : (
              <Tag>停用</Tag>
            )}
          </Space>
        </div>

        <div className="instrument-card-body">
          <div className="instrument-card-item">
            <div className="instrument-card-item-label">分类</div>
            <div className="instrument-card-item-value">
              <Tag color="blue" style={{ margin: 0 }}>{categoryLabel}</Tag>
            </div>
          </div>
          <div className="instrument-card-item">
            <div className="instrument-card-item-label">负责人</div>
            <div className="instrument-card-item-value">{item.responsible_name || '-'}</div>
          </div>
          <div className="instrument-card-item">
            <div className="instrument-card-item-label">下次校准</div>
            <div className="instrument-card-item-value">
              {nextDate ? (
                <Text type={isOverdue ? 'danger' : undefined} style={{ fontWeight: isOverdue ? 600 : 400 }}>
                  {dayjs(nextDate).format('YYYY-MM-DD')}
                </Text>
              ) : '-'}
            </div>
          </div>
          <div className="instrument-card-item">
            <div className="instrument-card-item-label">超期状态</div>
            <div className="instrument-card-item-value">
              {isOverdue ? <Tag color="red">是</Tag> : <Tag color="green">否</Tag>}
            </div>
          </div>
        </div>

        <div className="instrument-card-footer">
          <Space wrap size={8}>
            <Button
              size="small"
              type={isExpanded ? 'primary' : 'default'}
              icon={isExpanded ? <UpOutlined /> : <DownOutlined />}
              onClick={() => toggleCardExpand(item.id)}
            >
              {isExpanded ? '收起校准' : '查看校准'}
            </Button>
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => router.push(`/quality/instrument/list/edit?id=${item.id}`)}
            >
              编辑
            </Button>
          </Space>
        </div>

        {isExpanded && (
          <div className="instrument-expand-section" style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--ins-border)' }}>
            <ExpandedRow
              record={{ instrument: item, rules: [], recordsMap: new Map() }}
              onRefresh={loadData}
              isMobile={isMobile}
            />
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="instrument-page">
      <div className="instrument-toolbar">
        <div>
          <h1 style={{ fontSize: isMobile ? '18px' : '24px', fontWeight: 700, margin: 0, color: '#1f2937' }}>
            仪器设备台账
          </h1>
          <p style={{ fontSize: isMobile ? '12px' : '14px', color: '#6b7280', margin: '4px 0 0 0' }}>
            管理仪器设备信息，追踪校准周期与状态
          </p>
        </div>
        <Space wrap size={8}>
          {!isMobile && (
            <Space>
              <Button
                type={viewMode === 'table' ? 'primary' : 'default'}
                icon={<TableOutlined />}
                onClick={() => setViewMode('table')}
                size="small"
              >
                表格
              </Button>
              <Button
                type={viewMode === 'card' ? 'primary' : 'default'}
                icon={<AppstoreOutlined />}
                onClick={() => setViewMode('card')}
                size="small"
              >
                卡片
              </Button>
            </Space>
          )}
          <Button
            icon={<ReloadOutlined />}
            onClick={loadData}
            loading={loading}
            size={isMobile ? 'small' : 'middle'}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
            size={isMobile ? 'small' : 'middle'}
          >
            新增仪器
          </Button>
        </Space>
      </div>

      <div className="ins-card" style={{ padding: 16, marginBottom: 16 }}>
        <div className="records-search-area">
          <Input
            placeholder="仪器编号"
            value={filters.instrument_no}
            onChange={(e) => setFilters({ ...filters, instrument_no: e.target.value || undefined })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '160px' }}
            onPressEnter={handleSearch}
          />
          <Input
            placeholder="仪器名称"
            value={filters.instrument_name}
            onChange={(e) => setFilters({ ...filters, instrument_name: e.target.value || undefined })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '160px' }}
            onPressEnter={handleSearch}
          />
          <Select
            placeholder="仪器分类"
            value={filters.category}
            onChange={(value) => setFilters({ ...filters, category: value })}
            allowClear
            style={{ flex: isMobile ? '1' : 'auto', minWidth: isMobile ? '100%' : '140px' }}
          >
            {categoryOptions.map((opt) => (
              <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
            ))}
          </Select>
          <Space>
            <Button
              type="primary"
              icon={<SearchOutlined />}
              onClick={handleSearch}
              size={isMobile ? 'small' : 'middle'}
            >
              查询
            </Button>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleReset}
              size={isMobile ? 'small' : 'middle'}
            >
              重置
            </Button>
          </Space>
        </div>
      </div>

      {error ? (
        <div className="ins-card" style={{ padding: 48, textAlign: 'center' }}>
          <ExclamationCircleOutlined style={{ fontSize: 48, color: '#ef4444', marginBottom: 16 }} />
          <div style={{ marginBottom: 16 }}>
            <p style={{ color: '#475569', marginBottom: 8, fontSize: 15, fontWeight: 600 }}>数据加载失败</p>
            <p style={{ color: '#94a3b8', fontSize: 12 }}>{error}</p>
          </div>
          <Button type="primary" icon={<ReloadOutlined />} onClick={loadData}>
            重新加载
          </Button>
        </div>
      ) : (
        <Spin spinning={loading}>
          {viewMode === 'table' ? (
            <div className="ins-card" style={{ padding: 16 }}>
              <Table
                columns={columns}
                dataSource={data}
                rowKey="id"
                loading={loading}
                expandable={{
                  expandedRowKeys,
                  onExpand: (expanded, record) => {
                    setExpandedRowKeys(expanded ? [record.id] : [])
                  },
                  expandedRowRender: (record: InstrumentListItem) => (
                    <ExpandedRow
                      record={{ instrument: record, rules: [], recordsMap: new Map() }}
                      onRefresh={loadData}
                      isMobile={isMobile}
                    />
                  ),
                  rowExpandable: () => true,
                }}
                scroll={{ x: 960 }}
                locale={{
                  emptyText: loading ? '' : <Empty description="暂无数据" />,
                }}
                pagination={{
                  current: page,
                  pageSize: pageSize,
                  total: total,
                  showSizeChanger: !isMobile,
                  showQuickJumper: !isMobile,
                  showTotal: (t) => `共 ${t} 条`,
                  simple: isMobile,
                  onChange: (p, ps) => {
                    setPage(p)
                    setPageSize(ps)
                  },
                }}
              />
            </div>
          ) : (
            <>
              <div className="records-card-grid">
                {data.length > 0 ? (
                  data.map(renderInstrumentCard)
                ) : (
                  <div className="empty-state">
                    <Empty description="暂无数据" />
                  </div>
                )}
              </div>
              <div className="pagination-mobile">
                <span style={{ color: '#6b7280', fontSize: 13 }}>共 {total} 条</span>
                <Space>
                  <Button disabled={page === 1} onClick={() => setPage(page - 1)} size={isMobile ? 'small' : 'middle'}>
                    上一页
                  </Button>
                  <span style={{ color: '#1f2937', fontWeight: 600 }}>{page}</span>
                  <Button
                    disabled={page * pageSize >= total}
                    onClick={() => setPage(page + 1)}
                    size={isMobile ? 'small' : 'middle'}
                  >
                    下一页
                  </Button>
                </Space>
              </div>
            </>
          )}
        </Spin>
      )}

      <Drawer
        title="新增仪器"
        open={createDrawerVisible}
        onClose={() => {
          setCreateDrawerVisible(false)
          createForm.resetFields()
          ruleForm.resetFields()
          handleResetRecognition()
        }}
        width={isMobile ? '100%' : 900}
        className="instrument-drawer"
        styles={{ body: { paddingBottom: 80 } }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 2fr', gap: 16 }}>
          <div>
            <Divider plain style={{ margin: '0 0 12px 0', fontWeight: 600 }}>AI 图片识别</Divider>
            {!previewUrl ? (
              <div
                style={{
                  border: '2px dashed #d9d9d9',
                  borderRadius: 8,
                  padding: '32px 16px',
                  textAlign: 'center',
                  background: '#fafafa',
                  cursor: 'pointer',
                }}
                onClick={() => fileInputRef.current?.click()}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/jpg,image/webp"
                  style={{ display: 'none' }}
                  onChange={handleFileSelect}
                />
                <Spin spinning={uploading || recognizing} indicator={<LoadingOutlined spin />}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <CameraOutlined style={{ fontSize: 32, color: '#999' }} />
                    <p style={{ margin: 0, color: '#666', fontSize: 13 }}>
                      点击上传设备标签照片
                    </p>
                    <p style={{ margin: '4px 0 0', color: '#999', fontSize: 11 }}>
                      支持 JPG/PNG/WebP，最大 10MB
                    </p>
                  </div>
                </Spin>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                  <span style={{ fontWeight: 500, fontSize: 12 }}>已上传设备标签照片</span>
                  <Button type="link" size="small" onClick={handleResetRecognition}>
                    重新上传
                  </Button>
                </div>
                <img
                  src={previewUrl}
                  alt="设备标签预览"
                  style={{
                    maxWidth: '100%',
                    maxHeight: 150,
                    objectFit: 'contain',
                    display: 'block',
                    margin: '0 auto',
                    borderRadius: 4,
                  }}
                />
                {recognizedData && (
                  <div style={{ marginTop: 12, padding: 12, background: '#f0fdf4', borderRadius: 8 }}>
                    <p style={{ margin: 0, fontSize: 12, color: '#166534', fontWeight: 600 }}>识别结果已自动填充</p>
                  </div>
                )}
              </div>
            )}
          </div>

          <div style={{ overflowY: 'auto', maxHeight: isMobile ? '60vh' : 'calc(100vh - 200px)' }}>
            <Divider plain style={{ margin: '0 0 12px 0', fontWeight: 600 }}>基本信息</Divider>
            <Form form={createForm} layout="vertical">
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
                <Form.Item name="instrument_no" label="仪器编号" rules={[{ required: true }]}>
                  <Input placeholder="请输入仪器编号" />
                </Form.Item>
                <Form.Item name="instrument_name" label="仪器名称" rules={[{ required: true }]}>
                  <Input placeholder="请输入仪器名称" />
                </Form.Item>
                <Form.Item name="model" label="型号">
                  <Input placeholder="请输入型号" />
                </Form.Item>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
                <Form.Item name="serial_no" label="出厂编号">
                  <Input placeholder="请输入出厂编号" />
                </Form.Item>
                <Form.Item name="manufacturer" label="制造商">
                  <Input placeholder="请输入制造商" />
                </Form.Item>
                <Form.Item name="location" label="存放地点">
                  <Input placeholder="请输入存放地点" />
                </Form.Item>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
                <Form.Item name="category" label="仪器分类">
                  <Select placeholder="请选择分类">
                    {categoryOptions.map((opt) => (
                      <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
                <Form.Item name="responsible_name" label="使用负责人">
                  <Input placeholder="请输入负责人" />
                </Form.Item>
                <Form.Item name="manufacture_date" label="出厂日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
              </div>
              <Form.Item name="remark" label="备注">
                <Input.TextArea rows={2} placeholder="请输入备注" />
              </Form.Item>
            </Form>

            <Divider plain style={{ margin: '16px 0 12px 0', fontWeight: 600 }}>校准规则（可选）</Divider>
            <Form form={ruleForm} layout="vertical" initialValues={{ warning_days: 7 }}>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
                <Form.Item name="calibration_method" label="校准方式">
                  <Select placeholder="请选择" allowClear>
                    <Select.Option value="external">外委校准</Select.Option>
                    <Select.Option value="internal">内部校准</Select.Option>
                  </Select>
                </Form.Item>
                <Form.Item name="calibration_cycle" label="校准周期">
                  <InputNumber style={{ width: '100%' }} min={0} placeholder="请输入周期" />
                </Form.Item>
                <Form.Item name="calibration_unit" label="周期单位">
                  <Select placeholder="请选择" allowClear>
                    {unitOptions.map((opt) => (
                      <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: 12 }}>
                <Form.Item name="last_calibration_date" label="最近校准日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item name="next_calibration_date" label="下次校准日期">
                  <DatePicker style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item name="warning_days" label="提前预警天数">
                  <InputNumber style={{ width: '100%' }} min={0} />
                </Form.Item>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr', gap: 12 }}>
                <Form.Item name="calibration_agency" label="校准机构">
                  <Input placeholder="请输入校准机构" />
                </Form.Item>
                <Form.Item name="internal_calibrator_name" label="内校人员">
                  <Input placeholder="请输入内校人员" />
                </Form.Item>
              </div>
            </Form>
          </div>
        </div>

        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, padding: 16, background: '#fff', borderTop: '1px solid #e5e7eb' }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={() => {
              setCreateDrawerVisible(false)
              createForm.resetFields()
              ruleForm.resetFields()
              handleResetRecognition()
            }}>取消</Button>
            <Button type="primary" icon={<SaveOutlined />} onClick={handleCreateSubmit} loading={createLoading}>保存</Button>
          </Space>
        </div>
      </Drawer>
    </div>
  )
}
