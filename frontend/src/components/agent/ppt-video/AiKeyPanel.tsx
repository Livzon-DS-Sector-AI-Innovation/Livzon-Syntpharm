'use client'

import { useState } from 'react'
import { App, Button, Form, Input, InputNumber, Popconfirm, Space, Tag, Typography } from 'antd'
import { ApiOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons'

import { createAiConfig, deleteAiConfig, testAiConfig, updateAiConfig } from '@/actions/agent/ppt-video'
import type { AiConfigFormValue, AiConfigItem } from '@/types/agent/ppt-video'

interface Props {
  items: AiConfigItem[]
  onChanged: () => void
}

const PRESET_BASES = [
  { label: '阿里云百炼 MaaS', value: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { label: 'OpenAI', value: 'https://api.openai.com/v1' },
]

/**
 * 我的 API Key：本人私有，其他人既看不到也用不了。
 *
 * 明文 Key 只在提交时出现一次，回显一律用后端掩码。
 */
export default function AiKeyPanel({ items, onChanged }: Props) {
  const { message } = App.useApp()
  const [form] = Form.useForm<AiConfigFormValue>()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; text: string } | null>(null)

  const personal = items.filter((item) => item.visibility === 'personal')

  const openCreate = () => {
    setEditingId(null)
    setTestResult(null)
    form.resetFields()
    form.setFieldsValue({ temperature: 0.7, timeout_seconds: 60 })
    setFormOpen(true)
  }

  const openEdit = (item: AiConfigItem) => {
    setEditingId(item.id)
    setTestResult(null)
    form.setFieldsValue({
      config_name: item.config_name,
      api_base_url: item.api_base_url,
      model_name: item.model_name,
      temperature: item.temperature,
      timeout_seconds: item.timeout_seconds,
    })
    setFormOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    setBusy(true)
    const result = editingId
      ? await updateAiConfig(editingId, {
          ...values,
          // 编辑时留空表示不换 Key，不能把掩码当明文提交
          api_key: values.api_key?.trim() ? values.api_key.trim() : undefined,
        })
      : await createAiConfig(values)
    setBusy(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    setFormOpen(false)
    form.resetFields()
    onChanged()
  }

  const handleTest = async () => {
    const values = form.getFieldsValue()
    setBusy(true)
    const result = await testAiConfig(
      editingId && !values.api_key?.trim() ? ({ config_id: editingId } as AiConfigFormValue & { config_id: string }) : values,
    )
    setBusy(false)
    setTestResult({ ok: result.success, text: result.message || (result.success ? '连通正常' : '连通失败') })
  }

  const handleDelete = async (item: AiConfigItem) => {
    setBusy(true)
    const result = await deleteAiConfig(item.id)
    setBusy(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    onChanged()
  }

  return (
    <div className="flex flex-col gap-3">
      <Typography.Paragraph className="!mb-0 !text-[12px] !text-[#5D5B54]">
        你自己的 Key 只属于你：其他人既看不到也选不到，平台管理员同样读不到明文。
      </Typography.Paragraph>

      {personal.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[#E5E3DF] bg-[#FAFAF9] px-4 py-6 text-center text-[13px] text-[#A4A097]">
          还没有个人 Key，用系统预置模型也能直接写讲稿。
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {personal.map((item) => (
            <div
              key={item.id}
              className="rounded-xl border border-[#E5E3DF] bg-white px-3.5 py-3 transition-colors hover:border-[#5645D4]/40"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-[13px] font-semibold text-[#37352F]">{item.config_name}</span>
                    <Tag color="purple" className="!m-0 !text-[11px]">
                      个人私有
                    </Tag>
                  </div>
                  <div className="mt-1 truncate text-[12px] text-[#5D5B54]">{item.model_name}</div>
                  <div className="mt-0.5 truncate font-mono text-[11px] text-[#A4A097]">{item.masked_api_key}</div>
                </div>
                <Space size={2}>
                  <Button type="text" size="small" icon={<ThunderboltOutlined />} onClick={() => openEdit(item)}>
                    测试/编辑
                  </Button>
                  <Popconfirm
                    title="删除这个 Key？"
                    description="删除后引用它的项目会回退到全局默认模型"
                    okText="删除"
                    cancelText="取消"
                    onConfirm={() => handleDelete(item)}
                  >
                    <Button type="text" size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                </Space>
              </div>
              <div className="mt-1 truncate text-[11px] text-[#A4A097]">
                <ApiOutlined /> {item.api_base_url}
              </div>
            </div>
          ))}
        </div>
      )}

      {!formOpen ? (
        <Button type="dashed" icon={<PlusOutlined />} onClick={openCreate} block>
          添加我的模型
        </Button>
      ) : (
        <div className="rounded-xl border border-[#5645D4]/25 bg-[#EDE9F8]/40 px-3.5 py-3">
          <Form<AiConfigFormValue> form={form} layout="vertical" size="small" className="!mb-0">
            <Form.Item
              label="名称"
              name="config_name"
              rules={[{ required: true, message: '给这个 Key 起个名字，便于区分' }]}
            >
              <Input placeholder="例如：我的 qwen-max 体验账号" maxLength={64} />
            </Form.Item>
            <Form.Item
              label="接口地址"
              name="api_base_url"
              rules={[{ required: true, message: '填写 OpenAI 兼容接口地址' }]}
              extra={
                <Space size={4} wrap className="mt-1">
                  {PRESET_BASES.map((preset) => (
                    <Button
                      key={preset.value}
                      size="small"
                      type="link"
                      className="!px-0 !text-[11px]"
                      onClick={() => form.setFieldsValue({ api_base_url: preset.value })}
                    >
                      {preset.label}
                    </Button>
                  ))}
                </Space>
              }
            >
              <Input placeholder="https://…/compatible-mode/v1" />
            </Form.Item>
            <Form.Item label="模型名" name="model_name" rules={[{ required: true, message: '填写模型名，例如 qwen-max' }]}>
              <Input placeholder="qwen-max" maxLength={128} />
            </Form.Item>
            <Form.Item
              label={editingId ? 'API Key（留空则不修改）' : 'API Key'}
              name="api_key"
              rules={editingId ? [] : [{ required: true, message: '填写 API Key' }]}
            >
              <Input.Password placeholder="sk-…" autoComplete="new-password" />
            </Form.Item>
            <Space size={12} className="w-full">
              <Form.Item label="温度" name="temperature" className="!mb-2">
                <InputNumber min={0} max={2} step={0.1} style={{ width: 92 }} />
              </Form.Item>
              <Form.Item label="超时(秒)" name="timeout_seconds" className="!mb-2">
                <InputNumber min={10} max={600} step={10} style={{ width: 100 }} />
              </Form.Item>
            </Space>
          </Form>

          {testResult ? (
            <div
              className={`mb-2 rounded-lg px-2.5 py-1.5 text-[12px] ${
                testResult.ok ? 'bg-[#1AAE39]/10 text-[#1AAE39]' : 'bg-[#D93025]/10 text-[#D93025]'
              }`}
            >
              {testResult.text}
            </div>
          ) : null}

          <Space size={8} className="w-full justify-end">
            <Button size="small" icon={<ThunderboltOutlined />} loading={busy} onClick={handleTest}>
              测试连通
            </Button>
            <Button size="small" onClick={() => setFormOpen(false)}>
              取消
            </Button>
            <Button size="small" type="primary" loading={busy} icon={editingId ? <EditOutlined /> : <PlusOutlined />} onClick={handleSubmit}>
              {editingId ? '保存修改' : '保存 Key'}
            </Button>
          </Space>
        </div>
      )}
    </div>
  )
}