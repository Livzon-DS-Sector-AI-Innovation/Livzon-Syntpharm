'use client'
import { EquipmentCategory } from '@/types/equipment/generated-bridge'

import { useEffect } from 'react'
import { App, Form, Input, Button, Modal } from 'antd'
import { createCategory, updateCategory } from '@/actions/equipment'

const { TextArea } = Input

interface CategoryEditorProps {
  mode: 'create' | 'edit'
  parentId?: string
  initialData?: EquipmentCategory
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function CategoryEditor({ mode, parentId, initialData, open, onOpenChange, onSuccess }: CategoryEditorProps) {
  const [form] = Form.useForm()
  const { message } = App.useApp()

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
      
      if (mode === 'edit' && initialData?.id) {
        await updateCategory(initialData.id, values)
        message.success('更新分类成功')
      } else {
        await createCategory(values)
        message.success('创建分类成功')
      }
      
      onOpenChange(false)
      onSuccess()
    } catch (error: any) {
      if (error.errorFields) {
        // Validation error, do nothing
        return
      }
      message.error(error?.message || '操作失败')
    }
  }

  return (
    <Modal
      title={mode === 'edit' ? '编辑分类' : '新增分类'}
      open={open}
      onCancel={() => onOpenChange(false)}
      onOk={handleSubmit}
      okText="确认"
      cancelText="取消"
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item 
          name="name" 
          label="分类名称" 
          rules={[{ required: true, message: '请输入分类名称' }]}
        >
          <Input placeholder="例如：生产设备" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <TextArea rows={3} placeholder="可选填" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
