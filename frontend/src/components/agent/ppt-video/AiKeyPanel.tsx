'use client'

import { useState } from 'react'
import { App, Button, Form, Input, InputNumber, Popconfirm, Select, Space, Tag, Typography } from 'antd'
import { ApiOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons'

import {
  createAiConfig,
  deleteAiConfig,
  discoverAiModels,
  testAiConfig,
  updateAiConfig,
} from '@/actions/agent/ppt-video'
import type { AiConfigFormValue, AiConfigItem } from '@/types/agent/ppt-video'

interface Props {
  items: AiConfigItem[]
  onChanged: () => void
}

const PRESET_BASES = [
  { label: '阿里云百炼 MaaS', value: 'https://dashscope.aliyuncs.com/compatible-mode/v1' },
  { label: 'OpenAI', value: 'https://api.openai.com/v1' },
]

/** 卡片上最多平铺几个模型，超出的收成「+N」 */
const MAX_MODEL_TAGS = 4

/**
 * 自定义模型：一个 API Key 可勾选该网关下的多个模型。
 *
 * 模型名不再手填，点「获取模型」由后端代理拉取；网关不支持 /models 时，
 * 下拉框仍可直接输入模型名（mode="tags"），保证可用性。
 * 明文 Key 只在提交时出现一次，回显一律用后端掩码。
 */
export default function AiKeyPanel({ items, onChanged }: Props) {
  const { message } = App.useApp()
  const [form] = Form.useForm<AiConfigFormValue>()
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [candidates, setCandidates] = useState<string[]>([])
  const [discoverNote, setDiscoverNote] = useState<{ ok: boolean; text: string } | null>(null)
  const [testResult, setTestResult] = useState<{ ok: boolean; text: string } | null>(null)

  const personal = items.filter((item) => item.visibility === 'personal')

  const openCreate = () => {
    setEditingId(null)
    setTestResult(null)
    setDiscoverNote(null)
    setCandidates([])
    form.resetFields()
    form.setFieldsValue({ temperature: 0.7, timeout_seconds: 60, available_models: [] })
    setFormOpen(true)
  }

  const openEdit = (item: AiConfigItem) => {
    const models = item.available_models?.length ? item.available_models : [item.model_name]
    setEditingId(item.id)
    setTestResult(null)
    setDiscoverNote(null)
    setCandidates(models)
    form.setFieldsValue({
      config_name: item.config_name,
      api_base_url: item.api_base_url,
      available_models: models,
      temperature: item.temperature,
      timeout_seconds: item.timeout_seconds,
    })
    setFormOpen(true)
  }

  const handleDiscover = async () => {
    const values = form.getFieldsValue()
    const apiBaseUrl = values.api_base_url?.trim()
    const apiKey = values.api_key?.trim()
    if (!apiBaseUrl) {
      message.warning('请先填写接口地址')
      return
    }
    if (!apiKey && !editingId) {
      message.warning('请先填写密钥')
      return
    }

    setDiscovering(true)
    const result = await discoverAiModels({
      // 编辑态没换 Key 时复用已保存的 Key，避免让用户重新输入
      config_id: !apiKey && editingId ? editingId : undefined,
      api_base_url: apiBaseUrl,
      api_key: apiKey || undefined,
    })
    setDiscovering(false)

    if (!result.success) {
      // 失败不阻塞保存：仍可在下拉里手动输入模型名
      setDiscoverNote({ ok: false, text: result.message || '获取模型失败，可手动填写模型名' })
      return
    }

    const models = result.data?.models ?? []
    const selected = values.available_models ?? []
    setCandidates(Array.from(new Set([...selected, ...models])))
    // 新拉到的模型不自动全勾，只把候选放进下拉；用户自己勾
    form.setFieldsValue({ available_models: selected })
    setDiscoverNote({ ok: true, text: result.message || `获取到 ${models.length} 个模型` })
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
    const models = values.available_models ?? []
    if (models.length === 0) {
      message.warning('请先获取或填写至少一个模型')
      return
    }
    setBusy(true)
    const result = await testAiConfig({
      config_id: !values.api_key?.trim() && editingId ? editingId : undefined,
      api_base_url: values.api_base_url,
      api_key: values.api_key?.trim() || undefined,
      model_name: models[0],
    })
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

  const modelOptions = candidates.map((model) => ({ label: model, value: model }))

  return (
    <div className="flex flex-col gap-3">
      <Typography.Paragraph className="!mb-0 !text-[12px] !text-[#5D5B54]">
        你自己添加的模型只有你能用：同事看不到也选不到，管理员同样看不到明文密钥。
      </Typography.Paragraph>

      {personal.length === 0 ? (
        <div className="rounded-xl border border-dashed border-[#E5E3DF] bg-[#FAFAF9] px-4 py-6 text-center text-[13px] text-[#A4A097]">
          还没有自定义模型。用平台预置的模型也能直接写讲稿。
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {personal.map((item) => {
            const models = item.available_models?.length ? item.available_models : [item.model_name]
            const extra = models.length - MAX_MODEL_TAGS
            return (
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
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                      {models.slice(0, MAX_MODEL_TAGS).map((model) => (
                        <Tag key={model} className="!m-0 !text-[11px]">
                          {model}
                        </Tag>
                      ))}
                      {extra > 0 ? <span className="text-[11px] text-[#A4A097]">+{extra}</span> : null}
                    </div>
                    <div className="mt-1 truncate text-[11px] text-[#A4A097]">已保存密钥 {item.masked_api_key}</div>
                  </div>
                  <Space size={2}>
                    <Button type="text" size="small" icon={<ThunderboltOutlined />} onClick={() => openEdit(item)}>
                      测试/编辑
                    </Button>
                    <Popconfirm
                      title="删除这个模型？"
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
                  <ApiOutlined /> 接口地址 {item.api_base_url}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {!formOpen ? (
        <Button type="dashed" icon={<PlusOutlined />} onClick={openCreate} block>
          添加自定义模型
        </Button>
      ) : (
        <div className="rounded-xl border border-[#5645D4]/25 bg-[#EDE9F8]/40 px-3.5 py-3">
          <Form<AiConfigFormValue> form={form} layout="vertical" size="small" className="!mb-0">
            <Form.Item
              label="名称"
              name="config_name"
              rules={[{ required: true, message: '给这份配置起个名字，便于区分' }]}
            >
              <Input placeholder="例如：我的通义体验账号" maxLength={64} />
            </Form.Item>
            <Form.Item
              label="接口地址"
              name="api_base_url"
              rules={[{ required: true, message: '填写服务商提供的接口地址' }]}
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
            <Form.Item
              label={editingId ? '密钥（留空则不修改）' : '密钥'}
              name="api_key"
              rules={editingId ? [] : [{ required: true, message: '填写密钥' }]}
            >
              <Input.Password placeholder="粘贴服务商给的密钥" autoComplete="new-password" />
            </Form.Item>
            <Form.Item
              label={
                <span className="flex items-center gap-2">
                  模型
                  <Button
                    size="small"
                    type="link"
                    className="!h-auto !px-0 !text-[12px]"
                    icon={<ThunderboltOutlined />}
                    loading={discovering}
                    onClick={(event) => {
                      event.preventDefault()
                      event.stopPropagation()
                      void handleDiscover()
                    }}
                  >
                    获取模型
                  </Button>
                </span>
              }
              name="available_models"
              rules={[
                {
                  validator: (_, value: string[] | undefined) =>
                    value && value.length > 0
                      ? Promise.resolve()
                      : Promise.reject(new Error('请先获取模型，或手动输入模型名')),
                },
              ]}
              extra={
                <span className="text-[11px] text-[#A4A097]">
                  点「获取模型」加载这份配置可用的模型；也可以直接输入模型名后回车。勾选多个后可在「模型」页切换
                </span>
              }
            >
              <Select
                mode="tags"
                allowClear
                placeholder="先获取模型，或直接输入模型名"
                options={modelOptions}
                tokenSeparators={[',', '，']}
                notFoundContent={discovering ? '正在获取…' : '暂无候选，可手动输入'}
              />
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

          {discoverNote ? (
            <div
              className={`mb-2 rounded-lg px-2.5 py-1.5 text-[12px] ${
                discoverNote.ok ? 'bg-[#1AAE39]/10 text-[#1AAE39]' : 'bg-[#B26A00]/10 text-[#B26A00]'
              }`}
            >
              {discoverNote.text}
            </div>
          ) : null}

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
            <Button
              size="small"
              type="primary"
              loading={busy}
              icon={editingId ? <EditOutlined /> : <PlusOutlined />}
              onClick={handleSubmit}
            >
              {editingId ? '保存修改' : '保存密钥'}
            </Button>
          </Space>
        </div>
      )}
    </div>
  )
}