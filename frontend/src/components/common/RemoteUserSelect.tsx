'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Divider, Select, Spin } from 'antd'
import type { ReactNode } from 'react'
import { searchPersonnel } from '@/lib/api/client/identity'
import { UserAvatar, UserLabel } from '@/components/common/UserAvatar'

/**
 * 系统人员下拉（全站唯一实现，参照隐患台账 `fix/liujunguang_hazard-ledger`）：
 *
 * - 展开即取首批用户（无需先输关键字，新建账号后重新展开即可见）
 * - 关键字走 300ms 防抖的服务端搜索，并重置分页（未加载过的用户也能搜到）
 * - 下拉滚动到底自动续载下一页，不需要手动点「加载更多」
 * - 请求序号防竞态：慢响应不会覆盖新关键字的结果
 * - 选项「头像 + 姓名 + 部门」，已选标签「小头像 + 姓名」
 *
 * 与隐患模块的差异：这里额外支持多选（`mode="multiple"`），并用 `fallbackOptions`
 * 承载已保存值的姓名/头像快照，因此表单只需存 UUID，不必再维护平行的姓名数组。
 */

const SEARCH_DEBOUNCE_MS = 300
/** 每页条数：展开首屏 50 条，够用又不会拖慢响应 */
const PAGE_SIZE = 50
/** 触底判定余量：留 32px 避免亚像素误差导致永远触发不到 */
const SCROLL_BOTTOM_THRESHOLD = 32

/** 组件内部统一的行结构：不伪造生成契约的必填字段 */
interface PersonRow {
  id: string
  name: string
  username?: string | null
  department?: string | null
  avatar?: string | null
}

export interface RemoteUserSelectOption {
  value: string
  label: string
  avatar?: string | null
  /** 次级文案（部门），仅用于回显选项的展示 */
  description?: string | null
}

export interface RemoteUserSelectProps {
  /** 已选用户 UUID（多选为 UUID 数组） */
  value?: string | string[] | null
  /**
   * 单选回写 string | null，多选回写 string[]。
   * 第二参是本次选中的行（单选对象、多选数组），供仍要写姓名快照的老表单使用。
   */
  onChange?: (
    value: string | string[] | null,
    picked: RemoteUserSelectOption | RemoteUserSelectOption[] | null,
  ) => void
  /** 单选（默认）或多选 */
  mode?: 'single' | 'multiple'
  /** 单选已保存值的姓名快照（等价于单条 fallbackOptions），未出现在结果里时用于回显 */
  label?: string | null
  /** 单选已保存值的头像快照（可选），缺省走姓名首字兜底 */
  avatarSrc?: string | null
  placeholder?: string
  /** 默认允许清空 */
  allowClear?: boolean
  disabled?: boolean
  /** 已保存值的姓名/头像快照：未出现在当前列表时用于回显，避免显示 UUID */
  fallbackOptions?: RemoteUserSelectOption[]
  /** true = 只列已绑定飞书身份的账号（要发通知的场景）；默认 false 覆盖本地账号 */
  feishuBoundOnly?: boolean
  /** 选项次级文案附带登录账号（重名场景用于区分） */
  showUsername?: boolean
  style?: React.CSSProperties
}

/** 头像取值：服务端可能只给 thumb 或 url，统一按 thumb → url 回退 */
function avatarOf(person: { avatar_thumb?: string | null; avatar_url?: string | null }): string | undefined {
  return person.avatar_thumb || person.avatar_url || undefined
}

/** 已选标签里的紧凑头像（标签内不放部门，避免 tags 高度撑高） */
function CompactPersonLabel({ name, src }: { name: string; src?: string }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%', verticalAlign: 'middle' }}>
      <UserAvatar name={name} src={src} size={18} />
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
    </span>
  )
}

/** 下拉面板中的富选项：头像 + 姓名 +（账号 ·）部门 */
function PersonOptionRow({ person, showUsername }: { person: PersonRow; showUsername: boolean }) {
  const secondary = [showUsername ? person.username : null, person.department].filter(Boolean).join(' · ')
  return <UserLabel name={person.name} src={person.avatar} secondary={secondary || undefined} avatarSize={26} />
}

/** 按 id 去重合并：分页追加时避免同一用户出现两次 */
function mergeById(prev: PersonRow[], next: PersonRow[]): PersonRow[] {
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

/** 下拉底部只在请求中显示加载提示；没有更多数据时什么都不渲染 */
function ListLoadingFooter({ loading, hasRows }: { loading: boolean; hasRows: boolean }) {
  if (!loading || !hasRows) return null
  return (
    <>
      <Divider style={{ margin: '4px 0' }} />
      <div style={{ padding: '6px 0', textAlign: 'center' }}>
        <Spin size="small" />
      </div>
    </>
  )
}

/**
 * 远端人员搜索状态机：首屏、搜索、滚动续载共用一条分页链路。
 * 失败只影响列表本身，不向表单层抛错；首屏失败允许再次展开重试。
 */
function useRemotePersonnel(feishuBoundOnly: boolean) {
  const [rows, setRows] = useState<PersonRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)
  // 当前生效的关键字与已消费的分页游标（翻页/搜索都按它取下一页）
  const keywordRef = useRef('')
  const offsetRef = useRef(0)
  // 滚动是高频回调，用 ref 做请求闸门，避免 state 闭包滞后导致连发
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
        const next: PersonRow[] = page.items.map((item) => ({
          id: item.id,
          name: item.name,
          username: item.username,
          department: item.department,
          avatar: avatarOf(item),
        }))
        setRows((prev) => (offset === 0 ? next : mergeById(prev, next)))
        setTotal(page.total)
        setFailed(false)
        offsetRef.current = offset + next.length
      } catch {
        // 首屏失败时清空列表（可再次展开重试），追加失败保留已有结果
        if (seq === requestSeq.current) {
          setFailed(true)
          if (offset === 0) {
            setRows([])
            setTotal(0)
          }
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
    if (rows.length >= total) return
    void fetchPage(keywordRef.current, offsetRef.current)
  }, [fetchPage, rows.length, total])

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

  return { rows, loading, failed, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue }
}

/**
 * 系统人员下拉：头像 + 远端搜索 + 滚动续载。
 *
 * 受控用法：`value` 是 UUID（多选为 UUID 数组），`onChange` 只回写 UUID；
 * 姓名与头像由 `fallbackOptions` 提供快照，保证已保存值在未展开下拉时也能正常显示。
 */
export function RemoteUserSelect({
  value,
  onChange,
  mode = 'single',
  label,
  avatarSrc,
  placeholder = '搜索姓名选择系统用户',
  allowClear = true,
  disabled,
  fallbackOptions,
  feishuBoundOnly = false,
  showUsername = false,
  style,
}: RemoteUserSelectProps) {
  const multiple = mode === 'multiple'
  const { rows, loading, failed, searchValue, reload, handleSearch, handlePopupScroll, clearSearchValue } =
    useRemotePersonnel(feishuBoundOnly)

  const selectedIds = useMemo<string[]>(() => {
    if (multiple) return Array.isArray(value) ? value : []
    return typeof value === 'string' && value ? [value] : []
  }, [multiple, value])

  const fallbackById = useMemo(() => {
    const map = new Map<string, PersonRow>()
    for (const option of fallbackOptions ?? []) {
      map.set(option.value, {
        id: option.value,
        name: option.label,
        department: option.description ?? null,
        avatar: option.avatar ?? undefined,
      })
    }
    // 单选便捷快照：表单只存 UUID 时，用 label/avatarSrc 保证收起状态也显示姓名与头像
    const singleId = multiple ? null : selectedIds[0]
    if (singleId && (label || avatarSrc) && !map.has(singleId)) {
      map.set(singleId, { id: singleId, name: label || singleId, avatar: avatarSrc ?? undefined })
    }
    return map
  }, [fallbackOptions, multiple, selectedIds, label, avatarSrc])

  // 回显：已保存但不在当前结果里的人补到最前面（用快照显示姓名与头像）
  const displayRows = useMemo<PersonRow[]>(() => {
    const known = new Set(rows.map((row) => row.id))
    const missing: PersonRow[] = []
    for (const id of selectedIds) {
      if (known.has(id)) continue
      missing.push(fallbackById.get(id) ?? { id, name: '未知人员' })
    }
    return missing.length > 0 ? [...missing, ...rows] : rows
  }, [rows, selectedIds, fallbackById])

  const rowById = useMemo(() => new Map(displayRows.map((row) => [row.id, row])), [displayRows])

  /** 把内部行转成对外的选项快照，供需要姓名/部门的老表单直接使用 */
  const toOption = (row: PersonRow): RemoteUserSelectOption => ({
    value: row.id,
    label: row.name,
    avatar: row.avatar ?? undefined,
    description: row.department ?? undefined,
  })

  const handleChange = (next: string | string[] | undefined) => {
    if (multiple) {
      const ids = Array.isArray(next) ? next : []
      onChange?.(
        ids,
        ids.map((id) => {
          const row = rowById.get(id)
          return row ? toOption(row) : { value: id, label: id }
        }),
      )
      return
    }
    const id = typeof next === 'string' && next ? next : null
    const row = id ? rowById.get(id) : undefined
    onChange?.(id, row ? toOption(row) : null)
  }

  return (
    <Select
      mode={multiple ? 'multiple' : undefined}
      showSearch
      allowClear={allowClear}
      disabled={disabled}
      filterOption={false}
      defaultActiveFirstOption={false}
      /* 下拉按内容宽度展开：窄表单里「头像 + 姓名 + 部门」不会被 select 宽度挤成截断 */
      popupMatchSelectWidth={false}
      searchValue={searchValue}
      notFoundContent={
        loading ? <Spin size="small" /> : failed ? '人员加载失败，重新展开可重试' : '未找到匹配的系统用户'
      }
      placeholder={placeholder}
      style={{ width: '100%', ...style }}
      value={multiple ? selectedIds : (selectedIds[0] ?? undefined)}
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
          <ListLoadingFooter loading={loading} hasRows={displayRows.length > 0} />
        </>
      )}
      options={displayRows.map((row) => ({
        value: row.id,
        label: <CompactPersonLabel name={row.name} src={row.avatar ?? undefined} />,
      }))}
      optionRender={(option): ReactNode => {
        const row = rowById.get(String(option.value))
        return row ? <PersonOptionRow person={row} showUsername={showUsername} /> : (option.label as ReactNode)
      }}
    />
  )
}

/** 多选回写的人选结构（与 `lib/utils/form-person` 的 `PickedPerson` 一致） */
export interface PickedPerson {
  id: string
  name: string
  avatar?: string | null
}

export interface RemoteUserMultiSelectProps {
  /** 已选用户 UUID 列表 */
  value?: string[]
  /** 已保存的姓名快照（与 value 顺序一致），未搜索时用于回显，避免显示 UUID */
  labels?: string[]
  /** 已保存的头像快照（与 value 顺序一致），缺省走姓名首字兜底 */
  avatarSrcs?: Array<string | null | undefined>
  feishuBoundOnly?: boolean
  showUsername?: boolean
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  style?: React.CSSProperties
  /** 回写人选数组；表单侧用 `toPersonIds` 折回 UUID */
  onChange?: (persons: PickedPerson[]) => void
}

/**
 * 远端人员多选：与单选共用同一套取数逻辑（50 条一页、滚动续载、服务端搜索），
 * 受控值为 UUID 数组，姓名/头像快照按位置由 `labels`/`avatarSrcs` 传入。
 */
export function RemoteUserMultiSelect({ value, labels, avatarSrcs, onChange, ...rest }: RemoteUserMultiSelectProps) {
  const fallbackOptions = useMemo<RemoteUserSelectOption[]>(
    () =>
      (value ?? []).map((id, index) => ({
        value: id,
        label: labels?.[index] ?? id,
        avatar: avatarSrcs?.[index] ?? undefined,
      })),
    [value, labels, avatarSrcs],
  )

  return (
    <RemoteUserSelect
      {...rest}
      mode="multiple"
      value={value}
      fallbackOptions={fallbackOptions}
      onChange={(next, picked) => {
        const ids = Array.isArray(next) ? next : next ? [next] : []
        const chosen = Array.isArray(picked) ? picked : picked ? [picked] : []
        const byId = new Map(chosen.map((item) => [item.value, item]))
        onChange?.(
          ids.map((id) => {
            const option = byId.get(id)
            return { id, name: option?.label ?? id, avatar: option?.avatar ?? null }
          }),
        )
      }}
    />
  )
}

export default RemoteUserSelect