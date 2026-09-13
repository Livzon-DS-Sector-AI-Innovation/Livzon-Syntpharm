'use client'

import { useEffect } from 'react'
import { App, Form, Input, Modal } from 'antd'
import { createLocation, updateLocation } from '@/actions/equipment'
import { Location } from '@/types/equipment/generated-bridge'

const { TextArea } = Input

interface LocationEditorProps {
  mode: 'create' | 'edit'
  parentId?: string
  initialData?: Location
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function LocationEditor({ mode, parentId, initialData, open, onOpenChange, onSuccess }: LocationEditorProps) {
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
        await updateLocation(initialData.id, values)
        message.success('更新位置成功')
      } else {
        await createLocation(values)
        message.success('创建位置成功')
      }
      
      onOpenChange(false)
      onSuccess()
    } catch (error: unknown) {
      if (error && typeof error === "object" && "errorFields" in error && Array.isArray((error as { errorFields: unknown[] }).errorFields)) {
        // Validation error, do nothing
        return
      }
      message.error((error instanceof Error ? error.message : null) || '操作失败')
    }
  }

  return (
    <Modal
      title={mode === 'edit' ? '编辑位置' : '新增位置'}
      open={open}
      onCancel={() => onOpenChange(false)}
      onOk={handleSubmit}
      okText="确认"
      cancelText="取消"
    >
      <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
        <Form.Item 
          name="name" 
          label="位置名称" 
          rules={[{ required: true, message: '请输入位置名称' }]}
        >
          <Input placeholder="例如：A栋-1F-发酵区" />
        </Form.Item>
        <Form.Item name="description" label="备注">
          <TextArea rows={3} placeholder="可选填，如：恒温恒湿区域" />
        </Form.Item>
      </Form>
    </Modal>
  )
}
