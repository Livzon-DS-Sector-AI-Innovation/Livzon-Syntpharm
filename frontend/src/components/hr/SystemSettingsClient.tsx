'use client'

import { useEffect, useState } from 'react'
import { Button, Card, Form, Input, message, Divider } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import { updateSystemSettings } from '@/actions/admin'
import { apiGet } from '@/lib/api/client'

export default function SystemSettingsClient() {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  const loadSettings = async () => {
    setLoading(true)
    try {
      const data = await apiGet<Record<string, unknown>>('/api/v1/hr/system-settings')
      form.setFieldsValue(data)
    } catch (err: unknown) {
      message.error('加载设置失败: ' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    const values = form.getFieldsValue()
    setSaving(true)
    try {
      const json = await updateSystemSettings(values)
      if (json.code === 200) {
        message.success(json.message || '已保存')
      } else {
        message.error(json.message || '保存失败')
      }
    } catch (err: unknown) {
      message.error('保存失败: ' + (err instanceof Error ? err.message : '未知错误'))
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => { loadSettings() }, [])

  const feishuLabel = (name: string) => (
    <span>
      {name}
      <span style={{ color: '#999', fontSize: 12, marginLeft: 8 }}>
        （保存后需重启服务生效）
      </span>
    </span>
  )

  return (
    <Card loading={loading}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600 }}>系统设置</h2>
        <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
          保存设置
        </Button>
      </div>

      <Form form={form} layout="vertical">
        <Divider orientation="horizontal">飞书 - 主 Bot（招聘 / 人事）</Divider>
        <Form.Item label={feishuLabel('FEISHU_APP_ID')} name="FEISHU_APP_ID">
          <Input placeholder="cli_xxxx..." />
        </Form.Item>
        <Form.Item label={feishuLabel('FEISHU_APP_SECRET')} name="FEISHU_APP_SECRET">
          <Input.Password placeholder="飞书 App Secret" />
        </Form.Item>

        <Divider orientation="horizontal">飞书 - 车辆 Bot</Divider>
        <Form.Item label={feishuLabel('FEISHU_VEHICLE_APP_ID')} name="FEISHU_VEHICLE_APP_ID">
          <Input placeholder="cli_xxxx..." />
        </Form.Item>
        <Form.Item label={feishuLabel('FEISHU_VEHICLE_APP_SECRET')} name="FEISHU_VEHICLE_APP_SECRET">
          <Input.Password placeholder="飞书 Vehicle App Secret" />
        </Form.Item>

        <Divider orientation="horizontal">飞书 - 培训 Bot</Divider>
        <Form.Item label={feishuLabel('FEISHU_TRAINING_APP_ID')} name="FEISHU_TRAINING_APP_ID">
          <Input placeholder="cli_xxxx..." />
        </Form.Item>
        <Form.Item label={feishuLabel('FEISHU_TRAINING_APP_SECRET')} name="FEISHU_TRAINING_APP_SECRET">
          <Input.Password placeholder="飞书 Training App Secret" />
        </Form.Item>

        <Divider orientation="horizontal">AI 模型</Divider>
        <Form.Item label="AI_BASE_URL" name="AI_BASE_URL">
          <Input placeholder="https://api.moonshot.cn/v1" />
        </Form.Item>
        <Form.Item label="AI_API_KEY" name="AI_API_KEY">
          <Input.Password placeholder="sk-..." />
        </Form.Item>
        <Form.Item label="AI_MODEL" name="AI_MODEL">
          <Input placeholder="deepseek-v4-pro" />
        </Form.Item>
      </Form>
    </Card>
  )
}
