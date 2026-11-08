'use client'

/**
 * 研发模块「项目过滤器」共用逻辑。
 *
 * 研发报告、项目知识库都改成「默认全部项目 + 项目下拉收窄」，选择优先级：
 * URL `?projectId=` > 上次选择（localStorage）> 只有一个项目时自动落位 > 全部项目。
 *
 * 只在客户端 effect 里读 localStorage，避免 SSR/CSR 首屏不一致导致的 hydration 报错；
 * 「自动落位」只做一次，否则用户手动切回「全部项目」会被立刻弹回项目视图。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

/** 下拉中代表「全部项目」的哨兵值：antd Select 不适合用空串作为可选中项 */
export const ALL_PROJECTS_VALUE = '__all__'

/**
 * 存储层「用户主动选了全部项目」的哨兵值（项目 id 是 UUID，不会与之冲突）。
 * 有了它，「只有一个项目」时的自动落位才不会在刷新后把用户拽回项目视图。
 */
const STORED_ALL = 'all'

/** 读取上次选择，隐私模式下 localStorage 不可用时静默降级为「全部项目」 */
function readStored(key: string): string {
  if (typeof window === 'undefined') return ''
  try {
    return window.localStorage.getItem(key) ?? ''
  } catch {
    return ''
  }
}

function writeStored(key: string, value: string): void {
  if (typeof window === 'undefined') return
  try {
    if (value) window.localStorage.setItem(key, value)
    else window.localStorage.removeItem(key)
  } catch {
    // 记住选择失败不影响主流程，忽略即可
  }
}

interface Options {
  /** 页面路径：切项目时同步进 URL，刷新与分享不丢当前视图（可自带固定查询串） */
  basePath: string
  /** localStorage key，需带模块前缀，避免两个页面互相覆盖 */
  storageKey: string
  /** 从 URL 带过来的项目 id */
  initialProjectId?: string
  /** 可选项目总数：只有一个项目时自动落位，省掉一次选择 */
  projectCount: number
  /** 唯一项目的 id（projectCount 为 1 时才有意义） */
  soleProjectId?: string
}

interface Result {
  /** 空串表示「全部项目」 */
  projectId: string
  selectProject: (value: string) => void
}

export function useProjectFilter({
  basePath,
  storageKey,
  initialProjectId = '',
  projectCount,
  soleProjectId,
}: Options): Result {
  const router = useRouter()
  const [projectId, setProjectId] = useState(initialProjectId)

  /** 首次选择是否已完成：完成后再也不自动落位，保证「全部项目」能停住 */
  const initializedRef = useRef(false)
  /** 上一次来自 URL 的项目 id：用于区分「首次挂载」与「地址栏/前进后退变化」 */
  const lastInitialRef = useRef(initialProjectId)

  // 初始化：URL 优先（state 初值已生效）→ 上次选择 → 只有一个项目时落位
  useEffect(() => {
    if (initializedRef.current) return
    if (projectCount === 0) return // 项目列表还没回来，等下一次
    initializedRef.current = true

    if (initialProjectId) {
      writeStored(storageKey, initialProjectId)
      return
    }
    // 上次选择优先：`STORED_ALL` 表示用户上次就主动选了全部，此时不再自动落位
    const stored = readStored(storageKey)
    if (stored === STORED_ALL) return
    const fallback = projectCount === 1 ? (soleProjectId ?? '') : ''
    const next = stored || fallback
    if (!next) return
    // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage 与项目列表都只能在客户端拿到，无法在初始化阶段决定
    setProjectId(next)
  }, [initialProjectId, projectCount, soleProjectId, storageKey])

  // 地址栏或前进后退导致 URL 参数变化时，以 URL 为准（含回退到「全部项目」）
  useEffect(() => {
    if (lastInitialRef.current === initialProjectId) return
    lastInitialRef.current = initialProjectId
    setProjectId(initialProjectId)
    writeStored(storageKey, initialProjectId || STORED_ALL)
  }, [initialProjectId, storageKey])

  const selectProject = useCallback(
    (value: string) => {
      const next = value === ALL_PROJECTS_VALUE ? '' : value
      initializedRef.current = true
      setProjectId(next)
      // 显式选「全部」也记下来，否则只有一个项目时刷新会被自动落位拽回项目视图
      writeStored(storageKey, next || STORED_ALL)
      // basePath 允许自带固定参数（如 `?from=project-detail`），切项目时保留它们
      const separator = basePath.includes('?') ? '&' : '?'
      const url = next ? `${basePath}${separator}projectId=${encodeURIComponent(next)}` : basePath
      router.replace(url, { scroll: false })
    },
    [basePath, router, storageKey],
  )

  return { projectId, selectProject }
}