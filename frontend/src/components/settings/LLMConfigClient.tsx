'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  InputNumber,
  Typography,
  Space,
  Tag,
  Popconfirm,
  Tooltip,
  App,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  ArrowLeftOutlined,
  ApiOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import {
  getLLMConfigs,
  createLLMConfig,
  updateLLMConfig,
  deleteLLMConfig,
  testLLMConnection,
} from '@/actions/settings'
import type { LLMConfig } from '@/types/settings'

const { Title, Text } = Typography
const { TextArea } = Input

const CONFIG_TYPE_OPTIONS = [
  { value: 'text', label: '文本模型' },
  { value: 'vision', label: '视觉模型' },
]

interface LLMConfigClientProps {
  embedded?: boolean
}

export default function LLMConfigClient({ embedded = false }: LLMConfigClientProps) {
  const { message } = App.useApp()
  const router = useRouter()
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)
  const [form] = Form.useForm()

  const { data: configs = [], isLoading: loading } = useQuery({
    queryKey: ['llm-configs'],
    queryFn: async () => {
      const res = await getLLMConfigs()
      return res.data || []
    },
  })

  const handleCreate = () => {
    setEditingConfig(null)
    form.resetFields()
    form.setFieldsValue({
      config_type: 'text',
      temperature: 0.1,
      timeout_seconds: 120,
      is_active: false,
    })
    setModalOpen(true)
  }

  const handleEdit = (record: LLMConfig) => {
    setEditingConfig(record)
    form.setFieldsValue({
      config_name: record.config_name,
      config_type: record.config_type,
      api_base_url: record.api_base_url,
      api_key: '',
      model_name: record.model_name,
      temperature: record.temperature,
      timeout_seconds: record.timeout_seconds,
      is_active: record.is_active,
      notes: record.notes,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteLLMConfig(id)
      message.success('删除成功')
      queryClient.invalidateQueries({ queryKey: ['llm-configs'] })
    } catch {
      message.error('删除失败')
    }
  }

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      const payload = { ...values }
      if (editingConfig && !payload.api_key) {
        delete payload.api_key
      }
      setSaving(true)
      if (editingConfig) {
        await updateLLMConfig(editingConfig.id, payload)
        message.success('更新成功')
      } else {
        await createLLMConfig(payload)
        message.success('创建成功')
      }
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['llm-configs'] })
    } catch (error) {
      console.error('Save failed:', error)
    } finally {
      setSaving(false)
    }
  }

  const handleActivate = async (id: string) => {
    setTestingId(id)
    try {
      await updateLLMConfig(id, { is_active: true })
      message.success('已激活，所有 AI 调用将使用此配置')
      queryClient.invalidateQueries({ queryKey: ['llm-configs'] })
    } catch {
      message.error('激活失败')
    } finally {
      setTestingId(null)
    }
  }

  const handleTestConnection = async () => {
    try {
      const res = await testLLMConnection()
      if (res.data?.status === 'ok') {
        message.success('连接测试成功')
      } else {
        message.error(res.data?.detail || '连接测试失败')
      }
    } catch {
      message.error('连接测试失败')
    }
  }

  const columns = [
    {
      title: '配置名称',
      dataIndex: 'config_name',
      key: 'config_name',
      width: 180,
      render: (name: string, record: LLMConfig) => (
        <Space>
          {name}
          {record.is_active && <Tag color="success">当前使用</Tag>}
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'config_type',
      key: 'config_type',
      width: 110,
      render: (type: string) => {
        const opt = CONFIG_TYPE_OPTIONS.find((o) => o.value === type)
        return <Tag color={type === 'text' ? 'blue' : 'purple'}>{opt?.label || type}</Tag>
      },
    },
    {
      title: 'API 地址',
      dataIndex: 'api_base_url',
      key: 'api_base_url',
      ellipsis: true,
      width: 260,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 200, fixed: "right" as const,
      render: (model: string) => <Tag color="geekblue">{model}</Tag>,
    },
    {
      title: 'Temperature',
      dataIndex: 'temperature',
      key: 'temperature',
      width: 110,
    },
    {
      title: '超时(秒)',
      dataIndex: 'timeout_seconds',
      key: 'timeout_seconds',
      width: 100,
    },
    {
      title: '操作',
      key: 'actions',
      width: 200, fixed: "right" as const,
      render: (_: unknown, record: LLMConfig) => (
        <Space>
          {!record.is_active && (
            <Tooltip title="激活此配置">
              <Button
                type="link"
                size="small"
                icon={<CheckCircleOutlined />}
                loading={testingId === record.id}
                onClick={() => handleActivate(record.id)}
              />
            </Tooltip>
          )}
          <Tooltip title="编辑">
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="确定删除此配置？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Tooltip title="删除">
              <Button type="link" size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div style={{ maxWidth: 1300, margin: '0 auto', padding: embedded ? 0 : '24px' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 24,
        }}
      >
        <div>
        {!embedded && (
          <Button icon={<ArrowLeftOutlined />} onClick={() => router.back()} style={{ marginRight: 16 }}>
            返回
          </Button>
        )}
          <Title level={3} style={{ margin: 0 }}>
            <SettingOutlined style={{ marginRight: 12 }} />
            LLM 模型配置
          </Title>
          <Text style={{ fontSize: 14, color: '#666', marginTop: 8, display: 'block' }}>
            配置 AI 大模型 API 连接参数。同一时间仅一个配置生效。
          </Text>
        </div>
        <Space>
          <Button icon={<ApiOutlined />} onClick={handleTestConnection}>
            测试连接
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={handleCreate}
          >
            新建配置
          </Button>
        </Space>
      </div>

      <Card>
        <Table scroll={{ x: 1000 }}
          columns={columns}
          dataSource={configs}
          rowKey="id"
          loading={loading}
          size="middle"
          pagination={false}
        />
      </Card>

      <Modal
        title={editingConfig ? '编辑 LLM 配置' : '新建 LLM 配置'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        width={640}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="config_name"
            label="配置名称"
            rules={[{ required: true, message: '请输入配置名称' }]}
          >
            <Input placeholder="例如：生产环境 GPT-4o" />
          </Form.Item>

          <Form.Item
            name="config_type"
            label="配置类型"
            rules={[{ required: true, message: '请选择配置类型' }]}
          >
            <Select options={CONFIG_TYPE_OPTIONS} placeholder="选择配置类型" />
          </Form.Item>

          <Form.Item
            name="api_base_url"
            label="API 基础 URL"
            rules={[{ required: true, message: '请输入 API 地址' }]}
          >
            <Input placeholder="https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API 密钥"
            rules={[{ required: !editingConfig, message: '请输入 API 密钥' }]}
            extra={editingConfig ? '留空则不修改' : undefined}
          >
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item
            name="model_name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="gpt-4o" />
          </Form.Item>

          <Space size="large">
            <Form.Item name="temperature" label="Temperature">
              <InputNumber min={0} max={2} step={0.1} style={{ width: 120 }} />
            </Form.Item>
            <Form.Item name="timeout_seconds" label="超时(秒)">
              <InputNumber min={10} max={600} style={{ width: 120 }} />
            </Form.Item>
          </Space>

          <Form.Item name="is_active" label="激活状态" valuePropName="checked">
            <Switch checkedChildren="激活" unCheckedChildren="未激活" />
          </Form.Item>

          <Form.Item name="notes" label="备注">
            <TextArea rows={2} placeholder="配置说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
