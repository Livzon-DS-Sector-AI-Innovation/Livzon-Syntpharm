import Link from 'next/link'

/**
 * 全局 404：未匹配任何路由时渲染（未登录用户也可能命中，所以不放侧边导航）。
 *
 * ⚠️ 与 dashboard 版一样用**纯 RSC + Tailwind**：not-found 的边界渲染通道里
 * 客户端组件不输出 SSR 内容（详见 `(dashboard)/not-found.tsx` 的说明）。
 */
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center px-6 text-center">
      <div className="text-[52px] font-semibold leading-none text-[var(--color-steel)]">404</div>
      <h1 className="mt-4 text-[20px] font-semibold text-[var(--color-charcoal)]">页面不存在</h1>
      <p className="mt-2 max-w-[560px] text-[13px] text-[var(--color-steel)]">
        你访问的地址没有对应的页面，可能已被移除或路径输入有误。
      </p>
      <div className="mt-6 flex gap-3">
        <Link
          href="/"
          className="rounded-md bg-[var(--color-primary)] px-4 py-2 text-[13px] text-white hover:opacity-90"
        >
          返回首页
        </Link>
      </div>
    </div>
  )
}
