'use client'

import { Button, Result, Space } from 'antd'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { PERMISSION_DENIED_HINT, PERMISSION_DENIED_TITLE } from '@/lib/permissions/codes'

/**
 * 统一的边界页容器（未登录 / 无权限 / 找不到 / 服务错误 / 维护中）。
 *
 * 设计要点（避免「一个场景一个页面」导致外观与行为各说各话）：
 * - **一种外观**：全部走 antd Result，标题 / 说明 / 按钮位置一致；
 * - **一定给出下一步**：401 → 去登录；404 → 返回首页（有权限时多一个「去菜单管理」）；
 *   500 → 重试 / 返回首页；403 → 返回首页；
 * - **文案分层**：一句人话 + 可选 `detail`（权限码 / 错误编号 / 出错路径）给需要的人看；
 * - **不包裹容器**：要不要整屏居中由调用方决定（页面用 `min-h-[70vh]` 包一层，嵌入用裸用）。
 *
 * ⚠️ 这里**刻意不调用任何数据 hook**（如 `usePermission`，内部是 React Query）：
 * 边界页可能渲染在根 layout / 错误边界之下，那些位置没有业务 Provider。
 * 需要按权限决定按钮时，由**调用方的 RSC** 用 `hasPermission()` 判断后传 prop 进来
 * （见 `app/not-found.tsx`）。
 */
export type BoundaryKind = 'unauthorized' | 'forbidden' | 'notFound' | 'error' | 'maintenance'

export interface BoundaryResultProps {
  kind?: BoundaryKind
  /** 覆盖默认标题 */
  title?: string
  /** 覆盖默认说明 */
  subTitle?: string
  /** 细节补充：权限码 / 错误编号 / 出错路径等 */
  detail?: string
  /** 提供则显示「重试」按钮（错误场景） */
  onRetry?: () => void
  /** 是否显示「去菜单管理」（调用方在服务端判好权限再传） */
  showMenuAdmin?: boolean
  /** 额外按钮 */
  extra?: React.ReactNode
}

const STATUS: Record<BoundaryKind, '403' | '404' | '500' | 'warning'> = {
  unauthorized: '403',
  forbidden: '403',
  notFound: '404',
  error: '500',
  maintenance: 'warning',
}

const DEFAULTS: Record<BoundaryKind, { title: string; subTitle: string }> = {
  unauthorized: {
    title: '登录已过期',
    subTitle: '为保护数据安全，请重新登录后继续。',
  },
  forbidden: {
    title: PERMISSION_DENIED_TITLE,
    subTitle: PERMISSION_DENIED_HINT,
  },
  notFound: {
    title: '页面不存在',
    subTitle: '若你是从菜单点进来的，可能是该菜单的跳转路径配置有误。',
  },
  error: {
    title: '服务出错了',
    subTitle: '可重试或返回首页；若反复出现，请把错误编号发给管理员。',
  },
  maintenance: {
    title: '系统维护中',
    subTitle: '系统正在升级维护，请稍后再试。',
  },
}

/** 记住当前地址，登录后跳回（由 `proxy.ts` 在落地页消费） */
export function rememberLoginRedirect() {
  if (typeof window === 'undefined') return
  const target = `${window.location.pathname}${window.location.search}`
  if (target.startsWith('/login')) return
  document.cookie = `login_redirect=${encodeURIComponent(target)}; path=/; max-age=600`
}

export function BoundaryResult({
  kind = 'forbidden',
  title,
  subTitle,
  detail,
  onRetry,
  showMenuAdmin = false,
  extra,
}: BoundaryResultProps) {
  const pathname = usePathname()
  const preset = DEFAULTS[kind]
  const actions: React.ReactNode[] = []

  if (kind === 'unauthorized') {
    actions.push(
      <Button
        key="login"
        type="primary"
        onClick={() => {
          rememberLoginRedirect()
          window.location.href = '/login'
        }}
      >
        去登录
      </Button>,
    )
  }

  if (onRetry) {
    actions.push(
      <Button key="retry" type="primary" onClick={onRetry}>
        重试
      </Button>,
    )
  }

  // 找不到页面时，管理员多一个「去菜单管理」的自救入口（死链菜单就靠它排查）
  if (kind === 'notFound' && showMenuAdmin) {
    actions.push(
      <Link key="menus" href="/settings/menus">
        <Button>去菜单管理</Button>
      </Link>,
    )
  }

  if (kind !== 'unauthorized') {
    actions.push(
      <Link key="home" href="/">
        <Button type={onRetry ? 'default' : 'primary'}>返回首页</Button>
      </Link>,
    )
  }

  if (extra) actions.push(extra)

  return (
    <Result
      status={STATUS[kind]}
      title={title ?? preset.title}
      subTitle={
        <>
          <span>{subTitle ?? preset.subTitle}</span>
          {kind === 'notFound' && <div className="mt-1 text-[12px]">未找到：{pathname}</div>}
          {detail && <div className="mt-1 text-[12px] break-all">{detail}</div>}
        </>
      }
      extra={actions.length > 0 ? <Space wrap>{actions}</Space> : undefined}
    />
  )
}
