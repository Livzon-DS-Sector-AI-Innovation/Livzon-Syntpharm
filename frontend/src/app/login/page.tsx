import { headers } from 'next/headers'
import { FeishuLoginPanel } from '@/components/auth'

/** 按 UA 预判是否飞书容器，属于运行时数据，禁止静态预渲染。 */
export const dynamic = 'force-dynamic'

interface LoginPageProps {
  searchParams: Promise<{ error?: string; detail?: string; retry?: string }>
}

/**
 * 登录页 = 飞书登录。
 *
 * 在服务端读 User-Agent 决定首帧展示什么：飞书客户端内直接渲染「飞书登录中」
 * （避免先闪一下登录按钮页），普通浏览器直接渲染登录按钮页。
 * 账号密码登录已拆到独立页面 `/login/password`，本页不暴露入口。
 */
export default async function LoginPage({ searchParams }: LoginPageProps) {
  const [params, headerList] = await Promise.all([searchParams, headers()])
  const userAgent = headerList.get('user-agent') ?? ''
  const inFeishu = /Lark|Feishu/i.test(userAgent)

  return (
    <FeishuLoginPanel
      inFeishu={inFeishu}
      error={params.error}
      detail={params.detail}
      forceRetry={params.retry === '1'}
    />
  )
}