'use client'

import { useState, useCallback } from 'react'
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
  Alert,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
  LockOutlined,
  UnlockOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  IPQCInspection,
  IPQCInspectionListItem,
  IPQCInspectionCreate,
  IPQCInspectionItemCreate,
  IPQCInspectionFilter,
  IPQCInspectionStatus,
  IPQCInspectionStatusLabels,
  IPQCInspectionStatusColors,
  IPQCInspectionConclusion,
  IPQCInspectionConclusionLabels,
  IPQCInspectionConclusionColors,
  IPQCItemResult,
  IPQCItemResultLabels,
} from '@/types/ipqc'
import {
  getIPQCInspections,
  getIPQCInspection,
  createIPQCInspection,
  updateIPQCInspection,
  deleteIPQCInspection,
  submitIPQCInspectionForApproval,
  approveIPQCInspection,
  lockIPQCBatch,
  unlockIPQCBatch,
} from '@/actions/quality'

const { RangePicker } = DatePicker
const { Text } = Typography
const { TextArea } = Input

// 初始筛选条件
const initialFilters: IPQCInspectionFilter = {
  inspection_no: '',
  batch_no: '',
  product_code: '',
  product_name: '',
  process_stage: '',
  status: undefined,
  inspection_conclusion: undefined,
  batch_locked: undefined,
  start_date: undefined,
  end_date: undefined,
}

export default function IPQCPage() {
  // 状态
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<IPQCInspectionListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<IPQCInspectionFilter>(initialFilters)

  // 弹窗状态
  const [modalVisible, setModalVisible] = useState(false)
  const [modalTitle, setModalTitle] = useState('新建IPQC检验单')
  const [editingRecord, setEditingRecord] = useState<IPQCInspection | null>(null)
  const [viewRecord, setViewRecord] = useState<IPQCInspection | null>(null)
  const [viewModalVisible, setViewModalVisible] = useState(false)

  // 表单 - 两个 form 实例
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [items, setItems] = useState<IPQCInspectionItemCreate[]>([])
  const [submitLoading, setSubmitLoading] = useState(false)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getIPQCInspections({
        ...filters,
        page,
        page_size: pageSize,
      }) as { items?: IPQCInspectionListItem[]; total?: number; code?: number; message?: string; data?: { items?: IPQCInspectionListItem[]; total?: number } }
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
    setModalTitle('新建IPQC检验单')
    form.resetFields()
    setItems([])
    setModalVisible(true)
  }

  // 编辑
  const handleEdit = async (record: IPQCInspectionListItem) => {
    try {
      const response = await getIPQCInspection(record.id) as { code?: number; message?: string; data?: IPQCInspection }
      if (response.code === 200 || response.code === 0) {
        setEditingRecord(response.data!)
        setModalTitle('编辑IPQC检验单')
        editForm.setFieldsValue({
          ...response.data,
          sampling_time: response.data?.sampling_time ? dayjs(response.data.sampling_time) : null,
          production_date: response.data?.production_date ? dayjs(response.data.production_date) : null,
          inspection_date: response.data?.inspection_date ? dayjs(response.data.inspection_date) : null,
        })
        setItems(response.data?.items?.map((item: any, index: number) => ({
          item_no: index + 1,
          inspection_item: item.inspection_item,
          inspection_method: item.inspection_method,
          standard_value: item.standard_value,
          upper_limit: item.upper_limit,
          lower_limit: item.lower_limit,
          unit: item.unit,
          measured_value: item.measured_value,
          result: item.result,
          is_repeat_test: item.is_repeat_test,
          repeat_times: item.repeat_times,
          raw_data: item.raw_data,
          remark: item.remark,
        })) || [])
        setModalVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  // 查看详情
  const handleView = async (record: IPQCInspectionListItem) => {
    try {
      const response = await getIPQCInspection(record.id) as { code?: number; message?: string; data?: IPQCInspection }
      if (response.code === 200 || response.code === 0) {
        setViewRecord(response.data!)
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
      const response = await deleteIPQCInspection(id) as { code?: number; message?: string }
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
      const response = await submitIPQCInspectionForApproval(id) as { code?: number; message?: string; data?: { status?: string } }
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
      const response = await approveIPQCInspection(id, {
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

  // 锁定批次
  const handleLockBatch = async (id: string) => {
    try {
      const response = await lockIPQCBatch(id, 'IPQC检验不合格，批次锁定') as { code?: number; message?: string }
      if (response.code === 200 || response.code === 0) {
        message.success('批次已锁定')
        loadData()
      } else {
        message.error(response.message || '锁定失败')
      }
    } catch (error) {
      message.error('锁定失败')
    }
  }

  // 解锁批次
  const handleUnlockBatch = async (id: string) => {
    try {
      const response = await unlockIPQCBatch(id) as { code?: number; message?: string }
      if (response.code === 200 || response.code === 0) {
        message.success('批次已解锁')
        loadData()
      } else {
        message.error(response.message || '解锁失败')
      }
    } catch (error) {
      message.error('解锁失败')
    }
  }

  // 提交表单
  const handleSubmitForm = async () => {
    try {
      const values = editingRecord ? await editForm.validateFields() : await form.validateFields()

      const submitData: IPQCInspectionCreate = {
        ...values,
        sampling_time: values.sampling_time?.format('YYYY-MM-DDTHH:mm:ss'),
        production_date: values.production_date?.format('YYYY-MM-DDTHH:mm:ss'),
        inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
        items: items.map((item, index) => ({
          ...item,
          item_no: index + 1,
        })),
      }

      setSubmitLoading(true)

      let response: { code?: number; message?: string; data?: { inspection_no?: string; id?: string } }
      if (editingRecord) {
        response = await updateIPQCInspection(editingRecord.id, submitData) as typeof response
      } else {
        response = await createIPQCInspection(submitData) as typeof response
      }

      if (response.code === 200 || response.code === 0 || response.data?.inspection_no) {
        message.success(editingRecord ? '更新成功' : '创建成功')
        setModalVisible(false)
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

  // 保存并提交审批
  const handleSaveAndSubmit = async () => {
    try {
      // 根据编辑状态选择正确的表单
      const activeForm = editingRecord ? editForm : form
      const values = await activeForm.validateFields()

      // 前端验证：必须添加检验明细
      if (items.length === 0) {
        message.error('请先添加至少一条检验明细')
        return
      }

      // 前端验证：必须填写检验结论
      if (!values.inspection_conclusion) {
        message.error('请先选择检验结论')
        return
      }

      let recordId = editingRecord?.id

      // 如果是新建，先保存
      if (!recordId) {
        const submitData: IPQCInspectionCreate = {
          ...(await values),
          sampling_time: (await values).sampling_time?.format('YYYY-MM-DDTHH:mm:ss'),
          production_date: (await values).production_date?.format('YYYY-MM-DDTHH:mm:ss'),
          inspection_date: (await values).inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
          items: items.map((item, index) => ({
            ...item,
            item_no: index + 1,
          })),
        }

        setSubmitLoading(true)
        const createResponse = await createIPQCInspection(submitData) as { code?: number; message?: string; data?: { id?: string } }
        if (createResponse.code !== 200 && createResponse.code !== 0) {
          message.error(createResponse.message || '保存失败')
          setSubmitLoading(false)
          return
        }
        recordId = createResponse.data?.id
      } else {
        // 如果是编辑，先更新
        const submitData: IPQCInspectionCreate = {
          ...(await values),
          sampling_time: (await values).sampling_time?.format('YYYY-MM-DDTHH:mm:ss'),
          production_date: (await values).production_date?.format('YYYY-MM-DDTHH:mm:ss'),
          inspection_date: (await values).inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
          items: items.map((item, index) => ({
            ...item,
            item_no: index + 1,
          })),
        }

        setSubmitLoading(true)
        const updateResponse = await updateIPQCInspection(recordId, submitData) as { code?: number; message?: string }
        if (updateResponse.code !== 200 && updateResponse.code !== 0) {
          message.error(updateResponse.message || '保存失败')
          setSubmitLoading(false)
          return
        }
      }

      // 提交审批
      const submitResponse = await submitIPQCInspectionForApproval(recordId!) as { code?: number; message?: string }
      if (submitResponse.code === 200 || submitResponse.code === 0) {
        message.success('保存并提交成功')
        setModalVisible(false)
        loadData()
      } else {
        message.error(submitResponse.message || '提交失败')
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

  // 添加明细
  const handleAddItem = () => {
    const newItem: IPQCInspectionItemCreate = {
      item_no: items.length + 1,
      inspection_item: '',
    }
    setItems([...items, newItem])
  }

  // 删除明细
  const handleRemoveItem = (index: number) => {
    const newItems = items.filter((_, i) => i !== index)
    setItems(newItems.map((item, i) => ({ ...item, item_no: i + 1 })))
  }

  // 更新明细
  const handleUpdateItem = (index: number, field: string, value: unknown) => {
    const newItems = [...items]
    newItems[index] = { ...newItems[index], [field]: value }
    setItems(newItems)
  }

  // 工序/工段选项
  const processStageOptions = [
    { value: '粗品合成', label: '粗品合成' },
    { value: '精制', label: '精制' },
    { value: '结晶', label: '结晶' },
    { value: '过滤', label: '过滤' },
    { value: '干燥', label: '干燥' },
    { value: '粉碎', label: '粉碎' },
    { value: '混合', label: '混合' },
    { value: '分装', label: '分装' },
  ]

  // 表格列定义
  const columns: ColumnsType<IPQCInspectionListItem> = [
    {
      title: '检验单号',
      dataIndex: 'inspection_no',
      key: 'inspection_no',
      width: 150,
      fixed: 'left',
    },
    {
      title: '批次号',
      dataIndex: 'batch_no',
      key: 'batch_no',
      width: 120,
    },
    {
      title: '产品编码',
      dataIndex: 'product_code',
      key: 'product_code',
      width: 120,
    },
    {
      title: '产品名称',
      dataIndex: 'product_name',
      key: 'product_name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '工序/工段',
      dataIndex: 'process_stage',
      key: 'process_stage',
      width: 100,
    },
    {
      title: '取样点',
      dataIndex: 'sampling_point',
      key: 'sampling_point',
      width: 120,
    },
    {
      title: '取样时间',
      dataIndex: 'sampling_time',
      key: 'sampling_time',
      width: 160,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '-',
    },
    {
      title: '检验员',
      dataIndex: 'inspector_name',
      key: 'inspector_name',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 160,
      render: (value: IPQCInspectionStatus) => (
        <Tag color={IPQCInspectionStatusColors[value]}>
          {IPQCInspectionStatusLabels[value]}
        </Tag>
      ),
    },
    {
      title: '检验结论',
      dataIndex: 'inspection_conclusion',
      key: 'inspection_conclusion',
      width: 100,
      render: (value: IPQCInspectionConclusion) => value ? (
        <Tag color={IPQCInspectionConclusionColors[value]}>
          {IPQCInspectionConclusionLabels[value]}
        </Tag>
      ) : '-',
    },
    {
      title: '批次锁定',
      dataIndex: 'batch_locked',
      key: 'batch_locked',
      width: 90,
      render: (value: boolean) => value ? (
        <Tag color="error" icon={<LockOutlined />}>已锁定</Tag>
      ) : (
        <Tag color="success">正常</Tag>
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
      width: 280,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {(record.status === IPQCInspectionStatus.DRAFT || record.status === IPQCInspectionStatus.REJECTED) && (
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
          {record.status === IPQCInspectionStatus.DRAFT && (
            <Button type="primary" size="small" onClick={() => handleSubmit(record.id)}>
              提交
            </Button>
          )}
          {(record.status === IPQCInspectionStatus.SUBMITTED || 
            record.status === IPQCInspectionStatus.WORKSHOP_APPROVED || 
            record.status === IPQCInspectionStatus.QC_SUPERVISOR_APPROVED) && (
            <>
              <Button type="primary" size="small" icon={<CheckOutlined />} onClick={() => handleApprove(record.id, true)}>
                通过
              </Button>
              <Button danger size="small" icon={<CloseOutlined />} onClick={() => handleApprove(record.id, false)}>
                驳回
              </Button>
            </>
          )}
          {record.batch_locked ? (
            <Button size="small" icon={<UnlockOutlined />} onClick={() => handleUnlockBatch(record.id)}>
              解锁
            </Button>
          ) : (
            record.inspection_conclusion === IPQCInspectionConclusion.UNQUALIFIED && (
              <Button size="small" danger icon={<LockOutlined />} onClick={() => handleLockBatch(record.id)}>
                锁定
              </Button>
            )
          )}
        </Space>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Input
                placeholder="检验单号"
                value={filters.inspection_no}
                onChange={(e) => setFilters({ ...filters, inspection_no: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="批次号"
                value={filters.batch_no}
                onChange={(e) => setFilters({ ...filters, batch_no: e.target.value })}
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
                placeholder="工序/工段"
                value={filters.process_stage}
                onChange={(value) => setFilters({ ...filters, process_stage: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {processStageOptions.map((opt) => (
                  <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
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
                {Object.entries(IPQCInspectionStatusLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={4}>
              <Select
                placeholder="检验结论"
                value={filters.inspection_conclusion}
                onChange={(value) => setFilters({ ...filters, inspection_conclusion: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(IPQCInspectionConclusionLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="批次状态"
                value={filters.batch_locked}
                onChange={(value) => setFilters({ ...filters, batch_locked: value })}
                allowClear
                style={{ width: '100%' }}
              >
                <Select.Option value={true}>已锁定</Select.Option>
                <Select.Option value={false}>正常</Select.Option>
              </Select>
            </Col>
            <Col span={8}>
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
            <Col span={8} style={{ textAlign: 'right' }}>
              <Space>
                <Button type="primary" onClick={handleSearch}>查询</Button>
                <Button onClick={handleReset}>重置</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
                  新建检验单
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
          scroll={{ x: 2000 }}
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
      <Modal
        title={modalTitle}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        width={1100}
        footer={
          <Space>
            <Button onClick={() => setModalVisible(false)}>取消</Button>
            <Button onClick={handleSubmitForm} loading={submitLoading}>
              {editingRecord ? '保存' : '创建'}
            </Button>
            {editingRecord && (editingRecord.status === IPQCInspectionStatus.DRAFT || editingRecord.status === IPQCInspectionStatus.REJECTED) && (
              <Button type="primary" onClick={handleSaveAndSubmit} loading={submitLoading}>
                保存并提交审批
              </Button>
            )}
          </Space>
        }
      >
        <Form
          form={editingRecord ? editForm : form}
          layout="vertical"
          initialValues={editingRecord || undefined}
        >
          <Divider>批次信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="batch_record_no" label="关联批次生产记录单号">
                <Input placeholder="批次生产记录单号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="batch_no" label="批次号">
                <Input placeholder="请输入批次号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="product_code" label="产品编码" rules={[{ required: true }]}>
                <Input placeholder="请输入产品编码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="product_name" label="产品名称">
                <Input placeholder="请输入产品名称" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="product_specification" label="产品规格">
                <Input placeholder="产品规格" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="production_date" label="生产日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider>工序取样信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="process_stage" label="工序/工段">
                <Select placeholder="请选择工序/工段">
                  {processStageOptions.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_point" label="取样点">
                <Input placeholder="请输入取样点" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_no" label="取样单号">
                <Input placeholder="取样单号" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="sampling_time" label="取样时间">
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_quantity" label="取样数量">
                <InputNumber style={{ width: '100%' }} placeholder="取样数量" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_unit" label="取样单位">
                <Input placeholder="取样单位" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="sampling_location" label="取样位置">
                <Input placeholder="取样位置" />
              </Form.Item>
            </Col>
          </Row>

          <Divider>检验信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="inspection_date" label="检验日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="inspector_name" label="检验员">
                <Input placeholder="检验员姓名" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="standard_name" label="检验标准">
                <Input placeholder="检验标准名称" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="inspection_conclusion" label="检验结论">
                <Select placeholder="请选择检验结论">
                  {Object.entries(IPQCInspectionConclusionLabels).map(([value, label]) => (
                    <Select.Option key={value} value={value}>{label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="oos_report_no" label="OOS报告编号">
                <Input placeholder="OOS报告编号" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={24}>
              <Form.Item name="conclusion_reason" label="结论说明">
                <TextArea rows={2} placeholder="请输入结论说明" />
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
        </Form>

        <Divider>检验结果明细</Divider>
        {editingRecord?.inspection_conclusion === IPQCInspectionConclusion.UNQUALIFIED && (
          <Alert
            message="检验结论为不合格，检验完成后请确认是否需要生成偏差或OOS报告"
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
          />
        )}
        <Button type="dashed" onClick={handleAddItem} style={{ marginBottom: 16 }} icon={<PlusOutlined />}>
          添加检验项目
        </Button>

        {items.length > 0 && (
          <Table
            size="small"
            dataSource={items.map((item, index) => ({ ...item, key: index }))}
            columns={[
              { title: '项次', dataIndex: 'item_no', width: 60 },
              {
                title: '检验项目',
                dataIndex: 'inspection_item',
                width: 150,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'inspection_item', e.target.value)}
                    placeholder="检验项目"
                  />
                ),
              },
              {
                title: '检验方法',
                dataIndex: 'inspection_method',
                width: 120,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'inspection_method', e.target.value)}
                    placeholder="检验方法"
                  />
                ),
              },
              {
                title: '标准值',
                dataIndex: 'standard_value',
                width: 100,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'standard_value', e.target.value)}
                    placeholder="标准值"
                  />
                ),
              },
              {
                title: '上限',
                dataIndex: 'upper_limit',
                width: 80,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'upper_limit', e.target.value)}
                    placeholder="上限"
                  />
                ),
              },
              {
                title: '下限',
                dataIndex: 'lower_limit',
                width: 80,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'lower_limit', e.target.value)}
                    placeholder="下限"
                  />
                ),
              },
              {
                title: '单位',
                dataIndex: 'unit',
                width: 70,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'unit', e.target.value)}
                    placeholder="单位"
                  />
                ),
              },
              {
                title: '实测值',
                dataIndex: 'measured_value',
                width: 100,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'measured_value', e.target.value)}
                    placeholder="实测值"
                  />
                ),
              },
              {
                title: '单项判定',
                dataIndex: 'result',
                width: 100,
                render: (value, _record, index) => (
                  <Select
                    value={value}
                    onChange={(v) => handleUpdateItem(index, 'result', v)}
                    placeholder="判定"
                    style={{ width: '100%' }}
                  >
                    {Object.entries(IPQCItemResultLabels).map(([val, label]) => (
                      <Select.Option key={val} value={val}>{label}</Select.Option>
                    ))}
                  </Select>
                ),
              },
              {
                title: '备注',
                dataIndex: 'remark',
                width: 100,
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'remark', e.target.value)}
                    placeholder="备注"
                  />
                ),
              },
              {
                title: '操作',
                width: 80,
                render: (_: unknown, __: unknown, index: number) => (
                  <Button type="link" danger size="small" onClick={() => handleRemoveItem(index)}>
                    删除
                  </Button>
                ),
              },
            ]}
            pagination={false}
            scroll={{ x: 1400 }}
          />
        )}
      </Modal>

      {/* 查看详情弹窗 */}
      <Modal
        title="IPQC检验单详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={null}
        width={1000}
      >
        {viewRecord && (
          <>
            {viewRecord.batch_locked && (
              <Alert
                message="批次已锁定"
                description={viewRecord.batch_lock_reason}
                type="error"
                showIcon
                icon={<LockOutlined />}
                style={{ marginBottom: 16 }}
              />
            )}
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="检验单号">{viewRecord.inspection_no}</Descriptions.Item>
              <Descriptions.Item label="批次号">{viewRecord.batch_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="批次状态">
                {viewRecord.batch_locked ? <Tag color="error">已锁定</Tag> : <Tag color="success">正常</Tag>}
              </Descriptions.Item>
              <Descriptions.Item label="产品编码">{viewRecord.product_code}</Descriptions.Item>
              <Descriptions.Item label="产品名称">{viewRecord.product_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="产品规格">{viewRecord.product_specification || '-'}</Descriptions.Item>
              <Descriptions.Item label="工序/工段">{viewRecord.process_stage || '-'}</Descriptions.Item>
              <Descriptions.Item label="取样点">{viewRecord.sampling_point || '-'}</Descriptions.Item>
              <Descriptions.Item label="取样单号">{viewRecord.sampling_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="取样时间">
                {viewRecord.sampling_time ? dayjs(viewRecord.sampling_time).format('YYYY-MM-DD HH:mm') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="取样数量">
                {viewRecord.sampling_quantity ? `${viewRecord.sampling_quantity} ${viewRecord.sampling_unit || ''}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="取样位置">{viewRecord.sampling_location || '-'}</Descriptions.Item>
              <Descriptions.Item label="生产日期">
                {viewRecord.production_date ? dayjs(viewRecord.production_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="检验日期">
                {viewRecord.inspection_date ? dayjs(viewRecord.inspection_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="检验员">{viewRecord.inspector_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="检验标准">{viewRecord.standard_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="OOS报告编号">{viewRecord.oos_report_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={IPQCInspectionStatusColors[viewRecord.status]}>
                  {IPQCInspectionStatusLabels[viewRecord.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="检验结论">
                {viewRecord.inspection_conclusion ? (
                  <Tag color={IPQCInspectionConclusionColors[viewRecord.inspection_conclusion]}>
                    {IPQCInspectionConclusionLabels[viewRecord.inspection_conclusion]}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="结论说明" span={2}>{viewRecord.conclusion_reason || '-'}</Descriptions.Item>
              <Descriptions.Item label="备注" span={3}>{viewRecord.remark || '-'}</Descriptions.Item>
            </Descriptions>

            {viewRecord.items && viewRecord.items.length > 0 && (
              <>
                <Divider>检验结果明细</Divider>
                <Table
                  size="small"
                  dataSource={viewRecord.items}
                  rowKey="id"
                  pagination={false}
                  scroll={{ x: 1200 }}
                  columns={[
                    { title: '项次', dataIndex: 'item_no', width: 60 },
                    { title: '检验项目', dataIndex: 'inspection_item', width: 150 },
                    { title: '检验方法', dataIndex: 'inspection_method', width: 120 },
                    { title: '标准值', dataIndex: 'standard_value', width: 100 },
                    { title: '上限', dataIndex: 'upper_limit', width: 80 },
                    { title: '下限', dataIndex: 'lower_limit', width: 80 },
                    { title: '单位', dataIndex: 'unit', width: 60 },
                    { title: '实测值', dataIndex: 'measured_value', width: 100 },
                    {
                      title: '单项判定',
                      dataIndex: 'result',
                      width: 100,
                      render: (v: IPQCItemResult) => v ? IPQCItemResultLabels[v] : '-',
                    },
                    { title: '备注', dataIndex: 'remark' },
                  ]}
                />
              </>
            )}

            {viewRecord.deviation_id && (
              <>
                <Divider>关联偏差</Divider>
                <Alert message={`偏差ID: ${viewRecord.deviation_id}`} type="info" showIcon />
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  )
}
