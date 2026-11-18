import type { ModuleSetting, ModuleSettingBatchUpdate } from '@/types/module-settings'

/**
 * 运行时配置列表的展示口径（纯函数，便于复用与单测）。
 *
 * 后端已下发 label / group_name / is_secret / value_hint；
 * 未回填的存量配置项在这里统一降级：标题用 key、分组归入「其他」，
 * 不在前端维护第二份业务字典。
 */

export const OTHER_GROUP = '其他'

/** 功能域固定排序；未列出的分组按中文名排在后面，`其他` 永远垫底 */
const GROUP_ORDER = [
  '功能开关',
  'AI 模型',
  '调度任务',
  '飞书集成',
  '外部数据源',
  '通知与提醒',
  '文档生成',
  '报告生成',
  '账号与身份',
  '视频讲稿',
]

export const VALUE_TYPE_META: Record<string, { label: string; color: string }> = {
  bool: { label: '开关', color: 'blue' },
  int: { label: '数字', color: 'orange' },
  json: { label: 'JSON', color: 'purple' },
  string: { label: '文本', color: 'default' },
}

export function valueTypeLabel(valueType: string): string {
  return VALUE_TYPE_META[valueType]?.label ?? valueType
}

export function valueTypeColor(valueType: string): string {
  return VALUE_TYPE_META[valueType]?.color ?? 'default'
}

export function settingTitle(setting: ModuleSetting): string {
  const label = setting.label?.trim()
  return label ? label : setting.key
}

export function settingGroup(setting: ModuleSetting): string {
  const group = setting.group_name?.trim()
  return group ? group : OTHER_GROUP
}

export function isBoolEnabled(setting: ModuleSetting): boolean {
  return (setting.value ?? '').trim().toLowerCase() === 'true'
}

/** 已人工调整：后端按 updated_by 判定，初次生成/新建也计入 */
export function isManuallyAdjusted(setting: ModuleSetting): boolean {
  return setting.manually_adjusted === true
}

function pad(value: number): string {
  return String(value).padStart(2, '0')
}

/** 列表内的紧凑时间：`11-18 17:02`；无值时返回空串 */
export function formatShortTime(iso?: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return `${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
}

/** 悬浮提示用的完整时间 */
export function formatFullTime(iso?: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  const hms = `${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${hms}`
}

/** 「张三 · 11-18 17:02 修改」；未调整过显示「初始值」 */
export function describeChange(setting: ModuleSetting): string {
  if (!isManuallyAdjusted(setting)) return '初始值'
  const who = setting.updated_by_name?.trim() || '未知账号'
  const when = formatShortTime(setting.updated_at)
  return when ? `${who} · ${when} 修改` : `${who} 修改`
}

export type SettingSort = 'name' | 'updated'

export interface SettingQuery {
  keyword: string
  valueType: string
  group: string
  onlyAdjusted: boolean
  sortBy: SettingSort
}

export const DEFAULT_QUERY: SettingQuery = {
  keyword: '',
  valueType: 'all',
  group: 'all',
  onlyAdjusted: false,
  sortBy: 'name',
}

function matchesKeyword(setting: ModuleSetting, keyword: string): boolean {
  const needle = keyword.trim().toLowerCase()
  if (!needle) return true
  return [setting.key, setting.label, setting.description, setting.group_name]
    .filter((item): item is string => Boolean(item))
    .some((item) => item.toLowerCase().includes(needle))
}

export function filterSettings(settings: ModuleSetting[], query: SettingQuery): ModuleSetting[] {
  return settings.filter((setting) => {
    if (!matchesKeyword(setting, query.keyword)) return false
    if (query.valueType !== 'all' && setting.value_type !== query.valueType) return false
    if (query.group !== 'all' && settingGroup(setting) !== query.group) return false
    if (query.onlyAdjusted && !isManuallyAdjusted(setting)) return false
    return true
  })
}

export function sortSettings(settings: ModuleSetting[], sortBy: SettingSort): ModuleSetting[] {
  const sorted = [...settings]
  sorted.sort((a, b) => {
    if (sortBy === 'updated') {
      const left = a.updated_at ? Date.parse(a.updated_at) : 0
      const right = b.updated_at ? Date.parse(b.updated_at) : 0
      if (left !== right) return right - left
    }
    return settingTitle(a).localeCompare(settingTitle(b), 'zh-CN')
  })
  return sorted
}

export interface SettingGroupView {
  name: string
  items: ModuleSetting[]
}

function groupRank(name: string): [number, string] {
  if (name === OTHER_GROUP) return [GROUP_ORDER.length + 1, name]
  const index = GROUP_ORDER.indexOf(name)
  return index === -1 ? [GROUP_ORDER.length, name] : [index, name]
}

/** 过滤 + 排序 + 分组；空分组不产出 */
export function buildGroupedSettings(
  settings: ModuleSetting[],
  query: SettingQuery
): SettingGroupView[] {
  const filtered = sortSettings(filterSettings(settings, query), query.sortBy)
  const buckets = new Map<string, ModuleSetting[]>()
  for (const setting of filtered) {
    const name = settingGroup(setting)
    const bucket = buckets.get(name)
    if (bucket) bucket.push(setting)
    else buckets.set(name, [setting])
  }
  return [...buckets.entries()]
    .map(([name, items]) => ({ name, items }))
    .sort((a, b) => {
      const [rankA, nameA] = groupRank(a.name)
      const [rankB, nameB] = groupRank(b.name)
      if (rankA !== rankB) return rankA - rankB
      return nameA.localeCompare(nameB, 'zh-CN')
    })
}

/** 当前筛选结果里出现过的分组名（供筛选下拉使用，按固定顺序） */
export function collectGroups(settings: ModuleSetting[]): string[] {
  const names = new Set(settings.map(settingGroup))
  return [...names].sort((a, b) => {
    const [rankA, nameA] = groupRank(a)
    const [rankB, nameB] = groupRank(b)
    return rankA !== rankB ? rankA - rankB : nameA.localeCompare(nameB, 'zh-CN')
  })
}

/** 本模块可批量启停的项（只有布尔项） */
export function boolSettings(settings: ModuleSetting[]): ModuleSetting[] {
  return settings.filter((setting) => setting.value_type === 'bool')
}

/** 构造批量更新请求体 */
export function buildBatchPayload(
  settings: ModuleSetting[],
  value: 'true' | 'false'
): ModuleSettingBatchUpdate {
  return {
    items: settings.map((setting) => ({
      module: setting.module,
      key: setting.key,
      value,
    })),
  }
}

export interface ExportItem {
  module: string
  key: string
  label: string | null
  group: string
  value: string
  value_type: string
  is_secret: boolean
  note: string
}

/**
 * 导出载荷：密钥类不写明文（服务端本来也没下发），只标 is_secret 方便对照。
 */
export function buildExportPayload(settings: ModuleSetting[]): string {
  const items: ExportItem[] = sortSettings(settings, 'name').map((setting) => ({
    module: setting.module,
    key: setting.key,
    label: setting.label ?? null,
    group: settingGroup(setting),
    value: setting.is_secret ? '' : setting.value,
    value_type: setting.value_type,
    is_secret: setting.is_secret === true,
    note: setting.is_secret ? '密钥类配置已隐藏明文，请到系统配置中查看' : '',
  }))
  return JSON.stringify({ exported_at: new Date().toISOString(), settings: items }, null, 2)
}