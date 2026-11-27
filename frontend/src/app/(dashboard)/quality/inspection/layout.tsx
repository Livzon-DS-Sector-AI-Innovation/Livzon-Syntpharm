import type { ReactNode } from 'react'

import '@/components/quality/qc-report/qc-theme.css'

/**
 * 质量检验两个页面的局部主题。
 *
 * 只在 `/quality/inspection` 子树内挂载：注入设计 token、引入数字字体 Manrope。
 * 不碰全局 layout，避免影响其他页面。
 * Manrope 用 display=swap，字体没到之前先显示回退字体，不阻塞首屏。
 */
export default function QcInspectionLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      <link
        rel="stylesheet"
        href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&display=swap"
      />
      <div className="qc-theme">{children}</div>
    </>
  )
}
