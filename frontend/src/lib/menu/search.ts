import type { SubMenuItem } from '@/lib/menu-config'
import type { ResolvedModule } from '@/lib/menu/resolve'

/**
 * 顶栏全局搜索的内存索引。
 *
 * 数据源只有一份：`AppShell` 已按当前账号权限解析好的菜单树（`ResolvedModule[]`），
 * 因此搜索结果天然「搜得到 = 进得去」，不需要额外接口，也不会把无权菜单暴露出去。
 *
 * 匹配策略（刻意保持简单、可解释，不引拼音库）：
 * - 中文页面名子串匹配；
 * - 英文输入靠 `path` 片段命中（如 `deviation` → 偏差台账）；
 * - 多关键词用空格分隔，全部命中才算命中。
 */

export interface SearchEntry {
  /** 唯一键：`<模块 key>:<菜单 key>:<序号>`，静态项为 `static:<name>` */
  key: string
  label: string
  path: string
  /** 归属路径（不含自身），如「质量管理 / 偏差管理」；模块根路径为「质量管理」 */
  breadcrumb: string
  moduleKey: string
  moduleLabel: string
  /** 模块图标名，供 `ModuleIcon` 渲染 */
  icon: string
  /** 当前账号无该菜单权限：仍可搜索与跳转（进入无权限页），由 UI 渲染锁标识 */
  noAccess: boolean
  /** 以下为预计算的小写匹配键，只在 `buildSearchIndex` 阶段算一次 */
  labelKey: string
  pathKey: string
  breadcrumbKey: string
}

/** 搜索结果排序权重：数字越小越相关 */
const SCORE_EXACT = 0
const SCORE_PREFIX = 1
const SCORE_LABEL = 2
const SCORE_BREADCRUMB = 3
const SCORE_PATH = 4
const SCORE_NONE = Number.POSITIVE_INFINITY

const DEFAULT_LIMIT = 8

/** NFKC + 小写 + 空白归一：全角字符、大小写差异不影响命中 */
function normalizeText(value: string): string {
  return value.normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim()
}

function makeEntry(
  entry: Omit<SearchEntry, 'labelKey' | 'pathKey' | 'breadcrumbKey'>,
): SearchEntry {
  return {
    ...entry,
    labelKey: normalizeText(entry.label),
    pathKey: normalizeText(entry.path),
    breadcrumbKey: normalizeText(entry.breadcrumb),
  }
}

/**
 * 递归展开菜单树。
 *
 * - `disabled`（功能未开发）自身不入索引，但其子项仍继续展开：避免父节点占位把可用页面一起吃掉；
 * - 有 `children` 的父节点若同时带 `path`（如「偏差管理」落地页），父节点自身也是一条可跳转结果；
 * - 空 `path` 的纯分组节点不入索引，避免死链。
 */
function walkItems(
  items: SubMenuItem[],
  module: ResolvedModule,
  parentLabels: string[],
  out: SearchEntry[],
  seen: Set<string>,
): void {
  for (const item of items) {
    const noAccess = module.noAccess || Boolean(item.noAccess)
    const breadcrumb = [module.label, ...parentLabels].join(' / ')

    if (!item.disabled && item.path) {
      const dedupeKey = `${item.path}|${item.label}`
      if (!seen.has(dedupeKey)) {
        seen.add(dedupeKey)
        out.push(
          makeEntry({
            key: `${module.key}:${item.key}:${out.length}`,
            label: item.label,
            path: item.path,
            breadcrumb,
            moduleKey: module.key,
            moduleLabel: module.label,
            icon: module.icon,
            noAccess,
          }),
        )
      }
    }

    if (item.children && item.children.length > 0) {
      walkItems(item.children, module, [...parentLabels, item.label], out, seen)
    }
  }
}

/** 不属于业务模块的独立页面（与 `Sidebar.tsx` 的 SIMPLE_PAGES 对齐） */
const STATIC_ENTRIES: Array<Omit<SearchEntry, 'labelKey' | 'pathKey' | 'breadcrumbKey'>> = [
  {
    key: 'static:home',
    label: '首页',
    path: '/home',
    // 让「工作台」也能搜到首页
    breadcrumb: '工作台',
    moduleKey: 'home',
    moduleLabel: '首页',
    icon: 'dashboard',
    noAccess: false,
  },
  {
    key: 'static:profile',
    label: '个人信息',
    path: '/profile',
    breadcrumb: '个人中心',
    moduleKey: 'profile',
    moduleLabel: '个人中心',
    icon: 'users',
    noAccess: false,
  },
]

/**
 * 构建搜索索引（O(n)）。索引只在菜单树变化时重建，检索时不再做字符串归一。
 */
export function buildSearchIndex(menus: ResolvedModule[]): SearchEntry[] {
  const entries: SearchEntry[] = STATIC_ENTRIES.map(makeEntry)
  const seen = new Set(entries.map((entry) => `${entry.path}|${entry.label}`))

  for (const mod of menus) {
    const moduleKey = `${mod.path}|${mod.label}`
    if (mod.path && !seen.has(moduleKey)) {
      seen.add(moduleKey)
      entries.push(
        makeEntry({
          key: `module:${mod.key}`,
          label: mod.label,
          path: mod.path,
          breadcrumb: '模块',
          moduleKey: mod.key,
          moduleLabel: mod.label,
          icon: mod.icon,
          noAccess: mod.noAccess,
        }),
      )
    }
    walkItems(mod.children, mod, [], entries, seen)
  }

  return entries
}

/** 单关键词得分：完全相等 > 前缀 > 名称子串 > 归属路径 > 路由片段 */
function scoreToken(entry: SearchEntry, token: string): number {
  if (entry.labelKey === token) return SCORE_EXACT
  if (entry.labelKey.startsWith(token)) return SCORE_PREFIX
  if (entry.labelKey.includes(token)) return SCORE_LABEL
  if (entry.breadcrumbKey.includes(token)) return SCORE_BREADCRUMB
  if (entry.pathKey.includes(token)) return SCORE_PATH
  return SCORE_NONE
}

/**
 * 检索：所有关键词都必须命中（AND），条目得分取最弱的一个关键词，
 * 保证「偏差 台账」这类多词输入不会被单次强命中带偏。
 */
export function searchEntries(index: SearchEntry[], query: string, limit = DEFAULT_LIMIT): SearchEntry[] {
  const tokens = normalizeText(query).split(' ').filter(Boolean)
  if (tokens.length === 0) return []

  const scored: Array<{ entry: SearchEntry; score: number }> = []
  for (const entry of index) {
    let worst = SCORE_EXACT
    let matched = true
    for (const token of tokens) {
      const score = scoreToken(entry, token)
      if (score === SCORE_NONE) {
        matched = false
        break
      }
      worst = Math.max(worst, score)
    }
    if (matched) scored.push({ entry, score: worst })
  }

  scored.sort((a, b) => {
    if (a.score !== b.score) return a.score - b.score
    if (a.entry.labelKey.length !== b.entry.labelKey.length) {
      return a.entry.labelKey.length - b.entry.labelKey.length
    }
    const byLabel = a.entry.label.localeCompare(b.entry.label, 'zh-CN')
    if (byLabel !== 0) return byLabel
    return a.entry.path.localeCompare(b.entry.path)
  })

  return scored.slice(0, limit).map((item) => item.entry)
}