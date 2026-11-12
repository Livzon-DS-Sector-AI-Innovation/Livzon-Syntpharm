'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Divider, Select, Spin } from 'antd'
import type { ReactNode } from 'react'
import { searchPersonnel, type PersonnelOption } from '@/lib/api/client/identity'
import { UserAvatar, UserLabel } from '@/components/common/UserAvatar'

/** 搜索防抖：快速连打不会把每个字符都送到后端 */
const SEARCH_DEBOUNCE_MS = 300
/** 每页条数：展开首屏 50 条，够用又不会拖慢响应 */
const PAGE_SIZE = 50
/** 触底判定余量：留 32px 避免亚像素误差导致永远触发不到 */
const SCROLL_BOTTOM_THRESHOLD = 32

type Person = { id: string; name: string }

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

/** 下拉面板中的富选项：头像 + 姓名 +（账号 ·）部门 */
function PersonOptionRow({ person, showUsername }: { person: PersonnelOption; showUsername: boolean }) {
  const secondary = [showUsername ? person.username : null, person.department].filter(Boolean).join(' · ')
  return (
    <UserLabel name={person.name} src={avatarOf(person)} secondary={secondary || undefined} avatarSize={26} />
  )
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
 * 远端用户搜索的公共逻辑：
 * - 下拉展开即取首批用户（无需先输关键字）
 * - 关键字变化走 300ms 防抖服务端搜索，并重置分页（未加载过的用户也能搜到）
 * - 下拉滚动到底自动追加下一页，不需要手动点「加载更多」
 * - 请求序号防竞态：慢响应不会覆盖新关键字的结果
 */
function useRemoteUserSearch(feishuBoundOnly: boolean) {
  const [options, setOptions] = useState<PersonnelOption[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)
  // 当前生效的关键字与已消费的分页游标（翻页/搜索都按它取下一页）
  const keywordRef = useRef('')
  const offsetRef = useRef(0)
  // 滚动事件是高频回调，用 ref 做请求闸门，避免 state 闭包滞后导致连发
  const loadingRef = useRef(false)

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  const fetchPage = useCallback(
    async (keyword: string, offset: number) => {
      const seq = ++requestSeq.current
      loadingRef.current = true
      setLoading(true)
      try {
        const page = await searchPersonnel(keyword, offset, PAGE_SIZE, { feishuBoundOnly })
        if (seq !== requestSeq.current) return
        setOptions((prev) => (offset === 0 ? page.items : mergeById(prev, page.items)))
        setTotal(page.total)
        offsetRef.current = offset + page.items.length
      } catch {
        // 首屏失败时清空列表（可再次展开重试），追加失败保留已有结果
        if (seq === requestSeq.current && offset === 0) {
          setOptions([])
          setTotal(0)
        }
      } finally {
        if (seq === requestSeq.current) {
          loadingRef.current = false
          setLoading(false)
        }
      }
    },
    [feishuBoundOnly],
  )

  /** 每次展开都回到干净状态：清关键字、游标归零、重新拉首页（新建账号后立刻可见） */
  const reload = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current)
    keywordRef.current = ''
    offsetRef.current = 0
    setSearchValue('')
    void fetchPage('', 0)
  }, [fetchPage])

  const handleSearch = useCallback(
    (value: string) => {
      setSearchValue(value)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        keywordRef.current = value.trim()
        offsetRef.current = 0
        void fetchPage(keywordRef.current, 0)
      }, SEARCH_DEBOUNCE_MS)
    },
    [fetchPage],
  )

  const loadMore = useCallback(() => {
    if (loadingRef.current) return
    if (options.length >= total) return
    void fetchPage(keywordRef.current, offsetRef.current)
  }, [fetchPage, options.length, total])

  /** 触底自动续载：直接读滚动容器位置，不依赖 antd 内部状态 */
  const handlePopupScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const el = event.currentTarget
      if (el.scrollHeight - el.scrollTop - el.clientHeight > SCROLL_BOTTOM_THRESHOLD) return
      loadMore()
    },
    [loadMore],
  )

  /** 收起下拉时清空搜索框，下次展开不会残留上次的关键字 */
  const clearSearchValue = useCallback(() => setSearchValue(''), [])

  return { options, loading, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue }
}

/** 下拉底部只在请求中显示加载提示；没有更多数据时什么都不渲染 */
function ListLoadingFooter({ loading, hasOptions }: { loading: boolean; hasOptions: boolean }) {
  if (!loading || !hasOptions) return null
  return (
    <>
      <Divider style={{ margin: '4px 0' }} />
      <div style={{ padding: '6px 0', textAlign: 'center' }}>
        <Spin size="small" />
      </div>
    </>
  )
}

export interface RemoteUserSelectProps {
  /** 已选用户 UUID */
  value?: string | null
  /** 已保存的姓名快照：未出现在当前列表时用于回显，避免显示 UUID */
  label?: string | null
  /** 已保存的头像快照（可选），缺省走姓名首字兜底 */
  avatarSrc?: string | null
  /** true = 只列已绑定飞书身份的账号（要发通知的场景）；授权等场景传 false 以覆盖本地账号 */
  feishuBoundOnly?: boolean
  /** 选项次级文案是否带上登录账号（授权场景用于区分重名） */
  showUsername?: boolean
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /** Form.Item 会代为注入 onChange；裸用时必填 */
  onChange?: (person: Person | null) => void
}

/**
 * 远端用户选择器（单选）。
 *
 * 打开即加载 50 条，滚到底自动续载；输入关键字走服务端搜索，搜索结果同样分页续载。
 * 选择后同时回写 id 与姓名快照，姓名缺失时用快照兜底显示。
 */
export function RemoteUserSelect({
  value,
  label,
  avatarSrc,
  feishuBoundOnly = true,
  showUsername = false,
  allowClear = false,
  placeholder = '搜索姓名选择系统用户',
  disabled,
  onChange,
}: RemoteUserSelectProps) {
  const { options, loading, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue } =
    useRemoteUserSearch(feishuBoundOnly)
  // 选中快照：父级只传 value（如 Form 只存 id）时，重新展开/搜索后也能显示姓名而不是 UUID
  const [picked, setPicked] = useState<Person | null>(null)
  const snapshotName = label ?? (picked && picked.id === value ? picked.name : null)

  // 回显：已绑定但未出现在当前列表里时补一个选项，保证显示姓名（带头像）而不是 UUID
  const displayOptions: PersonnelOption[] = useMemo(
    () =>
      value && !options.some((o) => o.id === value)
        ? [{ id: value, name: snapshotName || value, avatar_thumb: avatarSrc || undefined }, ...options]
        : options,
    [options, value, snapshotName, avatarSrc],
  )

  const optionById = useMemo(() => new Map(displayOptions.map((o) => [o.id, o])), [displayOptions])

  const handleChange = (next: string | undefined) => {
    if (!next) {
      setPicked(null)
      onChange?.(null)
      return
    }
    const chosen = displayOptions.find((o) => o.id === next)
    if (!chosen) return
    setPicked({ id: chosen.id, name: chosen.name })
    onChange?.({ id: chosen.id, name: chosen.name })
  }

  return (
    <Select
      showSearch
      allowClear={allowClear}
      disabled={disabled}
      filterOption={false}
      defaultActiveFirstOption={false}
      searchValue={searchValue}
      notFoundContent={loading ? <Spin size="small" /> : '未找到匹配的系统用户'}
      placeholder={placeholder}
      style={{ width: '100%' }}
      value={value || undefined}
      onOpenChange={(open) => {
        if (open) reload()
        else clearSearchValue()
      }}
      onSearch={handleSearch}
      onPopupScroll={handlePopupScroll}
      onChange={handleChange}
      popupRender={(menu) => (
        <>
          {menu}
          <ListLoadingFooter loading={loading} hasOptions={displayOptions.length > 0} />
        </>
      )}
      options={displayOptions.map((o) => ({
        value: o.id,
        label: <CompactPersonLabel name={o.name} src={avatarOf(o)} />,
      }))}
      optionRender={(option): ReactNode => {
        const person = optionById.get(String(option.value))
        return person ? <PersonOptionRow person={person} showUsername={showUsername} /> : (option.label as ReactNode)
      }}
    />
  )
}

export interface RemoteUserMultiSelectProps {
  /** 已选用户 UUID 列表 */
  value?: string[]
  /** 已保存的姓名快照（与 value 顺序一致），未搜索时用于回显 */
  labels?: string[]
  /** 已保存的头像快照（与 value 顺序一致），缺省走姓名首字兜底 */
  avatarSrcs?: Array<string | null | undefined>
  /** true = 只列已绑定飞书身份的账号；传 false 以覆盖本地账号 */
  feishuBoundOnly?: boolean
  showUsername?: boolean
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /** Form.Item 会代为注入 onChange；裸用时必填 */
  onChange?: (persons: Person[]) => void
}

/**
 * 远端用户选择器（多选）。
 *
 * 与单选同一套取数逻辑：50 条一页、滚到底自动续、关键字走服务端；
 * 已选但不在当前列表/搜索结果里的人用姓名快照补进选项，标签不会消失。
 */
export function RemoteUserMultiSelect({
  value,
  labels,
  avatarSrcs,
  feishuBoundOnly = true,
  showUsername = false,
  allowClear = true,
  placeholder = '搜索姓名，可多选',
  disabled,
  onChange,
}: RemoteUserMultiSelectProps) {
  const { options, loading, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue } =
    useRemoteUserSearch(feishuBoundOnly)
  // 选中快照：父级只传 value（如 Form 只存 id 数组）时，重新展开/搜索后也能显示姓名
  const [pickedList, setPickedList] = useState<Person[]>([])
  // 稳定引用：value 缺省时不要在每次渲染造新数组，否则下级 useMemo 全部失效
  const selectedIds = useMemo(() => value ?? [], [value])
  const pickedNameMap = useMemo(
    () => new Map(pickedList.map((person) => [person.id, person.name])),
    [pickedList],
  )

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
            name: labelMap.get(id) || pickedNameMap.get(id) || id,
            avatar_thumb: avatarMap.get(id),
          }) as PersonnelOption,
      )
    return [...missing, ...options]
  }, [selectedIds, options, labelMap, avatarMap, pickedNameMap])

  const optionById = useMemo(() => new Map(displayOptions.map((o) => [o.id, o])), [displayOptions])

  const handleChange = (nextIds: string[]) => {
    const persons = nextIds
      .map((id) => {
        const picked = displayOptions.find((o) => o.id === id)
        if (picked) return { id: picked.id, name: picked.name }
        const fallback = labelMap.get(id)
        return fallback ? { id, name: fallback } : null
      })
      .filter((p): p is Person => p !== null)
    setPickedList(persons)
    onChange?.(persons)
  }

  return (
    <Select
      mode="multiple"
      showSearch
      allowClear={allowClear}
      disabled={disabled}
      filterOption={false}
      defaultActiveFirstOption={false}
      searchValue={searchValue}
      notFoundContent={loading ? <Spin size="small" /> : '未找到匹配的系统用户'}
      placeholder={placeholder}
      style={{ width: '100%' }}
      value={selectedIds}
      onOpenChange={(open) => {
        if (open) reload()
        else clearSearchValue()
      }}
      onSearch={handleSearch}
      onPopupScroll={handlePopupScroll}
      onChange={handleChange}
      popupRender={(menu) => (
        <>
          {menu}
          <ListLoadingFooter loading={loading} hasOptions={displayOptions.length > 0} />
        </>
      )}
      options={displayOptions.map((o) => ({
        value: o.id,
        label: <CompactPersonLabel name={o.name} src={avatarOf(o)} />,
      }))}
      optionRender={(option): ReactNode => {
        const person = optionById.get(String(option.value))
        return person ? <PersonOptionRow person={person} showUsername={showUsername} /> : (option.label as ReactNode)
      }}
    />
  )
}