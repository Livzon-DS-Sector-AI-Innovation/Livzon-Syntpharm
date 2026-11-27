import { headers } from 'next/headers'
import { FeishuLoginPanel } from '@/components/auth'
import { getFeishuH5ConfigApi } from '@/lib/api/server/auth'

/** 按 UA 预判是否飞书容器、并取免登配置，属于运行时数据，禁止静态预渲染。 */
export const dynamic = 'force-dynamic'

interface LoginPageProps {
  searchParams: Promise<{ error?: string; detail?: string; retry?: string }>
}

/**
 * 登录页 = 飞书登录。
 *
 * 在服务端读 User-Agent 决定首帧展示什么：飞书客户端内直接渲染「飞书登录中」
 * （避免先闪一下登录按钮页），普通浏览器直接渲染登录按钮页。
 * 免登配置也在服务端取，客户端不再用 useEffect 拉配置。
 * 账号密码登录已拆到独立页面 `/login/password`，本页不暴露入口。
 */
export default async function LoginPage({ searchParams }: LoginPageProps) {
  const [params, headerList, h5Config] = await Promise.all([
    searchParams,
    headers(),
    getFeishuH5ConfigApi(),
  ])
  const userAgent = headerList.get('user-agent') ?? ''
  const inFeishu = /Lark|Feishu/i.test(userAgent)

  return (
    <FeishuLoginPanel
      inFeishu={inFeishu}
      h5Config={h5Config}
      error={params.error}
      detail={params.detail}
      forceRetry={params.retry === '1'}
    />
  )
}