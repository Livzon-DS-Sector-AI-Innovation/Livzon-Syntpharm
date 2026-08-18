'use client'

import { useState, useEffect } from 'react'
import { App, Form, Input, Button, Popover, Space } from 'antd'
import { PlusOutlined, EditOutlined } from '@ant-design/icons'
import { useEquipmentStore } from '@/stores/equipment'
import { createCategory, updateCategory } from '@/actions/equipment'

const { TextArea } = Input

interface CategoryEditorProps {
  mode: 'create' | 'edit'
  parentId?: string
  initialData?: any
  trigger: React.ReactNode
  onSuccess: () => void
}

export function CategoryEditor({ mode, parentId, initialData, trigger, onSuccess }: CategoryEditorProps) {
  const [form] = Form.useForm()
  const { message } = App.useApp()
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (open) {
      form.setFieldsValue(initialData || { parent_id: parentId })
    } else {
      form.resetFields()
    }
  }, [open, form, initialData, parentId])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)

      if (mode === 'edit' && initialData?.id) {
        await updateCategory(initialData.id, values)
        message.success('更新分类成功')
      } else {
        await createCategory(values)
        message.success('创建分类成功')
      }
      setOpen(false)
      onSuccess()
    } catch (err: any) {
      if (err?.errorFields) return
      message.error('操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  const content = (
    <div style={{ width: 280 }}>
      <Form form={form} layout="vertical" onFinish={handleSubmit}>
        <Form.Item name="name" label="分类名称" rules={[{ required: true }]}>
          <Input placeholder="例如：生产设备" />
        </Form.Item>
        <Form.Item name="code" label="分类代码">
          <Input placeholder="例如：PROD" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <TextArea rows={2} />
        </Form.Item>
        <Form.Item name="parent_id" hidden>
          <Input />
        </Form.Item>
        <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
          <Space>
            <Button size="small" onClick={() => setOpen(false)}>取消</Button>
            <Button type="primary" size="small" htmlType="submit" loading={submitting}>
              {mode === 'edit' ? '更新' : '创建'}
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </div>
  )

  return (
    <Popover
      content={content}
      title={mode === 'edit' ? '编辑分类' : '新增分类'}
      trigger="click"
      open={open}
      onOpenChange={setOpen}
      placement="right"
    >
      {trigger}
    </Popover>
  )
}
