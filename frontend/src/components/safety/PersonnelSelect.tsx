'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Select, Spin } from 'antd'
import { searchPersonnel, type PersonnelOption } from '@/lib/api/client/identity'

const SEARCH_DEBOUNCE_MS = 300

/** 人员搜索公共逻辑：防抖 + 请求序号防竞态（慢响应不覆盖新结果） */
function usePersonnelSearch() {
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

  const handleSearch = useCallback((keyword: string) => {
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
  }, [])

  return { options, loading, handleSearch }
}

function optionLabel(person: PersonnelOption): string {
  return `${person.name}${person.username ? `（${person.username}）` : ''}${person.department ? ` - ${person.department}` : ''}`
}

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
 * 系统用户选择器（单选）。
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
  const { options, loading, handleSearch } = usePersonnelSearch()

  // 回显：已绑定但未搜索时补一个选项，保证显示姓名而不是 UUID
  const displayOptions: PersonnelOption[] =
    value && !options.some((o) => o.id === value) ? [{ id: value, name: label || value }, ...options] : options

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
      options={displayOptions.map((o) => ({ value: o.id, label: optionLabel(o) }))}
    />
  )
}

export interface PersonnelMultiSelectProps {
  /** 已选系统用户 UUID 列表 */
  value?: string[]
  /** 已保存的姓名快照（与 value 顺序一致），未搜索时用于回显 */
  labels?: string[]
  placeholder?: string
  disabled?: boolean
  onChange: (persons: { id: string; name: string }[]) => void
}

/**
 * 系统用户选择器（多选）。
 *
 * 用于「整改负责人」这类多人字段：提交时同时回写 UUID 列表与姓名快照，
 * 保证台账在不额外查用户表的情况下展示姓名。
 */
export function PersonnelMultiSelect({
  value,
  labels,
  placeholder = '搜索姓名/账号，可多选',
  disabled,
  onChange,
}: PersonnelMultiSelectProps) {
  const { options, loading, handleSearch } = usePersonnelSearch()
  const selectedIds = value ?? []

  // 回显：把尚未出现在搜索结果里的已选人员补进来（用姓名快照兜底）
  const missing: PersonnelOption[] = selectedIds
    .filter((id) => !options.some((o) => o.id === id))
    .map((id) => ({ id, name: labels?.[selectedIds.indexOf(id)] || id }) as PersonnelOption)
  const displayOptions: PersonnelOption[] = [...missing, ...options]

  const handleChange = (nextIds: string[]) => {
    const persons = nextIds
      .map((id) => {
        const picked = displayOptions.find((o) => o.id === id)
        if (picked) return { id: picked.id, name: picked.name }
        const fallback = labels?.[selectedIds.indexOf(id)]
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
      onSearch={handleSearch}
      onChange={handleChange}
      options={displayOptions.map((o) => ({ value: o.id, label: optionLabel(o) }))}
    />
  )
}