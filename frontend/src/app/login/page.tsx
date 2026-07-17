"use client"

import { Button, Card, Typography } from "antd"
import { useSearchParams } from "next/navigation"
import { Suspense } from "react"

const errorMessages: Record<string, string> = {
  invalid_state: "登录状态已过期，请重新登录",
  callback_failed: "登录失败，请重试",
  access_denied: "您拒绝了授权",
  auth_failed: "登录失败，请重试",
}

function LoginForm() {
  const searchParams = useSearchParams()
  const error = searchParams.get("error")

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Card className="w-full max-w-sm shadow-lg" variant="borderless">
        <div className="mb-8 text-center">
          <Typography.Title level={3} style={{ marginBottom: 4 }}>
            工厂管理平台
          </Typography.Title>
          <Typography.Text type="secondary">
            原料药制药厂综合业务管理系统
          </Typography.Text>
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600">
            {errorMessages[error] || "登录出错，请重试"}
            {error === 'auth_failed' && searchParams.get('detail') && (
              <div className="mt-2 text-xs text-red-500">
                {searchParams.get('detail')}
              </div>
            )}
          </div>
        )}

        <Button
          type="primary"
          size="large"
          block
          href="/api/v1/identity/auth/login"
          style={{ height: 44 }}
        >
          飞书登录
        </Button>
      </Card>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
