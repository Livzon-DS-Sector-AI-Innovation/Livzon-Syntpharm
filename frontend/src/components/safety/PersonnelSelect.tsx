'use client'

import { useEffect, useRef, useState } from 'react'
import { Select, Spin } from 'antd'
import { searchPersonnel, type PersonnelOption } from '@/lib/api/client/identity'

const SEARCH_DEBOUNCE_MS = 300

export interface PersonnelSelectProps {
  /** 已绑定的系统用户 UUID */
  value?: string | null
  /** 已保存的姓名，用于未搜索时回显（避免直接显示 UUID） */
  label?: string | null
  placeholder?: string
  disabled?: boolean
  onChange: (person: { id: string; name: string } | null) => void
}

/**
 * 系统用户选择器。
 *
 * 台账里的人员字段以 uuid 为准、姓名为展示快照，因此选择后需要同时回写 id 与 name。
 * 搜索走后端 /identity/personnel（姓名模糊匹配，重名用账号/部门区分）。
 */
export default function PersonnelSelect({
  value,
  label,
  placeholder = '搜索姓名/账号选择系统用户',
  disabled,
  onChange,
}: PersonnelSelectProps) {
  const [options, setOptions] = useState<PersonnelOption[]>([])
  const [loading, setLoading] = useState(false)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  const handleSearch = (keyword: string) => {
    if (timerRef.current) clearTimeout(timerRef.current)
    const kw = keyword.trim()
    if (!kw) {
      setOptions([])
      return
    }
    timerRef.current = setTimeout(async () => {
      const seq = ++requestSeq.current
      setLoading(true)
      try {
        const items = await searchPersonnel(kw, 50)
        if (seq === requestSeq.current) setOptions(items)
      } catch {
        if (seq === requestSeq.current) setOptions([])
      } finally {
        if (seq === requestSeq.current) setLoading(false)
      }
    }, SEARCH_DEBOUNCE_MS)
  }

  // 回显：已绑定但未搜索时补一个选项，保证显示姓名而不是 UUID
  const displayOptions: PersonnelOption[] =
    value && !options.some((o) => o.id === value)
      ? [{ id: value, name: label || value }, ...options]
      : options

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
      onSearch={handleSearch}
      onChange={handleChange}
      options={displayOptions.map((o) => ({
        value: o.id,
        label: `${o.name}${o.username ? `（${o.username}）` : ''}${o.department ? ` - ${o.department}` : ''}`,
      }))}
    />
  )
}