'use client'

import { useEffect, useState, useSyncExternalStore } from 'react'
import { Button, Card, Spin, Typography } from 'antd'
import type { components } from '@/types/generated/schema'
import { loginWithFeishuCode } from '@/actions/auth'
import { requestFeishuPreauthCode } from '@/lib/feishu/h5sdk'

const errorMessages: Record<string, string> = {
  invalid_state: '登录状态已过期，请重新登录',
  callback_failed: '登录失败，请重试',
  access_denied: '您拒绝了授权',
  auth_failed: '登录失败，请重试',
  account_deleted: '账号已被删除，请联系管理员处理',
  account_disabled: '账号已被禁用，请联系管理员',
}

/** 同一次会话只自动尝试一次：失败后不重试，避免反复弹授权 / 死循环。 */
const AUTO_TRY_FLAG = 'feishu_h5_login_tried'

/**
 * sessionStorage 不是 React 状态源，用 useSyncExternalStore 读取：
 * 服务端快照恒为 false，水合后再切到真实值，避免 SSR/CSR 首帧不一致，
 * 也不需要用 effect + setState 去同步。
 */
function subscribeAutoTryFlag(): () => void {
  return () => {}
}

function getAutoTrySnapshot(): boolean {
  return sessionStorage.getItem(AUTO_TRY_FLAG) === '1'
}

function getAutoTryServerSnapshot(): boolean {
  return false
}

interface FeishuLoginPanelProps {
  /** 服务端按 User-Agent 预判：飞书客户端内首帧直接显示「飞书登录中」，不闪登录页。 */
  inFeishu: boolean
  /** 服务端取到的免登配置（App ID + 开关）；取不到时按未启用处理。 */
  h5Config: components['schemas']['FeishuH5ConfigData']
  error?: string
  detail?: string
  /** ?retry=1：忽略「本会话已自动尝试」标记，强制重试（排查/复测用）。 */
  forceRetry?: boolean
}

/**
 * 登录页面板。
 *
 * - 飞书客户端内：先全屏「飞书登录中」自动免登，成功直接进系统；
 * - 免登失败（或本来就是普通浏览器 / 带 error 参数回跳）：才显示登录按钮。
 */
export default function FeishuLoginPanel({
  inFeishu,
  h5Config,
  error,
  detail,
  forceRetry = false,
}: FeishuLoginPanelProps) {
  const [autoError, setAutoError] = useState<string | null>(null)
  const alreadyTried = useSyncExternalStore(
    subscribeAutoTryFlag,
    getAutoTrySnapshot,
    getAutoTryServerSnapshot,
  )

  // 渲染期推导：是否该走自动免登（不再用 effect 里 setPhase 计算派生状态）
  const shouldAutoLogin =
    inFeishu && !error && h5Config.enabled && Boolean(h5Config.app_id) && (forceRetry || !alreadyTried)

  useEffect(() => {
    if (!shouldAutoLogin) return

    // 标记先落盘：即使中途失败 / 组件卸载，同一次会话也不会反复弹授权
    sessionStorage.setItem(AUTO_TRY_FLAG, '1')

    let cancelled = false

    const run = async () => {
      try {
        const code = await requestFeishuPreauthCode(h5Config.app_id)
        const result = await loginWithFeishuCode(code)
        if (result?.error) throw new Error(result.error)
        if (!result?.redirectTo) throw new Error('登录成功但未返回跳转地址')
        // 整页导航（不用 router 软跳）：确保 Set-Cookie 已落盘，
        // 避免紧随其后的 RSC 请求带不到 cookie、闪一下报错页再进来。
        window.location.replace(result.redirectTo)
        return
      } catch (err) {
        if (cancelled) return
        console.warn('[feishu-h5] auto login failed', err instanceof Error ? err.message : err)
        setAutoError(err instanceof Error ? err.message : '自动登录失败')
      }
    }

    void run()

    return () => {
      cancelled = true
    }
  }, [shouldAutoLogin, h5Config.app_id])

  if (shouldAutoLogin && !autoError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center gap-3">
          <Spin size="large" />
          <Typography.Text type="secondary">飞书登录中…</Typography.Text>
        </div>
      </div>
    )
  }

  const errorText = error ? errorMessages[error] || '登录出错，请重试' : null

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

        {errorText && (
          <div className="mb-4 rounded-md bg-red-50 p-3 text-sm text-red-600">
            {errorText}
            {error === 'auth_failed' && detail && (
              <div className="mt-2 text-xs text-red-500">{detail}</div>
            )}
          </div>
        )}

        {autoError && (
          <div className="mb-4 rounded-md bg-amber-50 p-3 text-sm text-amber-700">
            自动登录未成功：{autoError}，请点击下方按钮登录。
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