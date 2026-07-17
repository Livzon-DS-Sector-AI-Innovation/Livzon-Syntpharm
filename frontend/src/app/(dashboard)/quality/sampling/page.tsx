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
  SamplingOrder,
  SamplingOrderListItem,
  SamplingOrderCreate,
  SamplingOrderItemCreate,
  SamplingOrderFilter,
  SamplingSource,
  SamplingSourceLabels,
  SourceTypeLabels,
  SamplingStatus,
  SamplingStatusLabels,
  SamplingStatusColors,
  SamplingResult,
  SamplingResultLabels,
  SampleStatus,
  SamplingOrderListResponse,
  SampleStatusLabels,
  ExceptionReasonOptions,
} from '@/types/sampling'
import {
  getSamplingOrders,
  getSamplingOrder,
  createSamplingOrder,
  updateSamplingOrder,
  deleteSamplingOrder,
  submitSamplingOrderForApproval,
  approveSamplingOrder,
} from '@/actions/quality'

const { RangePicker } = DatePicker
const { Text } = Typography
const { TextArea } = Input

// 初始筛选条件
const initialFilters: SamplingOrderFilter = {
  order_no: '',
  material_code: '',
  material_name: '',
  sampling_source: undefined,
  status: undefined,
  sampling_result: undefined,
  start_date: undefined,
  end_date: undefined,
}

export default function SamplingPage() {
  // 状态
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<SamplingOrderListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<SamplingOrderFilter>(initialFilters)

  // 弹窗状态
  const [modalVisible, setModalVisible] = useState(false)
  const [modalTitle, setModalTitle] = useState('新建取样单')
  const [editingRecord, setEditingRecord] = useState<SamplingOrder | null>(null)
  const [viewRecord, setViewRecord] = useState<SamplingOrder | null>(null)
  const [viewModalVisible, setViewModalVisible] = useState(false)

  // 表单 - 两个 form 实例，完全模仿 batches 页面模式
  const [form] = Form.useForm()
  const [editForm] = Form.useForm()
  const [items, setItems] = useState<SamplingOrderItemCreate[]>([])
  const [submitLoading, setSubmitLoading] = useState(false)

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getSamplingOrders({
        ...filters,
        page,
        page_size: pageSize,
      })
      if (response.code === 200 || response.code === 0) {
        const data = response.data as SamplingOrderListResponse
        setData(data?.items || [])
        setTotal(data?.total || 0)
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
    setModalTitle('新建取样单')
    form.resetFields()
    setItems([])
    setModalVisible(true)
  }

  // 编辑
  const handleEdit = async (record: SamplingOrderListItem) => {
    try {
      const response = await getSamplingOrder(record.id)
      if (response.code === 200 || response.code === 0) {
        setEditingRecord(response.data)
        setModalTitle('编辑取样单')
        editForm.setFieldsValue({
          ...response.data,
          sampling_date: response.data.sampling_date ? dayjs(response.data.sampling_date) : null,
        })
        setItems(response.data.items?.map((item: any, index: number) => ({
          item_no: index + 1,
          sample_no: item.sample_no,
          sampling_count: item.sampling_count,
          retention_count: item.retention_count,
          retention_location: item.retention_location,
          sample_status: item.sample_status,
          retention_date: item.retention_date ? dayjs(item.retention_date).format('YYYY-MM-DD') : undefined,
          expiry_date: item.expiry_date ? dayjs(item.expiry_date).format('YYYY-MM-DD') : undefined,
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
  const handleView = async (record: SamplingOrderListItem) => {
    try {
      const response = await getSamplingOrder(record.id)
      if (response.code === 200 || response.code === 0) {
        setViewRecord(response.data)
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
      const response = await deleteSamplingOrder(id)
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
      const response = await submitSamplingOrderForApproval(id)
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
      const response = await approveSamplingOrder(id, {
        approval_status: approved ? 'approved' : 'rejected',
      })
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
      const values = editingRecord ? await editForm.validateFields() : await form.validateFields()

      let exceptionReasons: string | undefined
      if (values.sampling_result === SamplingResult.ABNORMAL && values.exception_reason_list) {
        exceptionReasons = JSON.stringify(values.exception_reason_list)
      }

      const submitData: SamplingOrderCreate = {
        ...values,
        sampling_date: values.sampling_date?.format('YYYY-MM-DDTHH:mm:ss'),
        exception_reasons: exceptionReasons,
        items: items.map((item, index) => ({
          ...item,
          item_no: index + 1,
          retention_date: item.retention_date && typeof item.retention_date === 'object' && 'format' in item.retention_date
            ? (item.retention_date as dayjs.Dayjs).format('YYYY-MM-DDTHH:mm:ss')
            : item.retention_date,
          expiry_date: item.expiry_date && typeof item.expiry_date === 'object' && 'format' in item.expiry_date
            ? (item.expiry_date as dayjs.Dayjs).format('YYYY-MM-DDTHH:mm:ss')
            : item.expiry_date,
        })),
      }

      setSubmitLoading(true)

      let response
      if (editingRecord) {
        response = await updateSamplingOrder(editingRecord.id, submitData)
      } else {
        response = await createSamplingOrder(submitData)
      }

      if (response.code === 200 || response.code === 0 || response.data?.order_no) {
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

  // 添加明细
  const handleAddItem = () => {
    const newItem: SamplingOrderItemCreate = {
      item_no: items.length + 1,
      sampling_count: 1,
      retention_count: 1,
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

  // 表格列定义
  const columns: ColumnsType<SamplingOrderListItem> = [
    {
      title: '取样单号',
      dataIndex: 'order_no',
      key: 'order_no',
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
      title: '取样来源',
      dataIndex: 'sampling_source',
      key: 'sampling_source',
      width: 100,
      render: (value: SamplingSource) => SamplingSourceLabels[value] || value,
    },
    {
      title: '取样日期',
      dataIndex: 'sampling_date',
      key: 'sampling_date',
      width: 120,
      render: (value) => value ? dayjs(value).format('YYYY-MM-DD') : '-',
    },
    {
      title: '取样人',
      dataIndex: 'sampler_name',
      key: 'sampler_name',
      width: 80,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (value: SamplingStatus) => (
        <Tag color={SamplingStatusColors[value]}>
          {SamplingStatusLabels[value]}
        </Tag>
      ),
    },
    {
      title: '判定结果',
      dataIndex: 'sampling_result',
      key: 'sampling_result',
      width: 100,
      render: (value: SamplingResult) => value ? (
        <Tag color={value === SamplingResult.NORMAL ? 'green' : 'red'}>
          {SamplingResultLabels[value]}
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
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          {(record.status === SamplingStatus.DRAFT || record.status === SamplingStatus.REJECTED) && (
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
          {record.status === SamplingStatus.DRAFT && (
            <Button type="primary" size="small" onClick={() => handleSubmit(record.id)}>
              提交
            </Button>
          )}
          {(record.status === SamplingStatus.PENDING_WAREHOUSE || record.status === SamplingStatus.PENDING_QA) && (
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
                placeholder="取样单号"
                value={filters.order_no}
                onChange={(e) => setFilters({ ...filters, order_no: e.target.value })}
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
                placeholder="取样来源"
                value={filters.sampling_source}
                onChange={(value) => setFilters({ ...filters, sampling_source: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(SamplingSourceLabels).map(([value, label]) => (
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
                {Object.entries(SamplingStatusLabels).map(([value, label]) => (
                  <Select.Option key={value} value={value}>{label}</Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={4}>
              <Select
                placeholder="判定结果"
                value={filters.sampling_result}
                onChange={(value) => setFilters({ ...filters, sampling_result: value })}
                allowClear
                style={{ width: '100%' }}
              >
                {Object.entries(SamplingResultLabels).map(([value, label]) => (
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
                  新建取样单
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
          scroll={{ x: 1500 }}
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

      {/* 新建/编辑弹窗 - 完全模仿 batches 页面模式 */}
      <Modal
        title={modalTitle}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSubmitForm}
        width={900}
        okText="确认"
        cancelText="取消"
        confirmLoading={submitLoading}
      >
        <Form
          form={editingRecord ? editForm : form}
          layout="vertical"
          initialValues={editingRecord || undefined}
        >
          <Divider>基本信息</Divider>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="source_type" label="来源类型" rules={[{ required: true }]}>
                <Select placeholder="请选择来源类型">
                  {Object.entries(SourceTypeLabels).map(([value, label]) => (
                    <Select.Option key={value} value={value}>{label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="source_no" label="关联单号">
                <Input placeholder="来料入库单号/生产批号" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_source" label="取样来源" rules={[{ required: true }]}>
                <Select placeholder="请选择取样来源">
                  {Object.entries(SamplingSourceLabels).map(([value, label]) => (
                    <Select.Option key={value} value={value}>{label}</Select.Option>
                  ))}
                </Select>
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
              <Form.Item name="batch_no" label="批次号">
                <Input placeholder="请输入批次号" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="specification" label="规格">
                <Input placeholder="请输入规格" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="unit" label="单位">
                <Input placeholder="请输入单位" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="quantity" label="批量/数量">
                <InputNumber style={{ width: '100%' }} placeholder="请输入数量" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="sampling_quantity" label="取样量">
                <InputNumber style={{ width: '100%' }} placeholder="请输入取样量" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_location" label="取样地点">
                <Input placeholder="请输入取样地点" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_date" label="取样日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="sampler_name" label="取样人">
                <Input placeholder="请输入取样人" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="sampling_result" label="取样判定">
                <Select placeholder="请选择取样判定">
                  {Object.entries(SamplingResultLabels).map(([val, label]) => (
                    <Select.Option key={val} value={val}>{label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="remark" label="备注">
            <TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>
        </Form>

        <Divider>取样明细</Divider>
        <Button type="dashed" onClick={handleAddItem} style={{ marginBottom: 16 }} icon={<PlusOutlined />}>
          添加明细
        </Button>

        {items.length > 0 && (
          <Table
            size="small"
            dataSource={items.map((item, index) => ({ ...item, key: index }))}
            columns={[
              { title: '项次', dataIndex: 'item_no', width: 60 },
              {
                title: '取样份数',
                dataIndex: 'sampling_count',
                width: 100,
                render: (value, _record, index) => (
                  <InputNumber
                    min={1}
                    value={value}
                    onChange={(v) => handleUpdateItem(index, 'sampling_count', v)}
                  />
                ),
              },
              {
                title: '留样份数',
                dataIndex: 'retention_count',
                width: 100,
                render: (value, _record, index) => (
                  <InputNumber
                    min={1}
                    value={value}
                    onChange={(v) => handleUpdateItem(index, 'retention_count', v)}
                  />
                ),
              },
              {
                title: '留样位置',
                dataIndex: 'retention_location',
                render: (value, _record, index) => (
                  <Input
                    value={value}
                    onChange={(e) => handleUpdateItem(index, 'retention_location', e.target.value)}
                    placeholder="留样位置"
                  />
                ),
              },
              {
                title: '有效期',
                dataIndex: 'expiry_date',
                width: 150,
                render: (value, _record, index) => (
                  <DatePicker
                    value={value}
                    onChange={(v) => handleUpdateItem(index, 'expiry_date', v)}
                  />
                ),
              },
              {
                title: '备注',
                dataIndex: 'remark',
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
          />
        )}
      </Modal>

      {/* 查看详情弹窗 */}
      <Modal
        title="取样单详情"
        open={viewModalVisible}
        onCancel={() => setViewModalVisible(false)}
        footer={null}
        width={800}
      >
        {viewRecord && (
          <>
            <Descriptions bordered size="small">
              <Descriptions.Item label="取样单号">{viewRecord.order_no}</Descriptions.Item>
              <Descriptions.Item label="来源类型">
                {SourceTypeLabels[viewRecord.source_type]}
              </Descriptions.Item>
              <Descriptions.Item label="关联单号">{viewRecord.source_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="取样来源">
                {SamplingSourceLabels[viewRecord.sampling_source]}
              </Descriptions.Item>
              <Descriptions.Item label="物料编码">{viewRecord.material_code}</Descriptions.Item>
              <Descriptions.Item label="物料名称">{viewRecord.material_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="批次号">{viewRecord.batch_no || '-'}</Descriptions.Item>
              <Descriptions.Item label="规格">{viewRecord.specification || '-'}</Descriptions.Item>
              <Descriptions.Item label="批量/数量">
                {viewRecord.quantity ? `${viewRecord.quantity} ${viewRecord.unit || ''}` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="取样量">{viewRecord.sampling_quantity || '-'}</Descriptions.Item>
              <Descriptions.Item label="取样地点">{viewRecord.sampling_location || '-'}</Descriptions.Item>
              <Descriptions.Item label="取样日期">
                {viewRecord.sampling_date ? dayjs(viewRecord.sampling_date).format('YYYY-MM-DD') : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="取样人">{viewRecord.sampler_name || '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">
                <Tag color={SamplingStatusColors[viewRecord.status]}>
                  {SamplingStatusLabels[viewRecord.status]}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="判定结果">
                {viewRecord.sampling_result ? (
                  <Tag color={viewRecord.sampling_result === SamplingResult.NORMAL ? 'green' : 'red'}>
                    {SamplingResultLabels[viewRecord.sampling_result]}
                  </Tag>
                ) : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="备注" span={2}>{viewRecord.remark || '-'}</Descriptions.Item>
            </Descriptions>

            {viewRecord.items && viewRecord.items.length > 0 && (
              <>
                <Divider>取样明细</Divider>
                <Table
                  size="small"
                  dataSource={viewRecord.items}
                  rowKey="id"
                  pagination={false}
                  columns={[
                    { title: '项次', dataIndex: 'item_no', width: 60 },
                    { title: '样品编号', dataIndex: 'sample_no', width: 150 },
                    { title: '取样份数', dataIndex: 'sampling_count', width: 80 },
                    { title: '留样份数', dataIndex: 'retention_count', width: 80 },
                    { title: '留样位置', dataIndex: 'retention_location', width: 150 },
                    {
                      title: '有效期',
                      dataIndex: 'expiry_date',
                      width: 120,
                      render: (v) => v ? dayjs(v).format('YYYY-MM-DD') : '-',
                    },
                    {
                      title: '状态',
                      dataIndex: 'sample_status',
                      width: 100,
                      render: (v: SampleStatus) => SampleStatusLabels[v] || v,
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