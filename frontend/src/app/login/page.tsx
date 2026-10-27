'use client'

import { Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { Button, Card, Typography } from "antd"

const errorMessages: Record<string, string> = {
  invalid_state: "登录状态已过期，请重新登录",
  callback_failed: "登录失败，请重试",
  access_denied: "您拒绝了授权",
  auth_failed: "登录失败，请重试",
}

/**
 * 默认登录页 = 飞书登录。
 *
 * 账号密码登录已拆到独立页面 `/login/password`，本页不再暴露入口，需直接访问该 URL。
 */
function FeishuLoginCard() {
  const searchParams = useSearchParams()
  const error = searchParams.get("error")

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Card className="w-full max-w-sm shadow-lg" variant="borderless">
        <div className="mb-6 text-center">
          <Typography.Title level={1} style={{ marginBottom: 4, fontSize: 24 }}>
            工厂管理平台
          </Typography.Title>
          <Typography.Text type="secondary">
            原料药制药厂综合业务管理系统
          </Typography.Text>
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600">
            {errorMessages[error] || "登录出错，请重试"}
            {error === "auth_failed" && searchParams.get("detail") && (
              <div className="mt-2 text-xs text-red-500">
                {searchParams.get("detail")}
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

        <p className="m-0 mt-3 text-center text-[12px] text-[var(--color-steel)]">
          使用企业飞书账号扫码 / 授权登录
        </p>
      </Card>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <FeishuLoginCard />
    </Suspense>
  )
}
