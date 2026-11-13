'use client'

import { useEffect, useState, type RefObject } from 'react'

/**
 * 详情页滚动工具。
 *
 * 关键背景：应用外壳（AppShell）把内容放在 `<main class="flex-1 overflow-y-auto">` 里，
 * 真正滚动的是这个容器，不是 window。因此：
 * - `window.scrollTo` / `html { scroll-behavior: smooth }` 对本页无效；
 * - antd `FloatButton.BackTop` 必须显式传 target。
 */

const SCROLLABLE_PATTERN = /(auto|scroll|overlay)/

/** 向上找最近的可滚动祖先，找不到时退回 documentElement（等价于整页滚动） */
export function getScrollElement(element: HTMLElement | null): HTMLElement {
  let node = element?.parentElement ?? null
  while (node && node !== document.body) {
    const style = window.getComputedStyle(node)
    if (SCROLLABLE_PATTERN.test(style.overflowY) && node.scrollHeight > node.clientHeight) {
      return node
    }
    node = node.parentElement
  }
  return document.documentElement
}

export function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * 平滑滚动到指定板块。滚动距离由 `scroll-mt-*`（scroll-margin-top）控制，
 * 元素不存在（板块被条件隐藏）时静默返回 false。
 */
export function scrollToSection(id: string): boolean {
  if (typeof document === 'undefined') return false
  const target = document.getElementById(id)
  if (!target) return false
  target.scrollIntoView({
    behavior: prefersReducedMotion() ? 'auto' : 'smooth',
    block: 'start',
  })
  return true
}

/**
 * 滚动高亮：监听滚动容器，取「顶部已越过判定线」的最后一个板块作为当前板块。
 * 用 rAF 合并滚动事件，只在 id 变化时 setState，避免滚动时整页重渲染。
 */
export function useActiveSection(
  rootRef: RefObject<HTMLElement | null>,
  ids: readonly string[],
): string | null {
  const idsKey = ids.join('|')
  const [active, setActive] = useState<string | null>(ids[0] ?? null)

  useEffect(() => {
    const root = rootRef.current
    const keys = idsKey ? idsKey.split('|') : []
    if (!root || keys.length === 0) return

    const scroller = getScrollElement(root)
    let frame = 0

    const measure = () => {
      frame = 0
      const containerTop = scroller === document.documentElement ? 0 : scroller.getBoundingClientRect().top
      // 判定线略低于容器顶部：板块标题刚进入视野就切换高亮
      const threshold = containerTop + 96
      let next: string | null = keys[0] ?? null
      for (const key of keys) {
        const el = document.getElementById(key)
        if (!el) continue
        if (el.getBoundingClientRect().top <= threshold) next = key
      }
      // 触底时最后一个板块可能永远越不过判定线，直接高亮它
      if (scroller.scrollTop + scroller.clientHeight >= scroller.scrollHeight - 8) {
        next = keys[keys.length - 1] ?? next
      }
      setActive((prev) => (prev === next ? prev : next))
    }

    const onScroll = () => {
      if (frame) return
      frame = window.requestAnimationFrame(measure)
    }

    measure()
    scroller.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      if (frame) window.cancelAnimationFrame(frame)
      scroller.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [rootRef, idsKey])

  return active
}