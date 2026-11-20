'use client'

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import { Dropdown } from "antd"
import { HomeOutlined } from "@ant-design/icons"
import { ModuleIcon } from "@/components/Icons"
import type { ResolvedModule } from "@/lib/menu/resolve"
import { MenuLockLabel } from "./MenuLockLabel"
import { computeVisibleCount, type OverflowFit } from "./computeVisibleCount"

/** 服务端没有 useLayoutEffect；同构别名既避免 SSR 告警，又保住「绘制前测量、不出闪动」 */
const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect

const TAB_CLASS =
  "flex items-center gap-1.5 px-3 h-full text-[14px] font-medium transition-colors whitespace-nowrap relative"

interface TabItem {
  key: string
  label: string
  path: string
  /** null = 首页（固定 HomeOutlined） */
  icon: string | null
  noAccess: boolean
}

interface TopNavModuleTabsProps {
  menus: ResolvedModule[]
  activeModule: string
}

/**
 * 顶栏模块 Tab 行（仅桌面显示，md 以下交给移动端下拉）。
 *
 * 横向空间不足时不再出现滚动条：放不下的 Tab 只加 `invisible`（visibility 保留布局盒子，
 * 因此测量幂等、不会前后抖动），尾部 Tab 收进右侧「更多」下拉。
 */
export function TopNavModuleTabs({ menus, activeModule }: TopNavModuleTabsProps) {
  const navRef = useRef<HTMLElement>(null)
  const moreRef = useRef<HTMLButtonElement>(null)
  // 初值 = 全部显示：服务端与客户端首帧 HTML 完全一致（无 hydration mismatch），
  // 水合后由 layout effect 按实测宽度收敛。
  const [fit, setFit] = useState<OverflowFit>({
    visibleCount: Number.MAX_SAFE_INTEGER,
    showMore: false,
  })

  const items = useMemo<TabItem[]>(
    () => [
      { key: "home", label: "首页", path: "/home", icon: null, noAccess: false },
      ...menus.map((mod) => ({
        key: mod.key,
        label: mod.label,
        path: mod.path,
        icon: mod.icon,
        noAccess: mod.noAccess,
      })),
    ],
    [menus],
  )

  // 菜单增删 / 改名都会改变 Tab 数量或宽度，拼成签名作为重测依据
  const signature = useMemo(() => items.map((item) => `${item.key}:${item.label}`).join("|"), [items])

  const measure = useCallback(() => {
    const nav = navRef.current
    const more = moreRef.current
    // 首行判空：fonts.ready 的回调可能晚于卸载
    if (!nav || !more) return
    const itemOffsets = Array.from(nav.querySelectorAll<HTMLElement>("[data-tab-item]")).map(
      (el) => el.offsetLeft + el.offsetWidth,
    )
    const next = computeVisibleCount({
      containerWidth: nav.clientWidth,
      itemOffsets,
      moreWidth: more.offsetWidth,
    })
    // 同值返回 prev：ResizeObserver 回调里避免无谓重渲染，也杜绝「测量 ↔ 渲染」循环
    setFit((prev) =>
      prev.visibleCount === next.visibleCount && prev.showMore === next.showMore ? prev : next,
    )
  }, [])

  useIsomorphicLayoutEffect(() => {
    measure()
    const nav = navRef.current
    if (!nav) return undefined
    const observer = new ResizeObserver(measure)
    // 只观察容器：观察「更多」按钮自身会形成「它的宽度变化 → 重算折叠 → 它再变化」的回路
    observer.observe(nav)
    // 图标字体加载完成后 Tab 宽度会变，补测一次；失败不影响主流程
    document.fonts?.ready.then(measure).catch(() => undefined)
    return () => observer.disconnect()
  }, [measure, signature])

  const activeIndex = items.findIndex((item) => item.key === activeModule)
  const activeCollapsed = activeIndex >= fit.visibleCount
  const activeCollapsedTone = activeCollapsed && !items[activeIndex]?.noAccess
  const overflowItems = items.slice(fit.visibleCount)

  return (
    <nav
      ref={navRef}
      className="hidden md:flex items-center gap-0.5 flex-1 h-full ml-8 relative overflow-hidden"
    >
      {items.map((item, index) => {
        const isActive = activeModule === item.key
        const hiddenTab = index >= fit.visibleCount
        // 无权限模块：灰显 + 锁，但仍可点击（模块 layout 守卫渲染无权限页）
        const tone = item.noAccess
          ? "text-[var(--color-steel)] opacity-55 hover:opacity-70"
          : isActive
            ? "text-[var(--color-ink)]"
            : "text-[var(--color-steel)] hover:text-[var(--color-charcoal)]"
        return (
          <Link
            key={item.key}
            href={item.path}
            data-tab-item
            aria-hidden={hiddenTab || undefined}
            tabIndex={hiddenTab ? -1 : undefined}
            className={`${TAB_CLASS} ${tone}${hiddenTab ? " invisible" : ""}`}
          >
            {item.icon ? (
              <ModuleIcon name={item.icon} className="w-4 h-4" />
            ) : (
              <HomeOutlined className="w-4 h-4" />
            )}
            {item.noAccess ? <MenuLockLabel label={item.label} /> : item.label}
            {isActive && !item.noAccess && (
              <span className="absolute bottom-0 left-3 right-3 h-[2px] bg-[var(--color-primary)] rounded-full" />
            )}
          </Link>
        )
      })}

      {/* 「更多」必须常驻 DOM、只用 invisible 隐藏：visibility 保留布局盒子才能一直量到宽度。
          若改成 hidden / 条件卸载，宽度读成 0 会让折叠结果在「显示 n 个」与「n-1 个」之间反复翻转。 */}
      <Dropdown
        trigger={["click"]}
        placement="bottomRight"
        menu={{
          items: overflowItems.map((item) => ({
            key: item.key,
            icon: item.icon ? (
              <ModuleIcon name={item.icon} className="w-4 h-4" />
            ) : (
              <HomeOutlined className="w-4 h-4" />
            ),
            label: (
              <Link href={item.path} className={item.noAccess ? "opacity-55" : undefined}>
                {item.noAccess ? <MenuLockLabel label={item.label} /> : item.label}
              </Link>
            ),
          })),
          selectedKeys: overflowItems.some((item) => item.key === activeModule) ? [activeModule] : [],
        }}
      >
        <button
          ref={moreRef}
          type="button"
          aria-haspopup="menu"
          className={`
            absolute right-0 top-0 h-full flex items-center gap-1 px-3
            text-[14px] font-medium whitespace-nowrap bg-[var(--color-canvas)] transition-colors
            ${activeCollapsedTone
              ? "text-[var(--color-ink)]"
              : "text-[var(--color-steel)] hover:text-[var(--color-charcoal)]"
            }
            ${fit.showMore ? "" : "invisible"}
          `}
        >
          更多
          <span className="text-[10px]">▾</span>
          {activeCollapsedTone && (
            <span className="absolute bottom-0 left-3 right-3 h-[2px] bg-[var(--color-primary)] rounded-full" />
          )}
        </button>
      </Dropdown>
    </nav>
  )
}