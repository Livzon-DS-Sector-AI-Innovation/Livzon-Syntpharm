'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Divider, Select, Spin } from 'antd'
import type { ReactNode } from 'react'
import type { DirectoryPersonItem } from '@/lib/api/client/hr'
import { fetchUserLookup, type UserLookupItem } from '@/lib/api/client/identity'
import { UserAvatar, UserLabel } from '@/components/common/UserAvatar'

/**
 * 统一人员选择器。
 *
 * 数据源是系统用户管理口径 `GET /api/v1/identity/users/lookup`，返回
 * `identity.users.id`（账号 UUID），**只包含启用账号**：没有账号的 HR 员工
 * 不会被列出，业务表也不再经由「按需建号」隐式产生账号。
 *
 * 全系统所有「选人」场景都必须走这里，不得再各自查 identity.users、
 * hr.employee_profiles 或 hr.directory。
 */

const SEARCH_DEBOUNCE_MS = 300
const PAGE_SIZE = 50
const SCROLL_BOTTOM_THRESHOLD = 32

export interface PickedPerson {
  /** hr.employee_profiles.id */
  id: string
  name: string
}

/**
 * 把系统账号映射成选择器内部统一结构。
 *
 * 字段名沿用 HR 目录的 DirectoryPersonItem：调用点（表单回填、姓名快照展示）
 * 都按这套字段写，换数据源后无需逐个改动。语义对照：
 * employee_no ← 登录账号，job_title_name ← 职务，department_names ← 所属部门。
 */
function toDirectoryPerson(account: UserLookupItem): DirectoryPersonItem {
  return {
    id: account.id,
    name: account.name,
    employee_no: account.username ?? '',
    job_title_name: account.position ?? '',
    department_names: account.department ? [account.department] : [],
    department_path: [],
    avatar_url: account.avatar_url ?? '',
  }
}

function avatarOf(person: DirectoryPersonItem): string | undefined {
  return person.avatar_url || undefined
}

function secondaryOf(person: DirectoryPersonItem): string | undefined {
  const department = person.department_names?.[person.department_names.length - 1]
  return [department, person.job_title_name].filter(Boolean).join(' · ') || undefined
}

function CompactPersonLabel({ name, src }: { name: string; src?: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%', verticalAlign: 'middle' }}>
      <UserAvatar name={name} src={src} size={18} />
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
    </span>
  )
}

function PersonOptionRow({ person }: { person: DirectoryPersonItem }) {
  return (
    <UserLabel name={person.name} src={avatarOf(person)} secondary={secondaryOf(person)} avatarSize={26} />
  )
}

function mergeById(prev: DirectoryPersonItem[], next: DirectoryPersonItem[]): DirectoryPersonItem[] {
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
 * 远端人员搜索：展开即取首批、关键字 300ms 防抖、滚动到底续载、请求序号防竞态。
 */
function useDirectorySearch() {
  const [options, setOptions] = useState<DirectoryPersonItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)
  const keywordRef = useRef('')
  const offsetRef = useRef(0)
  const loadingRef = useRef(false)

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  const fetchPage = useCallback(async (keyword: string, offset: number) => {
    const seq = ++requestSeq.current
    loadingRef.current = true
    setLoading(true)
    try {
      const page = await fetchUserLookup({ keyword: keyword || undefined, offset, limit: PAGE_SIZE })
      if (seq !== requestSeq.current) return
      const items = page.items.map(toDirectoryPerson)
      setOptions((prev) => (offset === 0 ? items : mergeById(prev, items)))
      setTotal(page.total)
      offsetRef.current = offset + page.items.length
    } catch {
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
  }, [])

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

  const handlePopupScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const el = event.currentTarget
      if (el.scrollHeight - el.scrollTop - el.clientHeight > SCROLL_BOTTOM_THRESHOLD) return
      loadMore()
    },
    [loadMore],
  )

  const clearSearchValue = useCallback(() => setSearchValue(''), [])

  return { options, loading, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue }
}

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

export interface PersonSelectProps {
  /** 已选人员 UUID（hr.employee_profiles.id） */
  value?: string | null
  /** 已保存的姓名快照：未出现在当前列表时用于回显，避免显示 UUID */
  label?: string | null
  /** 已保存的头像快照（可选），缺省走姓名首字兜底 */
  avatarSrc?: string | null
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /** @deprecated HR 目录不区分账号绑定状态，保留仅为兼容旧调用点 */
  feishuBoundOnly?: boolean
  /** @deprecated HR 目录不展示登录账号，保留仅为兼容旧调用点 */
  showUsername?: boolean
  /** Form.Item 会代为注入 onChange；裸用时必填 */
  onChange?: (person: PickedPerson | null) => void
  /** 选中完整人员对象（需要工号/部门等快照时使用） */
  onSelect?: (person: DirectoryPersonItem | null) => void
}

/** 默认导出的统一人员选择器（单选）。 */
export default function PersonSelect({
  value,
  label,
  avatarSrc,
  allowClear = false,
  placeholder = '搜索姓名选择人员',
  disabled,
  onChange,
  onSelect,
}: PersonSelectProps) {
  const { options, loading, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue } =
    useDirectorySearch()
  const [picked, setPicked] = useState<PickedPerson | null>(null)
  const snapshotName = label ?? (picked && picked.id === value ? picked.name : null)

  const displayOptions: DirectoryPersonItem[] = useMemo(() => {
    if (!value || options.some((o) => o.id === value)) return options
    const fallback: DirectoryPersonItem = {
      id: value,
      name: snapshotName || value,
      employee_no: '',
      job_title_name: '',
      department_names: [],
      department_path: [],
      avatar_url: avatarSrc || '',
    }
    return [fallback, ...options]
  }, [options, value, snapshotName, avatarSrc])

  const optionById = useMemo(() => new Map(displayOptions.map((o) => [o.id, o])), [displayOptions])

  const handleChange = (next: string | undefined) => {
    if (!next) {
      setPicked(null)
      onChange?.(null)
      onSelect?.(null)
      return
    }
    const chosen = displayOptions.find((o) => o.id === next)
    if (!chosen) return
    setPicked({ id: chosen.id, name: chosen.name })
    onChange?.({ id: chosen.id, name: chosen.name })
    onSelect?.(chosen)
  }

  return (
    <Select
      showSearch
      allowClear={allowClear}
      disabled={disabled}
      filterOption={false}
      defaultActiveFirstOption={false}
      searchValue={searchValue}
      notFoundContent={loading ? <Spin size="small" /> : '未找到匹配的人员'}
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
        return person ? <PersonOptionRow person={person} /> : (option.label as ReactNode)
      }}
    />
  )
}

export interface PersonMultiSelectProps {
  /** 已选人员 UUID 列表（hr.employee_profiles.id） */
  value?: string[]
  /** 已保存的姓名快照（与 value 顺序一致），未搜索时用于回显 */
  labels?: string[]
  /** 已保存的头像快照（与 value 顺序一致） */
  avatarSrcs?: Array<string | null | undefined>
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /** @deprecated HR 目录不区分账号绑定状态，保留仅为兼容旧调用点 */
  feishuBoundOnly?: boolean
  /** @deprecated HR 目录不展示登录账号，保留仅为兼容旧调用点 */
  showUsername?: boolean
  onChange?: (persons: PickedPerson[]) => void
  onSelectionChange?: (persons: DirectoryPersonItem[]) => void
}

/** 统一人员选择器（多选）。 */
export function PersonMultiSelect({
  value,
  labels,
  avatarSrcs,
  allowClear = true,
  placeholder = '搜索姓名，可多选',
  disabled,
  onChange,
  onSelectionChange,
}: PersonMultiSelectProps) {
  const { options, loading, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue } =
    useDirectorySearch()
  const [pickedList, setPickedList] = useState<PickedPerson[]>([])
  const selectedIds = useMemo(() => value ?? [], [value])
  const pickedNameMap = useMemo(() => new Map(pickedList.map((p) => [p.id, p.name])), [pickedList])
  const labelMap = useMemo(
    () => new Map(selectedIds.map((id, index) => [id, labels?.[index]])),
    [selectedIds, labels],
  )
  const avatarMap = useMemo(
    () => new Map(selectedIds.map((id, index) => [id, avatarSrcs?.[index] ?? undefined])),
    [selectedIds, avatarSrcs],
  )

  const displayOptions: DirectoryPersonItem[] = useMemo(() => {
    const missing = selectedIds
      .filter((id) => !options.some((o) => o.id === id))
      .map(
        (id): DirectoryPersonItem => ({
          id,
          name: labelMap.get(id) || pickedNameMap.get(id) || id,
          employee_no: '',
          job_title_name: '',
          department_names: [],
          department_path: [],
          avatar_url: avatarMap.get(id) || '',
        }),
      )
    return [...missing, ...options]
  }, [selectedIds, options, labelMap, avatarMap, pickedNameMap])

  const optionById = useMemo(() => new Map(displayOptions.map((o) => [o.id, o])), [displayOptions])

  const handleChange = (nextIds: string[]) => {
    const chosen = nextIds
      .map((id) => displayOptions.find((o) => o.id === id))
      .filter((item): item is DirectoryPersonItem => Boolean(item))
    setPickedList(chosen.map((item) => ({ id: item.id, name: item.name })))
    onChange?.(chosen.map((item) => ({ id: item.id, name: item.name })))
    onSelectionChange?.(chosen)
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
      notFoundContent={loading ? <Spin size="small" /> : '未找到匹配的人员'}
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
        return person ? <PersonOptionRow person={person} /> : (option.label as ReactNode)
      }}
    />
  )
}
export { PersonSelect }
