'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Switch,
  InputNumber,
  Typography,
  Space,
  App,
  Tag,
} from 'antd'
import {EditOutlined} from '@ant-design/icons'
import {
  getModuleSettings,
  updateModuleSetting,
} from '@/actions/module-settings'
import type { ModuleSetting } from '@/types/module-settings'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'
import { SettingsListCard } from './SettingsListCard'
import { SettingsPageHeader } from './SettingsPageHeader'

const { Text } = Typography
const { TextArea } = Input

interface ModuleSettingsClientProps {
  moduleCode: string
  moduleName: string
  moduleDescription: string
}

export default function ModuleSettingsClient({
  moduleCode,
  moduleName,
  moduleDescription,
}: ModuleSettingsClientProps) {
  const { message } = App.useApp()

  // 权限：无「平台配置管理」权限时隐藏编辑入口
  // （前端隐藏只是体验优化，后端 require_permission 仍会拦截绕过前端的调用）
  // 注意：hook 必须写在任何 early return 之前
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.configManage)

  const queryClient = useQueryClient()
  const [editingSetting, setEditingSetting] = useState<ModuleSetting | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const { data: settings = [], isLoading: loading } = useQuery({
    queryKey: ['module-settings', moduleCode],
    queryFn: async () => {
      const res = await getModuleSettings(moduleCode)
      return res.data || []
    },
  })

  const handleEdit = (setting: ModuleSetting) => {
    setEditingSetting(setting)
    form.setFieldsValue({
      value: setting.value,
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    if (!editingSetting) return

    try {
      const values = await form.validateFields()
      setSaving(true)

      await updateModuleSetting(editingSetting.module, editingSetting.key, {
        value: values.value,
      })

      message.success('配置已更新')
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['module-settings', moduleCode] })
    } catch (error) {
      console.error('Failed to save setting:', error)
      message.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const renderValue = (setting: ModuleSetting) => {
    switch (setting.value_type) {
      case 'bool':
        return (
          <Tag color={setting.value === 'true' ? 'green' : 'default'}>
            {setting.value === 'true' ? '启用' : '禁用'}
          </Tag>
        )
      case 'int':
        return <Text code>{setting.value}</Text>
      case 'json':
        return <Text code className="text-[12px]">{setting.value}</Text>
      default:
        return (
          <Text>
            {setting.value || (
              <span className="text-[12px] text-[var(--color-steel)]">未设置</span>
            )}
          </Text>
        )
    }
  }

  const renderEditInput = (setting: ModuleSetting) => {
    switch (setting.value_type) {
      case 'bool':
        return (
          <Form.Item name="value" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
        )
      case 'int':
        return (
          <Form.Item name="value" rules={[{ required: true, message: '请输入值' }]}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        )
      case 'json':
        return (
          <Form.Item name="value" rules={[{ required: true, message: '请输入值' }]}>
            <TextArea rows={6} placeholder="输入 JSON 格式" />
          </Form.Item>
        )
      default:
        return (
          <Form.Item name="value" rules={[{ required: true, message: '请输入值' }]}>
            <Input placeholder="输入配置值" />
          </Form.Item>
        )
    }
  }

  const columns = [
    {
      title: '配置项',
      dataIndex: 'key',
      key: 'key',
      width: 300,
      render: (key: string, setting: ModuleSetting) => (
        <Space orientation="vertical" size={0}>
          <span className="font-medium text-[var(--color-charcoal)]">{key}</span>
          {setting.description && (
            <span className="text-[12px] text-[var(--color-steel)]">{setting.description}</span>
          )}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'value_type',
      key: 'value_type',
      width: 100,
      render: (type: string) => (
        <Tag color={type === 'bool' ? 'blue' : type === 'int' ? 'orange' : 'default'}>
          {type}
        </Tag>
      ),
    },
    {
      title: '当前值',
      dataIndex: 'value',
      key: 'value',
      render: (_: unknown, setting: ModuleSetting) => renderValue(setting),
    },
    // 操作列：无「平台配置管理」权限时整列不出现
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'action',
            width: 100,
            render: (_: unknown, setting: ModuleSetting) => (
              <Button
                type="link"
                icon={<EditOutlined />}
                onClick={() => handleEdit(setting)}
              >
                编辑
              </Button>
            ),
          },
        ]
      : []),
  ]

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader title={moduleName} description={moduleDescription} />

      <SettingsListCard>
        <Table
          dataSource={settings}
          columns={columns}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 'max-content' }}
        />
      </SettingsListCard>

      <Modal
        title={`编辑配置: ${editingSetting?.key}`}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width="min(520px, calc(100vw - 24px))"
      >
        <Form form={form} layout="vertical">
          {editingSetting && renderEditInput(editingSetting)}
        </Form>
      </Modal>
    </div>
  )
}
