'use client'

import { useEffect, useState } from 'react'

/**
 * 订阅一个 CSS 媒体查询的当前状态。
 *
 * 统一替代各页面里手写的 `window.matchMedia(...) + useEffect + addEventListener`：
 * 首帧固定 `false`（服务端没有 window），挂载后立即同步真实值，监听器随组件卸载移除。
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false)

  useEffect(() => {
    const mql = window.matchMedia(query)
    const update = () => setMatches(mql.matches)
    update()
    mql.addEventListener('change', update)
    return () => mql.removeEventListener('change', update)
  }, [query])

  return matches
}

/** 移动端判定：与 DESIGN.md 的断点一致，`< 768px` 视为移动端。 */
export function useIsMobile(): boolean {
  return useMediaQuery('(max-width: 767px)')
}