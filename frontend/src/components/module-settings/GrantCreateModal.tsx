'use client'

import { useState } from 'react'
import { App, Form, Modal, Select, Typography } from 'antd'
import PersonSelect from '@/components/common/PersonSelect'
import { createGrant } from '@/actions/permission'
import type { RoleDetail } from '@/types/permission'

const { Text } = Typography

interface GrantCreateModalProps {
  open: boolean
  /** 当前账号有资格授予的角色（岗位角色 + 可为负责人/管理员时的「模块管理员」） */
  grantableRoles: RoleDetail[]
  onClose: () => void
  onSaved: () => void
}

/**
 * 新建授权弹窗：选员工 + 选本模块可授予角色。
 *
 * 数据范围当前统一 `all`（后端休眠），界面不暴露部门/本人范围。
 */
export default function GrantCreateModal({ open, grantableRoles, onClose, onSaved }: GrantCreateModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [granting, setGranting] = useState(false)

  const submit = async () => {
    const values = await form.validateFields()
    setGranting(true)
    try {
      await createGrant({
        user_id: values.user_id,
        role_id: values.role_id,
        scope_type: 'all',
      })
      message.success('授权成功')
      form.resetFields()
      onClose()
      onSaved()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '授权失败')
    } finally {
      setGranting(false)
    }
  }

  return (
    <Modal
      open={open}
      title="新建授权"
      confirmLoading={granting}
      onOk={submit}
      onCancel={onClose}
      okText="授权"
      cancelText="取消"
      destroyOnHidden
      afterOpenChange={(visible) => {
        if (visible) form.resetFields()
      }}
    >
      <Form form={form} layout="vertical" className="pt-2">
        {/* PersonSelect 的 onChange 回传的是 {id,name} 对象，取 id 存入表单 */}
        <Form.Item
          name="user_id"
          label="员工"
          rules={[{ required: true, message: '请选择员工' }]}
          getValueFromEvent={(person: { id: string } | null) => person?.id}
        >
          <PersonSelect placeholder="搜索姓名选择员工" />
        </Form.Item>
        <Form.Item name="role_id" label="岗位角色" rules={[{ required: true, message: '请选择岗位角色' }]}>
          <Select
            placeholder="选择岗位角色"
            options={grantableRoles.map((role) => ({ value: role.id, label: role.name }))}
          />
        </Form.Item>
        <Text type="secondary">数据范围当前统一为「全部数据」，暂不支持按部门或本人限制。</Text>
      </Form>
    </Modal>
  )
}
