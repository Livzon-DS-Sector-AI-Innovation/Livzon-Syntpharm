'use client'

import { useEffect } from 'react'
import Link from 'next/link'

/**
 * 路由级错误页（RSC / 渲染抛错时渲染）。
 *
 * 相比旧版修了两处：
 * 1. **不再把 `error.message` 原样丢给用户** —— 内部报错（SQL、文件路径、接口细节）
 *    会泄露实现细节；改为只展示可复制的 `digest` 编号，原始信息仅开发环境展开。
 * 2. **补上「返回首页」** —— 旧版只有「重试」，出错后用户无路可走。
 *
 * ⚠️ 与 `not-found.tsx` 一致，这里手写 Tailwind 而不用 antd：错误页同样走 Next 的
 * **边界渲染通道**，该通道下客户端组件不会输出 SSR 内容（会得到空白页）。
 * 本文件仍是客户端组件（需要 `reset` 回调），但只用原生元素 + `next/link`。
 */
export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('[app/error]', error)
  }, [error])

  const isDev = process.env.NODE_ENV !== 'production'

  return (
    <div className="flex min-h-[70vh] flex-col items-center justify-center px-6 text-center">
      <div className="text-[52px] font-semibold leading-none text-[var(--color-steel)]">500</div>
      <h2 className="mt-4 text-[20px] font-semibold text-[var(--color-charcoal)]">服务出错了</h2>
      <p className="mt-2 max-w-[560px] text-[13px] text-[var(--color-steel)]">
        可重试或返回首页；若反复出现，请把错误编号发给管理员。
      </p>
      {error.digest && (
        <code className="mt-2 text-[12px] text-[var(--color-steel)]">错误编号：{error.digest}</code>
      )}
      <div className="mt-6 flex gap-3">
        <button
          onClick={reset}
          className="rounded-md bg-[var(--color-primary)] px-4 py-2 text-[13px] text-white hover:opacity-90"
        >
          重试
        </button>
        <Link
          href="/"
          className="rounded-md border border-[var(--color-mist)] px-4 py-2 text-[13px] text-[var(--color-charcoal)] hover:bg-[var(--color-surface)]"
        >
          返回首页
        </Link>
      </div>
      {isDev && error.message && (
        <pre className="mt-4 max-w-[720px] overflow-auto rounded bg-[var(--color-surface)] p-2 text-left text-[12px] text-[var(--color-steel)]">
          {error.message}
        </pre>
      )}
    </div>
  )
}
