'use client'

import { useEffect, useState } from 'react'
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
}

export function WorkshopDrawer({ open, workshopId, onClose, onSuccess }: WorkshopDrawerProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const isEdit = !!workshopId

  useEffect(() => {
    if (open && workshopId) {
      setLoading(true)
      getWorkshopById(workshopId)
        .then((data) => {
          form.setFieldsValue({
            code: data.code,
            name: data.name,
            category: data.category,
            sort_order: data.sort_order,
            is_active: data.is_active,
          })
        })
        .catch(() => {
          message.error('加载车间详情失败')
        })
        .finally(() => setLoading(false))
    } else if (open && !workshopId) {
      form.resetFields()
      form.setFieldsValue(DEFAULT_VALUES)
    }
  }, [open, workshopId, form, message])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      if (isEdit && workshopId) {
        await updateWorkshopAction(workshopId, values)
        message.success('更新成功')
      } else {
        await createWorkshopAction(values)
        message.success('创建成功')
      }
      onSuccess()
    } catch (error: unknown) {
      if (error?.errorFields) return // form validation error
      message.error(isEdit ? '更新失败' : '创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Drawer
      title={isEdit ? '编辑车间' : '新增车间'}
      open={open}
      onClose={onClose}
      width={480}
      extra={
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit} loading={submitting}>
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
