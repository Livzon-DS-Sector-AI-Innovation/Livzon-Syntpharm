'use client'

import React, { useState, useEffect } from 'react'
import {
  Tabs,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  DatePicker,
  Space,
  Tag,
  Card,
  Row,
  Col,
  Statistic,
  message,
  Popconfirm,
  Divider,
  Alert,
  Tooltip,
  Spin,
  Steps,
  Descriptions,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckOutlined,
  CloseOutlined,
  LockOutlined,
  UnlockOutlined,
  FileTextOutlined,
  SafetyOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
  RobotOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import jsPDF from 'jspdf'
import {
  Deviation,
  deviationTypeLabels,
  deviationLevelLabels,
  deviationStatusLabels,
  getStatusColor,
  DeviationStatistics,
} from '@/types/deviation'
import * as deviationActions from '@/actions/deviation'

const { TextArea } = Input

// 部门列表
const DEPARTMENT_LIST = [
  '生产部', '质量部', '工程部', '仓储部', '采购部', '研发部', '人事部', '设备部'
]

// ============ GMP免责声明组件 ============
const GMPDisclaimer: React.FC = () => (
  <Alert
    message="GMP合规提示"
    description="AI生成内容仅供参考，最终以人工审核确认。生成的描述和分析需符合企业SOP及GMP法规要求，人工对最终内容的合规性和完整性负责。"
    type="warning"
    showIcon
    icon={<WarningOutlined />}
    style={{ marginBottom: 16 }}
  />
)

// ============ AI辅助按钮组件 ============
interface AIButtonProps {
  label: string
  loading: boolean
  onClick: () => void
  tooltip?: string
}

const AIButton: React.FC<AIButtonProps> = ({ label, loading, onClick, tooltip }) => (
  <Tooltip title={tooltip || '点击使用AI辅助生成'}>
    <Button
      type="link"
      size="small"
      icon={<RobotOutlined spin={loading} />}
      loading={loading}
      onClick={onClick}
      style={{ padding: '0 4px', height: 'auto', color: '#1890ff' }}
    >
      {label}
    </Button>
  </Tooltip>
)

// ============ AI结果弹窗组件 ============
interface AIResultModalProps {
  open: boolean
  onClose: () => void
  onApply: () => void
  title: string
  result: string
  loading: boolean
}

const AIResultModal: React.FC<AIResultModalProps> = ({
  open,
  onClose,
  onApply,
  title,
  result,
  loading
}) => (
  <Modal
    title={<Space><RobotOutlined /> {title}</Space>}
    open={open}
    onCancel={onClose}
    footer={[
      <Button key="close" onClick={onClose}>关闭</Button>,
      <Button key="apply" type="primary" onClick={onApply}>应用到表单</Button>
    ]}
    width={700}
  >
    {loading ? (
      <div style={{ textAlign: 'center', padding: 40 }}>
        <Spin tip="AI正在生成中，请稍候..." />
      </div>
    ) : (
      <div>
        <Alert
          message="免责声明"
          description="以下内容由AI辅助生成，仅供参考，最终以人工审核确认。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <div style={{
          whiteSpace: 'pre-wrap',
          lineHeight: 1.8,
          padding: 16,
          background: '#f5f5f5',
          borderRadius: 8,
          maxHeight: 400,
          overflow: 'auto'
        }}>
          {result}
        </div>
      </div>
    )}
  </Modal>
)

// ============ 偏差列表标签页 ============
const DeviationListTab: React.FC<{
  onView: (deviation: Deviation) => void
  onRefresh: () => void
}> = ({ onView, onRefresh }) => {
  const [loading, setLoading] = useState(false)
  const [deviations, setDeviations] = useState<Deviation[]>([])
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 })
  const [searchForm] = Form.useForm()
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [createForm] = Form.useForm()
  const [aiLoading, setAiLoading] = useState(false)
  const [aiModalVisible, setAiModalVisible] = useState(false)
  const [aiModalTitle, setAiModalTitle] = useState('')
  const [aiResult, setAiResult] = useState('')
  const [aiTargetField, setAiTargetField] = useState('')

  const fetchDeviations = async (values?: any) => {
    setLoading(true)
    try {
      const result = await deviationActions.getDeviations({
        deviation_type: values?.deviation_type,
        status: values?.status,
        start_date: values?.date_range?.[0]?.format('YYYY-MM-DD'),
        end_date: values?.date_range?.[1]?.format('YYYY-MM-DD'),
        page: pagination.current,
        page_size: pagination.pageSize,
      })
      const data = result.data || result
      setDeviations(data.items || [])
      setPagination(prev => ({ ...prev, total: data.total || 0 }))
    } catch (error: any) {
      message.error(error.message || '获取偏差列表失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDeviations()
  }, [pagination.current, pagination.pageSize])

  // AI生成偏差描述（基于完整表单数据）
  const handleAIGenerateDescription = async () => {
    const values = createForm.getFieldsValue()
    if (!values.keywords) {
      message.warning('请先输入关键词描述')
      return
    }
    setAiLoading(true)
    setAiModalTitle('偏差描述生成')
    setAiTargetField('description')
    try {
      const result = await deviationActions.aiGenerateDescription({
        deviation_type: values.deviation_type,
        deviation_level: values.deviation_level,
        occurrence_date: values.occurrence_date?.format('YYYY-MM-DD'),
        discovering_department: values.discovering_department,
        product_name: values.product_name,
        production_batch: values.production_batch,
        keywords: values.keywords,
      })
      const data = result.data || result
      setAiResult(data.description || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI生成失败')
    } finally {
      setAiLoading(false)
    }
  }

  // AI分析影响范围（基于完整表单数据）
  const handleAIAnalyzeImpact = async () => {
    const values = createForm.getFieldsValue()
    if (!values.deviation_type && !values.description) {
      message.warning('请先填写偏差类型或偏差描述')
      return
    }
    setAiLoading(true)
    setAiModalTitle('影响范围分析')
    setAiTargetField('impact_scope')
    try {
      const result = await deviationActions.aiAnalyzeImpact({
        deviation_type: values.deviation_type,
        deviation_level: values.deviation_level,
        occurrence_date: values.occurrence_date?.format('YYYY-MM-DD'),
        discovering_department: values.discovering_department,
        product_name: values.product_name,
        production_batch: values.production_batch,
        description: values.description,
      })
      const data = result.data || result
      setAiResult(data.impact_analysis || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI分析失败')
    } finally {
      setAiLoading(false)
    }
  }

  // AI生成应急措施（基于完整表单数据）
  const handleAIGenerateEmergency = async () => {
    const values = createForm.getFieldsValue()
    if (!values.deviation_type && !values.description) {
      message.warning('请先填写偏差类型或偏差描述')
      return
    }
    setAiLoading(true)
    setAiModalTitle('应急措施生成')
    setAiTargetField('emergency_measures')
    try {
      const result = await deviationActions.aiGenerateEmergencyMeasures({
        deviation_type: values.deviation_type,
        deviation_level: values.deviation_level,
        occurrence_date: values.occurrence_date?.format('YYYY-MM-DD'),
        discovering_department: values.discovering_department,
        product_name: values.product_name,
        production_batch: values.production_batch,
        description: values.description,
      })
      const data = result.data || result
      setAiResult(data.emergency_measures || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI生成失败')
    } finally {
      setAiLoading(false)
    }
  }

  // 应用AI结果到表单
  const applyAiResult = () => {
    if (aiResult) {
      createForm.setFieldValue(aiTargetField, aiResult)
      setAiModalVisible(false)
      message.success('已应用到表单')
    }
  }

  const handleCreate = async (values: any) => {
    try {
      const processedValues = {
        ...values,
        // 映射前端字段名到后端字段名
        abnormal_description: values.description,
        occurrence_date: values.occurrence_date?.format('YYYY-MM-DD'),
      }
      // 删除不需要的字段
      delete processedValues.description
      await deviationActions.createDeviation(processedValues)
      message.success('创建成功')
      setCreateModalVisible(false)
      createForm.resetFields()
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '创建失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deviationActions.deleteDeviation(id)
      message.success('删除成功')
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleSubmit = async (id: string) => {
    try {
      await deviationActions.submitDeviation(id)
      message.success('提交成功，偏差已进入调查流程')
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '提交失败')
    }
  }

  const columns: ColumnsType<Deviation> = [
    {
      title: '偏差编号',
      dataIndex: 'deviation_no',
      width: 150,
      render: (no: string, record) => (
        <a onClick={() => onView(record)}>{no}</a>
      ),
    },
    {
      title: '偏差类型',
      dataIndex: 'deviation_type',
      width: 100,
      render: (type) => deviationTypeLabels[type] || type,
    },
    {
      title: '偏差级别',
      dataIndex: 'deviation_level',
      width: 80,
      render: (level) => (
        <Tag color={level === 'critical' ? 'red' : level === 'major' ? 'orange' : 'blue'}>
          {deviationLevelLabels[level] || level}
        </Tag>
      ),
    },
    {
      title: '发生日期',
      dataIndex: 'occurrence_date',
      width: 120,
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '涉及批次',
      dataIndex: 'production_batch',
      width: 120,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)}>{deviationStatusLabels[status] || status}</Tag>
      ),
    },
    {
      title: '批次锁定',
      dataIndex: 'batch_locked',
      width: 100,
      render: (locked) => locked ? (
        <Tag color="red" icon={<LockOutlined />}>已锁定</Tag>
      ) : <Tag>未锁定</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => onView(record)}>
            查看
          </Button>
          {record.status === 'draft' && (
            <>
              <Popconfirm title="确认提交？" description="提交后将进入偏差调查流程" onConfirm={() => handleSubmit(record.id)}>
                <Button type="link" size="small" icon={<CheckOutlined />} style={{ color: '#52c41a' }}>
                  提交
                </Button>
              </Popconfirm>
              <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Form form={searchForm} layout="inline" onFinish={() => {
          setPagination(prev => ({ ...prev, current: 1 }))
          fetchDeviations(searchForm.getFieldsValue())
        }}>
          <Form.Item name="deviation_type" label="偏差类型">
            <Select allowClear style={{ width: 120 }}>
              {Object.entries(deviationTypeLabels).map(([value, label]) => (
                <Select.Option key={value} value={value}>{label}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="status" label="状态">
            <Select allowClear style={{ width: 120 }}>
              {Object.entries(deviationStatusLabels).map(([value, label]) => (
                <Select.Option key={value} value={value}>{label}</Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="date_range" label="日期范围">
            <DatePicker.RangePicker />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} htmlType="submit">查询</Button>
              <Button onClick={() => { searchForm.resetFields(); fetchDeviations() }}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>

      <Card size="small">
        <Space style={{ marginBottom: 16 }}>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
            发起偏差
          </Button>
        </Space>

        <Table
          columns={columns}
          dataSource={deviations}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1200 }}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (page, pageSize) => setPagination({ current: page, pageSize, total: pagination.total }),
          }}
        />
      </Card>

      {/* 发起偏差弹窗 */}
      <Modal
        title={<Space><FileTextOutlined /> 发起偏差</Space>}
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={800}
      >
        <GMPDisclaimer />
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="deviation_type" label="偏差类型" rules={[{ required: true }]}>
                <Select>
                  {Object.entries(deviationTypeLabels).map(([value, label]) => (
                    <Select.Option key={value} value={value}>{label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="deviation_level" label="偏差级别" rules={[{ required: true }]}>
                <Select>
                  {Object.entries(deviationLevelLabels).map(([value, label]) => (
                    <Select.Option key={value} value={value}>{label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="occurrence_date" label="发生日期" rules={[{ required: true }]}>
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="discovering_department" label="发现部门">
                <Select>
                  {DEPARTMENT_LIST.map(dept => (
                    <Select.Option key={dept} value={dept}>{dept}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="product_name" label="产品/物料名称">
                <Input placeholder="输入产品或物料名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="production_batch" label="生产批次">
                <Input placeholder="输入批次号" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            name="keywords"
            label={
              <Space>
                <span>关键词描述</span>
                <AIButton
                  label="AI扩展"
                  loading={aiLoading}
                  onClick={handleAIGenerateDescription}
                  tooltip="输入简短关键词，AI自动扩写为标准偏差描述"
                />
              </Space>
            }
          >
            <Input placeholder="简述偏差现象，如：HPLC出峰异常、检测结果超标" />
          </Form.Item>
          <Form.Item
            name="description"
            label={
              <Space>
                <span>偏差现象描述</span>
                <AIButton
                  label="AI生成"
                  loading={aiLoading}
                  onClick={handleAIGenerateDescription}
                  tooltip="点击使用AI辅助生成标准偏差描述"
                />
              </Space>
            }
          >
            <TextArea rows={4} placeholder="详细描述偏差现象，包括时间、地点、具体表现等" />
          </Form.Item>
          <Form.Item
            name="impact_scope"
            label={
              <Space>
                <span>影响范围</span>
                <AIButton
                  label="AI分析"
                  loading={aiLoading}
                  onClick={handleAIAnalyzeImpact}
                  tooltip="基于偏差类型和批次信息，AI自动分析影响范围"
                />
              </Space>
            }
          >
            <TextArea rows={3} placeholder="分析偏差对产品质量、批次、检验项目等的影响范围" />
          </Form.Item>
          <Form.Item
            name="emergency_measures"
            label={
              <Space>
                <span>应急措施</span>
                <AIButton
                  label="AI生成"
                  loading={aiLoading}
                  onClick={handleAIGenerateEmergency}
                  tooltip="根据偏差类型自动生成合规的应急处置方案"
                />
              </Space>
            }
          >
            <TextArea rows={3} placeholder="已采取或建议采取的应急措施" />
          </Form.Item>
          <Row justify="end">
            <Space>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">提交偏差</Button>
            </Space>
          </Row>
        </Form>
      </Modal>

      {/* AI结果弹窗 */}
      <AIResultModal
        open={aiModalVisible}
        onClose={() => setAiModalVisible(false)}
        onApply={applyAiResult}
        title={aiModalTitle}
        result={aiResult}
        loading={aiLoading}
      />
    </div>
  )
}

// ============ 偏差调查标签页 ============
const InvestigationTab: React.FC<{ onRefresh: () => void }> = ({ onRefresh }) => {
  const [loading, setLoading] = useState(false)
  const [deviations, setDeviations] = useState<Deviation[]>([])
  const [aiLoading, setAiLoading] = useState(false)
  const [aiModalVisible, setAiModalVisible] = useState(false)
  const [aiModalTitle, setAiModalTitle] = useState('')
  const [aiResult, setAiResult] = useState('')
  const [aiTargetField, setAiTargetField] = useState('')
  const [form] = Form.useForm()

  useEffect(() => {
    fetchDeviations()
  }, [])

  const fetchDeviations = async () => {
    setLoading(true)
    try {
      const result = await deviationActions.getDeviations({ page_size: 100 })
      const data = result.data || result
      const list = (data.items || []).filter((d: Deviation) =>
        d.status === 'submitted' || d.status === 'investigating'
      )
      setDeviations(list)
    } catch (error: any) {
      message.error(error.message || '获取偏差列表失败')
    } finally {
      setLoading(false)
    }
  }

  // AI直接原因分析
  const handleAIDirectCauseAnalysis = async () => {
    const values = form.getFieldsValue()
    if (!values.deviation_id) {
      message.warning('请先选择偏差')
      return
    }
    setAiLoading(true)
    setAiModalTitle('直接原因分析')
    setAiTargetField('direct_cause')
    try {
      const result = await deviationActions.aiAnalyzeDirectCause({
        deviation_type: 'general',
        description: values.description,
        product_name: values.product_name,
        production_batch: values.production_batch,
      })
      const data = result.data || result
      setAiResult(data.direct_cause_analysis || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI分析失败')
    } finally {
      setAiLoading(false)
    }
  }

  // AI根因分析（5M1E）
  const handleAIRootCauseAnalysis = async () => {
    const values = form.getFieldsValue()
    if (!values.deviation_id) {
      message.warning('请先选择偏差')
      return
    }
    setAiLoading(true)
    setAiModalTitle('根本原因分析（5M1E）')
    setAiTargetField('root_cause')
    try {
      const deviation = deviations.find(d => d.id === values.deviation_id)
      const result = await deviationActions.aiAnalyzeRootCause({
        deviation_type: deviation?.deviation_type || 'general',
        description: values.description || deviation?.description,
        direct_cause: values.direct_cause,
      })
      const data = result.data || result
      setAiResult(data.root_cause_analysis || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI分析失败')
    } finally {
      setAiLoading(false)
    }
  }

  // AI影响评估
  const handleAIImpactAssessment = async () => {
    const values = form.getFieldsValue()
    if (!values.deviation_id) {
      message.warning('请先选择偏差')
      return
    }
    setAiLoading(true)
    setAiModalTitle('影响评估')
    setAiTargetField('impact_assessment')
    try {
      const deviation = deviations.find(d => d.id === values.deviation_id)
      const result = await deviationActions.aiAnalyzeImpact({
        deviation_type: deviation?.deviation_type || 'general',
        product_name: deviation?.product_name,
        production_batch: deviation?.production_batch,
        description: values.description || deviation?.description,
      })
      const data = result.data || result
      setAiResult(data.impact_analysis || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI分析失败')
    } finally {
      setAiLoading(false)
    }
  }

  const applyAiResult = () => {
    if (aiResult) {
      form.setFieldValue(aiTargetField, aiResult)
      setAiModalVisible(false)
      message.success('已应用到表单')
    }
  }

  const columns: ColumnsType<Deviation> = [
    {
      title: '偏差编号',
      dataIndex: 'deviation_no',
      width: 150,
    },
    {
      title: '偏差类型',
      dataIndex: 'deviation_type',
      width: 100,
      render: (type) => deviationTypeLabels[type] || type,
    },
    {
      title: '偏差级别',
      dataIndex: 'deviation_level',
      width: 80,
      render: (level) => (
        <Tag color={level === 'critical' ? 'red' : level === 'major' ? 'orange' : 'blue'}>
          {deviationLevelLabels[level] || level}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)}>{deviationStatusLabels[status] || status}</Tag>
      ),
    },
    {
      title: '偏差描述',
      dataIndex: 'description',
      ellipsis: true,
      render: (text: string) => (
        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
          {text || '-'}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: Deviation) => (
        <Space size={2}>
          <Tooltip title="查看">
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewDeviation(record)} style={{ padding: '0 4px' }} />
          </Tooltip>
          <Tooltip title="编辑">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditDeviation(record)} style={{ padding: '0 4px' }} />
          </Tooltip>
          <Tooltip title="完成调查">
            <Button type="link" size="small" icon={<CheckOutlined />} onClick={() => handleQuickComplete(record)} style={{ color: '#52c41a', padding: '0 4px' }} />
          </Tooltip>
        </Space>
      ),
    },
  ]

  // 查看偏差详情
  const handleViewDeviation = async (record: Deviation) => {
    // 获取完整详细信息后填充表单
    try {
      const result = await deviationActions.getDeviationById(record.id)
      if (result.code === 200 && result.data) {
        const deviation = result.data.deviation
        const investigation = result.data.investigation
        form.setFieldsValue({
          deviation_id: record.id,
          description: deviation.abnormal_description || deviation.description || '',
          direct_cause: investigation?.direct_cause || '',
          root_cause: investigation?.root_cause || '',
          investigation_conclusion: investigation?.investigation_conclusion || '',
        })
        message.info('查看偏差详情：请在表单中查看已填充的偏差信息')
      }
    } catch (error) {
      console.error('获取偏差详情失败:', error)
      message.error('获取偏差详情失败')
    }
  }

  // 编辑偏差
  const handleEditDeviation = async (record: Deviation) => {
    // 填充表单并获取详细信息
    form.setFieldValue('deviation_id', record.id)
    await handleSelectDeviation(record.id)
    message.info('已加载偏差信息，可进行编辑')
  }

  // 快速完成调查
  const handleQuickComplete = async (record: Deviation) => {
    Modal.confirm({
      title: '确认完成调查',
      content: `确定要完成偏差 ${record.deviation_no} 的调查吗？`,
      onOk: async () => {
        try {
          // 获取最新数据
          const result = await deviationActions.getDeviationById(record.id)
          if (result.code === 200 && result.data) {
            const deviation = result.data.deviation
            const investigation = result.data.investigation
            await deviationActions.updateDeviation(record.id, {
              status: 'investigation_completed',
              description: deviation.abnormal_description || deviation.description,
              investigation: {
                direct_cause: investigation?.direct_cause || '',
                root_cause: investigation?.root_cause || '',
                investigation_conclusion: investigation?.investigation_conclusion || '',
              },
            })
            message.success('调查已完成')
            fetchDeviations()
            onRefresh()
          }
        } catch (error: any) {
          message.error(error.message || '操作失败')
        }
      },
    })
  }

  // 处理选择偏差后的数据回填
  const handleSelectDeviation = async (deviationId: string) => {
    try {
      const result = await deviationActions.getDeviationById(deviationId)
      if (result.code === 200 && result.data) {
        const deviation = result.data.deviation
        const investigation = result.data.investigation
        form.setFieldsValue({
          description: deviation.abnormal_description || deviation.description || '',
          direct_cause: investigation?.direct_cause || '',
          root_cause: investigation?.root_cause || '',
          investigation_conclusion: investigation?.investigation_conclusion || '',
        })
      }
    } catch (error) {
      console.error('获取偏差详情失败:', error)
      message.error('获取偏差详情失败')
    }
  }

  // AI生成调查结论
  const handleAIConclusion = async () => {
    const values = form.getFieldsValue()
    if (!values.deviation_id) {
      message.warning('请先选择偏差')
      return
    }
    if (!values.direct_cause || !values.root_cause) {
      message.warning('请先完成直接原因和根本原因分析')
      return
    }
    setAiLoading(true)
    setAiModalTitle('调查结论生成')
    setAiTargetField('investigation_conclusion')
    try {
      const deviation = deviations.find(d => d.id === values.deviation_id)
      const result = await deviationActions.aiAnalyzeRootCause({
        deviation_type: deviation?.deviation_type || 'general',
        description: values.description || deviation?.description,
        direct_cause: values.direct_cause,
        root_cause: values.root_cause,
      })
      const data = result.data || result
      // 生成调查结论
      const conclusion = `基于对偏差的全面调查分析：

直接原因：${values.direct_cause}

根本原因（5M1E分析）：${values.root_cause}

调查结论：${data.root_cause_analysis || '经过系统分析，该偏差的根本原因已明确，建议采取相应的纠正和预防措施。'}`
      setAiResult(conclusion)
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI生成失败')
    } finally {
      setAiLoading(false)
    }
  }

  // 保存调查
  const handleSaveInvestigation = async () => {
    try {
      const values = form.getFieldsValue()
      if (!values.deviation_id) {
        message.warning('请先选择偏差')
        return
      }
      await deviationActions.updateDeviation(values.deviation_id, {
        description: values.description,
        investigation: {
          direct_cause: values.direct_cause,
          root_cause: values.root_cause,
          investigation_conclusion: values.investigation_conclusion,
        },
      })
      message.success('保存成功')
      // 刷新列表以显示更新后的数据
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '保存失败')
    }
  }

  // 完成调查
  const handleCompleteInvestigation = async () => {
    try {
      const values = form.getFieldsValue()
      if (!values.deviation_id) {
        message.warning('请先选择偏差')
        return
      }
      await deviationActions.updateDeviation(values.deviation_id, {
        status: 'investigation_completed',
        description: values.description,
        investigation: {
          direct_cause: values.direct_cause,
          root_cause: values.root_cause,
          investigation_conclusion: values.investigation_conclusion,
        },
      })
      message.success('调查已完成，可进入CAPA整改流程')
      form.resetFields()
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '操作失败')
    }
  }

  return (
    <div>
      <GMPDisclaimer />
      <Alert
        message="偏差调查说明"
        description="对已提交的偏差进行调查，使用5M1E方法分析根本原因，形成调查结论。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 偏差选择 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Form.Item name="deviation_id" label="选择偏差" rules={[{ required: true, message: '请选择要调查的偏差' }]}>
            <Select
              placeholder="请选择偏差"
              onChange={handleSelectDeviation}
              showSearch
              optionFilterProp="children"
            >
              {deviations.map(d => (
                <Select.Option key={d.id} value={d.id}>
                  {d.deviation_no} - {deviationTypeLabels[d.deviation_type]} ({deviationStatusLabels[d.status]})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Card>

      {/* 调查表单 */}
      <Card title="调查信息" size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="description" label="偏差描述">
                <TextArea rows={3} placeholder="偏差描述信息（选择偏差后自动填充）" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="direct_cause"
                label={
                  <Space>
                    <span>直接原因</span>
                    <AIButton
                      label="AI分析"
                      loading={aiLoading}
                      onClick={handleAIDirectCauseAnalysis}
                      tooltip="使用AI分析直接原因"
                    />
                  </Space>
                }
              >
                <TextArea rows={2} placeholder="分析直接原因（可点击AI分析辅助生成）" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="root_cause"
                label={
                  <Space>
                    <span>根本原因（5M1E分析）</span>
                    <Tag color="blue">人机料法环测</Tag>
                    <AIButton
                      label="AI分析"
                      loading={aiLoading}
                      onClick={handleAIRootCauseAnalysis}
                      tooltip="使用5M1E方法分析根本原因"
                    />
                  </Space>
                }
              >
                <TextArea rows={3} placeholder="使用5M1E方法分析根本原因：人(Man)、机(Machine)、料(Material)、法(Method)、环(Environment)、测(Measurement)（选择偏差后自动填充）" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="investigation_conclusion"
                label={
                  <Space>
                    <span>调查结论</span>
                    <AIButton
                      label="AI生成"
                      loading={aiLoading}
                      onClick={handleAIConclusion}
                      tooltip="根据直接原因和根本原因自动生成调查结论"
                    />
                  </Space>
                }
              >
                <TextArea rows={3} placeholder="填写调查结论" />
              </Form.Item>
            </Col>
          </Row>

          <Row justify="end">
            <Space>
              <Button onClick={() => form.resetFields()}>重置</Button>
              <Button type="primary" onClick={handleSaveInvestigation}>保存调查</Button>
              <Button type="primary" icon={<CheckOutlined />} onClick={handleCompleteInvestigation} style={{ backgroundColor: '#52c41a' }}>
                完成调查
              </Button>
            </Space>
          </Row>
        </Form>
      </Card>

      {/* 偏差列表 */}
      <Card title="待调查偏差列表" size="small">
        <Table
          columns={columns}
          dataSource={deviations}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 5 }}
          size="small"
        />
      </Card>

      <AIResultModal
        open={aiModalVisible}
        onClose={() => setAiModalVisible(false)}
        onApply={applyAiResult}
        title={aiModalTitle}
        result={aiResult}
        loading={aiLoading}
      />
    </div>
  )
}

// ============ CAPA整改标签页 ============
const CAPATab: React.FC<{ onRefresh: () => void }> = ({ onRefresh }) => {
  const [loading, setLoading] = useState(false)
  const [deviations, setDeviations] = useState<Deviation[]>([])
  const [completedDeviations, setCompletedDeviations] = useState<Deviation[]>([])
  const [aiLoading, setAiLoading] = useState(false)
  const [aiModalVisible, setAiModalVisible] = useState(false)
  const [aiModalTitle, setAiModalTitle] = useState('')
  const [aiResult, setAiResult] = useState('')
  const [aiTargetField, setAiTargetField] = useState('')
  const [form] = Form.useForm()
  const [activeTab, setActiveTab] = useState('pending')
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedDeviation, setSelectedDeviation] = useState<any>(null)
  const [reportGenerating, setReportGenerating] = useState(false)
  const [completeCorrectionModalVisible, setCompleteCorrectionModalVisible] = useState(false)
  const [completeForm] = Form.useForm()

  useEffect(() => {
    fetchDeviations()
  }, [])

  const fetchDeviations = async () => {
    setLoading(true)
    try {
      const result = await deviationActions.getDeviations({ page_size: 100 })
      const data = result.data || result
      // 待整改列表
      const pendingList = (data.items || []).filter((d: Deviation) =>
        d.status === 'investigation_completed' || d.status === 'correction_pending' || d.status === 'correction_in_progress'
      )
      // 已完成整改列表
      const completedList = (data.items || []).filter((d: Deviation) =>
        d.status === 'correction_completed' || d.status === 'closed'
      )
      setDeviations(pendingList)
      setCompletedDeviations(completedList)
    } catch (error: any) {
      message.error(error.message || '获取偏差列表失败')
    } finally {
      setLoading(false)
    }
  }

  // 查看已完成整改偏差详情
  const handleViewCompleted = async (record: Deviation) => {
    try {
      const result = await deviationActions.getDeviationById(record.id)
      if (result.code === 200 && result.data) {
        setSelectedDeviation(result.data)
        setDetailModalVisible(true)
      }
    } catch (error: any) {
      message.error(error.message || '获取详情失败')
    }
  }

  // 生成整改报告 - jsPDF原生绘制 + 中文字体
  const handleGenerateReport = async () => {
    if (!selectedDeviation) return
    setReportGenerating(true)
    try {
      const deviation = selectedDeviation.deviation
      const investigation = selectedDeviation.investigation
      const correction = selectedDeviation.correction

      // 创建PDF
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4'
      })

      const pageWidth = pdf.internal.pageSize.getWidth()
      const pageHeight = pdf.internal.pageSize.getHeight()
      const marginLeft = 20
      const marginRight = 20
      const marginTop = 20
      const marginBottom = 25
      const contentWidth = pageWidth - marginLeft - marginRight

      // 加载中文字体
      const fontUrl = '/fonts/simhei.ttf'
      const fontResponse = await fetch(fontUrl)
      const fontBuffer = await fontResponse.arrayBuffer()
      const fontBase64 = btoa(
        new Uint8Array(fontBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      )

      // 添加字体到PDF
      pdf.addFileToVFS('SimHei.ttf', fontBase64)
      pdf.addFont('SimHei.ttf', 'SimHei', 'normal')
      pdf.addFont('SimHei.ttf', 'SimHei', 'bold')

      // 设置字体
      pdf.setFont('SimHei')

      let currentY = marginTop
      let pageNum = 1

      // 辅助函数：绘制横线
      const drawLine = (y: number) => {
        pdf.setDrawColor(200, 200, 200)
        pdf.setLineWidth(0.3)
        pdf.line(marginLeft, y, pageWidth - marginRight, y)
      }

      // 辅助函数：添加页码
      const addPageNumber = (num: number) => {
        const lineY = pageHeight - 8
        pdf.setDrawColor(150, 150, 150)
        pdf.setLineWidth(0.3)
        pdf.line(marginLeft, lineY - 2, pageWidth - marginRight, lineY - 2)
        pdf.setFontSize(9)
        pdf.setTextColor(100, 100, 100)
        pdf.text(`第 ${num} 页`, pageWidth / 2, lineY, { align: 'center' })
      }

      // 辅助函数：添加续页页头
      const addContinuationHeader = () => {
        // 页头标题位置
        pdf.setFontSize(9)
        pdf.setTextColor(120, 120, 120)
        pdf.text(`偏差整改报告 - ${deviation.deviation_no || '未填写'}`, marginLeft, marginTop + 5)
        // 页头下方横线
        pdf.setDrawColor(180, 180, 180)
        pdf.setLineWidth(0.4)
        pdf.line(marginLeft, marginTop + 8, pageWidth - marginRight, marginTop + 8)
        // 内容从横线下方开始
        currentY = marginTop + 14
      }

      // 辅助函数：检查分页
      const checkPageBreak = (neededHeight: number) => {
        if (currentY + neededHeight > pageHeight - marginBottom) {
          addPageNumber(pageNum)
          pdf.addPage()
          pageNum++
          currentY = marginTop
          addContinuationHeader()
          return true
        }
        return false
      }

      // 辅助函数：绘制标题
      const drawTitle = (text: string) => {
        checkPageBreak(16)
        pdf.setFontSize(18)
        pdf.setTextColor(51, 51, 51)
        pdf.setFont('SimHei', 'bold')
        pdf.text(text, pageWidth / 2, currentY, { align: 'center' })
        currentY += 8
      }

      // 辅助函数：绘制分隔线
      const drawDivider = () => {
        pdf.setDrawColor(51, 51, 51)
        pdf.setLineWidth(1)
        pdf.line(marginLeft, currentY, pageWidth - marginRight, currentY)
        currentY += 10
      }

      // 辅助函数：绘制章节标题
      const drawSectionTitle = (text: string) => {
        checkPageBreak(14)
        pdf.setFontSize(12)
        pdf.setTextColor(0, 51, 102)
        pdf.setFont('SimHei', 'bold')
        // 左侧标记线
        pdf.setDrawColor(0, 51, 102)
        pdf.setLineWidth(1.5)
        pdf.line(marginLeft, currentY - 2, marginLeft, currentY + 3)
        pdf.text(text, marginLeft + 5, currentY)
        currentY += 10
      }

      // 辅助函数：绘制标签行
      const drawLabelLine = (label: string, value: string) => {
        checkPageBreak(8)
        pdf.setFontSize(10)
        pdf.setTextColor(51, 51, 51)
        pdf.setFont('SimHei', 'normal')
        pdf.text(`${label}：${value || '未填写'}`, marginLeft + 5, currentY)
        currentY += 8
      }

      // 辅助函数：绘制多行文本
      const drawMultilineText = (text: string, indent: number = 5) => {
        if (!text || text.trim() === '') {
          checkPageBreak(8)
          pdf.setFontSize(10)
          pdf.setTextColor(150, 150, 150)
          pdf.text('无', marginLeft + indent, currentY)
          currentY += 8
          return
        }

        const lines = text.split('\n')
        for (const line of lines) {
          if (!line.trim()) {
            currentY += 5
            continue
          }

          // 智能分割长行
          const maxWidth = contentWidth - indent
          const textLines = pdf.splitTextToSize(line.trim(), maxWidth)

          for (const textLine of textLines) {
            checkPageBreak(9)
            pdf.setFontSize(10)
            pdf.setTextColor(80, 80, 80)
            pdf.setFont('SimHei', 'normal')
            pdf.text(textLine, marginLeft + indent, currentY)
            currentY += 8
          }
        }
      }

      // ========== 开始绘制PDF内容 ==========

      // 标题
      drawTitle('偏差整改报告')
      drawDivider()

      // 一、基本信息
      drawSectionTitle('一、基本信息')
      drawLabelLine('偏差编号', deviation.deviation_no)
      drawLabelLine('偏差类型', deviationTypeLabels[deviation.deviation_type] || deviation.deviation_type)
      drawLabelLine('偏差等级', deviationLevelLabels[deviation.deviation_level] || deviation.deviation_level)
      drawLabelLine('发生日期', deviation.occurrence_date ? new Date(deviation.occurrence_date).toLocaleDateString() : '未填写')
      drawLabelLine('发现部门', deviation.discovering_department || '未填写')
      drawLabelLine('产品批次', deviation.production_batch || '未填写')
      currentY += 8

      // 二、偏差描述
      drawSectionTitle('二、偏差描述')
      drawMultilineText(deviation.abnormal_description || deviation.description)
      currentY += 8

      // 三、应急措施
      drawSectionTitle('三、应急措施')
      drawMultilineText(deviation.emergency_measures)
      currentY += 8

      // 四、调查信息
      drawSectionTitle('四、调查信息')
      drawLabelLine('直接原因', investigation?.direct_cause || '未填写')
      drawMultilineText(`根本原因（5M1E分析）：${investigation?.root_cause || '未填写'}`)
      drawMultilineText(`调查结论：${investigation?.investigation_conclusion || '未填写'}`)
      currentY += 8

      // 五、整改措施
      drawSectionTitle('五、整改措施')
      drawLabelLine('整改措施（CA+PA）', '')
      drawMultilineText(correction?.correction_measures || '未填写')
      drawLabelLine('责任部门', correction?.responsible_department)
      drawLabelLine('计划完成日期', correction?.plan_completion_date ? new Date(correction.plan_completion_date).toLocaleDateString() : '未填写')
      drawLabelLine('整改进度', `${correction?.progress || 0}%`)
      currentY += 8

      // 底部信息
      checkPageBreak(18)
      drawLine(currentY + 2)
      currentY += 8
      pdf.setFontSize(8)
      pdf.setTextColor(150, 150, 150)
      pdf.text(`报告生成时间：${new Date().toLocaleString()}`, marginLeft, currentY)
      currentY += 6
      pdf.text('本报告由AI辅助生成，仅供参考，最终以人工审核确认为准。', marginLeft, currentY)

      // 添加最后一页页码
      addPageNumber(pageNum)

      // 下载PDF
      const fileName = `偏差整改报告_${deviation.deviation_no}_${dayjs().format('YYYYMMDD')}.pdf`
      pdf.save(fileName)

      message.success('整改报告已生成')
    } catch (error: any) {
      message.error(error.message || '生成报告失败')
    } finally {
      setReportGenerating(false)
    }
  }

  // AI生成CAPA
  const handleAIGenerateCAPA = async () => {
    const values = form.getFieldsValue()
    if (!values.deviation_id) {
      message.warning('请先选择偏差')
      return
    }
    setAiLoading(true)
    setAiModalTitle('CAPA生成（纠正预防措施）')
    setAiTargetField('correction_measures')
    try {
      const deviation = deviations.find(d => d.id === values.deviation_id)
      const result = await deviationActions.aiGenerateCAPA({
        deviation_type: deviation?.deviation_type || 'general',
        root_cause: values.root_cause,
        deviation_level: deviation?.deviation_level,
        department: values.responsible_department,
      })
      const data = result.data || result
      setAiResult(data.capa || '')
      setAiModalVisible(true)
    } catch (error: any) {
      message.error(error.message || 'AI生成失败')
    } finally {
      setAiLoading(false)
    }
  }

  const applyAiResult = () => {
    if (aiResult) {
      form.setFieldValue(aiTargetField, aiResult)
      setAiModalVisible(false)
      message.success('已应用到表单')
    }
  }

  const columns: ColumnsType<Deviation> = [
    {
      title: '偏差编号',
      dataIndex: 'deviation_no',
      width: 150,
    },
    {
      title: '偏差类型',
      dataIndex: 'deviation_type',
      width: 100,
      render: (type) => deviationTypeLabels[type] || type,
    },
    {
      title: '根本原因',
      dataIndex: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status) => (
        <Tag color={getStatusColor(status)}>{deviationStatusLabels[status] || status}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 160,
      render: (_: any, record: Deviation) => (
        <Space size={2}>
          <Tooltip title="查看详情">
            <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleViewPending(record)} style={{ padding: '0 4px' }} />
          </Tooltip>
          <Tooltip title="完成整改">
            <Button type="link" size="small" icon={<CheckOutlined />} onClick={() => handleStartCompleteCorrection(record)} style={{ color: '#52c41a', padding: '0 4px' }} />
          </Tooltip>
        </Space>
      ),
    },
  ]

  // 查看待整改偏差详情
  const handleViewPending = async (record: Deviation) => {
    try {
      const result = await deviationActions.getDeviationById(record.id)
      if (result.code === 200 && result.data) {
        setSelectedDeviation(result.data)
        setDetailModalVisible(true)
      }
    } catch (error: any) {
      message.error(error.message || '获取详情失败')
    }
  }

  // 开始完成整改 - 填充表单
  const handleStartCompleteCorrection = async (record: Deviation) => {
    try {
      const result = await deviationActions.getDeviationById(record.id)
      if (result.code === 200 && result.data) {
        const deviation = result.data.deviation
        const correction = result.data.correction
        // 填充表单
        form.setFieldsValue({
          deviation_id: record.id,
          correction_measures: correction?.correction_measures || '',
          responsible_department: correction?.responsible_department || '',
          due_date: correction?.plan_completion_date ? dayjs(correction.plan_completion_date) : null,
        })
        // 显示完成整改弹窗
        setCompleteCorrectionModalVisible(true)
      }
    } catch (error: any) {
      message.error(error.message || '获取详情失败')
    }
  }

  // 处理选择偏差后的数据回填
  const handleSelectDeviation = (deviationId: string) => {
    const deviation = deviations.find(d => d.id === deviationId)
    if (deviation) {
      form.setFieldsValue({
        correction_measures: '',
        responsible_department: '',
        due_date: null,
      })
    }
  }

  // 保存CAPA
  const handleSaveCAPA = async () => {
    try {
      const values = form.getFieldsValue()
      if (!values.deviation_id) {
        message.warning('请先选择偏差')
        return
      }
      await deviationActions.updateDeviation(values.deviation_id, {
        correction: {
          correction_measures: values.correction_measures,
          responsible_department: values.responsible_department,
          plan_completion_date: values.due_date?.format('YYYY-MM-DD'),
        },
      })
      message.success('保存成功')
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '保存失败')
    }
  }

  // 完成整改
  const handleCompleteCorrection = async () => {
    try {
      const values = form.getFieldsValue()
      if (!values.deviation_id) {
        message.warning('请先选择偏差')
        return
      }
      await deviationActions.updateDeviation(values.deviation_id, {
        status: 'closed',
        correction: {
          correction_measures: values.correction_measures,
          responsible_department: values.responsible_department,
          plan_completion_date: values.due_date?.format('YYYY-MM-DD'),
        },
      })
      message.success('整改已完成，偏差已关闭')
      form.resetFields()
      fetchDeviations()
      onRefresh()
    } catch (error: any) {
      message.error(error.message || '操作失败')
    }
  }

  return (
    <div>
      <GMPDisclaimer />
      <Alert
        message="CAPA管理说明"
        description="针对偏差调查发现的根本原因，制定纠正措施（CA）和预防措施（PA），跟踪整改进度和效果验证。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 偏差选择 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Form.Item name="deviation_id" label="选择偏差" rules={[{ required: true, message: '请选择要整改的偏差' }]}>
            <Select
              placeholder="请选择偏差"
              onChange={handleSelectDeviation}
              showSearch
              optionFilterProp="children"
            >
              {deviations.map(d => (
                <Select.Option key={d.id} value={d.id}>
                  {d.deviation_no} - {deviationTypeLabels[d.deviation_type]} ({deviationStatusLabels[d.status]})
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Card>

      {/* CAPA表单 */}
      <Card title="整改措施" size="small" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical">
          <Row gutter={16}>
            <Col span={24}>
              <Form.Item
                name="correction_measures"
                label={
                  <Space>
                    <span>整改措施（CA+PA）</span>
                    <AIButton
                      label="AI生成"
                      loading={aiLoading}
                      onClick={handleAIGenerateCAPA}
                      tooltip="根据根本原因自动生成纠正措施和预防措施"
                    />
                  </Space>
                }
              >
                <TextArea rows={6} placeholder="纠正措施（CA）：针对已发生的偏差采取的纠正行动&#10;预防措施（PA）：防止类似偏差再次发生的预防措施&#10;（AI生成将同时包含CA和PA）" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="responsible_department" label="负责部门">
                <Select placeholder="选择负责部门">
                  {DEPARTMENT_LIST.map(dept => (
                    <Select.Option key={dept} value={dept}>{dept}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="due_date" label="完成期限">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row justify="end">
            <Space>
              <Button onClick={() => form.resetFields()}>重置</Button>
              <Button type="primary" onClick={handleSaveCAPA}>保存</Button>
              <Button type="primary" icon={<CheckOutlined />} onClick={handleCompleteCorrection} style={{ backgroundColor: '#52c41a' }}>
                完成整改
              </Button>
            </Space>
          </Row>
        </Form>
      </Card>

      {/* 偏差列表 - 带Tab切换 */}
      <Card size="small">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={[
            {
              key: 'pending',
              label: `待整改 (${deviations.length})`,
              children: (
                <Table
                  columns={columns}
                  dataSource={deviations}
                  rowKey="id"
                  loading={loading}
                  pagination={{ pageSize: 5 }}
                  size="small"
                />
              ),
            },
            {
              key: 'completed',
              label: `已完成整改 (${completedDeviations.length})`,
              children: (
                <Table
                  columns={[
                    {
                      title: '偏差编号',
                      dataIndex: 'deviation_no',
                      width: 150,
                    },
                    {
                      title: '偏差类型',
                      dataIndex: 'deviation_type',
                      width: 100,
                      render: (type) => deviationTypeLabels[type] || type,
                    },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 100,
                      render: (status) => (
                        <Tag color={getStatusColor(status)}>{deviationStatusLabels[status] || status}</Tag>
                      ),
                    },
                    {
                      title: '操作',
                      width: 80,
                      render: (_: any, record: Deviation) => (
                        <Button type="link" size="small" onClick={() => handleViewCompleted(record)}>
                          查看详情
                        </Button>
                      ),
                    },
                  ]}
                  dataSource={completedDeviations}
                  rowKey="id"
                  loading={loading}
                  pagination={{ pageSize: 5 }}
                  size="small"
                />
              ),
            },
          ]}
        />
      </Card>

      {/* 已完成整改详情弹窗 */}
      <Modal
        title="偏差整改详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
          <Button
            key="report"
            type="primary"
            loading={reportGenerating}
            onClick={handleGenerateReport}
            icon={<FileTextOutlined />}
          >
            生成整改报告
          </Button>,
        ]}
        width={800}
      >
        {selectedDeviation && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="偏差编号">{selectedDeviation.deviation?.deviation_no}</Descriptions.Item>
            <Descriptions.Item label="偏差类型">{deviationTypeLabels[selectedDeviation.deviation?.deviation_type] || selectedDeviation.deviation?.deviation_type}</Descriptions.Item>
            <Descriptions.Item label="偏差等级">{deviationLevelLabels[selectedDeviation.deviation?.deviation_level] || selectedDeviation.deviation?.deviation_level}</Descriptions.Item>
            <Descriptions.Item label="发生日期">{selectedDeviation.deviation?.occurrence_date ? new Date(selectedDeviation.deviation.occurrence_date).toLocaleDateString() : '未填写'}</Descriptions.Item>
            <Descriptions.Item label="发现部门">{selectedDeviation.deviation?.discovering_department || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="产品批次">{selectedDeviation.deviation?.production_batch || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="偏差描述">{selectedDeviation.deviation?.abnormal_description || selectedDeviation.deviation?.description || '无'}</Descriptions.Item>
            <Descriptions.Item label="应急措施">{selectedDeviation.deviation?.emergency_measures || '无'}</Descriptions.Item>
            <Descriptions.Item label="直接原因">{selectedDeviation.investigation?.direct_cause || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="根本原因">{selectedDeviation.investigation?.root_cause || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="调查结论">{selectedDeviation.investigation?.investigation_conclusion || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="整改措施">{selectedDeviation.correction?.correction_measures || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="责任部门">{selectedDeviation.correction?.responsible_department || '未填写'}</Descriptions.Item>
            <Descriptions.Item label="计划完成日期">{selectedDeviation.correction?.plan_completion_date ? new Date(selectedDeviation.correction.plan_completion_date).toLocaleDateString() : '未填写'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      {/* 完成整改弹窗 */}
      <Modal
        title={<Space><CheckOutlined style={{ color: '#52c41a' }} /> 完成整改</Space>}
        open={completeCorrectionModalVisible}
        onCancel={() => setCompleteCorrectionModalVisible(false)}
        footer={null}
        width={700}
      >
        <Alert
          message="完成整改确认"
          description="请确认整改措施已全部落实，确认后偏差将关闭。"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={completeForm} layout="vertical">
          <Form.Item
            name="correction_measures"
            label="整改措施（CA+PA）"
          >
            <TextArea rows={5} placeholder="纠正措施（CA）和预防措施（PA）" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="responsible_department" label="负责部门">
                <Select placeholder="选择负责部门">
                  {DEPARTMENT_LIST.map(dept => (
                    <Select.Option key={dept} value={dept}>{dept}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="completion_date" label="实际完成日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="completion_result" label="整改完成情况说明">
            <TextArea rows={3} placeholder="说明整改措施的实际执行情况和效果" />
          </Form.Item>
          <Row justify="end">
            <Space>
              <Button onClick={() => setCompleteCorrectionModalVisible(false)}>取消</Button>
              <Button
                type="primary"
                icon={<CheckOutlined />}
                onClick={async () => {
                  const values = completeForm.getFieldsValue()
                  const deviationId = completeForm.getFieldValue('deviation_id')
                  if (!deviationId) {
                    message.warning('偏差ID不存在，请重新打开')
                    return
                  }
                  try {
                    await deviationActions.updateDeviation(deviationId, {
                      status: 'closed',
                      correction: {
                        correction_measures: values.correction_measures,
                        responsible_department: values.responsible_department,
                        plan_completion_date: values.completion_date?.format('YYYY-MM-DD'),
                      },
                    })
                    message.success('整改已完成，偏差已关闭')
                    setCompleteCorrectionModalVisible(false)
                    completeForm.resetFields()
                    fetchDeviations()
                    onRefresh()
                  } catch (error: any) {
                    message.error(error.message || '操作失败')
                  }
                }}
                style={{ backgroundColor: '#52c41a' }}
              >
                确认完成
              </Button>
            </Space>
          </Row>
        </Form>
      </Modal>

      <AIResultModal
        open={aiModalVisible}
        onClose={() => setAiModalVisible(false)}
        onApply={applyAiResult}
        title={aiModalTitle}
        result={aiResult}
        loading={aiLoading}
      />
    </div>
  )
}

// ============ 偏差详情弹窗 ============
const DeviationDetailModal: React.FC<{
  deviation: Deviation | null
  open: boolean
  onClose: () => void
  onRefresh: () => void
}> = ({ deviation, open, onClose, onRefresh }) => {
  const [lockModalVisible, setLockModalVisible] = useState(false)
  const [lockReason, setLockReason] = useState('')
  const [locking, setLocking] = useState(false)
  const [unlocking, setUnlocking] = useState(false)

  if (!deviation) return null

  const getStepsItems = () => {
    const steps: { title: string; status: 'error' | 'process' | 'finish' | 'wait' }[] = [
      { title: '发起', status: 'finish' },
      { title: '调查', status: deviation.status === 'investigating' ? 'process' :
        ['investigation_completed', 'correction_pending', 'correction_in_progress', 'closed'].includes(deviation.status) ? 'finish' : 'wait' },
      { title: '整改', status: ['correction_in_progress'].includes(deviation.status) ? 'process' :
        ['correction_completed', 'closed'].includes(deviation.status) ? 'finish' : 'wait' },
      { title: '关闭', status: deviation.status === 'closed' ? 'finish' : 'wait' },
    ]
    return steps
  }

  const handleLockBatch = async () => {
    if (!lockReason.trim()) {
      message.warning('请输入锁定原因')
      return
    }
    setLocking(true)
    try {
      await deviationActions.lockBatch(deviation.id, { reason: lockReason })
      message.success('批次已锁定')
      setLockModalVisible(false)
      setLockReason('')
      onRefresh()
      // 重新获取详情
      const result = await deviationActions.getDeviationById(deviation.id)
      if (result.code === 200 && result.data?.deviation) {
        onClose()
        // 通过重新打开详情来刷新数据
        setTimeout(() => {
          onRefresh()
        }, 100)
      }
    } catch (error: any) {
      message.error(error.message || '锁定失败')
    } finally {
      setLocking(false)
    }
  }

  const handleUnlockBatch = async () => {
    setUnlocking(true)
    try {
      await deviationActions.unlockBatch(deviation.id)
      message.success('批次已解锁')
      onRefresh()
      // 重新获取详情
      const result = await deviationActions.getDeviationById(deviation.id)
      if (result.code === 200 && result.data?.deviation) {
        onClose()
        setTimeout(() => {
          onRefresh()
        }, 100)
      }
    } catch (error: any) {
      message.error(error.message || '解锁失败')
    } finally {
      setUnlocking(false)
    }
  }

  return (
    <>
      <Modal
        title={<Space><FileTextOutlined /> 偏差详情 - {deviation.deviation_no}</Space>}
        open={open}
        onCancel={onClose}
        footer={
          <Space>
            <Button onClick={onClose}>关闭</Button>
            {deviation.production_batch && (
              deviation.batch_locked ? (
                <Popconfirm
                  title="确认解锁批次？"
                  description="解锁后批次可以正常使用，确定要解锁吗？"
                  onConfirm={handleUnlockBatch}
                  okText="确认解锁"
                  cancelText="取消"
                  okButtonProps={{ loading: unlocking, danger: true }}
                >
                  <Button danger icon={<UnlockOutlined />} loading={unlocking}>
                    解锁批次
                  </Button>
                </Popconfirm>
              ) : (
                <Button type="primary" danger icon={<LockOutlined />} onClick={() => setLockModalVisible(true)}>
                  锁定批次
                </Button>
              )
            )}
          </Space>
        }
        width={900}
      >
        <Steps current={0} items={getStepsItems()} style={{ marginBottom: 24 }} />

        <Descriptions bordered column={2} size="small">
          <Descriptions.Item label="偏差编号">{deviation.deviation_no}</Descriptions.Item>
          <Descriptions.Item label="偏差类型">
            <Tag>{deviationTypeLabels[deviation.deviation_type] || deviation.deviation_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="偏差级别">
            <Tag color={deviation.deviation_level === 'critical' ? 'red' : deviation.deviation_level === 'major' ? 'orange' : 'blue'}>
              {deviationLevelLabels[deviation.deviation_level] || deviation.deviation_level}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={getStatusColor(deviation.status)}>{deviationStatusLabels[deviation.status] || deviation.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="发生日期">
            {deviation.occurrence_date ? dayjs(deviation.occurrence_date).format('YYYY-MM-DD') : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="发现部门">{deviation.discovering_department || '-'}</Descriptions.Item>
          <Descriptions.Item label="产品/物料">{deviation.product_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="生产批次">{deviation.production_batch || '-'}</Descriptions.Item>
          <Descriptions.Item label="偏差描述" span={2}>{deviation.abnormal_description || deviation.description || '-'}</Descriptions.Item>
          <Descriptions.Item label="影响范围" span={2}>{deviation.impact_scope || '-'}</Descriptions.Item>
          <Descriptions.Item label="应急措施" span={2}>{deviation.emergency_measures || '-'}</Descriptions.Item>
          <Descriptions.Item label="批次状态" span={2}>
            {deviation.batch_locked ? (
              <Tag color="red" icon={<LockOutlined />}>已锁定</Tag>
            ) : (
              <Tag icon={<UnlockOutlined />}>未锁定</Tag>
            )}
            {deviation.batch_lock_reason && (
              <span style={{ marginLeft: 8, color: '#666' }}>原因: {deviation.batch_lock_reason}</span>
            )}
          </Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {deviation.created_at ? dayjs(deviation.created_at).format('YYYY-MM-DD HH:mm') : '-'}
          </Descriptions.Item>
        </Descriptions>
      </Modal>

      {/* 批次锁定确认弹窗 */}
      <Modal
        title={<Space><LockOutlined /> 批次锁定</Space>}
        open={lockModalVisible}
        onCancel={() => {
          setLockModalVisible(false)
          setLockReason('')
        }}
        onOk={handleLockBatch}
        okText="确认锁定"
        cancelText="取消"
        confirmLoading={locking}
        okButtonProps={{ danger: true }}
      >
        <Alert
          message="GMP合规提示"
          description="偏差涉及批次需立即锁定，防止不合格产品流入下一工序。锁定后批次将被隔离，直至偏差处理完成。"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form layout="vertical">
          <Form.Item label="锁定批次" required>
            <Tag color="red">{deviation.production_batch || '未指定批次'}</Tag>
          </Form.Item>
          <Form.Item label="锁定原因" required>
            <TextArea
              rows={3}
              placeholder="请输入批次锁定原因，如：偏差涉及产品质量风险，需隔离检测"
              value={lockReason}
              onChange={(e) => setLockReason(e.target.value)}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}

// ============ 主页面组件 ============
export default function DeviationPage() {
  const [activeTab, setActiveTab] = useState('list')
  const [statistics, setStatistics] = useState<DeviationStatistics | null>(null)
  const [selectedDeviation, setSelectedDeviation] = useState<Deviation | null>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  const refreshData = async () => {
    try {
      const result = await deviationActions.getDeviationStatistics()
      if (result.code === 200 || result.code === 0) {
        setStatistics(result.data as DeviationStatistics)
      }
    } catch (error) {
      console.error('Failed to refresh statistics:', error)
    }
  }

  useEffect(() => {
    refreshData()
  }, [])

  const handleViewDeviation = async (deviation: Deviation) => {
    try {
      const result = await deviationActions.getDeviationById(deviation.id)
      if (result.code === 200 && result.data?.deviation) {
        setSelectedDeviation(result.data.deviation)
      } else {
        setSelectedDeviation(deviation)
      }
    } catch (error) {
      console.error('Failed to fetch deviation details:', error)
      setSelectedDeviation(deviation)
    }
    setDetailModalVisible(true)
  }

  const tabItems = [
    {
      key: 'list',
      label: (
        <span><FileTextOutlined /> 偏差列表</span>
      ),
      children: <DeviationListTab onView={handleViewDeviation} onRefresh={refreshData} />,
    },
    {
      key: 'investigation',
      label: (
        <span><SearchOutlined /> 偏差调查</span>
      ),
      children: <InvestigationTab onRefresh={refreshData} />,
    },
    {
      key: 'capa',
      label: (
        <span><SafetyOutlined /> CAPA整改</span>
      ),
      children: <CAPATab onRefresh={refreshData} />,
    },
  ]

  // 统计卡片 - 与Tab页面数据保持一致
  const byStatus = statistics?.by_status || {}
  // 调查中 = submitted + investigating
  const investigatingCount = (byStatus.submitted || 0) + (byStatus.investigating || 0)
  // 整改中 = investigation_completed + correction_pending + correction_in_progress
  const correctionCount = (byStatus.investigation_completed || 0) + (byStatus.correction_pending || 0) + (byStatus.correction_in_progress || 0)
  // 已关闭 = closed + correction_completed
  const closedCount = (byStatus.closed || 0) + (byStatus.correction_completed || 0)

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: '#faad14' }} />
            AI智能偏差管理系统
          </Space>
        }
      >
        {/* 统计卡片 */}
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card size="small">
              <Statistic title="待处理" value={byStatus.draft || 0} valueStyle={{ color: '#faad14' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="调查中" value={investigatingCount} valueStyle={{ color: '#1890ff' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="整改中" value={correctionCount} valueStyle={{ color: '#722ed1' }} />
            </Card>
          </Col>
          <Col span={6}>
            <Card size="small">
              <Statistic title="已关闭" value={closedCount} valueStyle={{ color: '#52c41a' }} />
            </Card>
          </Col>
        </Row>

        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
        />
      </Card>

      <DeviationDetailModal
        deviation={selectedDeviation}
        open={detailModalVisible}
        onClose={() => setDetailModalVisible(false)}
        onRefresh={refreshData}
      />
    </div>
  )
}