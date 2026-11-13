'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Divider, Select, Spin } from 'antd'
import { fetchEmployeeProfiles } from '@/lib/api/client/hr'
import { UserAvatar, UserLabel } from '@/components/common/UserAvatar'
import type { EmployeeProfileListItem } from '@/types/hr'

const SEARCH_DEBOUNCE_MS = 300
const PAGE_SIZE = 50

type Employee = { id: string; name: string; avatar?: string }

export interface RemoteEmployeeSelectProps {
  value?: string | null
  label?: string | null
  avatarSrc?: string | null
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /** Form.Item 注入的受控值回调 */
  onChange?: (value: string | null) => void
  /** 选中回调（Form.Item 会覆盖 onChange，副作用走这里） */
  onSelect?: (employee: Employee | null) => void
}

function toEmployee(item: EmployeeProfileListItem): Employee {
  return { id: item.id, name: item.name, avatar: item.avatar_url || undefined }
}

function mergeById(prev: EmployeeProfileListItem[], next: EmployeeProfileListItem[]): EmployeeProfileListItem[] {
  const seen = new Set(prev.map((item) => item.id))
  const merged = [...prev]
  for (const item of next) {
    if (seen.has(item.id)) continue
    seen.add(item.id)
    merged.push(item)
  }
  return merged
}

export function RemoteEmployeeSelect({
  value,
  label,
  avatarSrc,
  allowClear = false,
  placeholder = '搜索姓名选择员工',
  disabled,
  onChange,
  onSelect,
}: RemoteEmployeeSelectProps) {
  const [options, setOptions] = useState<EmployeeProfileListItem[]>([])
  const [loading, setLoading] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const [picked, setPicked] = useState<Employee | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)
  const keywordRef = useRef('')
  const pageRef = useRef(1)
  const hasMoreRef = useRef(false)
  const loadingRef = useRef(false)

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  const fetchPage = useCallback(async (keyword: string, page: number) => {
    const seq = ++requestSeq.current
    loadingRef.current = true
    setLoading(true)
    try {
      const result = await fetchEmployeeProfiles({
        keyword: keyword || undefined,
        status: '1',
        page,
        page_size: PAGE_SIZE,
      })
      if (seq !== requestSeq.current) return
      setOptions((prev) => (page === 1 ? result.items : mergeById(prev, result.items)))
      pageRef.current = page
      hasMoreRef.current = page * PAGE_SIZE < result.total
    } catch {
      if (seq === requestSeq.current && page === 1) setOptions([])
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
    pageRef.current = 1
    setSearchValue('')
    void fetchPage('', 1)
  }, [fetchPage])

  const handleSearch = useCallback(
    (keyword: string) => {
      setSearchValue(keyword)
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        keywordRef.current = keyword
        pageRef.current = 1
        void fetchPage(keyword, 1)
      }, SEARCH_DEBOUNCE_MS)
    },
    [fetchPage],
  )

  const loadMore = useCallback(() => {
    if (loadingRef.current || !hasMoreRef.current) return
    void fetchPage(keywordRef.current, pageRef.current + 1)
  }, [fetchPage])

  const handlePopupScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const el = event.currentTarget
      if (el.scrollHeight - el.scrollTop - el.clientHeight > 32) return
      loadMore()
    },
    [loadMore],
  )

  const snapshot = picked && picked.id === value ? picked : null
  const selectedName = label || snapshot?.name
  const selectedAvatar = avatarSrc || snapshot?.avatar

  const selectOptions = options.map((item) => {
    const employee = toEmployee(item)
    const secondary = [item.job_title_name, item.department_level1_name, item.department_level2_name]
      .filter(Boolean)
      .join(' · ')
    return {
      value: employee.id,
      label: <UserLabel name={employee.name} src={employee.avatar} secondary={secondary || undefined} avatarSize={26} />,
      employee,
    }
  })

  return (
    <Select
      showSearch
      allowClear={allowClear}
      disabled={disabled}
      placeholder={placeholder}
      filterOption={false}
      value={value ?? undefined}
      searchValue={searchValue}
      onSearch={handleSearch}
      onDropdownVisibleChange={(open) => {
        if (open) reload()
        else setSearchValue('')
      }}
      onPopupScroll={handlePopupScroll}
      onChange={(next: string | undefined, option) => {
        const employee = (option as { employee?: Employee } | undefined)?.employee ?? null
        setPicked(employee)
        onChange?.(next ?? null)
        onSelect?.(employee)
      }}
      options={selectOptions}
      labelRender={() =>
        selectedName ? (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, maxWidth: '100%' }}>
            <UserAvatar name={selectedName} src={selectedAvatar} size={18} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selectedName}</span>
          </span>
        ) : null
      }
      notFoundContent={loading ? <Spin size="small" /> : undefined}
      dropdownRender={(menu) => (
        <>
          {menu}
          {loading && options.length > 0 && (
            <>
              <Divider style={{ margin: '4px 0' }} />
              <div style={{ padding: '6px 0', textAlign: 'center' }}>
                <Spin size="small" />
              </div>
            </>
          )}
        </>
      )}
    />
  )
}
