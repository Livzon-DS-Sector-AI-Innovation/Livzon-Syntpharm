'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, App, Button, Card, Form, Input, Typography } from 'antd'
import { changeMyPassword } from '@/actions/users'

const { Text, Title } = Typography

interface ChangePasswordClientProps {
  userName: string
  /** 被标记「首登需改密」：改完前进不了系统，文案要说明原因 */
  forced?: boolean
}

/**
 * 修改当前登录用户的密码。
 *
 * - 被管理员重置过密码（`must_change_password=true`）的用户会被 `(dashboard)/layout.tsx`
 *   重定向到 `/change-password`，改完才能继续用其它页面；
 * - 已改密的用户可从右上角用户菜单主动进入，修改自己的密码。
 */
export function ChangePasswordClient({ userName, forced = false }: ChangePasswordClientProps) {
  const { message } = App.useApp()
  const router = useRouter()
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async () => {
    const values = await form.validateFields().catch(() => null)
    if (!values) return // antd 已在字段上提示

    setSubmitting(true)
    try {
      const result = await changeMyPassword({
        old_password: values.old_password,
        new_password: values.new_password,
      })
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success('密码已修改')
      // 强制改密场景下 land 到首页；主动改密场景下也回首页（导航会重新下发）
      router.replace('/')
      router.refresh()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <Card className="w-full max-w-md shadow-lg" variant="borderless">
        <div className="mb-4 text-center">
          <Title level={4} style={{ marginBottom: 4 }}>
            {forced ? '请先修改密码' : '修改密码'}
          </Title>
          <Text type="secondary" className="text-[13px]">
            {userName}
          </Text>
        </div>

        {forced && (
          <Alert
            type="warning"
            showIcon
            className="mb-4"
            message="当前密码由管理员重置（或为初始密码）"
            description="为保证账号安全，请先设置一个只有你知道的新密码，之后才能继续使用系统。"
          />
        )}

        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="old_password"
            label="当前密码"
            rules={[{ required: true, message: '请输入当前密码' }]}
          >
            <Input.Password autoComplete="current-password" placeholder="请输入当前密码" />
          </Form.Item>

          <Form.Item
            name="new_password"
            label="新密码"
            rules={[
              { required: true, message: '请输入新密码' },
              { min: 6, message: '新密码至少 6 位' },
            ]}
          >
            <Input.Password autoComplete="new-password" placeholder="至少 6 位" />
          </Form.Item>

          <Form.Item
            name="confirm_password"
            label="确认新密码"
            dependencies={['new_password']}
            rules={[
              { required: true, message: '请再次输入新密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('new_password') === value) {
                    return Promise.resolve()
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'))
                },
              }),
            ]}
          >
            <Input.Password autoComplete="new-password" placeholder="再次输入新密码" />
          </Form.Item>

          <Button type="primary" htmlType="submit" block loading={submitting}>
            确认修改
          </Button>
        </Form>

        {forced && (
          <p className="m-0 mt-3 text-center text-[12px] text-[var(--color-steel)]">
            忘记当前密码？请联系管理员在你的账号上重新生成一次随机密码。
          </p>
        )}
      </Card>
    </div>
  )
}
