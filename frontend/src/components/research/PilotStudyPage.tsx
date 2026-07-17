'use client'

import { useState, useEffect } from 'react'
import { App, Card, Table, Button, Drawer, Form, Input, InputNumber, Select, Tag, Space, Popconfirm, Tabs, Descriptions, Divider, Row, Col, Empty } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { fetchPilotStudies } from '@/lib/api/client/research/rd-project'
import { RdPilotStudy } from '@/types/research/rd-project'
import { createPilotStudy, updatePilotStudy } from '@/actions/research/rd-project'

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

export function PilotStudyPage({ projectId }: Props) {
  const { message: msgApi } = App.useApp()
  const [studies, setStudies] = useState<RdPilotStudy[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<RdPilotStudy | null>(null)
  const [form] = Form.useForm()

  const loadData = async () => {
    setLoading(true)
    try {
      const data = await fetchPilotStudies(projectId)
      setStudies(data)
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

  const openEdit = (record: RdPilotStudy) => {
    setEditingRecord(record)
    form.setFieldsValue({
      batch_no: record.batch_no,
      batch_size: record.batch_size,
      status: record.status,
      notes: record.notes,
      material_balance_input: record.material_balance?.input_materials || '',
      material_balance_output: record.material_balance?.output_materials || '',
      material_balance_yield: record.material_balance?.yield_pct,
      material_balance_notes: record.material_balance?.notes || '',
      equip_reactor: record.equipment_selection?.reactor || '',
      equip_condenser: record.equipment_selection?.condenser || '',
      equip_dryer: record.equipment_selection?.dryer || '',
      equip_filter: record.equipment_selection?.filter || '',
      equip_other: record.equipment_selection?.other_equipment || '',
      equip_notes: record.equipment_selection?.notes || '',
      eng_calc_reaction: record.engineering_calc?.reaction_params || '',
      eng_calc_heat: record.engineering_calc?.heat_transfer || '',
      eng_calc_stirring: record.engineering_calc?.stirring_params || '',
      eng_calc_scaling: record.engineering_calc?.scaling_factor || '',
      eng_calc_notes: record.engineering_calc?.notes || '',
      ehs_hazard: record.ehs_assessment?.hazard_identification || '',
      ehs_protection: record.ehs_assessment?.protection_measures || '',
      ehs_waste: record.ehs_assessment?.waste_treatment || '',
      ehs_emergency: record.ehs_assessment?.emergency_plan || '',
      ehs_notes: record.ehs_assessment?.notes || '',
      scale_param: record.scale_up_effect?.scale_parameters || '',
      scale_therm: record.scale_up_effect?.thermal_effects || '',
      scale_mix: record.scale_up_effect?.mixing_effects || '',
      scale_quality: record.scale_up_effect?.quality_impact || '',
      scale_notes: record.scale_up_effect?.notes || '',
    })
    setDrawerOpen(true)
  }

  const collectJsonFields = (values: Record<string, any>) => ({
    material_balance: {
      input_materials: values.material_balance_input || '',
      output_materials: values.material_balance_output || '',
      yield_pct: values.material_balance_yield,
      notes: values.material_balance_notes || '',
    },
    equipment_selection: {
      reactor: values.equip_reactor || '',
      condenser: values.equip_condenser || '',
      dryer: values.equip_dryer || '',
      filter: values.equip_filter || '',
      other_equipment: values.equip_other || '',
      notes: values.equip_notes || '',
    },
    engineering_calc: {
      reaction_params: values.eng_calc_reaction || '',
      heat_transfer: values.eng_calc_heat || '',
      stirring_params: values.eng_calc_stirring || '',
      scaling_factor: values.eng_calc_scaling || '',
      notes: values.eng_calc_notes || '',
    },
    ehs_assessment: {
      hazard_identification: values.ehs_hazard || '',
      protection_measures: values.ehs_protection || '',
      waste_treatment: values.ehs_waste || '',
      emergency_plan: values.ehs_emergency || '',
      notes: values.ehs_notes || '',
    },
    scale_up_effect: {
      scale_parameters: values.scale_param || '',
      thermal_effects: values.scale_therm || '',
      mixing_effects: values.scale_mix || '',
      quality_impact: values.scale_quality || '',
      notes: values.scale_notes || '',
    },
  })

  const handleSave = async () => {
    const values = await form.validateFields()
    const jsonFields = collectJsonFields(values)
    const payload = {
      batch_no: values.batch_no,
      batch_size: values.batch_size,
      status: values.status,
      notes: values.notes,
      ...jsonFields,
    }
    try {
      if (editingRecord) {
        await updatePilotStudy(editingRecord.id, payload)
        msgApi.success('更新成功')
      } else {
        await createPilotStudy(projectId, payload)
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
      const { deletePilotStudy } = await import('@/actions/research/modules')
      await deletePilotStudy(id)
      msgApi.success('删除成功')
      loadData()
    } catch (e: any) {
      msgApi.error(e.message || '删除失败')
    }
  }

  const columns = [
    { title: '批次号', dataIndex: 'batch_no', key: 'batch_no', width: 120, render: (v: string) => v || '-' },
    { title: '批次规模', dataIndex: 'batch_size', key: 'batch_size', width: 100, render: (v: number) => v != null ? `${v} kg` : '-' },
    { title: '状态', dataIndex: 'status', key: 'status', width: 90, render: (v: string) => <Tag color={statusColorMap[v] || 'default'}>{statusLabelMap[v] || v}</Tag> },
    { title: '物料衡算', dataIndex: 'material_balance', key: 'material_balance', width: 90, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '设备选型', dataIndex: 'equipment_selection', key: 'equipment_selection', width: 90, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '工程计算', dataIndex: 'engineering_calc', key: 'engineering_calc', width: 90, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: 'EHS 评估', dataIndex: 'ehs_assessment', key: 'ehs_assessment', width: 90, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    { title: '放大效应', dataIndex: 'scale_up_effect', key: 'scale_up_effect', width: 90, render: (v: object) => v ? <Tag color="blue">已填写</Tag> : <Tag>未填</Tag> },
    {
      title: '操作', key: 'action', width: 120, fixed: 'right' as const,
      render: (_: any, record: RdPilotStudy) => (
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
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="batch_no" label="批次号" rules={[{ required: true, message: '请输入批次号' }]}>
                <Input placeholder="如：PS-2026-001" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="batch_size" label="批次规模 (kg)">
                <InputNumber style={{ width: '100%' }} min={0} placeholder="如：50" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="status" label="状态">
            <Select options={statusOptions} />
          </Form.Item>
          <Form.Item name="notes" label="备注">
            <Input.TextArea rows={3} placeholder="备注信息..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'material',
      label: '物料衡算',
      children: (
        <>
          <Form.Item name="material_balance_input" label="投入物料">
            <Input.TextArea rows={4} placeholder="列出所有投入物料及其用量，如：&#10;原料A: 10.0 kg&#10;溶剂B: 50.0 L&#10;催化剂C: 0.5 kg" />
          </Form.Item>
          <Form.Item name="material_balance_output" label="产出物料">
            <Input.TextArea rows={4} placeholder="列出所有产出物料及其量，如：&#10;产品: 8.5 kg&#10;母液: 45.0 L&#10;废渣: 2.0 kg" />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="material_balance_yield" label="收率 (%)">
                <InputNumber style={{ width: '100%' }} min={0} max={100} precision={1} placeholder="如：85.0" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="material_balance_notes" label="衡算说明">
            <Input.TextArea rows={3} placeholder="物料衡算的补充说明..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'equipment',
      label: '设备选型',
      children: (
        <>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="equip_reactor" label="反应釜">
                <Input placeholder="如：50L 搪玻璃反应釜" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="equip_condenser" label="冷凝器">
                <Input placeholder="如：5㎡ 列管式冷凝器" />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="equip_filter" label="过滤设备">
                <Input placeholder="如：三足式离心机" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="equip_dryer" label="干燥设备">
                <Input placeholder="如：双锥回转真空干燥机" />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item name="equip_other" label="其他设备">
            <Input.TextArea rows={2} placeholder="其他需要的设备..." />
          </Form.Item>
          <Form.Item name="equip_notes" label="设备选型说明">
            <Input.TextArea rows={3} placeholder="设备选型依据和注意事项..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'engineering',
      label: '工程计算',
      children: (
        <>
          <Form.Item name="eng_calc_reaction" label="反应工程参数">
            <Input.TextArea rows={4} placeholder="反应温度、压力、时间等关键参数计算..." />
          </Form.Item>
          <Form.Item name="eng_calc_heat" label="传热计算">
            <Input.TextArea rows={4} placeholder="换热面积、冷却/加热介质流量等..." />
          </Form.Item>
          <Form.Item name="eng_calc_stirring" label="搅拌参数">
            <Input.TextArea rows={3} placeholder="搅拌转速、桨叶类型、功率计算..." />
          </Form.Item>
          <Form.Item name="eng_calc_scaling" label="放大系数">
            <Input placeholder="如：放大倍数 10x，基于等比放大原则" />
          </Form.Item>
          <Form.Item name="eng_calc_notes" label="计算说明">
            <Input.TextArea rows={2} placeholder="工程计算的补充说明..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'ehs',
      label: 'EHS 评估',
      children: (
        <>
          <Form.Item name="ehs_hazard" label="危险有害因素辨识">
            <Input.TextArea rows={4} placeholder="识别涉及的危险化学品、反应风险（放热、产气等）、燃爆风险..." />
          </Form.Item>
          <Form.Item name="ehs_protection" label="防护措施">
            <Input.TextArea rows={4} placeholder="个人防护装备、通风要求、防爆措施、安全联锁..." />
          </Form.Item>
          <Form.Item name="ehs_waste" label="三废处理">
            <Input.TextArea rows={3} placeholder="废水、废气、固废的处理方案..." />
          </Form.Item>
          <Form.Item name="ehs_emergency" label="应急预案">
            <Input.TextArea rows={3} placeholder="异常情况（泄漏、火灾、中毒等）的应急处理措施..." />
          </Form.Item>
          <Form.Item name="ehs_notes" label="EHS 补充说明">
            <Input.TextArea rows={2} placeholder="其他 EHS 相关注意事项..." />
          </Form.Item>
        </>
      ),
    },
    {
      key: 'scale',
      label: '放大效应',
      children: (
        <>
          <Form.Item name="scale_param" label="放大参数">
            <Input.TextArea rows={3} placeholder="放大规模、放大倍数、关键工艺参数对比..." />
          </Form.Item>
          <Form.Item name="scale_therm" label="热效应分析">
            <Input.TextArea rows={4} placeholder="放大后的传热变化、温度控制难点、局部过热风险..." />
          </Form.Item>
          <Form.Item name="scale_mix" label="混合效应分析">
            <Input.TextArea rows={4} placeholder="放大后的混合均匀性、传质变化、加料方式影响..." />
          </Form.Item>
          <Form.Item name="scale_quality" label="对质量的影响">
            <Input.TextArea rows={3} placeholder="放大对产品纯度、晶型、粒度等质量指标的影响评估..." />
          </Form.Item>
          <Form.Item name="scale_notes" label="放大效应补充说明">
            <Input.TextArea rows={2} placeholder="其他放大效应相关观察和建议..." />
          </Form.Item>
        </>
      ),
    },
  ]

  return (
    <div>
      <Card
        title="中试研究记录"
        extra={<Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建记录</Button>}
      >
        <Table
          dataSource={studies}
          columns={columns}
          rowKey="id"
          loading={loading}
          size="small"
          pagination={false}
          scroll={{ x: 1100 }}
        />
      </Card>

      <Drawer
        title={editingRecord ? '编辑中试研究记录' : '新建中试研究记录'}
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
