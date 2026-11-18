'use client'

import { useEffect, useState } from 'react'
import { Alert, App, Form, Input, Modal } from 'antd'
import PermissionTreePanel from '@/components/settings/PermissionTreePanel'
import { createRole, updateRole } from '@/actions/permission'
import type { PermissionTreeNode, RoleDetail } from '@/types/permission'

interface RoleEditModalProps {
  open: boolean
  moduleCode: string
  /** 权限树里只保留本模块节点（已把模块管理入口码置灰） */
  moduleTree: PermissionTreeNode[]
  treeError: unknown
  /** 传值时是编辑，null 是新建 */
  editingRole: RoleDetail | null
  onClose: () => void
  onSaved: () => void
}

/**
 * 岗位角色新建 / 编辑弹窗。
 *
 * 从 `ModulePermissionPanel` 拆出来：表单、提交、错误提示自成一体，
 * 主面板只负责列表与入口，避免一个文件里同时堆两个弹窗 + 两张表。
 */
export default function RoleEditModal({
  open,
  moduleCode,
  moduleTree,
  treeError,
  editingRole,
  onClose,
  onSaved,
}: RoleEditModalProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)

  // 每次打开按当前记录回填：编辑带出名称与已有权限，新建从空白开始
  useEffect(() => {
    if (!open) return
    form.setFieldsValue({
      name: editingRole?.name ?? '',
      permission_codes: editingRole?.permission_codes ?? [],
    })
  }, [open, editingRole, form])

  const submit = async () => {
    const values = await form.validateFields()
    const permissionCodes: string[] = values.permission_codes ?? []
    setSaving(true)
    try {
      if (editingRole) {
        // 编码不可改：历史授权按角色 ID 关联，改编码会造成认知混乱
        const result = await updateRole(editingRole.id, {
          name: String(values.name).trim(),
          permission_codes: permissionCodes,
        })
        if (!result.ok) {
          message.error(result.message)
          return
        }
        message.success('角色已更新')
      } else {
        const result = await createRole({
          name: String(values.name).trim(),
          category: 'module',
          module_code: moduleCode,
          permission_codes: permissionCodes,
        })
        if (!result.ok) {
          message.error(result.message)
          return
        }
        message.success('角色已创建')
      }
      onClose()
      onSaved()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      open={open}
      title={editingRole ? `编辑角色 · ${editingRole.name}` : '新建岗位角色'}
      width={720}
      confirmLoading={saving}
      onOk={submit}
      onCancel={onClose}
      okText="保存"
      cancelText="取消"
      destroyOnHidden
    >
      <Form form={form} layout="vertical" className="pt-2">
        <Form.Item
          name="name"
          label="角色名称"
          rules={[{ required: true, message: '请填写角色名称，如「偏差审核员」' }]}
        >
          <Input placeholder="偏差审核员" maxLength={50} />
        </Form.Item>
        <Form.Item name="permission_codes" label="权限（只显示本模块业务权限）">
          {treeError ? (
            <Alert
              type="error"
              showIcon
              message="权限目录加载失败"
              description={treeError instanceof Error ? treeError.message : '请刷新页面重试'}
            />
          ) : (
            <PermissionTreePanel tree={moduleTree} />
          )}
        </Form.Item>
      </Form>
    </Modal>
  )
}
