'use client'

import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Drawer, Form, Input, Select, InputNumber, Switch, Button, Space, Spin, App } from 'antd'
import {
  createWorkshopAction,
  updateWorkshopAction,
  getWorkshopById,
} from '@/actions/energy'
import type { WorkshopCategory } from '@/types/energy'

interface WorkshopDrawerProps {
  open: boolean
  workshopId: string | null
  onClose: () => void
  onSuccess: () => void
}

const DEFAULT_VALUES = {
  category: 'workshop' as WorkshopCategory,
  sort_order: 0,
  is_active: true,
  excluded_energy_types: [] as string[],
}

// 合计行实体：其数值等于其他实体之和，勾选后全厂汇总不再计入该项（月度明细仍可见）
const excludedTypeOptions = [
  { label: '电力', value: 'electricity' },
  { label: '自来水', value: 'water' },
  { label: '蒸汽', value: 'steam' },
  { label: '天然气', value: 'natural_gas' },
]

export function WorkshopDrawer({ open, workshopId, onClose, onSuccess }: WorkshopDrawerProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const isEdit = !!workshopId

  // 使用 useQuery 获取车间数据（挂在 ['energy-workshops'] 前缀下，车间保存后随列表一并失效）
  const { data: workshopData, isLoading: loading } = useQuery({
    queryKey: ['energy-workshops', 'detail', workshopId],
    queryFn: async () => {
      if (!workshopId) return null
      const data = await getWorkshopById(workshopId)
      return data
    },
    enabled: open && !!workshopId,
  })

  // 当数据加载完成后设置表单值
  useEffect(() => {
    if (open && workshopData) {
      form.setFieldsValue({
        code: workshopData.code,
        name: workshopData.name,
        category: workshopData.category,
        sort_order: workshopData.sort_order,
        is_active: workshopData.is_active,
        excluded_energy_types: workshopData.excluded_energy_types ?? [],
      })
    } else if (open && !workshopId) {
      form.resetFields()
      form.setFieldsValue(DEFAULT_VALUES)
    }
  }, [open, workshopId, workshopData, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (isEdit && workshopId) {
        await updateWorkshopAction(workshopId, values)
        message.success('更新成功')
      } else {
        await createWorkshopAction(values)
        message.success('创建成功')
      }
      onSuccess()
    } catch (error: unknown) {
      if (error && typeof error === "object" && "errorFields" in error) return // form validation error
      message.error(isEdit ? '更新失败' : '创建失败')
    }
  }

  return (
    <Drawer forceRender
      title={isEdit ? '编辑车间' : '新增车间'}
      open={open}
      onClose={onClose}
      size={480}
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit}>
            {isEdit ? '保存' : '创建'}
          </Button>
        </Space>
      }
    >
      <Spin spinning={loading}>
        <Form form={form} layout="vertical" initialValues={DEFAULT_VALUES}>
          <Form.Item
            name="code"
            label="车间编码"
            rules={[
              { required: true, message: '请输入车间编码' },
              { max: 50, message: '编码不超过50个字符' },
            ]}
          >
            <Input placeholder="如 WS001" />
          </Form.Item>
          <Form.Item
            name="name"
            label="车间名称"
            rules={[
              { required: true, message: '请输入车间名称' },
              { max: 100, message: '名称不超过100个字符' },
            ]}
          >
            <Input placeholder="如 固体制剂车间" />
          </Form.Item>
          <Form.Item
            name="category"
            label="分类"
            rules={[{ required: true, message: '请选择分类' }]}
          >
            <Select
              options={[
                { value: 'workshop', label: '生产车间' },
                { value: 'position', label: '岗位' },
                { value: 'support', label: '辅助部门' },
                { value: 'utility', label: '动力设施' },
              ]}
            />
          </Form.Item>
          <Form.Item
            name="excluded_energy_types"
            label="不计入全厂汇总"
            tooltip="合计行（数值等于其他车间之和）勾选对应能源类型后，能源总览与全厂合计会剔除该项，避免重复计数；月度记录明细不受影响。"
          >
            <Select mode="multiple" allowClear placeholder="不勾选则全部计入" options={excludedTypeOptions} />
          </Form.Item>
          <Form.Item name="sort_order" label="排序">
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="is_active" label="是否启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Spin>
    </Drawer>
  )
}
