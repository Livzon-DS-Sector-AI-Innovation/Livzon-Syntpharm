'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Divider, Select, Spin } from 'antd'
import type { ReactNode } from 'react'
import { searchPersonnel, type PersonnelOption } from '@/lib/api/client/identity'
import { UserAvatar, UserLabel } from '@/components/common/UserAvatar'

const SEARCH_DEBOUNCE_MS = 300
/** 每页条数：与后端 limit 上限（500）相比留足余量，展开首屏够用又不拖慢响应 */
const PAGE_SIZE = 50

/** 头像取值：服务端可能只给 thumb 或 url，统一按 thumb → url 回退 */
function avatarOf(person: PersonnelOption): string | undefined {
  return person.avatar_thumb || person.avatar_url || undefined
}

/** 选项/已选标签里的紧凑头像（标签内不放部门，避免 tags 高度撑高） */
function CompactPersonLabel({ name, src }: { name: string; src?: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%', verticalAlign: 'middle' }}>
      <UserAvatar name={name} src={src} size={18} />
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
    </span>
  )
}

/** 下拉面板中的富选项：头像 + 姓名 + 部门（与系统管理/设备人员口径一致） */
function PersonOptionRow({ person }: { person: PersonnelOption }) {
  return <UserLabel name={person.name} src={avatarOf(person)} secondary={person.department} avatarSize={26} />
}

/** 按 id 去重合并：分页追加时避免同一用户出现两次 */
function mergeById(prev: PersonnelOption[], next: PersonnelOption[]): PersonnelOption[] {
  if (prev.length === 0) return next
  const seen = new Set(prev.map((item) => item.id))
  const merged = [...prev]
  for (const item of next) {
    if (seen.has(item.id)) continue
    seen.add(item.id)
    merged.push(item)
  }
  return merged
}

/**
 * 人员搜索公共逻辑：
 * - 下拉展开即取首批系统用户（只含已绑定飞书的账号，不必先输关键字）
 * - 关键字变化走 300ms 防抖模糊搜索，并重置分页
 * - 请求序号防竞态（慢响应不覆盖新结果）
 */
function usePersonnelSearch() {
  const [options, setOptions] = useState<PersonnelOption[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)
  // 当前生效的关键字与已消费的分页游标（翻页/搜索都按它取下一页）
  const keywordRef = useRef('')
  const offsetRef = useRef(0)
  // 首屏是否已成功加载过：避免每次展开都重复请求
  const loadedRef = useRef(false)

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  const fetchPage = useCallback(async (keyword: string, offset: number) => {
    const seq = ++requestSeq.current
    setLoading(true)
    try {
      const page = await searchPersonnel(keyword, offset, PAGE_SIZE, { feishuBoundOnly: true })
      if (seq !== requestSeq.current) return
      setOptions((prev) => (offset === 0 ? page.items : mergeById(prev, page.items)))
      setTotal(page.total)
      offsetRef.current = offset + page.items.length
      loadedRef.current = true
    } catch {
      // 首屏失败时清空列表（可再次展开重试），追加失败保留已有结果
      if (seq === requestSeq.current && offset === 0) {
        setOptions([])
        setTotal(0)
      }
    } finally {
      if (seq === requestSeq.current) setLoading(false)
    }
  }, [])

  const loadFirstPage = useCallback(() => {
    if (loadedRef.current || loading) return
    void fetchPage(keywordRef.current, 0)
  }, [fetchPage, loading])

  const handleSearch = useCallback(
    (keyword: string) => {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        keywordRef.current = keyword.trim()
        offsetRef.current = 0
        void fetchPage(keywordRef.current, 0)
      }, SEARCH_DEBOUNCE_MS)
    },
    [fetchPage],
  )

  const loadMore = useCallback(() => {
    if (loading) return
    if (options.length >= total) return
    void fetchPage(keywordRef.current, offsetRef.current)
  }, [fetchPage, loading, options.length, total])

  return { options, total, loading, hasMore: options.length < total, loadFirstPage, loadMore, handleSearch }
}

/** 下拉底部「加载更多」：列表已到末页时不渲染 */
function LoadMoreFooter({
  loading,
  hasMore,
  shown,
  total,
  onLoadMore,
}: {
  loading: boolean
  hasMore: boolean
  shown: number
  total: number
  onLoadMore: () => void
}) {
  if (!hasMore) return null
  return (
    <>
      <Divider style={{ margin: '4px 0' }} />
      <div style={{ padding: '4px 8px', textAlign: 'center' }}>
        <Button
          type="link"
          size="small"
          loading={loading}
          // 阻止默认 mousedown，避免点击时下拉被收起
          onMouseDown={(event) => event.preventDefault()}
          onClick={onLoadMore}
        >
          加载更多（已显示 {shown} / 共 {total}）
        </Button>
      </div>
    </>
  )
}

export interface PersonnelSelectProps {
  /** 已绑定的系统用户 UUID */
  value?: string | null
  /** 已保存的姓名，用于未搜索时回显（避免直接显示 UUID） */
  label?: string | null
  /** 已保存的头像地址（可选），用于未搜索时回显真实头像；缺省走姓名首字兜底 */
  avatarSrc?: string | null
  placeholder?: string
  disabled?: boolean
  onChange: (person: { id: string; name: string } | null) => void
}

/**
 * 系统用户选择器（单选）。
 *
 * 台账里的人员字段以 uuid 为准、姓名为展示快照，因此选择后需要同时回写 id 与 name。
 * 搜索走后端 /identity/personnel，只列已绑定飞书身份的系统用户（审批人/整改负责人要能收到飞书通知），
 * 输入关键字按姓名模糊匹配；下拉项显示「头像 + 姓名 + 部门」，已选值同样带头像。
 */
export default function PersonnelSelect({
  value,
  label,
  avatarSrc,
  placeholder = '搜索姓名选择系统用户',
  disabled,
  onChange,
}: PersonnelSelectProps) {
  const { options, total, loading, hasMore, loadFirstPage, loadMore, handleSearch } = usePersonnelSearch()

  // 回显：已绑定但未出现在列表里时补一个选项，保证显示姓名（带头像）而不是 UUID
  const displayOptions: PersonnelOption[] = useMemo(
    () =>
      value && !options.some((o) => o.id === value)
        ? [{ id: value, name: label || value, avatar_thumb: avatarSrc || undefined }, ...options]
        : options,
    [options, value, label, avatarSrc],
  )

  const optionById = useMemo(() => new Map(displayOptions.map((o) => [o.id, o])), [displayOptions])

  const handleChange = (next: string | undefined) => {
    if (!next) {
      onChange(null)
      return
    }
    const picked = displayOptions.find((o) => o.id === next)
    if (picked) onChange({ id: picked.id, name: picked.name })
  }

  return (
    <Select
      showSearch
      allowClear={false}
      disabled={disabled}
      filterOption={false}
      defaultActiveFirstOption={false}
      notFoundContent={loading ? <Spin size="small" /> : '未找到匹配的系统用户'}
      placeholder={placeholder}
      style={{ width: '100%' }}
      value={value || undefined}
      onOpenChange={(open) => {
        if (open) loadFirstPage()
      }}
      onSearch={handleSearch}
      onChange={handleChange}
      popupRender={(menu) => (
        <>
          {menu}
          <LoadMoreFooter
            loading={loading}
            hasMore={hasMore}
            shown={options.length}
            total={total}
            onLoadMore={loadMore}
          />
        </>
      )}
      options={displayOptions.map((o) => ({
        value: o.id,
        label: <CompactPersonLabel name={o.name} src={avatarOf(o)} />,
      }))}
      optionRender={(option): ReactNode => {
        const person = optionById.get(String(option.value))
        return person ? <PersonOptionRow person={person} /> : (option.label as ReactNode)
      }}
    />
  )
}

export interface PersonnelMultiSelectProps {
  /** 已选系统用户 UUID 列表 */
  value?: string[]
  /** 已保存的姓名快照（与 value 顺序一致），未搜索时用于回显 */
  labels?: string[]
  /** 已保存的头像快照（与 value 顺序一致），未搜索时用于回显；缺省走姓名首字兜底 */
  avatarSrcs?: Array<string | null | undefined>
  placeholder?: string
  disabled?: boolean
  onChange: (persons: { id: string; name: string }[]) => void
}

/**
 * 系统用户选择器（多选）。
 *
 * 用于「整改负责人」这类多人字段：提交时同时回写 UUID 列表与姓名快照，
 * 保证台账在不额外查用户表的情况下展示姓名；下拉项与已选标签均带头像。
 */
export function PersonnelMultiSelect({
  value,
  labels,
  avatarSrcs,
  placeholder = '搜索姓名，可多选',
  disabled,
  onChange,
}: PersonnelMultiSelectProps) {
  const { options, total, loading, hasMore, loadFirstPage, loadMore, handleSearch } = usePersonnelSearch()
  // 稳定引用：value 缺省时不要在每次渲染造新数组，否则下级 useMemo 全部失效
  const selectedIds = useMemo(() => value ?? [], [value])

  // 姓名快照按 id 建索引：value 顺序即快照顺序，直接用 Map 查比 indexOf 稳
  const labelMap = useMemo(
    () => new Map(selectedIds.map((id, index) => [id, labels?.[index]])),
    [selectedIds, labels],
  )
  const avatarMap = useMemo(
    () => new Map(selectedIds.map((id, index) => [id, avatarSrcs?.[index] ?? undefined])),
    [selectedIds, avatarSrcs],
  )

  // 回显：把尚未出现在列表里的已选人员补进来（用姓名/头像快照兜底）
  const displayOptions: PersonnelOption[] = useMemo(() => {
    const missing = selectedIds
      .filter((id) => !options.some((o) => o.id === id))
      .map(
        (id) =>
          ({
            id,
            name: labelMap.get(id) || id,
            avatar_thumb: avatarMap.get(id),
          }) as PersonnelOption,
      )
    return [...missing, ...options]
  }, [selectedIds, options, labelMap, avatarMap])

  const optionById = useMemo(() => new Map(displayOptions.map((o) => [o.id, o])), [displayOptions])

  const handleChange = (nextIds: string[]) => {
    const persons = nextIds
      .map((id) => {
        const picked = displayOptions.find((o) => o.id === id)
        if (picked) return { id: picked.id, name: picked.name }
        const fallback = labelMap.get(id)
        return fallback ? { id, name: fallback } : null
      })
      .filter((p): p is { id: string; name: string } => p !== null)
    onChange(persons)
  }

  return (
    <Select
      mode="multiple"
      showSearch
      allowClear
      disabled={disabled}
      filterOption={false}
      defaultActiveFirstOption={false}
      notFoundContent={loading ? <Spin size="small" /> : '未找到匹配的系统用户'}
      placeholder={placeholder}
      style={{ width: '100%' }}
      value={selectedIds}
      onOpenChange={(open) => {
        if (open) loadFirstPage()
      }}
      onSearch={handleSearch}
      onChange={handleChange}
      popupRender={(menu) => (
        <>
          {menu}
          <LoadMoreFooter
            loading={loading}
            hasMore={hasMore}
            shown={options.length}
            total={total}
            onLoadMore={loadMore}
          />
        </>
      )}
      options={displayOptions.map((o) => ({
        value: o.id,
        label: <CompactPersonLabel name={o.name} src={avatarOf(o)} />,
      }))}
      optionRender={(option): ReactNode => {
        const person = optionById.get(String(option.value))
        return person ? <PersonOptionRow person={person} /> : (option.label as ReactNode)
      }}
    />
  )
}