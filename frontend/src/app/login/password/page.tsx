'use client'

import { useActionState } from "react"
import Link from "next/link"
import { Button, Card, Divider, Input, Typography } from "antd"
import { LockOutlined, UserOutlined } from "@ant-design/icons"
import { loginWithPassword } from "@/actions/auth"
import type { LoginActionState } from "@/types/auth"

const INITIAL_STATE: LoginActionState = {}

/**
 * 账号密码登录页（独立页面）。
 *
 * 默认登录页 `/login` 只放飞书登录；本页是它的补充入口，
 * 底部提供「返回飞书登录」链接。
 */
export default function PasswordLoginPage() {
  const [state, formAction, pending] = useActionState(loginWithPassword, INITIAL_STATE)

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Card className="w-full max-w-sm shadow-lg" variant="borderless">
        <div className="mb-6 text-center">
          <h1 className="sr-only">账号密码登录</h1>
          <Typography.Title level={3} style={{ marginBottom: 4 }}>
            账号密码登录
          </Typography.Title>
          <Typography.Text type="secondary">
            原料药制药厂综合业务管理系统
          </Typography.Text>
        </div>

        <form action={formAction}>
          <div className="space-y-4">
            <Input
              name="username"
              size="large"
              placeholder="账号 / 邮箱 / 手机号 / 工号"
              prefix={<UserOutlined className="text-[var(--color-stone)]" />}
              autoComplete="username"
              required
            />
            <Input.Password
              name="password"
              size="large"
              placeholder="密码"
              prefix={<LockOutlined className="text-[var(--color-stone)]" />}
              autoComplete="current-password"
              required
            />
            {state.error && (
              <div className="rounded-md bg-red-50 p-2 text-[13px] text-red-600">
                {state.error}
              </div>
            )}
            <Button
              type="primary"
              size="large"
              block
              htmlType="submit"
              loading={pending}
              style={{ height: 44 }}
            >
              登录
            </Button>
          </div>
        </form>

        <Divider plain className="!my-5">
          <span className="text-[12px] text-[var(--color-stone)]">或</span>
        </Divider>

        <Link
          href="/login"
          className="block text-center text-[13px] text-[var(--color-primary)] hover:underline"
        >
          返回飞书登录
        </Link>
      </Card>
    </div>
  )
}
