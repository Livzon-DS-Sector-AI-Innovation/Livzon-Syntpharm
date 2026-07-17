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
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  IQCInspection,
  IQCInspectionListItem,
  IQCInspectionCreate,
  IQCInspectionItemCreate,
  IQCInspectionFilter,
  IQCSourceType,
  IQCSourceTypeLabels,
  MaterialCategory,
  MaterialCategoryLabels,
  InspectionStatus,
  InspectionStatusLabels,
  InspectionStatusColors,
  InspectionConclusion,
  InspectionConclusionLabels,
  InspectionConclusionColors,
  ItemResult,
  ItemResultLabels,
} from '@/types/iqc'
import {
  getIQCInspections,
  getIQCInspection,
  createIQCInspection,
  updateIQCInspection,
  deleteIQCInspection,
  submitIQCInspectionForApproval,
  approveIQCInspection,
} from '@/actions/quality'

const { RangePicker } = DatePicker
const { Text } = Typography
const { TextArea } = Input

// 初始筛选条件
const initialFilters: IQCInspectionFilter = {
  inspection_no: '',
  material_code: '',
  material_name: '',
  material_category: undefined,
  supplier_name: '',
  status: undefined,
  inspection_conclusion: undefined,
  start_date: undefined,
  end_date: undefined,
}

export default function IQCPage() {
  // 状态
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<IQCInspectionListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<IQCInspectionFilter>(initialFilters)

  // 表单 - 两个 form 实例必须放在一起
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()

  // 弹窗状态
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [createItems, setCreateItems] = useState<IQCInspectionItemCreate[]>([])
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editRecord, setEditRecord] = useState<IQCInspection | null>(null)
  const [editItems, setEditItems] = useState<IQCInspectionItemCreate[]>([])
  const [viewRecord, setViewRecord] = useState<IQCInspection | null>(null)
  const [viewModalVisible, setViewModalVisible] = useState(false)
  const [submitLoading, setSubmitLoading] = useState(false)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getIQCInspections({
        ...filters,
        page,
        page_size: pageSize,
      }) as { items?: IQCInspectionListItem[]; total?: number; code?: number; message?: string; data?: { items?: IQCInspectionListItem[]; total?: number } }
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
    createForm.resetFields()
    setCreateItems([])
    setCreateModalVisible(true)
  }

  // 编辑
  const handleEdit = async (record: IQCInspectionListItem) => {
    try {
      const response = await getIQCInspection(record.id) as { code?: number; message?: string; data?: IQCInspection }
      if (response.code === 200 || response.code === 0) {
        setEditRecord(response.data!)
        editForm.setFieldsValue({
          ...response.data,
          manufacturing_date: response.data?.manufacturing_date ? dayjs(response.data.manufacturing_date) : null,
          expiry_date: response.data?.expiry_date ? dayjs(response.data.expiry_date) : null,
          inspection_date: response.data?.inspection_date ? dayjs(response.data.inspection_date) : null,
        })
        setEditItems(response.data?.items?.map((item: any, index: number) => ({
          item_no: index + 1,
          inspection_item: item.inspection_item,
          inspection_method: item.inspection_method,
          standard_value: item.standard_value,
          unit: item.unit,
          measured_value: item.measured_value,
          result: item.result,
          is_repeat_test: item.is_repeat_test,
          raw_data: item.raw_data,
          remark: item.remark,
        })) || [])
        setEditModalVisible(true)
      } else {
        message.error(response.message || '获取数据失败')
      }
    } catch (error) {
      message.error('获取数据失败')
    }
  }

  // 查看详情
  const handleView = async (record: IQCInspectionListItem) => {
    try {
      const response = await getIQCInspection(record.id) as { code?: number; message?: string; data?: IQCInspection }
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
      const response = await deleteIQCInspection(id) as { code?: number; message?: string }
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
      const response = await submitIQCInspectionForApproval(id) as { code?: number; message?: string; data?: { status?: string } }
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
      const response = await approveIQCInspection(id, {
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

  // 提交新建表单
  const handleCreateSubmit = async () => {
    try {
      const values = await createForm.validateFields()

      const submitData: IQCInspectionCreate = {
        ...values,
        manufacturing_date: values.manufacturing_date?.format('YYYY-MM-DDTHH:mm:ss'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DDTHH:mm:ss'),
        inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
        items: createItems.map((item, index) => ({
          ...item,
          item_no: index + 1,
        })),
      }

      setSubmitLoading(true)
      const response = await createIQCInspection(submitData) as { code?: number; message?: string; data?: { inspection_no?: string } }

      if (response.code === 200 || response.code === 0 || response.data?.inspection_no) {
        message.success('创建成功')
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

  // 提交编辑表单
  const handleEditSubmit = async () => {
    try {
      const values = await editForm.validateFields()

      const submitData: IQCInspectionCreate = {
        ...values,
        manufacturing_date: values.manufacturing_date?.format('YYYY-MM-DDTHH:mm:ss'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DDTHH:mm:ss'),
        inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
        items: editItems.map((item, index) => ({
          ...item,
          item_no: index + 1,
        })),
      }

      setSubmitLoading(true)
      const response = await updateIQCInspection(editRecord!.id, submitData) as { code?: number; message?: string; data?: { inspection_no?: string } }

      if (response.code === 200 || response.code === 0) {
        message.success('更新成功')
        setEditModalVisible(false)
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
  const handleEditSaveAndSubmit = async () => {
    try {
      const values = await editForm.validateFields()

      const submitData: IQCInspectionCreate = {
        ...values,
        manufacturing_date: values.manufacturing_date?.format('YYYY-MM-DDTHH:mm:ss'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DDTHH:mm:ss'),
        inspection_date: values.inspection_date?.format('YYYY-MM-DDTHH:mm:ss'),
        items: editItems.map((item, index) => ({
          ...item,
          item_no: index + 1,
        })),
      }

      setSubmitLoading(true)

      // 先更新
      const updateResponse = await updateIQCInspection(editRecord!.id, submitData) as { code?: number; message?: string }
      if (updateResponse.code !== 200 && updateResponse.code !== 0) {
        message.error(updateResponse.message || '保存失败')
        setSubmitLoading(false)
        return
      }

      // 提交审批
      const submitResponse = await submitIQCInspectionForApproval(editRecord!.id) as { code?: number; message?: string }
      if (submitResponse.code === 200 || submitResponse.code === 0) {
        message.success('保存并提交成功')
        setEditModalVisible(false)
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

  // 新建 - 添加明细
  const handleCreateAddItem = () => {
    const newItem: IQCInspectionItemCreate = {
      item_no: createItems.length + 1,
      inspection_item: '',
    }
    setCreateItems([...createItems, newItem])
  }

  // 新建 - 删除明细
  const handleCreateRemoveItem = (index: number) => {
    const newItems = createItems.filter((_, i) => i !== index)
    setCreateItems(newItems.map((item, i) => ({ ...item, item_no: i + 1 })))
  }

  // 新建 - 更新明细
  const handleCreateUpdateItem = (index: number, field: string, value: unknown) => {
    const newItems = [...createItems]
    newItems[index] = { ...newItems[index], [field]: value }
    setCreateItems(newItems)
  }

  // 编辑 - 添加明细
  const handleEditAddItem = () => {
    const newItem: IQCInspectionItemCreate = {
      item_no: editItems.length + 1,
      inspection_item: '',
    }
    setEditItems([...editItems, newItem])
  }

  // 编辑 - 删除明细
  const handleEditRemoveItem = (index: number) => {
    const newItems = editItems.filter((_, i) => i !== index)
    setEditItems(newItems.map((item, i) => ({ ...item, item_no: i + 1 })))
  }

  // 编辑 - 更新明细
  const handleEditUpdateItem = (index: number, field: string, value: unknown) => {
    const newItems = [...editItems]
    newItems[index] = { ...newItems[index], [field]: value }
    setEditItems(newItems)
  }

  // 表格列定义
  const columns: ColumnsType<IQCInspectionListItem> = [
    {
      title: '检验单号',
      dataIndex: 'inspection_no',
      key: 'inspection_no',
      width: 150,
      fixed: 'left',
    },
    {
      title: '物料编码',
      dataIndex: 'material_code',
      key: 'material_code',
      width: 120,
    },
    {
      title: '物料名称',
      dataIndex: 'material_name',
      key: 'material_name',
      width: 180,
      ellipsis: true,
    },
    {
      title: '批次号',
      dataIndex: 'batch_no',
      key: 'batch_no',
      width: 120,
    },
    {
      title: '供应商',
      dataIndex: 'supplier_name',
      key: 'supplier_name',
      width: 150,
    },
    {
      title: '检验日期',
      dataIndex: 'inspection_date',
      key: 'inspection_date',
      width: 120,
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
      width: 140,
      render: (value: InspectionStatus) => (
        <Tag color={InspectionStatusColors[value]}>
          {InspectionStatusLabels[value]}
        </Tag>
      ),
    },
    {
      title: '检验结论',
      dataIndex: 'inspection_conclusion',
      key: 'inspection_conclusion',
      width: 100,
      render: (value: InspectionConclusion) => value ? (
        <Tag color={InspectionConclusionColors[value]}>
          {InspectionConclusionLabels[value]}
        </Tag>
      ) : '-',
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
      width: 220,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {(record.status === InspectionStatus.DRAFT || record.status === InspectionStatus.REJECTED) && (
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
          {record.status === InspectionStatus.DRAFT && (
            <Button type="primary" size="small" onClick={() => handleSubmit(record.id)}>
              提交
            </Button>
          )}
          {(record.status === InspectionStatus.SUBMITTED || record.status === InspectionStatus.DEPARTMENT_APPROVED || record.status === InspectionStatus.QA_APPROVED) && (
            <>
              <Button type="primary" size="small" icon={<CheckOutlined />} onClick={() => handleApprove(record.id, true)}>
                通过
              </Button>
              <Button danger size="small" icon={<CloseOutlined />} onClick={() => handleApprove(record.id, false)}>
                驳回
              </Button>
            </>
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
                placeholder="物料编码"
                value={filters.material_code}
                onChange={(e) => setFilters({ ...filters, material_code: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Input
                placeholder="物料名称"
                value={filters.material_name}
                onChange={(e) => setFilters({ ...filters, material_name: e.target.value })}
                allowClear
              />
            </Col>
            <Col span={4}>
              <Select
                placeholder="物料类别"
                value={filters.material_category}
                onChange={(value) => setFilters({ ...filters, material_category: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(MaterialCategoryLabels).map(([value, label]) => (
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
                {Object.entries(InspectionStatusLabels).map(([value, label]) => (
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
                {Object.entries(InspectionConclusionLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
          </Row>
          <Row gutter={16} style={{ marginTop: 12 }}>
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
            <Col span={16} style={{ textAlign: 'right' }}>
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
          scroll={{ x: 1600 }}
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

      {/* 新建弹窗 */}
      {createModalVisible && (
        <Modal
          title="新建IQC检验单"
          open={createModalVisible}
          onCancel={() => setCreateModalVisible(false)}
          width={1000}
          destroyOnHidden
          footer={
            <Space>
              <Button onClick={() => setCreateModalVisible(false)}>取消</Button>
              <Button onClick={handleCreateSubmit} loading={submitLoading}>
                创建
              </Button>
            </Space>
          }
        >
          <Form
            form={createForm}
            layout="vertical"
          >
            <Divider>基本信息</Divider>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="source_type" label="来源类型" rules={[{ required: true }]}>
                  <Select placeholder="请选择来源类型">
                    {Object.entries(IQCSourceTypeLabels).map(([value, label]) => (
                      <Select.Option key={value} value={value}>{label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="source_no" label="来源单号">
                  <Input placeholder="采购到货单号" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="sampling_order_no" label="关联取样单号">
                  <Input placeholder="取样单号" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="material_code" label="物料编码" rules={[{ required: true }]}>
                  <Input placeholder="请输入物料编码" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="material_name" label="物料名称">
                  <Input placeholder="请输入物料名称" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="material_category" label="物料类别">
                  <Select placeholder="请选择物料类别">
                    {Object.entries(MaterialCategoryLabels).map(([value, label]) => (
                      <Select.Option key={value} value={value}>{label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="batch_no" label="批次号">
                  <Input placeholder="请输入批次号" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="specification" label="规格">
                  <Input placeholder="请输入规格" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="unit" label="单位">
                  <Input placeholder="单位" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="supplier_code" label="供应商编码">
                  <Input placeholder="供应商编码" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="supplier_name" label="供应商名称">
                  <Input placeholder="供应商名称" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="quantity_received" label="到货数量">
                  <InputNumber style={{ width: '100%' }} placeholder="到货数量" />
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
                <Form.Item name="expiry_date" label="有效期">
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
                  <Input placeholder="检验员姓名" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="standard_name" label="检验标准">
                  <Input placeholder="检验标准名称" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="inspection_conclusion" label="检验结论">
                  <Select placeholder="请选择检验结论">
                    {Object.entries(InspectionConclusionLabels).map(([value, label]) => (
                      <Select.Option key={value} value={value}>{label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="remark" label="备注">
              <TextArea rows={2} placeholder="请输入备注" />
            </Form.Item>
          </Form>

          <Divider>检验结果明细</Divider>
          <Button type="dashed" onClick={handleCreateAddItem} style={{ marginBottom: 16 }} icon={<PlusOutlined />}>
            添加检验项目
          </Button>

          {createItems.length > 0 && (
            <Table
              size="small"
              dataSource={createItems.map((item, index) => ({ ...item, key: index }))}
              columns={[
                { title: '项次', dataIndex: 'item_no', width: 60 },
                {
                  title: '检验项目',
                  dataIndex: 'inspection_item',
                  width: 150,
                  render: (value, _record, index) => (
                    <Input
                      value={value}
                      onChange={(e) => handleCreateUpdateItem(index, 'inspection_item', e.target.value)}
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
                      onChange={(e) => handleCreateUpdateItem(index, 'inspection_method', e.target.value)}
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
                      onChange={(e) => handleCreateUpdateItem(index, 'standard_value', e.target.value)}
                      placeholder="标准值"
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
                      onChange={(e) => handleCreateUpdateItem(index, 'measured_value', e.target.value)}
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
                      onChange={(v) => handleCreateUpdateItem(index, 'result', v)}
                      placeholder="判定"
                      style={{ width: '100%' }}
                    >
                      {Object.entries(ItemResultLabels).map(([val, label]) => (
                        <Select.Option key={val} value={val}>{label}</Select.Option>
                      ))}
                    </Select>
                  ),
                },
                {
                  title: '备注',
                  dataIndex: 'remark',
                  render: (value, _record, index) => (
                    <Input
                      value={value}
                      onChange={(e) => handleCreateUpdateItem(index, 'remark', e.target.value)}
                      placeholder="备注"
                    />
                  ),
                },
                {
                  title: '操作',
                  width: 80,
                  render: (_: unknown, __: unknown, index: number) => (
                    <Button type="link" danger size="small" onClick={() => handleCreateRemoveItem(index)}>
                      删除
                    </Button>
                  ),
                },
              ]}
              pagination={false}
            />
          )}
        </Modal>
      )}

      {/* 编辑弹窗 */}
      {editModalVisible && (
        <Modal
          title="编辑IQC检验单"
          open={editModalVisible}
          onCancel={() => setEditModalVisible(false)}
          width={1000}
          destroyOnHidden
          footer={
            <Space>
              <Button onClick={() => setEditModalVisible(false)}>取消</Button>
              <Button onClick={handleEditSubmit} loading={submitLoading}>
                保存
              </Button>
              {editRecord && (editRecord.status === InspectionStatus.DRAFT || editRecord.status === InspectionStatus.REJECTED) && (
                <Button type="primary" onClick={handleEditSaveAndSubmit} loading={submitLoading}>
                  保存并提交审批
                </Button>
              )}
            </Space>
          }
        >
          <Form
            form={editForm}
            layout="vertical"
          >
            <Divider>基本信息</Divider>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="source_type" label="来源类型" rules={[{ required: true }]}>
                  <Select placeholder="请选择来源类型">
                    {Object.entries(IQCSourceTypeLabels).map(([value, label]) => (
                      <Select.Option key={value} value={value}>{label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="source_no" label="来源单号">
                  <Input placeholder="采购到货单号" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="sampling_order_no" label="关联取样单号">
                  <Input placeholder="取样单号" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="material_code" label="物料编码" rules={[{ required: true }]}>
                  <Input placeholder="请输入物料编码" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="material_name" label="物料名称">
                  <Input placeholder="请输入物料名称" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="material_category" label="物料类别">
                  <Select placeholder="请选择物料类别">
                    {Object.entries(MaterialCategoryLabels).map(([value, label]) => (
                      <Select.Option key={value} value={value}>{label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="batch_no" label="批次号">
                  <Input placeholder="请输入批次号" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="specification" label="规格">
                  <Input placeholder="请输入规格" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="unit" label="单位">
                  <Input placeholder="单位" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="supplier_code" label="供应商编码">
                  <Input placeholder="供应商编码" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="supplier_name" label="供应商名称">
                  <Input placeholder="供应商名称" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="quantity_received" label="到货数量">
                  <InputNumber style={{ width: '100%' }} placeholder="到货数量" />
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
                <Form.Item name="expiry_date" label="有效期">
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
                  <Input placeholder="检验员姓名" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="standard_name" label="检验标准">
                  <Input placeholder="检验标准名称" />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="inspection_conclusion" label="检验结论">
                  <Select placeholder="请选择检验结论">
                    {Object.entries(InspectionConclusionLabels).map(([value, label]) => (
                      <Select.Option key={value} value={value}>{label}</Select.Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="remark" label="备注">
              <TextArea rows={2} placeholder="请输入备注" />
            </Form.Item>
          </Form>

          <Divider>检验结果明细</Divider>
          <Button type="dashed" onClick={handleEditAddItem} style={{ marginBottom: 16 }} icon={<PlusOutlined />}>
            添加检验项目
          </Button>

          {editItems.length > 0 && (
            <Table
              size="small"
              dataSource={editItems.map((item, index) => ({ ...item, key: index }))}
              columns={[
                { title: '项次', dataIndex: 'item_no', width: 60 },
                {
                  title: '检验项目',
                  dataIndex: 'inspection_item',
                  width: 150,
                  render: (value, _record, index) => (
                    <Input
                      value={value}
                      onChange={(e) => handleEditUpdateItem(index, 'inspection_item', e.target.value)}
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
                      onChange={(e) => handleEditUpdateItem(index, 'inspection_method', e.target.value)}
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
                      onChange={(e) => handleEditUpdateItem(index, 'standard_value', e.target.value)}
                      placeholder="标准值"
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
                      onChange={(e) => handleEditUpdateItem(index, 'measured_value', e.target.value)}
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
                      onChange={(v) => handleEditUpdateItem(index, 'result', v)}
                      placeholder="判定"
                      style={{ width: '100%' }}
                    >
                      {Object.entries(ItemResultLabels).map(([val, label]) => (
                        <Select.Option key={val} value={val}>{label}</Select.Option>
                      ))}
                    </Select>
                  ),
                },
                {
                  title: '备注',
                  dataIndex: 'remark',
                  render: (value, _record, index) => (
                    <Input
                      value={value}
                      onChange={(e) => handleEditUpdateItem(index, 'remark', e.target.value)}
                      placeholder="备注"
                    />
                  ),
                },
                {
                  title: '操作',
                  width: 80,
                  render: (_: unknown, __: unknown, index: number) => (
                    <Button type="link" danger size="small" onClick={() => handleEditRemoveItem(index)}>
                      删除
                    </Button>
                  ),
                },
              ]}
              pagination={false}
            />
          )}
        </Modal>
      )}

      {/* 查看详情弹窗 */}
      <Modal
        title="IQC检验单详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={null}
        width={900}
      >
        {viewRecord && (
          <>
            {/* 第一行 */}
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="检验单号" span={1}>{viewRecord.inspection_no}</Descriptions.Item>
              <Descriptions.Item label="来源类型" span={1}>
                {IQCSourceTypeLabels[viewRecord.source_type]}
              </Descriptions.Item>
              <Descriptions.Item label="来源单号" span={1}>{viewRecord.source_no || '-'}</Descriptions.Item>
              {/* 第二行 */}
              <Descriptions.Item label="物料编码" span={1}>{viewRecord.material_code}</Descriptions.Item>
              <Descriptions.Item label="物料名称" span={1}>{viewRecord.material_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="物料类别" span={1}>
                {viewRecord.material_category ? MaterialCategoryLabels[viewRecord.material_category] : '-'}
              </Descriptions.Item>
              {/* 第三行 */}
              <Descriptions.Item label="批次号" span={1}>{viewRecord.batch_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="规格" span={1}>{viewRecord.specification || '-'}</Descriptions.Item>
              <Descriptions.Item label="供应商" span={1}>{viewRecord.supplier_name || '-'}</Descriptions.Item>
              {/* 第四行 */}
              <Descriptions.Item label="到货数量" span={1}>
                {viewRecord.quantity_received ? `${viewRecord.quantity_received} ${viewRecord.unit || ''}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="生产日期" span={1}>
                {viewRecord.manufacturing_date ? dayjs(viewRecord.manufacturing_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="有效期" span={1}>
                {viewRecord.expiry_date ? dayjs(viewRecord.expiry_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              {/* 第五行 */}
              <Descriptions.Item label="检验日期" span={1}>
                {viewRecord.inspection_date ? dayjs(viewRecord.inspection_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="检验员" span={1}>{viewRecord.inspector_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="检验标准" span={1}>{viewRecord.standard_name || '-'}</Descriptions.Item>
              {/* 第六行 */}
              <Descriptions.Item label="状态" span={1}>
                <Tag color={InspectionStatusColors[viewRecord.status]}>
                  {InspectionStatusLabels[viewRecord.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="检验结论" span={1}>
                {viewRecord.inspection_conclusion ? (
                  <Tag color={InspectionConclusionColors[viewRecord.inspection_conclusion]}>
                    {InspectionConclusionLabels[viewRecord.inspection_conclusion]}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="关联取样单" span={1}>{viewRecord.sampling_order_no || '-'}</Descriptions.Item>
              {/* 第七行 */}
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
                  columns={[
                    { title: '项次', dataIndex: 'item_no', width: 60 },
                    { title: '检验项目', dataIndex: 'inspection_item', width: 150 },
                    { title: '检验方法', dataIndex: 'inspection_method', width: 120 },
                    { title: '标准值', dataIndex: 'standard_value', width: 100 },
                    { title: '实测值', dataIndex: 'measured_value', width: 100 },
                    {
                      title: '单项判定',
                      dataIndex: 'result',
                      width: 100,
                      render: (v: ItemResult) => v ? ItemResultLabels[v] : '-',
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
