'use client'

import { useSyncExternalStore } from "react"

const MOBILE_QUERY = "(max-width: 767px)"

function subscribe(callback: () => void) {
  const mql = window.matchMedia(MOBILE_QUERY)
  mql.addEventListener("change", callback)
  return () => mql.removeEventListener("change", callback)
}

function getSnapshot() {
  return window.matchMedia(MOBILE_QUERY).matches
}

function getServerSnapshot() {
  return false
}

/**
 * 是否为移动端（<768px，与 Tailwind 的 md 断点一致）。
 *
 * 基于 useSyncExternalStore + matchMedia：SSR 阶段返回 false（按桌面渲染），水合后立即校正。
 * 用于「行为差异」（如表格分页 simple、点击打开抽屉等），布局差异请优先用 Tailwind 断点
 * （hidden md:flex 等）由 CSS 决定，避免 window.innerWidth + useEffect 的首屏闪动。
 */
export function useIsMobile() {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
