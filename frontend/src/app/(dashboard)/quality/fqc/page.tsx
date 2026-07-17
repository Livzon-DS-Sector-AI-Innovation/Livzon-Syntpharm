'use client'

import { useState, useCallback, useRef } from 'react'
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
  PrinterOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  FQCInspection,
  FQCInspectionListItem,
  FQCInspectionCreate,
  FQCInspectionItemCreate,
  FQCInspectionFilter,
  FQCInspectionStatus,
  FQCInspectionStatusLabels,
  FQCInspectionStatusColors,
  FQCInspectionConclusion,
  FQCInspectionConclusionLabels,
  FQCInspectionConclusionColors,
  FQCItemResult,
  FQCItemResultLabels,
  FQCInspectionCategory,
  FQCInspectionCategoryLabels,
  FQCReleaseStatus,
  FQCReleaseStatusLabels,
} from '@/types/fqc'
import {
  getFQCInspections,
  getFQCInspection,
  createFQCInspection,
  updateFQCInspection,
  deleteFQCInspection,
  submitFQCInspectionForApproval,
  approveFQCInspection,
  applyFQCReinspection,
  releaseFQCInspection,
  lockFQCBatch,
  unlockFQCBatch,
} from '@/actions/quality'

const { RangePicker } = DatePicker
const { Text } = Typography
const { TextArea } = Input

// 初始筛选条件
const initialFilters: FQCInspectionFilter = {
  inspection_no: '',
  batch_no: '',
  product_code: '',
  product_name: '',
  production_workshop: '',
  status: undefined,
  inspection_conclusion: undefined,
  release_status: undefined,
  batch_locked: undefined,
  start_date: undefined,
  end_date: undefined,
}

export default function FQCPage() {
  // 状态
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<FQCInspectionListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<FQCInspectionFilter>(initialFilters)

  // 弹窗状态 - 新建和编辑使用不同的弹窗
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [modalTitle, setModalTitle] = useState('新建FQC检验单')
  const [editingRecord, setEditingRecord] = useState<FQCInspection | null>(null)
  const [viewRecord, setViewRecord] = useState<FQCInspection | null>(null)
  const [viewModalVisible, setViewModalVisible] = useState(false)

  // 表单 - 只有一个 form 实例用于新建
  const [createForm] = Form.useForm()
  const [items, setItems] = useState<FQCInspectionItemCreate[]>([])
  const [submitLoading, setSubmitLoading] = useState(false)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getFQCInspections({
        ...filters,
        page,
        page_size: pageSize,
      }) as { items?: FQCInspectionListItem[]; total?: number; code?: number; message?: string; data?: { items?: FQCInspectionListItem[]; total?: number } }
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
    setModalTitle('新建FQC检验单')
    createForm.resetFields()
    setItems([])
    setCreateModalVisible(true)
  }

  // 编辑
  const handleEdit = async (record: FQCInspectionListItem) => {
    try {
      const response = await getFQCInspection(record.id) as { code?: number; message?: string; data?: FQCInspection }
      if (response.code === 200 || response.code === 0) {
        setEditingRecord(response.data!)
        setModalTitle('编辑FQC检验单')
        createForm.setFieldsValue({
          ...response.data,
          manufacturing_date: response.data?.manufacturing_date ? dayjs(response.data.manufacturing_date) : null,
          expiry_date: response.data?.expiry_date ? dayjs(response.data.expiry_date) : null,
          inspection_date: response.data?.inspection_date ? dayjs(response.data.inspection_date) : null,
        })
        setItems(response.data?.items?.map((item: any, index: number) => ({
          item_no: index + 1,
          inspection_category: item.inspection_category,
          inspection_item: item.inspection_item,
          inspection_method: item.inspection_method,
          standard_value: item.standard_value,
          unit: item.unit,
          measured_value: item.measured_value,
          result: item.result,
          is_oos: item.is_oos,
          oos_description: item.oos_description,
          is_repeat_test: item.is_repeat_test,
          repeat_times: item.repeat_times,
          remark: item.remark,
        })) || [])
        setCreateModalVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  // 查看详情
  const handleView = async (record: FQCInspectionListItem) => {
    try {
      const response = await getFQCInspection(record.id) as { code?: number; message?: string; data?: FQCInspection }
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
      const response = await deleteFQCInspection(id) as { code?: number; message?: string }
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
      const response = await submitFQCInspectionForApproval(id) as { code?: number; message?: string; data?: { status?: string } }
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
      const response = await approveFQCInspection(id, {
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

  // 申请复检
  const handleReinspection = async (id: string) => {
    Modal.confirm({
      title: '申请复检',
      content: '请输入复检原因：',
      okText: '确认',
      cancelText: '取消',
      onOk: async () => {
        const reason = '申请复检' // 实际应该让用户输入
        try {
          const response = await applyFQCReinspection(id, reason) as { code?: number; message?: string }
          if (response.code === 200 || response.code === 0) {
            message.success('复检申请已提交')
            loadData()
          } else {
            message.error(response.message || '申请失败')
          }
        } catch (error) {
          message.error('申请失败')
        }
      },
    })
  }

  // 放行
  const handleRelease = async (id: string) => {
    try {
      const response = await releaseFQCInspection(id) as { code?: number; message?: string }
      if (response.code === 200 || response.code === 0) {
        message.success('放行成功')
        loadData()
      } else {
        message.error(response.message || '放行失败')
      }
    } catch (error) {
      message.error('放行失败')
    }
  }

  // 锁定批次
  const handleLockBatch = async (id: string) => {
    try {
      const response = await lockFQCBatch(id, 'FQC检验不合格，批次锁定') as { code?: number; message?: string }
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
      const response = await unlockFQCBatch(id) as { code?: number; message?: string }
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

  // 提交新建表单
  const handleSubmitForm = async () => {
    try {
      const values = await createForm.validateFields()

      const submitData: FQCInspectionCreate = {
        ...values,
        manufacturing_date: values.manufacturing_date?.format('YYYY-MM-DDTHH:mm:ss'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DDTHH:mm:ss'),
        inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
        items: items.map((item, index) => ({
          ...item,
          item_no: index + 1,
        })),
      }

      setSubmitLoading(true)

      let response: { code?: number; message?: string; data?: { inspection_no?: string; id?: string } }
      if (editingRecord) {
        response = await updateFQCInspection(editingRecord.id, submitData) as typeof response
      } else {
        response = await createFQCInspection(submitData) as typeof response
      }

      if (response.code === 200 || response.code === 0 || response.data?.inspection_no) {
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

  // 保存并提交审批（新建）
  const handleSaveAndSubmit = async () => {
    try {
      const values = await createForm.validateFields()

      // 前端验证
      if (items.length === 0) {
        message.error('请先添加至少一条检验明细')
        return
      }
      if (!values.inspection_conclusion) {
        message.error('请先选择检验结论')
        return
      }

      let recordId = editingRecord?.id

      if (!recordId) {
        const submitData: FQCInspectionCreate = {
          ...values,
          manufacturing_date: values.manufacturing_date?.format('YYYY-MM-DDTHH:mm:ss'),
          expiry_date: values.expiry_date?.format('YYYY-MM-DDTHH:mm:ss'),
          inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
          items: items.map((item, index) => ({
            ...item,
            item_no: index + 1,
          })),
        }

        setSubmitLoading(true)
        const createResponse = await createFQCInspection(submitData) as { code?: number; message?: string; data?: { id?: string } }
        if (createResponse.code !== 200 && createResponse.code !== 0) {
          message.error(createResponse.message || '保存失败')
          setSubmitLoading(false)
          return
        }
        recordId = createResponse.data?.id
      } else {
        const submitData: FQCInspectionCreate = {
          ...values,
          manufacturing_date: values.manufacturing_date?.format('YYYY-MM-DDTHH:mm:ss'),
          expiry_date: values.expiry_date?.format('YYYY-MM-DDTHH:mm:ss'),
          inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
          items: items.map((item, index) => ({
            ...item,
            item_no: index + 1,
          })),
        }

        setSubmitLoading(true)
        const updateResponse = await updateFQCInspection(recordId, submitData) as { code?: number; message?: string }
        if (updateResponse.code !== 200 && updateResponse.code !== 0) {
          message.error(updateResponse.message || '保存失败')
          setSubmitLoading(false)
          return
        }
      }

      // 提交审批
      const submitResponse = await submitFQCInspectionForApproval(recordId!) as { code?: number; message?: string }
      if (submitResponse.code === 200 || submitResponse.code === 0) {
        message.success('保存并提交成功')
        setCreateModalVisible(false)
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
    const newItem: FQCInspectionItemCreate = {
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

  // 检验类别选项
  const categoryOptions = [
    { value: FQCInspectionCategory.CONTENT, label: '含量' },
    { value: FQCInspectionCategory.RELATED_SUBSTANCES, label: '有关物质' },
    { value: FQCInspectionCategory.RESIDUAL_SOLVENTS, label: '残留溶剂' },
    { value: FQCInspectionCategory.PHYSICAL_CHEMICAL, label: '理化' },
    { value: FQCInspectionCategory.MICROBIOLOGY, label: '微生物' },
  ]

  // 表格列定义
  const columns: ColumnsType<FQCInspectionListItem> = [
    {
      title: '检验单号',
      dataIndex: 'inspection_no',
      key: 'inspection_no',
      width: 150,
      fixed: 'left',
    },
    {
      title: '成品批号',
      dataIndex: 'batch_no',
      key: 'batch_no',
      width: 120,
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
      title: '生产车间',
      dataIndex: 'production_workshop',
      key: 'production_workshop',
      width: 100,
    },
    {
      title: '批量',
      dataIndex: 'batch_quantity',
      key: 'batch_quantity',
      width: 80,
    },
    {
      title: '检验日期',
      dataIndex: 'inspection_date',
      key: 'inspection_date',
      width: 110,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD') : '-',
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
      width: 130,
      render: (value: FQCInspectionStatus) => (
        <Tag color={FQCInspectionStatusColors[value]}>
          {FQCInspectionStatusLabels[value]}
        </Tag>
      ),
    },
    {
      title: '检验结论',
      dataIndex: 'inspection_conclusion',
      key: 'inspection_conclusion',
      width: 90,
      render: (value: FQCInspectionConclusion) => value ? (
        <Tag color={FQCInspectionConclusionColors[value]}>
          {FQCInspectionConclusionLabels[value]}
        </Tag>
      ) : '-',
    },
    {
      title: '放行状态',
      dataIndex: 'release_status',
      key: 'release_status',
      width: 90,
      render: (value: FQCReleaseStatus) => value ? (
        <Tag>{FQCReleaseStatusLabels[value]}</Tag>
      ) : '-',
    },
    {
      title: '批次状态',
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
      width: 320,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small" wrap>
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {(record.status === FQCInspectionStatus.DRAFT || record.status === FQCInspectionStatus.REJECTED) && (
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
          {record.status === FQCInspectionStatus.DRAFT && (
            <Button type="primary" size="small" onClick={() => handleSubmit(record.id)}>
              提交
            </Button>
          )}
          {(record.status === FQCInspectionStatus.SUBMITTED || 
            record.status === FQCInspectionStatus.QC_SUPERVISOR_APPROVED || 
            record.status === FQCInspectionStatus.QA_APPROVED) && (
            <>
              <Button type="primary" size="small" icon={<CheckOutlined />} onClick={() => handleApprove(record.id, true)}>
                通过
              </Button>
              <Button danger size="small" icon={<CloseOutlined />} onClick={() => handleApprove(record.id, false)}>
                驳回
              </Button>
            </>
          )}
          {record.status === FQCInspectionStatus.FINAL_APPROVED && record.inspection_conclusion === FQCInspectionConclusion.QUALIFIED && !record.batch_locked && (
            <Button type="primary" size="small" icon={<CheckOutlined />} onClick={() => handleRelease(record.id)}>
              放行
            </Button>
          )}
          {record.inspection_conclusion === FQCInspectionConclusion.UNQUALIFIED && (
            record.batch_locked ? (
              <Button size="small" icon={<UnlockOutlined />} onClick={() => handleUnlockBatch(record.id)}>
                解锁
              </Button>
            ) : (
              <Button size="small" danger icon={<LockOutlined />} onClick={() => handleLockBatch(record.id)}>
                锁定
              </Button>
            )
          )}
          {(record.status === FQCInspectionStatus.FINAL_APPROVED || record.status === FQCInspectionStatus.LOCKED) && 
           record.inspection_conclusion === FQCInspectionConclusion.UNQUALIFIED && (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => handleReinspection(record.id)}>
              复检
            </Button>
          )}
          <Button size="small" icon={<PrinterOutlined />}>
            打印
          </Button>
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
                placeholder="成品批号"
                value={filters.batch_no}
                onChange={(e) => setFilters({ ...filters, batch_no: e.target.value })}
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
              <Input
                placeholder="生产车间"
                value={filters.production_workshop}
                onChange={(e) => setFilters({ ...filters, production_workshop: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="状态"
                value={filters.status}
                onChange={(value) => setFilters({ ...filters, status: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(FQCInspectionStatusLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="检验结论"
                value={filters.inspection_conclusion}
                onChange={(value) => setFilters({ ...filters, inspection_conclusion: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(FQCInspectionConclusionLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 12 }}>
            <Col span={4}>
              <Select
                placeholder="放行状态"
                value={filters.release_status}
                onChange={(value) => setFilters({ ...filters, release_status: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(FQCReleaseStatusLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
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
            <Col span={12} style={{ textAlign: 'right' }}>
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
          scroll={{ x: 2200 }}
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

      {/* 新建弹窗 - 条件渲染确保 Form 只在 Modal 打开时挂载 */}
      {createModalVisible && (
      <Modal
        title="新建FQC检验单"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        destroyOnHidden
        width={1200}
        footer={
          <Space>
            <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
            <Button onClick={handleSubmitForm} loading={submitLoading}>创建</Button>
          </Space>
        }
      >
        <Form
          form={createForm}
          layout="vertical"
        >
          <Divider>单据关联信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="batch_record_no" label="批生产记录编号">
                <Input placeholder="批生产记录编号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="batch_no" label="成品生产批号">
                <Input placeholder="请输入成品批号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="product_code" label="成品物料编码" rules={[{ required: true }]}>
                <Input placeholder="请输入物料编码" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="product_name" label="产品名称">
                <Input placeholder="产品名称" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_order_no" label="入库取样单号">
                <Input placeholder="取样单号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="batch_quantity" label="批量">
                <InputNumber style={{ width: '100%' }} placeholder="批量" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="production_workshop" label="生产车间">
                <Input placeholder="生产车间" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="standard_name" label="质量标准">
                <Input placeholder="质量标准名称" />
              </Form.Item>
            </Col>
          </Row>

          <Divider>基础信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="cas_no" label="CAS号">
                <Input placeholder="CAS号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="manufacturer" label="生产厂家">
                <Input placeholder="生产厂家" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="specification" label="产品规格/包装">
                <Input placeholder="产品规格/包装" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="manufacturing_date" label="生产日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="expiry_date" label="有效期至">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="inspection_date" label="检验日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="inspector_name" label="检验员">
                <Input placeholder="检验员" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="inspection_conclusion" label="检验结论">
                <Select placeholder="请选择检验结论">
                  {Object.entries(FQCInspectionConclusionLabels).map(([value, label]) => (
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
        {editingRecord?.inspection_conclusion === FQCInspectionConclusion.UNQUALIFIED && (
          <Alert
            message="检验结论为不合格，请确认是否已生成OOS报告，批次将被锁定禁止放行"
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
                title: '检验类别',
                dataIndex: 'inspection_category',
                width: 120,
                render: (value, _record, index) => (
                  <Select
                    value={value}
                    onChange={(v) => handleUpdateItem(index, 'inspection_category', v)}
                    placeholder="检验类别"
                    style={{ width: '100%' }}
                  >
                    {categoryOptions.map((opt) => (
                      <Select.Option key={opt.value} value={opt.value}>{opt.label}</Select.Option>
                    ))}
                  </Select>
                ),
              },
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
                title: '标准值/限度',
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
                title: '单位',
                dataIndex: 'unit',
                width: 60,
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
                    {Object.entries(FQCItemResultLabels).map(([val, label]) => (
                      <Select.Option key={val} value={val}>{label}</Select.Option>
                    ))}
                  </Select>
                ),
              },
              {
                title: '超标',
                dataIndex: 'is_oos',
                width: 60,
                render: (value: boolean, _record, index) => (
                  <Select
                    value={value}
                    onChange={(v) => handleUpdateItem(index, 'is_oos', v)}
                    style={{ width: '100%' }}
                  >
                    <Select.Option value={false}>否</Select.Option>
                    <Select.Option value={true}>是</Select.Option>
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
            scroll={{ x: 1500 }}
          />
        )}
      </Modal>
      )}

      {/* 查看详情弹窗 */}
      <Modal
        title="FQC检验单详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={null}
        width={1100}
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
              {/* 第1行 */}
              <Descriptions.Item label="检验单号" span={1}>{viewRecord.inspection_no}</Descriptions.Item>
              <Descriptions.Item label="成品批号" span={1}>{viewRecord.batch_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="批次状态" span={1}>
                {viewRecord.batch_locked ? <Tag color="error">已锁定</Tag> : <Tag color="success">正常</Tag>}
              </Descriptions.Item>
              {/* 第2行 */}
              <Descriptions.Item label="产品编码" span={1}>{viewRecord.product_code}</Descriptions.Item>
              <Descriptions.Item label="产品名称" span={1}>{viewRecord.product_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="生产车间" span={1}>{viewRecord.production_workshop || '-'}</Descriptions.Item>
              {/* 第3行 */}
              <Descriptions.Item label="批量" span={1}>{viewRecord.batch_quantity || '-'}</Descriptions.Item>
              <Descriptions.Item label="CAS号" span={1}>{viewRecord.cas_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="生产厂家" span={1}>{viewRecord.manufacturer || '-'}</Descriptions.Item>
              {/* 第4行 */}
              <Descriptions.Item label="生产日期" span={1}>
                {viewRecord.manufacturing_date ? dayjs(viewRecord.manufacturing_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="有效期至" span={1}>
                {viewRecord.expiry_date ? dayjs(viewRecord.expiry_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="产品规格" span={1}>{viewRecord.specification || '-'}</Descriptions.Item>
              {/* 第5行 */}
              <Descriptions.Item label="检验日期" span={1}>
                {viewRecord.inspection_date ? dayjs(viewRecord.inspection_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="检验员" span={1}>{viewRecord.inspector_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="质量标准" span={1}>{viewRecord.standard_name || '-'}</Descriptions.Item>
              {/* 第6行 */}
              <Descriptions.Item label="OOS报告编号" span={1}>{viewRecord.oos_report_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="检验报告编号" span={1}>{viewRecord.report_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态" span={1}>
                <Tag color={FQCInspectionStatusColors[viewRecord.status]}>
                  {FQCInspectionStatusLabels[viewRecord.status]}
                </Tag>
              </Descriptions.Item>
              {/* 第7行 */}
              <Descriptions.Item label="检验结论" span={1}>
                {viewRecord.inspection_conclusion ? (
                  <Tag color={FQCInspectionConclusionColors[viewRecord.inspection_conclusion]}>
                    {FQCInspectionConclusionLabels[viewRecord.inspection_conclusion]}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="放行状态" span={1}>
                {viewRecord.release_status ? FQCReleaseStatusLabels[viewRecord.release_status] : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="结论说明" span={1}>{viewRecord.conclusion_reason || '-'}</Descriptions.Item>
              {/* 第8行 - 备注占满整行 */}
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
                  scroll={{ x: 1400 }}
                  columns={[
                    { title: '项次', dataIndex: 'item_no', width: 60 },
                    { title: '检验类别', dataIndex: 'inspection_category', width: 100,
                      render: (v: FQCInspectionCategory) => v ? FQCInspectionCategoryLabels[v] : '-' },
                    { title: '检验项目', dataIndex: 'inspection_item', width: 150 },
                    { title: '检验方法', dataIndex: 'inspection_method', width: 120 },
                    { title: '标准值/限度', dataIndex: 'standard_value', width: 100 },
                    { title: '单位', dataIndex: 'unit', width: 60 },
                    { title: '实测值', dataIndex: 'measured_value', width: 100 },
                    {
                      title: '单项判定',
                      dataIndex: 'result',
                      width: 80,
                      render: (v: FQCItemResult) => v ? FQCItemResultLabels[v] : '-',
                    },
                    {
                      title: '超标',
                      dataIndex: 'is_oos',
                      width: 60,
                      render: (v: boolean) => v ? <Tag color="error">是</Tag> : '否',
                    },
                    { title: '备注', dataIndex: 'remark' },
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
