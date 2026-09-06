'use client'

import { useState } from 'react'
import dayjs from 'dayjs'
import {
  Table,
  Button,
  Space,
  Select,
  Modal,
  Form,
  Input,
  InputNumber,
  Tag,
  Card,
  Row,
  Col,
  DatePicker,
  App,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  getBatches,
  getProductionRecords,
  createProductionRecord,
  updateProductionRecord,
  deleteProductionRecord,
} from '@/actions/production'
import type {
  ProductionRecord,
  Batch,
} from '@/types/production'


export function RecordsPageClient() {
  const { message, modal } = App.useApp()
  const queryClient = useQueryClient()
  const [form] = Form.useForm()
  const [modalVisible, setModalVisible] = useState(false)
  const [editingRecord, setEditingRecord] = useState<ProductionRecord | null>(null)
  const [selectedBatchId, setSelectedBatchId] = useState<string | undefined>()
  const [operationType, setOperationType] = useState<string | undefined>()

  // Load batches for the dropdown
  const { data: batches = [] } = useQuery({
    queryKey: ['production-batches-dropdown'],
    queryFn: async () => {
      const response = await getBatches({ page: 1, page_size: 100 })
      if (response.code === 200) {
        return response.data
      }
      return []
    },
  })

  // Load production records for the selected batch
  const { data: productionRecords = [], isLoading: loading } = useQuery({
    queryKey: ['production-records', selectedBatchId],
    queryFn: async () => {
      if (!selectedBatchId) return []
      const response = await getProductionRecords(selectedBatchId)
      if (response.code === 200) {
        return response.data
      }
      return []
    },
    enabled: !!selectedBatchId,
  })

  const handleAdd = () => {
    if (!selectedBatchId) {
      message.warning('请先选择批次')
      return
    }
    setEditingRecord(null)
    setOperationType(undefined)
    form.resetFields()
    setModalVisible(true)
  }

  const handleEdit = (record: ProductionRecord) => {
    setEditingRecord(record)
    setOperationType(record.operation_type)
    form.resetFields()

    // 解析 parameters 中的数量
    let quantity: number | undefined
    try {
      if (record.parameters) {
        const params = JSON.parse(record.parameters)
        quantity = params.quantity
      }
    } catch {}

    // 设置表单值
    form.setFieldsValue({
      record_no: record.record_no,
      operation_type: record.operation_type,
      step_no: record.step_no ? Number(record.step_no) : undefined,
      step_name: record.step_name,
      operator_name: record.operator_name,
      quantity,
      operation_time: record.operation_time ? dayjs(record.operation_time) : null,
      result: record.result,
      remarks: record.remarks,
    })
    setModalVisible(true)
  }

  const handleDelete = async (id: string) => {
    modal.confirm({
      title: '确认删除',
      content: '确定要删除这条生产记录吗？',
      onOk: async () => {
        try {
          const response = await deleteProductionRecord(id)
          if (response.code === 200) {
            message.success('删除成功')
            queryClient.invalidateQueries({ queryKey: ['production-records'] })
          } else {
            message.error(response.message || '删除失败')
          }
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const handleSubmit = async () => {
    if (!selectedBatchId) return

    try {
      const values = await form.validateFields()

      const parameters: Record<string, number> = {}
      if (values.quantity !== undefined && values.quantity !== null) {
        parameters.quantity = values.quantity
      }

      const submitData = {
        record_no: values.record_no,
        step_no: values.step_no,
        step_name: values.step_name,
        operation_type: values.operation_type,
        operator_name: values.operator_name,
        result: values.result,
        remarks: values.remarks,
        parameters: Object.keys(parameters).length > 0 ? JSON.stringify(parameters) : undefined,
        operation_time: values.operation_time && values.operation_time.isValid()
          ? values.operation_time.toISOString()
          : new Date().toISOString(),
      }

      if (editingRecord) {
        const response = await updateProductionRecord(editingRecord.id, submitData)
        if (response.code === 200) {
          message.success('更新成功')
          setModalVisible(false)
          queryClient.invalidateQueries({ queryKey: ['production-records'] })
        } else {
          message.error(response.message || '更新失败')
        }
      } else {
        const response = await createProductionRecord({ ...submitData, batch_id: selectedBatchId })
        if (response.code === 200) {
          message.success('创建成功')
          setModalVisible(false)
          form.resetFields()
          queryClient.invalidateQueries({ queryKey: ['production-records'] })
        } else {
          message.error(response.message || '创建失败')
        }
      }
    } catch (error) {
      console.error('表单验证失败:', error)
    }
  }

  const columns: ColumnsType<ProductionRecord> = [
    {
      title: '记录编号',
      dataIndex: 'record_no',
      key: 'record_no',
      width: 150,
    },
    {
      title: '操作类型',
      dataIndex: 'operation_type',
      key: 'operation_type',
      width: 120,
      render: (type: string) => {
        const typeMap: Record<string, { color: string; label: string }> = {
          material_add: { color: 'blue', label: '投料' },
          transfer: { color: 'cyan', label: '转序' },
          sampling: { color: 'purple', label: '取样' },
          equipment_check: { color: 'orange', label: '设备检查' },
          parameter_record: { color: 'geekblue', label: '参数记录' },
          packaging: { color: 'green', label: '包装' },
        }
        const config = typeMap[type] || { color: 'default', label: type }
        return <Tag color={config.color}>{config.label}</Tag>
      },
    },
    {
      title: '步骤序号',
      dataIndex: 'step_no',
      key: 'step_no',
      width: 100,
    },
    {
      title: '步骤名称',
      dataIndex: 'step_name',
      key: 'step_name',
      width: 150,
    },
    {
      title: '操作人',
      dataIndex: 'operator_name',
      key: 'operator_name',
      width: 120,
    },
    {
      title: '操作时间',
      dataIndex: 'operation_time',
      key: 'operation_time',
      width: 160,
      render: (time: string) => time ? new Date(time).toLocaleString('zh-CN') : '-',
    },
    {
      title: '操作结果',
      dataIndex: 'result',
      key: 'result',
      width: 150,
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={() => handleDelete(record.id)}>
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="p-6">
      <Card title="生产记录">
        <Row gutter={16} className="mb-4">
          <Col span={8}>
            <Select
              placeholder="请选择批次"
              value={selectedBatchId}
              onChange={(value) => setSelectedBatchId(value)}
              style={{ width: '100%' }}
              showSearch
              optionFilterProp="children"
              options={(batches as Batch[]).map((b) => ({
                value: b.id,
                label: `${b.batch_no} - ${b.product_name || b.product_code}`,
              }))}
            />
          </Col>
          <Col span={4}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAdd}
              disabled={!selectedBatchId}
            >
              新建记录
            </Button>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={productionRecords}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1100 }}
          pagination={{ pageSize: 20 }}
          locale={{ emptyText: '请先选择批次' }}
        />
      </Card>

      <Modal
        title={editingRecord ? '编辑生产记录' : '新建生产记录'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
        okText="确认"
        cancelText="取消"
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="record_no"
                label="记录编号"
                rules={[{ required: true, message: '请输入记录编号' }]}
              >
                <Input placeholder="请输入记录编号" disabled={!!editingRecord} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="operation_type"
                label="操作类型"
                rules={[{ required: true, message: '请选择操作类型' }]}
              >
                <Select
                  placeholder="请选择"
                  onChange={(value) => setOperationType(value)}
                  options={[
                    { value: 'material_add', label: '投料' },
                    { value: 'transfer', label: '转序' },
                    { value: 'sampling', label: '取样' },
                    { value: 'equipment_check', label: '设备检查' },
                    { value: 'parameter_record', label: '参数记录' },
                    { value: 'packaging', label: '包装' },
                  ]}
                />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="step_no" label="步骤序号">
                <InputNumber min={1} style={{ width: '100%' }} placeholder="请输入步骤序号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="step_name" label="步骤名称">
                <Input placeholder="请输入步骤名称" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="operator_name" label="操作人">
                <Input placeholder="请输入操作人" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="quantity"
                label={operationType === 'material_add' ? '投料量 (kg)' : operationType === 'packaging' ? '产出量 (kg)' : '数量'}
              >
                <InputNumber min={0} style={{ width: '100%' }} placeholder="请输入数量" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="operation_time" label="操作时间">
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="result" label="操作结果">
            <Input.TextArea rows={2} placeholder="请输入操作结果" />
          </Form.Item>
          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={2} placeholder="请输入备注" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
