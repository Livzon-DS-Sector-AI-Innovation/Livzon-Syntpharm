'use client'

import { useState } from 'react'
import { Alert, App, Button, Card, Form, Input, Switch, Tag } from 'antd'
import {
  sendDeviationNotifyTestAction,
  updateDeviationNotifySettingsAction,
} from '@/actions/quality'
import type { DeviationNotifySettings, DeviationNotifyTestResult } from '@/types/quality'

interface NotifySettingsCardProps {
  initialSettings: DeviationNotifySettings | null
}

interface NotifyFormValues {
  enabled: boolean
  chat_id: string
  flow: boolean
  ai_done: boolean
  overdue: boolean
  weekly: boolean
  gmp_group: boolean
}

const EVENT_FIELDS: { name: keyof Omit<NotifyFormValues, 'enabled' | 'chat_id'>; label: string; hint: string }[] = [
  { name: 'flow', label: '流转即时通知', hint: '提交调查、审核通过、退回、关闭等环节变化' },
  { name: 'ai_done', label: 'AI 分析完成', hint: 'AI 分析结束转入调查时通知调查人' },
  { name: 'overdue', label: '超期提醒', hint: '定时扫描超期偏差并提醒处理人' },
  { name: 'weekly', label: '每周确认提醒', hint: '每周提醒生产车间确认生产与偏差状态' },
  { name: 'gmp_group', label: '未提交偏差群通知', hint: '生产车间未提交偏差时发送到群聊' },
]

/** 偏差通知设置：总开关 + 群 chat_id + 各类事件开关 + 测试发送自检 */
export function NotifySettingsCard({ initialSettings }: NotifySettingsCardProps) {
  const { message } = App.useApp()
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [testResult, setTestResult] = useState<DeviationNotifyTestResult | null>(null)
  const [form] = Form.useForm<NotifyFormValues>()

  const initialValues: NotifyFormValues = {
    enabled: initialSettings?.enabled ?? true,
    chat_id: initialSettings?.chat_id ?? '',
    flow: initialSettings?.events?.flow ?? true,
    ai_done: initialSettings?.events?.ai_done ?? true,
    overdue: initialSettings?.events?.overdue ?? true,
    weekly: initialSettings?.events?.weekly ?? true,
    gmp_group: initialSettings?.events?.gmp_group ?? true,
  }

  const handleSave = async () => {
    const values = await form.validateFields()
    setSaving(true)
    const result = await updateDeviationNotifySettingsAction({
      enabled: values.enabled,
      chat_id: values.chat_id ?? '',
      events: {
        flow: values.flow,
        ai_done: values.ai_done,
        overdue: values.overdue,
        weekly: values.weekly,
        gmp_group: values.gmp_group,
      },
    })
    setSaving(false)
    if (result.code === 200) {
      message.success('通知设置已保存')
    } else {
      message.error(result.message)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    const result = await sendDeviationNotifyTestAction()
    setTesting(false)
    if (result.data) {
      setTestResult(result.data)
      if (result.data.sent) {
        message.success(result.data.message)
      } else {
        message.error(result.data.message)
      }
      return
    }
    message.error(result.message)
  }

  const unboundContacts = testResult?.contacts?.filter((item) => !item.bound) ?? []

  return (
    <Card size="small" title="通知设置" className="shadow-sm">
      <Form form={form} layout="vertical" initialValues={initialValues}>
        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          <Form.Item name="enabled" label="启用偏差通知" valuePropName="checked">
            <Switch checkedChildren="开" unCheckedChildren="关" />
          </Form.Item>
          <Form.Item
            name="chat_id"
            label="群聊 chat_id"
            extra="留空表示不发送群消息；即时通知走个人消息"
          >
            <Input placeholder="oc_xxxxxxxx" maxLength={128} allowClear />
          </Form.Item>
        </div>

        <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
          {EVENT_FIELDS.map((field, index) => (
            <Form.Item
              key={field.name}
              name={field.name}
              label={field.label}
              extra={field.hint}
              valuePropName="checked"
              className={index === EVENT_FIELDS.length - 1 ? 'sm:col-span-2' : undefined}
            >
              <Switch checkedChildren="开" unCheckedChildren="关" />
            </Form.Item>
          ))}
        </div>

        {testResult && (
          <Alert
            className="mb-4"
            type={testResult.sent ? 'success' : 'error'}
            showIcon
            title={testResult.message}
            description={
              <div className="space-y-1 break-words text-xs">
                <div>
                  平台凭证：
                  <Tag color={testResult.platform_ready ? 'green' : 'red'}>
                    {testResult.platform_ready ? '就绪' : '未配置'}
                  </Tag>
                  当前账号飞书绑定：
                  <Tag color={testResult.self_bound ? 'green' : 'red'}>
                    {testResult.self_bound ? '已绑定' : '未绑定'}
                  </Tag>
                </div>
                {testResult.contacts && testResult.contacts.length > 0 && (
                  <div>
                    环节处理人 {testResult.contacts.length} 位，未绑定 {unboundContacts.length} 位
                    {unboundContacts.length > 0 && (
                      <span className="ml-1">
                        （{unboundContacts
                          .slice(0, 5)
                          .map((item) => `${item.name}·${item.role}·${item.department}`)
                          .join('，')}
                        {unboundContacts.length > 5 ? ' 等' : ''}）
                      </span>
                    )}
                  </div>
                )}
              </div>
            }
          />
        )}

        <div className="flex justify-end gap-2">
          <Button loading={testing} onClick={handleTest}>
            发送测试通知
          </Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            保存通知设置
          </Button>
        </div>
      </Form>
    </Card>
  )
}