'use client'

import { useState, useCallback, useMemo } from 'react'
import {
  Table,
  Button,
  Space,
  Input,
  Select,
  DatePicker,
  Tag,
  Modal,
  Form,
  InputNumber,
  message,
  Popconfirm,
  Card,
  Row,
  Col,
  Divider,
  Typography,
  Descriptions,
  Tabs,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
  LineChartOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  StabilityStudy,
  StabilityStudyListItem,
  StabilityStudyCreate,
  StabilityStudyFilter,
  StabilityStudyStatus,
  StabilityStudyStatusLabels,
  StabilityStudyStatusColors,
  StabilityStudyType,
  StabilityStudyTypeLabels,
  StabilitySampleNode,
  StabilitySampleNodeCreate,
  SampleNodeStatus,
  SampleNodeStatusLabels,
  SampleNodeStatusColors,
  StabilityInspection,
  StabilityInspectionCreate,
  StabilityInspectionItemCreate,
  StabilityInspectionStatus,
  StabilityInspectionStatusLabels,
  StabilityInspectionStatusColors,
  StabilityInspectionConclusion,
  StabilityInspectionConclusionLabels,
  StabilityItemResult,
  StabilityItemResultLabels,
} from '@/types/stability'
import {
  getStabilityStudies,
  getStabilityStudy,
  createStabilityStudy,
  updateStabilityStudy,
  deleteStabilityStudy,
  submitStabilityStudy,
  approveStabilityStudy,
  getStabilityStudySampleNodes,
  getStabilityInspections,
  getStabilityInspection,
  createStabilityInspection,
  updateStabilityInspection,
  submitStabilityInspection,
} from '@/actions/quality'

const { RangePicker } = DatePicker
const { Text } = Typography
const { TextArea } = Input

// 初始筛选条件
const initialFilters: StabilityStudyFilter = {
  study_no: '',
  product_code: '',
  product_name: '',
  study_type: undefined,
  status: undefined,
  batch_no: '',
  start_date: undefined,
  end_date: undefined,
}

// 默认取样间隔（长期试验）
const DEFAULT_SAMPLE_INTERVALS = [0, 3, 6, 9, 12, 18, 24, 36, 48, 60]

export default function StabilityStudyPage() {
  // 状态
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<StabilityStudyListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<StabilityStudyFilter>(initialFilters)

  // 弹窗状态
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [modalTitle, setModalTitle] = useState('新建稳定性试验方案')
  const [editingRecord, setEditingRecord] = useState<StabilityStudy | null>(null)
  const [viewRecord, setViewRecord] = useState<StabilityStudy | null>(null)
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [sampleNodes, setSampleNodes] = useState<StabilitySampleNode[]>([])
  const [activeTab, setActiveTab] = useState('info')

  // 表单
  const [createForm] = Form.useForm()
  const [submitLoading, setSubmitLoading] = useState(false)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getStabilityStudies({
        ...filters,
        page,
        page_size: pageSize,
      }) as { items?: StabilityStudyListItem[]; total?: number; code?: number; message?: string; data?: { items?: StabilityStudyListItem[]; total?: number } }
      if (response.items !== undefined) {
        setData(response.items || [])
        setTotal(response.total || 0)
      } else if (response.code === 200 || response.code === 0) {
        setData(response.data?.items || [])
        setTotal(response.data?.total || 0)
      } else {
        message.error(response.message || '加载失败')
      }
    } catch (error) {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

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

  // 新建
  const handleCreate = () => {
    setEditingRecord(null)
    setModalTitle('新建稳定性试验方案')
    createForm.resetFields()
    createForm.setFieldsValue({
      study_type: StabilityStudyType.LONG_TERM,
      sample_intervals: DEFAULT_SAMPLE_INTERVALS,
      temperature: '25±2℃',
      humidity: '60±10%',
    })
    setSampleNodes([])
    setCreateModalVisible(true)
  }

  // 编辑
  const handleEdit = async (record: StabilityStudyListItem) => {
    try {
      const response = await getStabilityStudy(record.id) as { code?: number; message?: string; data?: StabilityStudy }
      if (response.code === 200 || response.code === 0) {
        setEditingRecord(response.data!)
        setModalTitle('编辑稳定性试验方案')
        createForm.setFieldsValue({
          ...response.data,
          start_date: response.data?.start_date ? dayjs(response.data.start_date) : null,
          end_date: response.data?.end_date ? dayjs(response.data.end_date) : null,
          expiry_date: response.data?.expiry_date ? dayjs(response.data.expiry_date) : null,
        })
        // 加载取样节点
        const nodesResponse = await getStabilityStudySampleNodes(record.id) as { code?: number; data?: StabilitySampleNode[] }
        if (nodesResponse.code === 200 || nodesResponse.code === 0) {
          setSampleNodes(nodesResponse.data || [])
        }
        setCreateModalVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  // 查看详情
  const handleView = async (record: StabilityStudyListItem) => {
    try {
      const response = await getStabilityStudy(record.id) as { code?: number; message?: string; data?: StabilityStudy }
      if (response.code === 200 || response.code === 0) {
        setViewRecord(response.data!)
        // 加载取样节点
        const nodesResponse = await getStabilityStudySampleNodes(record.id) as { code?: number; data?: StabilitySampleNode[] }
        if (nodesResponse.code === 200 || nodesResponse.code === 0) {
          setSampleNodes(nodesResponse.data || [])
        }
        setViewModalVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  // 删除
  const handleDelete = async (id: string) => {
    try {
      const response = await deleteStabilityStudy(id) as { code?: number; message?: string }
      if (response.code === 200 || response.code === 0 || response.message?.includes('成功')) {
        message.success('删除成功')
        loadData()
      } else {
        message.error(response.message || '删除失败')
      }
    } catch (error) {
      message.error('删除失败')
    }
  }

  // 提交审批
  const handleSubmit = async (id: string) => {
    try {
      const response = await submitStabilityStudy(id) as { code?: number; message?: string; data?: { status?: string } }
      if (response.code === 200 || response.code === 0 || response.data?.status) {
        message.success('提交成功')
        loadData()
      } else {
        message.error(response.message || '提交失败')
      }
    } catch (error) {
      message.error('提交失败')
    }
  }

  // 审批
  const handleApprove = async (id: string, approved: boolean) => {
    try {
      const response = await approveStabilityStudy(id, {
        approval_status: approved ? 'approved' : 'rejected',
      }) as { code?: number; message?: string; data?: { status?: string } }
      if (response.code === 200 || response.code === 0 || response.data?.status) {
        message.success(approved ? '审批通过' : '已驳回')
        loadData()
      } else {
        message.error(response.message || '操作失败')
      }
    } catch (error) {
      message.error('操作失败')
    }
  }

  // 提交表单
  const handleSubmitForm = async () => {
    try {
      const values = await createForm.validateFields()

      const submitData: StabilityStudyCreate = {
        ...values,
        start_date: values.start_date?.format('YYYY-MM-DD'),
        end_date: values.end_date?.format('YYYY-MM-DD'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DD'),
        sample_nodes: sampleNodes.map((node, index) => ({
          node_no: index + 1,
          node_month: node.node_month,
          node_name: node.node_name,
          planned_date: node.planned_date,
          sample_quantity: node.sample_quantity,
        })),
      }

      setSubmitLoading(true)

      let response: { code?: number; message?: string; data?: { study_no?: string; id?: string } }
      if (editingRecord) {
        response = await updateStabilityStudy(editingRecord.id, submitData) as typeof response
      } else {
        response = await createStabilityStudy(submitData) as typeof response
      }

      if (response.code === 200 || response.code === 0 || response.data?.study_no) {
        message.success(editingRecord ? '更新成功' : '创建成功')
        setCreateModalVisible(false)
        loadData()
      } else {
        message.error(response.message || '操作失败')
      }
    } catch (error: unknown) {
      if ((error as { errorFields?: unknown }).errorFields) {
        return
      }
      message.error((error as Error).message || '操作失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  // 生成取样节点
  const handleGenerateSampleNodes = () => {
    const values = createForm.getFieldsValue()
    const startDate = values.start_date

    if (!startDate) {
      message.warning('请先选择开始日期')
      return
    }

    // 确保 sample_intervals 是数组
    let intervals: number[] = []
    if (Array.isArray(values.sample_intervals)) {
      intervals = values.sample_intervals
    } else if (typeof values.sample_intervals === 'string' && values.sample_intervals) {
      intervals = values.sample_intervals.split(',').map(Number).filter((n: number) => !isNaN(n))
    } else {
      intervals = DEFAULT_SAMPLE_INTERVALS
    }

    if (intervals.length === 0) {
      intervals = DEFAULT_SAMPLE_INTERVALS
    }

    const nodes: StabilitySampleNode[] = intervals.map((month: number, index: number) => {
      const plannedDate = startDate.add(month, 'month')
      return {
        id: `temp_${index}`,
        stability_study_id: '',
        node_no: index + 1,
        node_month: month,
        node_name: `${month}月`,
        planned_date: plannedDate.format('YYYY-MM-DD'),
        status: SampleNodeStatus.PENDING,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
    })

    setSampleNodes(nodes)
    message.success(`已生成 ${nodes.length} 个取样节点`)
  }

  // 更新取样节点
  const handleUpdateSampleNode = (index: number, field: string, value: unknown) => {
    const newNodes = [...sampleNodes]
    newNodes[index] = { ...newNodes[index], [field]: value }
    setSampleNodes(newNodes)
  }

  // 试验类型切换
  const handleStudyTypeChange = (type: StabilityStudyType) => {
    let temp = '25±2℃'
    let humidity = '60±10%'
    let intervals = DEFAULT_SAMPLE_INTERVALS

    switch (type) {
      case StabilityStudyType.ACCELERATED:
        temp = '40±2℃'
        humidity = '75±5%'
        intervals = [0, 1, 2, 3, 6]
        break
      case StabilityStudyType.INTERMEDIATE:
        temp = '30±2℃'
        humidity = '65±5%'
        intervals = [0, 3, 6, 9, 12, 18, 24, 36]
        break
      default:
        intervals = DEFAULT_SAMPLE_INTERVALS
    }

    createForm.setFieldsValue({ temperature: temp, humidity, sample_intervals: intervals })
  }

  // 表格列定义
  const columns: ColumnsType<StabilityStudyListItem> = [
    {
      title: '方案编号',
      dataIndex: 'study_no',
      key: 'study_no',
      width: 150,
      fixed: 'left',
    },
    {
      title: '产品编码',
      dataIndex: 'product_code',
      key: 'product_code',
      width: 100,
    },
    {
      title: '产品名称',
      dataIndex: 'product_name',
      key: 'product_name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '批号',
      dataIndex: 'batch_no',
      key: 'batch_no',
      width: 120,
    },
    {
      title: '试验类型',
      dataIndex: 'study_type',
      key: 'study_type',
      width: 100,
      render: (value: StabilityStudyType) => StabilityStudyTypeLabels[value],
    },
    {
      title: '温度',
      dataIndex: 'temperature',
      key: 'temperature',
      width: 80,
    },
    {
      title: '湿度',
      dataIndex: 'humidity',
      key: 'humidity',
      width: 80,
    },
    {
      title: '开始日期',
      dataIndex: 'start_date',
      key: 'start_date',
      width: 110,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD') : '-',
    },
    {
      title: '研发人员',
      dataIndex: 'developer_name',
      key: 'developer_name',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (value: StabilityStudyStatus) => (
        <Tag color={StabilityStudyStatusColors[value]}>
          {StabilityStudyStatusLabels[value]}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 250,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small" wrap>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {(record.status === StabilityStudyStatus.DRAFT || record.status === StabilityStudyStatus.REJECTED) && (
            <>
              <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
                编辑
              </Button>
              <Popconfirm
                title="确定删除？"
                onConfirm={() => handleDelete(record.id)}
                okText="确定"
                cancelText="取消"
              >
                <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                  删除
                </Button>
              </Popconfirm>
            </>
          )}
          {record.status === StabilityStudyStatus.DRAFT && (
            <Button type="primary" size="small" onClick={() => handleSubmit(record.id)}>
              提交
            </Button>
          )}
          {(record.status === StabilityStudyStatus.SUBMITTED ||
            record.status === StabilityStudyStatus.DEVELOPER_APPROVED ||
            record.status === StabilityStudyStatus.QC_SUPERVISOR_APPROVED ||
            record.status === StabilityStudyStatus.QA_APPROVED ||
            record.status === StabilityStudyStatus.FINAL_APPROVED) && (
            <>
              <Button type="primary" size="small" icon={<CheckOutlined />} onClick={() => handleApprove(record.id, true)}>
                通过
              </Button>
              <Button danger size="small" icon={<CloseOutlined />} onClick={() => handleApprove(record.id, false)}>
                驳回
              </Button>
            </>
          )}
          {record.status === StabilityStudyStatus.ACTIVE && (
            <Button type="link" size="small" icon={<LineChartOutlined />}>
              趋势
            </Button>
          )}
        </Space>
      ),
    },
  ]

  // 取样节点表格列
  const sampleNodeColumns = useMemo(() => [
    { title: '项次', dataIndex: 'node_no', width: 60 },
    { title: '月数', dataIndex: 'node_month', width: 80 },
    { title: '节点名称', dataIndex: 'node_name', width: 120 },
    {
      title: '计划日期',
      dataIndex: 'planned_date',
      width: 120,
      render: (value: string, _record: StabilitySampleNode, index: number) => (
        <Input
          value={value}
          onChange={(e) => handleUpdateSampleNode(index, 'planned_date', e.target.value)}
          placeholder="计划日期"
        />
      ),
    },
    { title: '取样数量', dataIndex: 'sample_quantity', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (value: SampleNodeStatus) => (
        <Tag color={SampleNodeStatusColors[value]}>
          {SampleNodeStatusLabels[value]}
        </Tag>
      ),
    },
  ], [sampleNodes])

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Input
                placeholder="方案编号"
                value={filters.study_no}
                onChange={(e) => setFilters({ ...filters, study_no: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="产品编码"
                value={filters.product_code}
                onChange={(e) => setFilters({ ...filters, product_code: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="产品名称"
                value={filters.product_name}
                onChange={(e) => setFilters({ ...filters, product_name: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="试验类型"
                value={filters.study_type}
                onChange={(value) => setFilters({ ...filters, study_type: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(StabilityStudyTypeLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="状态"
                value={filters.status}
                onChange={(value) => setFilters({ ...filters, status: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(StabilityStudyStatusLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <RangePicker
                style={{ width: '100%' }}
                onChange={(dates) => {
                  setFilters({
                    ...filters,
                    start_date: dates?.[0]?.format('YYYY-MM-DD') || undefined,
                    end_date: dates?.[1]?.format('YYYY-MM-DD') || undefined,
                  })
                }}
              />
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={12} style={{ textAlign: 'right' }}>
              <Space>
                <Button type="primary" onClick={handleSearch}>查询</Button>
                <Button onClick={handleReset}>重置</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建试验方案
                </Button>
              </Space>
            </Col>
          </Row>
        </div>

        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1800 }}
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

      {/* 新建/编辑弹窗 */}
      {createModalVisible && (
      <Modal
        title={modalTitle}
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        width={1100}
        footer={
          <Space>
            <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
            <Button type="primary" onClick={handleSubmitForm} loading={submitLoading}>
              {editingRecord ? '更新' : '创建'}
            </Button>
          </Space>
        }
      >
        <Form form={createForm} layout="vertical">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'info',
                label: '基本信息',
                children: (
                  <>
                    <Divider>产品信息</Divider>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="product_code" label="产品编码" rules={[{ required: true }]}>
                          <Input placeholder="请输入产品编码" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="product_name" label="产品名称">
                          <Input placeholder="请输入产品名称" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="product_category" label="产品类别">
                          <Input placeholder="请输入产品类别" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="batch_no" label="批号" rules={[{ required: true, message: '请输入批号' }]}>
                          <Input placeholder="请输入批号" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="batch_quantity" label="批量">
                          <InputNumber style={{ width: '100%' }} placeholder="批量" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="packaging_spec" label="包装规格">
                          <Input placeholder="请输入包装规格" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider>试验条件</Divider>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="study_type" label="试验类型" rules={[{ required: true }]}>
                          <Select placeholder="请选择试验类型" onChange={handleStudyTypeChange}>
                            {Object.entries(StabilityStudyTypeLabels).map(([value, label]) => (
                              <Select.Option key={value} value={value}>{label}</Select.Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="temperature" label="温度">
                          <Input placeholder="温度条件" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="humidity" label="湿度">
                          <Input placeholder="湿度条件" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="start_date" label="开始日期">
                          <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="end_date" label="结束日期">
                          <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="expiry_date" label="有效期至">
                          <DatePicker style={{ width: '100%' }} />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Divider>质量标准</Divider>
                    <Row gutter={16}>
                      <Col span={8}>
                        <Form.Item name="standard_name" label="质量标准">
                          <Input placeholder="质量标准名称" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="standard_version" label="版本">
                          <Input placeholder="版本号" />
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Form.Item name="developer_name" label="研发人员">
                          <Input placeholder="研发人员" />
                        </Form.Item>
                      </Col>
                    </Row>

                    <Row gutter={16}>
                      <Col span={24}>
                        <Form.Item name="remark" label="备注">
                          <TextArea rows={2} placeholder="请输入备注" />
                        </Form.Item>
                      </Col>
                    </Row>
                  </>
                ),
              },
              {
                key: 'nodes',
                label: '取样节点',
                children: (
                  <>
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                      <Col span={8}>
                        <Form.Item name="sample_intervals" label="取样间隔（月）">
                          <Select mode="multiple" placeholder="选择取样时间点">
                            {[0, 1, 2, 3, 6, 9, 12, 18, 24, 36, 48, 60].map((m) => (
                              <Select.Option key={m} value={m}>{m}月</Select.Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={8}>
                        <Button onClick={handleGenerateSampleNodes} style={{ marginTop: 24 }}>
                          生成取样节点
                        </Button>
                      </Col>
                    </Row>

                    {sampleNodes.length > 0 && (
                      <Table
                        size="small"
                        dataSource={sampleNodes.map((node, index) => ({ ...node, key: index }))}
                        columns={sampleNodeColumns}
                        pagination={false}
                        scroll={{ x: 800 }}
                      />
                    )}
                  </>
                ),
              },
            ]}
          />
        </Form>
      </Modal>
      )}

      {/* 查看详情弹窗 */}
      <Modal
        title="稳定性试验方案详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={null}
        width={1100}
      >
        {viewRecord && (
          <>
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="方案编号" span={1}>{viewRecord.study_no}</Descriptions.Item>
              <Descriptions.Item label="产品编码" span={1}>{viewRecord.product_code}</Descriptions.Item>
              <Descriptions.Item label="产品名称" span={1}>{viewRecord.product_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="批号" span={1}>{viewRecord.batch_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="批量" span={1}>{viewRecord.batch_quantity || '-'}</Descriptions.Item>
              <Descriptions.Item label="包装规格" span={1}>{viewRecord.packaging_spec || '-'}</Descriptions.Item>
              <Descriptions.Item label="试验类型" span={1}>
                {viewRecord.study_type && StabilityStudyTypeLabels[viewRecord.study_type]}
              </Descriptions.Item>
              <Descriptions.Item label="温度" span={1}>{viewRecord.temperature || '-'}</Descriptions.Item>
              <Descriptions.Item label="湿度" span={1}>{viewRecord.humidity || '-'}</Descriptions.Item>
              <Descriptions.Item label="开始日期" span={1}>
                {viewRecord.start_date ? dayjs(viewRecord.start_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="结束日期" span={1}>
                {viewRecord.end_date ? dayjs(viewRecord.end_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="有效期至" span={1}>
                {viewRecord.expiry_date ? dayjs(viewRecord.expiry_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="质量标准" span={1}>{viewRecord.standard_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="版本" span={1}>{viewRecord.standard_version || '-'}</Descriptions.Item>
              <Descriptions.Item label="研发人员" span={1}>{viewRecord.developer_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态" span={1}>
                <Tag color={StabilityStudyStatusColors[viewRecord.status]}>
                  {StabilityStudyStatusLabels[viewRecord.status]}
                </Tag>
              </Descriptions.Item>
            </Descriptions>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="备注">{viewRecord.remark || '-'}</Descriptions.Item>
            </Descriptions>

            {sampleNodes.length > 0 && (
              <>
                <Divider>取样节点</Divider>
                <Table
                  size="small"
                  dataSource={sampleNodes}
                  rowKey="id"
                  pagination={false}
                  scroll={{ x: 800 }}
                  columns={[
                    { title: '项次', dataIndex: 'node_no', width: 60 },
                    { title: '月数', dataIndex: 'node_month', width: 80 },
                    { title: '节点名称', dataIndex: 'node_name', width: 120 },
                    {
                      title: '计划日期',
                      dataIndex: 'planned_date',
                      width: 120,
                      render: (v: string) => v || '-',
                    },
                    { title: '取样数量', dataIndex: 'sample_quantity', width: 100 },
                    {
                      title: '状态',
                      dataIndex: 'status',
                      width: 100,
                      render: (v: SampleNodeStatus) => (
                        <Tag color={SampleNodeStatusColors[v]}>
                          {SampleNodeStatusLabels[v]}
                        </Tag>
                      ),
                    },
                  ]}
                />
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  )
}
