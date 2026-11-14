'use client'

import { useState } from 'react'
import { Button, Card, Form, Input, message, Divider } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { updateSystemSettings } from '@/actions/admin'
import { apiGet } from '@/lib/api/client'
import type { components } from '@/types/generated/schema'

type HrSystemSettingsValues = components['schemas']['HrSystemSettingsApiResponse']['data']

export default function SystemSettingsClient() {
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)

  const { isLoading: loading } = useQuery({
    queryKey: ['hr-system-settings'],
    queryFn: async () => {
      const data = await apiGet<HrSystemSettingsValues>('/api/v1/hr/system-settings')
      if (!data.HR_ORG_SYNC_ROOTS || data.HR_ORG_SYNC_ROOTS.length === 0) {
        data.HR_ORG_SYNC_ROOTS = [{ department_id: '', name: '' }]
      }
      form.setFieldsValue(data)
      return data
    },
  })

  const handleSave = async () => {
    try {
      await form.validateFields()
    } catch {
      return
    }
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

  const feishuLabel = (name: string) => (
    <span>
      {name}
      <span style={{ color: 'var(--color-stone)', fontSize: 12, marginLeft: 8 }}>
        （保存后需重启服务生效）
      </span>
    </span>
  )

  return (
    <Card loading={loading}>
      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', marginBottom: 24 }}>
        <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
          保存设置
        </Button>
      </div>

      <Form form={form} layout="vertical">
        <Divider>飞书 - 主 Bot（招聘 / 人事）</Divider>
        <Form.Item label={feishuLabel('App ID')} name="FEISHU__PLATFORM__APP_ID">
          <Input placeholder="cli_xxxx..." />
        </Form.Item>
        <Form.Item label={feishuLabel('App Secret')} name="FEISHU__PLATFORM__APP_SECRET">
          <Input.Password placeholder="飞书 App Secret" />
        </Form.Item>

        <Divider>飞书 - 车辆 Bot</Divider>
        <Form.Item label={feishuLabel('车辆 Bot App ID')} name="FEISHU__VEHICLE__CREDENTIALS__APP_ID">
          <Input placeholder="cli_xxxx..." />
        </Form.Item>
        <Form.Item label={feishuLabel('车辆 Bot App Secret')} name="FEISHU__VEHICLE__CREDENTIALS__APP_SECRET">
          <Input.Password placeholder="飞书 Vehicle App Secret" />
        </Form.Item>

        <Divider>飞书 - 培训 Bot</Divider>
        <Form.Item label={feishuLabel('培训 Bot App ID')} name="FEISHU__TRAINING__CREDENTIALS__APP_ID">
          <Input placeholder="cli_xxxx..." />
        </Form.Item>
        <Form.Item label={feishuLabel('培训 Bot App Secret')} name="FEISHU__TRAINING__CREDENTIALS__APP_SECRET">
          <Input.Password placeholder="飞书 Training App Secret" />
        </Form.Item>

        <Divider>HR 组织架构同步</Divider>
        <Form.List name="HR_ORG_SYNC_ROOTS">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <div key={key} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <Form.Item
                    {...restField}
                    label="公司名称"
                    name={[name, 'name']}
                    rules={[{ required: true, message: '请输入公司名称' }]}
                    style={{ flex: 1 }}
                  >
                    <Input placeholder="如 珠海保税区丽珠合成制药有限公司" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    label="根部门 ID"
                    name={[name, 'department_id']}
                    rules={[{ required: true, message: '请输入根部门 ID' }]}
                    style={{ flex: 1 }}
                  >
                    <Input placeholder="飞书 open_department_id" />
                  </Form.Item>
                  <Button
                    danger
                    style={{ marginTop: 30 }}
                    onClick={() => remove(name)}
                    disabled={fields.length <= 1}
                  >
                    删除
                  </Button>
                </div>
              ))}
              <Button style={{ marginBottom: 16 }} onClick={() => add({ department_id: '', name: '' })}>
                添加公司
              </Button>
            </>
          )}
        </Form.List>

        <Divider>AI 模型</Divider>
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
