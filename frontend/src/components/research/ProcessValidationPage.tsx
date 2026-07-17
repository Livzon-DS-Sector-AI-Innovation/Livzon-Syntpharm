'use client'

import { useState, useEffect } from 'react'
import { App, Card, Table, Button, Drawer, Form, Input, InputNumber, Select, Tag, Space, Popconfirm, Tabs, Row, Col } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { fetchValidations } from '@/lib/api/client/research/rd-project'
import { RdProcessValidation } from '@/types/research/rd-project'
import { createValidation, updateValidation } from '@/actions/research/rd-project'

interface Props { projectId: string }

const statusOptions = [
  { value: 'draft', label: '草稿' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
]

const statusColorMap: Record<string, string> = {
  draft: 'default',
  in_progress: 'processing',
  completed: 'success',
}

const statusLabelMap: Record<string, string> = {
  draft: '草稿',
  in_progress: '进行中',
  completed: '已完成',
}

export function ProcessValidationPage({ projectId }: Props) {
  const { message: msgApi } = App.useApp()
  const [validations, setValidations] = useState<RdProcessValidation[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdProcessValidation | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchValidations(projectId)
      setValidations(data)
    } catch (e: any) {
      msgApi.error(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadData() }, [projectId])

  const openCreate = () => {
    setEditingRecord(null)
    form.resetFields()
    form.setFieldsValue({ status: 'draft' })
    setDrawerOpen(true)
  }

  const openEdit = (record: RdProcessValidation) => {
    setEditingRecord(record)
    form.setFieldsValue({
      status: record.status,
      notes: record.notes,
      validation_conclusion: record.validation_conclusion,
      proto_scope: record.validation_protocol?.scope || '',
      proto_objectives: record.validation_protocol?.objectives || '',
      proto_criteria: record.validation_protocol?.acceptance_criteria || '',
      proto_sampling: record.validation_protocol?.sampling_plan || '',
      proto_params: record.validation_protocol?.critical_parameters || '',
      proto_notes: record.validation_protocol?.notes || '',
      batch_list: record.validation_batches?.batch_list || '',
      batch_params: record.validation_batches?.process_parameters || '',
      batch_ipc: record.validation_batches?.ipc_results || '',
      batch_yield: record.validation_batches?.yield_summary || '',
      batch_notes: record.validation_batches?.notes || '',
      stat_methods: record.statistical_analysis?.methods || '',
      stat_cpk: record.statistical_analysis?.cpk_results || '',
      stat_uniformity: record.statistical_analysis?.uniformity_test || '',
      stat_oot: record.statistical_analysis?.oot_analysis || '',
      stat_notes: record.statistical_analysis?.notes || '',
    })
    setDrawerOpen(true)
  }

  const collectJsonFields = (values: Record<string, any>) => ({
    validation_protocol: {
      scope: values.proto_scope || '',
      objectives: values.proto_objectives || '',
      acceptance_criteria: values.proto_criteria || '',
      sampling_plan: values.proto_sampling || '',
      critical_parameters: values.proto_params || '',
      notes: values.proto_notes || '',
    },
    validation_batches: {
      batch_list: values.batch_list || '',
      process_parameters: values.batch_params || '',
      ipc_results: values.batch_ipc || '',
      yield_summary: values.batch_yield || '',
      notes: values.batch_notes || '',
    },
    statistical_analysis: {
      methods: values.stat_methods || '',
      cpk_results: values.stat_cpk || '',
      uniformity_test: values.stat_uniformity || '',
      oot_analysis: values.stat_oot || '',
      notes: values.stat_notes || '',
    },
  })

  const handleSave = async () => {
    const values = await form.validateFields()
    const jsonFields = collectJsonFields(values)
    const payload = {
      status: values.status,
      notes: values.notes,
      validation_conclusion: values.validation_conclusion,
      ...jsonFields,
    }
    try {
      if (editingRecord) {
        await updateValidation(editingRecord.id, payload)
        msgApi.success('更新成功')
      } else {
        await createValidation(projectId, payload)
        msgApi.success('创建成功')
      }
      setDrawerOpen(false)
      form.resetFields()
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '保存失败')
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const { deleteValidation } = await import('@/actions/research/modules')
      await deleteValidation(id)
      msgApi.success('删除成功')
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '删除失败')
    }
  }

  const columns = [
    { title: '验证方案', dataIndex: 'validation_protocol', key: 'validation_protocol', width: 100, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '验证批次', dataIndex: 'validation_batches', key: 'validation_batches', width: 100, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '统计分析', dataIndex: 'statistical_analysis', key: 'statistical_analysis', width: 100, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '验证结论', dataIndex: 'validation_conclusion', key: 'validation_conclusion', width: 200, ellipsis: true, render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{statusLabelMap[v] || v}</Tag> },
    { title: '备注', dataIndex: 'notes', key: 'notes', width: 150, ellipsis: true, render: (v: string) => v || '-' },
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: any, record: RdProcessValidation) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除此记录？" onConfirm={() => handleDelete(record.id)} okText="删除" cancelText="取消">
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const tabItems = [
    {
      key: 'basic',
      label: '基本信息',
      children: (
        <>
          <Form.Item name="status" label="状态">
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="validation_conclusion" label="验证结论">
            <Input.TextArea rows={4} placeholder="工艺验证总体结论..." />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="备注信息..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'protocol',
      label: '验证方案',
      children: (
        <>
          <Form.Item name="proto_scope" label="验证范围">
            <Input.TextArea rows={3} placeholder="明确验证的产品、工艺、设备范围..." />
          </Form.Item>
          <Form.Item name="proto_objectives" label="验证目标">
            <Input.TextArea rows={3} placeholder="验证要达到的目标和关键质量指标..." />
          </Form.Item>
          <Form.Item name="proto_criteria" label="验收标准">
            <Input.TextArea rows={4} placeholder="各质量指标的验收标准，如：&#10;含量: 98.0%-102.0%&#10;有关物质: 单杂≤0.10%, 总杂≤0.30%&#10;干燥失重: ≤0.50%" />
          </Form.Item>
          <Form.Item name="proto_sampling" label="取样方案">
            <Input.TextArea rows={3} placeholder="取样点、取样频次、取样量、取样方法..." />
          </Form.Item>
          <Form.Item name="proto_params" label="关键工艺参数">
            <Input.TextArea rows={3} placeholder="需验证的关键工艺参数及其范围..." />
          </Form.Item>
          <Form.Item name="proto_notes" label="方案补充说明">
            <Input.TextArea rows={2} placeholder="其他验证方案相关内容..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'batches',
      label: '验证批次',
      children: (
        <>
          <Form.Item name="batch_list" label="批次信息">
            <Input.TextArea rows={4} placeholder="验证批次的详细信息，如：&#10;批次1: VP-2026-001, 50kg, 2026-03-01&#10;批次2: VP-2026-002, 50kg, 2026-03-05&#10;批次3: VP-2026-003, 50kg, 2026-03-10" />
          </Form.Item>
          <Form.Item name="batch_params" label="工艺参数记录">
            <Input.TextArea rows={4} placeholder="各批次关键工艺参数实际执行记录..." />
          </Form.Item>
          <Form.Item name="batch_ipc" label="过程控制结果">
            <Input.TextArea rows={4} placeholder="各批次 IPC 检测结果汇总..." />
          </Form.Item>
          <Form.Item name="batch_yield" label="收率汇总">
            <Input.TextArea rows={3} placeholder="各批次收率数据，如：&#10;批次1: 87.5%&#10;批次2: 86.8%&#10;批次3: 88.1%&#10;平均: 87.5%, RSD: 0.75%" />
          </Form.Item>
          <Form.Item name="batch_notes" label="批次记录补充说明">
            <Input.TextArea rows={2} placeholder="其他批次相关观察..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'statistics',
      label: '统计分析',
      children: (
        <>
          <Form.Item name="stat_methods" label="统计方法">
            <Input.TextArea rows={3} placeholder="使用的统计分析方法，如：描述性统计、Cpk分析、方差分析..." />
          </Form.Item>
          <Form.Item name="stat_cpk" label="Cpk/Ppk 分析">
            <Input.TextArea rows={4} placeholder="各关键质量属性的 Cpk/Ppk 计算结果，如：&#10;含量 Cpk: 1.45&#10;单杂 Cpk: 1.67&#10;收率 Cpk: 1.32" />
          </Form.Item>
          <Form.Item name="stat_uniformity" label="均匀性检验">
            <Input.TextArea rows={3} placeholder="批内/批间均匀性检验结果..." />
          </Form.Item>
          <Form.Item name="stat_oot" label="OOT 分析">
            <Input.TextArea rows={3} placeholder="趋势外推分析结果，是否存在异常趋势..." />
          </Form.Item>
          <Form.Item name="stat_notes" label="统计分析补充说明">
            <Input.TextArea rows={2} placeholder="其他统计分析相关内容..." />
          </Form.Item>
        </>
      ),
    },
  ]

  return (
    <div>
      <Card
        title="工艺验证记录"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建记录</Button>}
      >
        <Table
          dataSource={validations}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 1000 }}
        />
      </Card>

      <Drawer
        title={editingRecord ? '编辑工艺验证记录' : '新建工艺验证记录'}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); form.resetFields() }}
        styles={{ wrapper: { width: 720 } }}
        extra={
          <Space>
            <Button onClick={() => { setDrawerOpen(false); form.resetFields() }}>取消</Button>
            <Button type="primary" onClick={handleSave}>保存</Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <Tabs items={tabItems} />
        </Form>
      </Drawer>
    </div>
  )
}
