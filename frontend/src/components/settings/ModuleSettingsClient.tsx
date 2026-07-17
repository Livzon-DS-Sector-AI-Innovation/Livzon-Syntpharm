'use client'

import { useState, useEffect } from 'react'
import {
  Card,
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
import { EditOutlined, SaveOutlined } from '@ant-design/icons'
import {
  getModuleSettings,
  updateModuleSetting,
  type ModuleSetting,
} from '@/actions/module-settings'

const { Title, Text } = Typography
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
  const [settings, setSettings] = useState<ModuleSetting[]>([])
  const [loading, setLoading] = useState(false)
  const [editingSetting, setEditingSetting] = useState<ModuleSetting | null>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  const loadSettings = async () => {
    setLoading(true)
    try {
      const res = await getModuleSettings(moduleCode)
      setSettings(res.data || [])
    } catch (error) {
      console.error('Failed to load settings:', error)
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSettings()
  }, [moduleCode])

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
      loadSettings()
    } catch (error) {
      console.error('Failed to save setting:', error)
      message.error('保存失败')
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
        return <Text code style={{ fontSize: 12 }}>{setting.value}</Text>
      default:
        return <Text>{setting.value || <Text type="secondary">未设置</Text>}</Text>
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
          <Text strong>{key}</Text>
          {setting.description && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {setting.description}
            </Text>
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
      render: (_: any, setting: ModuleSetting) => renderValue(setting),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, setting: ModuleSetting) => (
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

  return (
    <>
      <Card>
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <div>
            <Title level={4}>{moduleName}配置</Title>
            <Text type="secondary">{moduleDescription}</Text>
          </div>

          <Table
            dataSource={settings}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={false}
          />
        </Space>
      </Card>

      <Modal
        title={`编辑配置: ${editingSetting?.key}`}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleSave}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          {editingSetting && renderEditInput(editingSetting)}
        </Form>
      </Modal>
    </>
  )
}
