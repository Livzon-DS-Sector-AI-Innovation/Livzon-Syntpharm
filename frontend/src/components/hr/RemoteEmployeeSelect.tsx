'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Divider, Select, Spin } from 'antd'
import { fetchEmployeeProfiles, fetchEmployees } from '@/lib/api/client/hr'
import { UserLabel } from '@/components/common/UserAvatar'
import type { Employee, EmployeeProfileListItem } from '@/types/hr'

const SEARCH_DEBOUNCE_MS = 300
const PAGE_SIZE = 50

export interface RemoteEmployeeOption {
  /** 稳定标识：profiles 源为 employee_profiles.id，employees 源为 hr.employees.id */
  id: string
  name: string
  employee_number: string
  department?: string
  job_title?: string
  avatar?: string
}

export interface RemoteEmployeeSelectProps {
  value?: string | string[] | null
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /**
   * 数据源：
   * - `profiles`（默认）：员工档案（hr.employee_profiles，只读镜像）
   * - `employees`：传统员工表（hr.employees），入职/培训等旧页面使用
   */
  source?: 'profiles' | 'employees'
  /** onChange 返回的字段：`profiles` 恒为 id；`employees` 可选 id 或 employee_number */
  valueKey?: 'id' | 'employee_number'
  mode?: 'single' | 'multiple'
  /** 服务端部门筛选（单部门） */
  department?: string
  /** 服务端部门筛选（多部门，按部门分别取首页后合并） */
  departments?: string[]
  /** 已选值回显（未展开下拉时也能显示姓名） */
  fallbackOptions?: RemoteEmployeeOption[]
  /** Form.Item 注入的受控值回调 */
  onChange?: (value: string | string[] | null) => void
  /** 单选选中回调（Form.Item 会覆盖 onChange，副作用走这里） */
  onSelect?: (employee: RemoteEmployeeOption | null) => void
  /** 多选选中回调，返回完整员工对象，便于同时回填姓名/工号 */
  onSelectionChange?: (employees: RemoteEmployeeOption[]) => void
}

function profileToOption(item: EmployeeProfileListItem): RemoteEmployeeOption {
  return {
    id: item.id,
    name: item.name,
    employee_number: '',
    department: item.department_level2_name || item.department_level1_name || undefined,
    job_title: item.job_title_name || undefined,
    avatar: item.avatar_url || undefined,
  }
}

function employeeToOption(item: Employee): RemoteEmployeeOption {
  return {
    id: item.id,
    name: item.name,
    employee_number: item.employee_number,
    department: item.department || undefined,
    job_title: item.position || undefined,
  }
}

function mergeById(prev: RemoteEmployeeOption[], next: RemoteEmployeeOption[]): RemoteEmployeeOption[] {
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
  allowClear = false,
  placeholder = '搜索姓名选择员工',
  disabled,
  source = 'profiles',
  valueKey = 'id',
  mode = 'single',
  department,
  departments,
  fallbackOptions,
  onChange,
  onSelect,
  onSelectionChange,
}: RemoteEmployeeSelectProps) {
  const [options, setOptions] = useState<RemoteEmployeeOption[]>([])
  const [loading, setLoading] = useState(false)
  const [searchValue, setSearchValue] = useState('')
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const requestSeq = useRef(0)
  const keywordRef = useRef('')
  const pageRef = useRef(1)
  const hasMoreRef = useRef(false)
  const loadingRef = useRef(false)

  const deptList = useMemo(() => {
    if (departments && departments.length > 0) return departments
    return department ? [department] : []
  }, [department, departments])

  const optionValue = useCallback(
    (employee: RemoteEmployeeOption) => (valueKey === 'employee_number' ? employee.employee_number : employee.id),
    [valueKey],
  )

  useEffect(
    () => () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    },
    [],
  )

  const fetchProfilesPage = useCallback(
    async (keyword: string, page: number) => {
      const result = await fetchEmployeeProfiles({
        keyword: keyword || undefined,
        status: '1',
        department_id: deptList.length === 1 ? deptList[0] : undefined,
        page,
        page_size: PAGE_SIZE,
      })
      return {
        items: result.items.map(profileToOption),
        total: result.total,
      }
    },
    [deptList],
  )

  const fetchEmployeesPage = useCallback(
    async (keyword: string, page: number) => {
      if (deptList.length > 1) {
        // 后端只支持单部门筛选；多部门时按部门取首页合并（与旧页面行为一致）。
        const pages = await Promise.all(
          deptList.map((dept) =>
            fetchEmployees({ department: dept, keyword: keyword || undefined, page: 1, page_size: PAGE_SIZE }),
          ),
        )
        const items = pages.flatMap((res) => ((res.data ?? []) as Employee[]).map(employeeToOption))
        return { items: mergeById([], items), total: items.length }
      }
      const res = await fetchEmployees({
        department: deptList[0],
        keyword: keyword || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      return {
        items: ((res.data ?? []) as Employee[]).map(employeeToOption),
        total: res.meta?.total ?? 0,
      }
    },
    [deptList],
  )

  const fetchPage = useCallback(
    async (keyword: string, page: number) => {
      const seq = ++requestSeq.current
      loadingRef.current = true
      setLoading(true)
      try {
        const result =
          source === 'profiles' ? await fetchProfilesPage(keyword, page) : await fetchEmployeesPage(keyword, page)
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
    },
    [fetchEmployeesPage, fetchProfilesPage, source],
  )

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
    if (deptList.length > 1) return
    void fetchPage(keywordRef.current, pageRef.current + 1)
  }, [deptList.length, fetchPage])

  const handlePopupScroll = useCallback(
    (event: React.UIEvent<HTMLDivElement>) => {
      const el = event.currentTarget
      if (el.scrollHeight - el.scrollTop - el.clientHeight > 32) return
      loadMore()
    },
    [loadMore],
  )

  const allOptions = useMemo(() => {
    if (!fallbackOptions || fallbackOptions.length === 0) return options
    return mergeById(fallbackOptions, options)
  }, [fallbackOptions, options])

  const selectedValues = useMemo(() => {
    if (mode === 'multiple') return Array.isArray(value) ? value : value ? [value] : []
    return value ? [String(value)] : []
  }, [mode, value])

  const selectOptions = allOptions.map((employee) => {
    const secondary = [employee.job_title, employee.department].filter(Boolean).join(' · ')
    return {
      value: optionValue(employee),
      label: (
        <UserLabel
          name={employee.name}
          src={employee.avatar}
          secondary={secondary || undefined}
          avatarSize={26}
        />
      ),
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
      mode={mode === 'multiple' ? 'multiple' : undefined}
      value={mode === 'multiple' ? selectedValues : (value ?? undefined)}
      searchValue={searchValue}
      onSearch={handleSearch}
      onDropdownVisibleChange={(open) => {
        if (open) reload()
        else setSearchValue('')
      }}
      onPopupScroll={handlePopupScroll}
      onChange={(next: string | string[] | undefined, option) => {
        if (mode === 'multiple') {
          const nextValues = Array.isArray(next) ? next : next ? [next] : []
          const selectedOptions = Array.isArray(option) ? option : option ? [option] : []
          const employees = selectedOptions
            .map((item) => (item as { employee?: RemoteEmployeeOption } | undefined)?.employee)
            .filter((item): item is RemoteEmployeeOption => Boolean(item))
          onChange?.(nextValues)
          onSelectionChange?.(employees)
          return
        }
        const employee = (option as { employee?: RemoteEmployeeOption } | undefined)?.employee ?? null
        onChange?.(next ?? null)
        onSelect?.(employee)
      }}
      options={selectOptions}
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
