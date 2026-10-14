import Link from 'next/link'

/**
 * 登录后的 404（**带侧边导航**）。
 *
 * 配合 `[...notFound]/page.tsx` 兜底路由，让 `/settings/test` 这类不存在的路径在这里渲染 ——
 * 此时 dashboard layout 已渲染（左侧菜单可用），用户不会「卡死在一个白页上」。
 *
 * ⚠️ 为什么这里手写 Tailwind，而不用 antd 的 `Result`（页面内用的是 `BoundaryResult`）：
 * not-found 属于 Next 的**边界渲染通道**，实测在该通道里客户端组件不会输出 SSR 内容
 * （用纯 div 的 RSC 能渲染、换成 antd 组件后 HTML 里什么都没有）。边界页的首要目标是
 * 「一定有内容」，所以这里只用 RSC + Tailwind + `next/link`。
 */
export default function DashboardNotFound() {
  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      <div className="text-[52px] font-semibold leading-none text-[var(--color-steel)]">404</div>
      <h2 className="mt-4 text-[20px] font-semibold text-[var(--color-charcoal)]">页面不存在</h2>
      <p className="mt-2 max-w-[560px] text-[13px] text-[var(--color-steel)]">
        若你是从菜单点进来的，可能是该菜单的「跳转路径」配置有误（对应的页面不存在）。
      </p>
      <div className="mt-6 flex gap-3">
        <Link
          href="/"
          className="rounded-md bg-[var(--color-primary)] px-4 py-2 text-[13px] text-white hover:opacity-90"
        >
          返回首页
        </Link>
        <Link
          href="/settings/menus"
          className="rounded-md border border-[var(--color-mist)] px-4 py-2 text-[13px] text-[var(--color-charcoal)] hover:bg-[var(--color-surface)]"
        >
          去菜单管理
        </Link>
      </div>
    </div>
  )
}
