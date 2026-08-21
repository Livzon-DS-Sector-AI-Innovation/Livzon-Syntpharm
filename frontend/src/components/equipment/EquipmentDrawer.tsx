'use client'

import { useState, useEffect, useRef } from 'react'
import { App, Drawer, Form, Input, Select, DatePicker, Button, Space, InputNumber } from 'antd'
import dayjs from 'dayjs'
import { useEquipmentStore } from '@/stores/equipment'
import { EquipmentStatus } from '@/types/equipment/generated-bridge'
import { createEquipment, updateEquipment } from '@/actions/equipment'

const { TextArea } = Input

const statusOptions: { label: string; value: EquipmentStatus }[] = [
  { label: '在用', value: '在用' },
  { label: '备用', value: '备用' },
  { label: '维修中', value: '维修中' },
  { label: '停用', value: '停用' },
  { label: '报废', value: '报废' },
]


interface EquipmentDrawerProps {
  onRefresh?: () => void
}

export function EquipmentDrawer({ onRefresh }: EquipmentDrawerProps) {
  const [form] = Form.useForm()
  const { message } = App.useApp()
  const [submitting, setSubmitting] = useState(false)
  const _searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const {
    equipmentDrawerOpen,
    editingEquipment,
    closeEquipmentDrawer,
    departments,
  } = useEquipmentStore()



  useEffect(() => {
    if (equipmentDrawerOpen) {
      if (editingEquipment) {

        form.setFieldsValue({
          name: editingEquipment.name,
          asset_no: editingEquipment.asset_no,
          label_no: editingEquipment.label_no ?? undefined,
          equipment_tag: editingEquipment.equipment_tag ?? undefined,
          equipment_class: editingEquipment.equipment_class ?? undefined,
          category_description: editingEquipment.category_description ?? undefined,
          location_text: editingEquipment.location_text ?? undefined,
          status: editingEquipment.status,
          model: editingEquipment.model ?? undefined,
          specification: editingEquipment.specification ?? undefined,
          manufacturer: editingEquipment.manufacturer ?? undefined,
          supplier: editingEquipment.supplier ?? undefined,
          production_date: editingEquipment.production_date ? dayjs(editingEquipment.production_date) : undefined,
          commissioning_date: editingEquipment.commissioning_date ? dayjs(editingEquipment.commissioning_date) : undefined,
          scrap_status: editingEquipment.scrap_status ?? undefined,
          scrap_time: editingEquipment.scrap_time ? dayjs(editingEquipment.scrap_time) : undefined,
          description: editingEquipment.description ?? undefined,
          department_id: editingEquipment.department_id ?? undefined,
          responsible_person_id: editingEquipment.responsible_person_id ?? undefined,
          quantity: (editingEquipment.technical_params as Record<string, unknown>)?.['数量'] ?? 1,
        })
      } else {
        form.resetFields()
      }
    }
  }, [equipmentDrawerOpen, editingEquipment, form])


  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      const { quantity, ...restValues } = values
      const technicalParams = editingEquipment?.technical_params || {}
      const submitData = {
        ...restValues,
        technical_params: {
          ...technicalParams,
          '数量': quantity ?? 1,
        },
        production_date: restValues.production_date
          ? restValues.production_date.format('YYYY-MM-DD')
          : undefined,
        commissioning_date: restValues.commissioning_date
          ? restValues.commissioning_date.format('YYYY-MM-DD')
          : undefined,
        scrap_time: restValues.scrap_time
          ? restValues.scrap_time.format('YYYY-MM-DD')
          : undefined,
      }
      if (editingEquipment) {
        await updateEquipment(editingEquipment.id, submitData)
        message.success('更新设备成功')
      } else {
        await createEquipment(submitData)
        message.success('创建设备成功')
      }
      closeEquipmentDrawer()
      onRefresh?.()
    } catch (err: any) {
      // Ant Design validation errors have an errorFields property
      if (err?.errorFields) return
      message.error('操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Drawer
      title={editingEquipment ? '编辑设备' : '新增设备'}
      size={480}
      open={equipmentDrawerOpen}
      onClose={closeEquipmentDrawer}
      destroyOnHidden
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '24px' },
      }}
      extra={
        <Space>
          <Button onClick={closeEquipmentDrawer}>取消</Button>
          <Button type="primary" loading={submitting} onClick={handleSubmit}>
            保存
          </Button>
        </Space>
      }
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark="optional"
        styles={{ label: { fontWeight: 500, color: '#1a1a1a' } }}
      >
        <Form.Item
          name="name"
          label="设备名称"
          rules={[{ required: true, message: '请输入设备名称' }]}
        >
          <Input placeholder="请输入设备名称" />
        </Form.Item>
        <Form.Item
          name="asset_no"
          label="资产编号"
          rules={[{ required: true, message: '请输入设备编号' }]}
        >
          <Input placeholder="请输入唯一设备编号" disabled={!!editingEquipment} />
        </Form.Item>
        <Form.Item name="label_no" label="标签号">
          <Input placeholder="请输入标签号" />
        </Form.Item>
        <Form.Item name="equipment_tag" label="设备位号">
          <Input placeholder="请输入设备位号" />
        </Form.Item>
        <Form.Item name="equipment_class" label="设备分类">
          <Select placeholder="请选择设备分类等级" allowClear>
            <Select.Option value="A">A类</Select.Option>
            <Select.Option value="B">B类</Select.Option>
            <Select.Option value="C">C类</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item name="category_description" label="资产类别说明">
          <Input placeholder="请输入资产类别说明" />
        </Form.Item>
        <Form.Item name="location_text" label="设备位置">
          <Input placeholder="请输入设备位置" />
        </Form.Item>
        <Form.Item name="department_id" label="归属部门">
          <Select
            placeholder="请选择归属部门"
            allowClear
            showSearch
            optionFilterProp="label"
            options={departments.map(d => ({ label: d.name, value: d.id }))}
          />
        </Form.Item>
        <Form.Item name="responsible_person_display" label="负责人">
          <Input placeholder="请输入负责人"  />
        </Form.Item>
        <Form.Item name="responsible_person_id" hidden>
          <Input />
        </Form.Item>
        <Form.Item
          name="status"
          label="设备状态"
          rules={[{ required: true, message: '请选择设备状态' }]}
        >
          <Select placeholder="请选择设备状态" options={statusOptions} />
        </Form.Item>

        <Form.Item name="model" label="设备型号">
          <Input placeholder="请输入设备型号" />
        </Form.Item>
        <Form.Item name="specification" label="设备规格">
          <Input placeholder="请输入设备规格" />
        </Form.Item>
        <Form.Item name="manufacturer" label="制造商">
          <Input placeholder="请输入制造商" />
        </Form.Item>
        <Form.Item name="supplier" label="供应商">
          <Input placeholder="请输入供应商" />
        </Form.Item>
        <Form.Item name="production_date" label="出厂日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="commissioning_date" label="投用日期">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="current_cost" label="当前成本">
          <InputNumber
            placeholder="请输入当前成本"
            style={{ width: '100%' }}
            min={0}
            precision={2}
          />
        </Form.Item>
        <Form.Item name="book_value" label="账面净值">
          <InputNumber
            placeholder="请输入账面净值"
            style={{ width: '100%' }}
            min={0}
            precision={2}
          />
        </Form.Item>
        <Form.Item name="quantity" label="数量">
          <InputNumber
            placeholder="请输入数量"
            style={{ width: '100%' }}
            min={1}
            precision={0}
            defaultValue={1}
          />
        </Form.Item>
        <Form.Item name="scrap_status" label="报废状态">
          <Select placeholder="请选择报废状态" allowClear options={[
            { label: '未报废', value: '未报废' },
            { label: '已报废', value: '已报废' },
          ]} />
        </Form.Item>
        <Form.Item name="scrap_time" label="报废时间">
          <DatePicker style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="description" label="设备描述">
          <TextArea rows={4} placeholder="请输入设备描述" />
        </Form.Item>
      </Form>
    </Drawer>
  )
}