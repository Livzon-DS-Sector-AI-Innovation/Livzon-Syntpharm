'use client'

import { useState, useCallback, useEffect } from 'react'
import {
  Card,
  Button,
  Space,
  Tag,
  Form,
  Input,
  Select,
  Switch,
  message,
  Divider,
  Typography,
} from 'antd'
import {
  SaveOutlined,
  BellOutlined,
  RobotOutlined,
  UserOutlined,
  GroupOutlined,
} from '@ant-design/icons'
import {
  getReminderConfigs,
  createReminderConfig,
  updateReminderConfig,
  type ReminderConfig,
} from '@/actions/instrument'
import '../instrument-style.css'

const { Text } = Typography

const REMINDER_TIMINGS: Array<{
  name: 'remind_30_days' | 'remind_14_days' | 'remind_7_days' | 'remind_overdue'
  label: string
  desc: string
  accent: string
}> = [
  { name: 'remind_30_days', label: '提前30天', desc: '一个月预警', accent: 'var(--ins-primary)' },
  { name: 'remind_14_days', label: '提前14天', desc: '两周预警', accent: 'var(--ins-warning)' },
  { name: 'remind_7_days', label: '提前7天', desc: '一周预警', accent: 'var(--ins-danger)' },
  { name: 'remind_overdue', label: '超期提醒', desc: '已逾期告警', accent: 'var(--ins-danger)' },
]

export default function ReminderSettingsPage() {
  const [loading, setLoading] = useState(false)
  const [submitLoading, setSubmitLoading] = useState(false)
  const [configs, setConfigs] = useState<ReminderConfig[]>([])
  const [form] = Form.useForm()
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  const loadConfigs = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getReminderConfigs()
      const items = response.items || []
      setConfigs(items)
      if (items.length > 0) {
        const first = items[0]
        form.setFieldsValue({
          name: first.name,
          feishu_app_id: first.feishu_app_id,
          feishu_app_secret: undefined,
          chat_id: first.chat_id,
          receive_id_type: first.receive_id_type || 'open_id',
          remind_30_days: first.remind_30_days,
          remind_14_days: first.remind_14_days,
          remind_7_days: first.remind_7_days,
          remind_overdue: first.remind_overdue,
          is_active: first.is_active,
        })
      }
    } catch (error) {
      message.error('加载配置失败')
    } finally {
      setLoading(false)
    }
  }, [form])

  useEffect(() => {
    loadConfigs()
  }, [loadConfigs])

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSubmitLoading(true)

      const saveData = {
        ...values,
        name: values.name || '仪器校准提醒',
      }
      if (!saveData.feishu_app_secret) {
        delete saveData.feishu_app_secret
      }

      if (configs.length > 0) {
        await updateReminderConfig(configs[0].id, saveData as Parameters<typeof updateReminderConfig>[1])
        message.success('配置已更新')
      } else {
        await createReminderConfig(saveData as Parameters<typeof createReminderConfig>[0])
        message.success('配置已保存')
      }
      loadConfigs()
    } catch (error) {
      message.error('保存失败')
    } finally {
      setSubmitLoading(false)
    }
  }

  return (
    <div className="instrument-page">
      <div className="instrument-toolbar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: isMobile ? 36 : 44,
              height: isMobile ? 36 : 44,
              borderRadius: 12,
              background: 'var(--ins-primary-bg)',
              color: 'var(--ins-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: isMobile ? 18 : 22,
              flexShrink: 0,
            }}
          >
            <BellOutlined />
          </div>
          <div>
            <h1
              style={{
                fontSize: isMobile ? '18px' : '24px',
                fontWeight: 700,
                margin: 0,
                color: 'var(--ins-text)',
                letterSpacing: '-0.02em',
              }}
            >
              提醒设置
            </h1>
            <p
              style={{
                fontSize: isMobile ? '12px' : '14px',
                color: 'var(--ins-text-secondary)',
                margin: '4px 0 0 0',
              }}
            >
              配置飞书机器人提醒，及时通知校准到期
            </p>
          </div>
        </div>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={submitLoading}
          size={isMobile ? 'small' : 'middle'}
          style={{
            borderRadius: 10,
            boxShadow: '0 4px 12px rgba(79, 70, 229, 0.25)',
            fontWeight: 600,
          }}
        >
          保存配置
        </Button>
      </div>

      <Card
        className="ins-card"
        variant="borderless"
        loading={loading}
        style={{ overflow: 'hidden' }}
        styles={{ body: { padding: isMobile ? 16 : 24 } }}
      >
        <Form form={form} layout="vertical">
          {/* 飞书机器人配置 */}
          <div className="settings-section">
            <div className="settings-section-title">
              <RobotOutlined />
              <span>飞书机器人配置</span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                gap: 12,
              }}
            >
              <Form.Item
                name="feishu_app_id"
                label="App ID"
                rules={[{ required: true, message: '请输入飞书应用的 App ID' }]}
              >
                <Input placeholder="cli_xxxxxxxxxxxxxxxxxx" allowClear />
              </Form.Item>

              <Form.Item
                name="feishu_app_secret"
                label="App Secret"
                tooltip="不修改请留空，首次配置或更换密钥时填写"
              >
                <Input.Password placeholder="不修改请留空" />
              </Form.Item>
            </div>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          {/* 接收者配置 */}
          <div className="settings-section">
            <div className="settings-section-title">
              <UserOutlined />
              <span>接收者配置</span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                gap: 12,
              }}
            >
              <Form.Item
                name="receive_id_type"
                label="接收者类型"
                rules={[{ required: true }]}
              >
                <Select placeholder="请选择">
                  <Select.Option value="open_id">
                    <Space>
                      <UserOutlined />
                      用户
                    </Space>
                  </Select.Option>
                  <Select.Option value="chat_id">
                    <Space>
                      <GroupOutlined />
                      群组
                    </Space>
                  </Select.Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="chat_id"
                label="接收者ID"
                rules={[{ required: true, message: '请输入接收者ID' }]}
              >
                <Input
                  placeholder={
                    form.getFieldValue('receive_id_type') === 'open_id'
                      ? '输入用户 open_id'
                      : '输入飞书群 ID'
                  }
                  allowClear
                />
              </Form.Item>
            </div>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 12px',
                background: 'var(--ins-primary-bg)',
                borderRadius: 8,
                marginTop: 4,
              }}
            >
              <RobotOutlined style={{ color: 'var(--ins-primary)', fontSize: 14 }} />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {form.getFieldValue('receive_id_type') === 'open_id'
                  ? '提示：通过手机号或邮箱查询用户 open_id 后填入上方'
                  : '提示：在飞书群设置中获取群 ID'}
              </Text>
            </div>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          {/* 提醒时机 */}
          <div className="settings-section">
            <div className="settings-section-title">
              <BellOutlined />
              <span>提醒时机</span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? 'repeat(2, 1fr)' : 'repeat(4, 1fr)',
                gap: 12,
              }}
            >
              {REMINDER_TIMINGS.map((item) => (
                <div
                  key={item.name}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '12px 14px',
                    background: 'var(--ins-bg)',
                    border: '1px solid var(--ins-border)',
                    borderLeft: `3px solid ${item.accent}`,
                    borderRadius: 12,
                    transition: 'all 0.2s ease',
                  }}
                >
                  <Form.Item name={item.name} valuePropName="checked" noStyle>
                    <Switch size={isMobile ? 'small' : 'default'} />
                  </Form.Item>
                  <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
                    <Text
                      style={{
                        fontSize: 13,
                        fontWeight: 600,
                        color: 'var(--ins-text)',
                        lineHeight: 1.2,
                      }}
                    >
                      {item.label}
                    </Text>
                    <Text style={{ fontSize: 11, color: 'var(--ins-text-light)' }}>
                      {item.desc}
                    </Text>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <Divider style={{ margin: '8px 0' }} />

          {/* 基本设置 */}
          <div className="settings-section" style={{ marginBottom: 0 }}>
            <div className="settings-section-title">
              <span>基本设置</span>
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr',
                gap: 12,
              }}
            >
              <Form.Item name="name" label="配置名称">
                <Input placeholder="如：仪器校准提醒" allowClear />
              </Form.Item>

              <Form.Item name="is_active" label="状态" valuePropName="checked">
                <Switch checkedChildren="启用" unCheckedChildren="停用" />
              </Form.Item>
            </div>
          </div>

          {configs.length > 0 && (
            <>
              <Divider style={{ margin: '16px 0 8px 0' }} />
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  flexWrap: 'wrap',
                  gap: 12,
                  padding: '12px 16px',
                  background: configs[0].is_active
                    ? 'var(--ins-success-bg)'
                    : 'var(--ins-bg)',
                  border: `1px solid ${
                    configs[0].is_active ? 'var(--ins-success)' : 'var(--ins-border)'
                  }`,
                  borderLeft: `3px solid ${
                    configs[0].is_active ? 'var(--ins-success)' : 'var(--ins-text-light)'
                  }`,
                  borderRadius: 10,
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag color={configs[0].is_active ? 'success' : 'default'} style={{ margin: 0 }}>
                    {configs[0].is_active ? '已启用' : '已停用'}
                  </Tag>
                  <Text style={{ fontSize: 13, color: 'var(--ins-text-secondary)' }}>
                    当前配置状态
                  </Text>
                </div>
                <Text style={{ fontSize: 12, color: 'var(--ins-text-light)' }}>
                  最后更新：{new Date(configs[0].updated_at).toLocaleString('zh-CN')}
                </Text>
              </div>
            </>
          )}
        </Form>
      </Card>
    </div>
  )
}
