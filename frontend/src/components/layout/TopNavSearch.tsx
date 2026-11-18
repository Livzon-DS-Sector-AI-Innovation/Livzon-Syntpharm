'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { CloseOutlined } from '@ant-design/icons'
import { Empty } from 'antd'
import { ModuleIcon, SearchIcon } from '@/components/Icons'
import type { ResolvedModule } from '@/lib/menu/resolve'
import { buildSearchIndex, searchEntries, type SearchEntry } from '@/lib/menu/search'
import { MenuLockLabel } from './MenuLockLabel'

interface TopNavSearchProps {
  /** AppShell 统一解析后的权限菜单树：搜得到即进得去 */
  menus: ResolvedModule[]
}

/**
 * 把命中的关键词标成主题色，其余原样输出。
 * 只做小写匹配，不重新归一化原文，避免 NFKC 改变长度后切错位置。
 */
function highlightLabel(label: string, query: string): ReactNode {
  const tokens = query
    .normalize('NFKC')
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
  if (tokens.length === 0) return label

  const lower = label.toLowerCase()
  const ranges: Array<[number, number]> = []
  for (const token of tokens) {
    let from = 0
    while (from < lower.length) {
      const index = lower.indexOf(token, from)
      if (index < 0) break
      ranges.push([index, index + token.length])
      from = index + token.length
    }
  }
  if (ranges.length === 0) return label

  ranges.sort((a, b) => a[0] - b[0])
  const merged: Array<[number, number]> = []
  for (const range of ranges) {
    const last = merged[merged.length - 1]
    if (last && range[0] <= last[1]) {
      last[1] = Math.max(last[1], range[1])
    } else {
      merged.push([range[0], range[1]])
    }
  }

  const nodes: ReactNode[] = []
  let cursor = 0
  merged.forEach(([start, end]) => {
    if (start > cursor) nodes.push(label.slice(cursor, start))
    nodes.push(
      <mark key={`${start}-${end}`} className="bg-transparent text-[var(--color-primary)]">
        {label.slice(start, end)}
      </mark>,
    )
    cursor = end
  })
  if (cursor < label.length) nodes.push(label.slice(cursor))
  return nodes
}

/**
 * 顶栏内联搜索：点图标展开输入框，输入即出下拉结果。
 *
 * 桌面端内联在顶栏右侧；移动端顶栏空间不足，展开为覆盖顶栏的输入行。
 * 纯前端匹配，不发请求。
 */
export function TopNavSearch({ menus }: TopNavSearchProps) {
  const router = useRouter()
  const pathname = usePathname()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)

  const containerRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([])

  const index = useMemo(() => buildSearchIndex(menus), [menus])
  const results = useMemo(() => searchEntries(index, query), [index, query])
  const trimmedQuery = query.trim()
  const active = results.length > 0 ? Math.min(activeIndex, results.length - 1) : -1

  const closeSearch = useCallback(() => {
    setOpen(false)
    setQuery('')
    setActiveIndex(0)
  }, [])

  const openSearch = useCallback(() => {
    setOpen(true)
    requestAnimationFrame(() => inputRef.current?.focus())
  }, [])

  // 路由变化（含点击结果跳转、侧栏跳转）后自动收起。
  // 渲染期比对而非 effect 内 setState：避免级联渲染（react-hooks/set-state-in-effect）。
  const [prevPathname, setPrevPathname] = useState(pathname)
  if (prevPathname !== pathname) {
    setPrevPathname(pathname)
    if (open) {
      setOpen(false)
      setQuery('')
      setActiveIndex(0)
    }
  }

  // 外部点击关闭：用 mousedown 而非 blur，避免点结果时先触发 blur 导致点不中
  useEffect(() => {
    if (!open) return
    const handlePointerDown = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) closeSearch()
    }
    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [open, closeSearch])

  // 高亮项滚动进可视区（结果超出 320px 时）
  useEffect(() => {
    if (active < 0) return
    itemRefs.current[active]?.scrollIntoView({ block: 'nearest' })
  }, [active])

  const navigate = useCallback(
    (entry: SearchEntry) => {
      closeSearch()
      router.push(entry.path)
    },
    [closeSearch, router],
  )

  /**
   * 键盘处理挂在展开容器上而非 input 上：焦点移到结果按钮时 Esc 仍生效。
   * 注意不能用 document 级监听兜底：Next 的 React 根容器就是 document，
   * 同节点上的监听器无法被 `stopPropagation` 拦截，会导致「Esc 只清空」变成直接关闭。
   */
  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      if (query) {
        setQuery('')
        setActiveIndex(0)
      } else {
        closeSearch()
      }
      return
    }
    // 以下按键只对输入框生效；结果按钮上的 Enter 交给原生 click
    if (event.target !== inputRef.current) return
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      if (results.length > 0) setActiveIndex((current) => (current + 1) % results.length)
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      if (results.length > 0) setActiveIndex((current) => (current - 1 + results.length) % results.length)
      return
    }
    if (event.key === 'Enter' && active >= 0) {
      event.preventDefault()
      navigate(results[active])
    }
  }

  return (
    <div
      ref={containerRef}
      className={open ? 'fixed inset-x-3 top-2 z-50 md:static md:inset-auto' : 'relative'}
    >
      {!open ? (
        <button
          type="button"
          onClick={openSearch}
          aria-label="搜索页面"
          title="搜索页面"
          className="flex h-8 w-8 items-center justify-center rounded-[var(--rounded-sm)] text-[var(--color-steel)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-charcoal)]"
        >
          <SearchIcon className="h-[18px] w-[18px]" />
        </button>
      ) : (
        <div className="relative" onKeyDown={handleKeyDown}>
          <div className="flex h-10 items-center gap-2 rounded-[var(--rounded-md)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] px-2.5 shadow-sm md:h-8 md:w-[220px] md:border-transparent md:bg-[var(--color-surface)] md:px-2 md:shadow-none lg:w-[260px]">
            <SearchIcon className="h-[16px] w-[16px] shrink-0 text-[var(--color-steel)]" />
            <input
              ref={inputRef}
              value={query}
              onChange={(event) => {
                setQuery(event.target.value)
                setActiveIndex(0)
              }}
              placeholder="搜索页面 / 功能"
              role="combobox"
              aria-label="搜索页面"
              aria-expanded
              aria-controls="topnav-search-results"
              aria-autocomplete="list"
              aria-activedescendant={active >= 0 ? `topnav-search-option-${active}` : undefined}
              className="min-w-0 flex-1 bg-transparent text-[13px] text-[var(--color-ink)] outline-none placeholder:text-[var(--color-stone)]"
            />
            <button
              type="button"
              onClick={closeSearch}
              aria-label="关闭搜索"
              className="shrink-0 text-[12px] text-[var(--color-steel)] transition-colors hover:text-[var(--color-charcoal)]"
            >
              <CloseOutlined />
            </button>
          </div>

          <div className="absolute left-0 right-0 top-full z-50 mt-1.5 overflow-hidden rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] shadow-lg md:left-auto md:right-0 md:w-[420px]">
            {trimmedQuery === '' ? (
              <p className="px-3 py-4 text-[12px] leading-5 text-[var(--color-stone)]">
                输入模块名或页面名，如「偏差」「菜单管理」「deviation」
                <br />
                ↑↓ 选择，回车打开，Esc 关闭
              </p>
            ) : results.length === 0 ? (
              <div className="px-3 py-3">
                <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="未找到匹配页面" />
              </div>
            ) : (
              <div
                id="topnav-search-results"
                role="listbox"
                aria-label="搜索结果"
                className="max-h-[320px] overflow-y-auto p-1"
              >
                {results.map((entry, entryIndex) => (
                  <button
                    key={entry.key}
                    id={`topnav-search-option-${entryIndex}`}
                    ref={(node) => {
                      itemRefs.current[entryIndex] = node
                    }}
                    type="button"
                    role="option"
                    aria-selected={entryIndex === active}
                    onMouseEnter={() => setActiveIndex(entryIndex)}
                    onClick={() => navigate(entry)}
                    className={[
                      'flex w-full items-center gap-2.5 rounded-[var(--rounded-sm)] px-2.5 py-2 text-left transition-colors',
                      entryIndex === active ? 'bg-[var(--color-surface)]' : '',
                    ].join(' ')}
                  >
                    <ModuleIcon name={entry.icon} className="h-4 w-4 shrink-0 text-[var(--color-steel)]" />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-[13px] text-[var(--color-ink)]">
                        {entry.noAccess ? (
                          <MenuLockLabel label={entry.label} />
                        ) : (
                          highlightLabel(entry.label, trimmedQuery)
                        )}
                      </span>
                      <span className="mt-0.5 block truncate text-[11px] text-[var(--color-steel)]">
                        {entry.breadcrumb}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}