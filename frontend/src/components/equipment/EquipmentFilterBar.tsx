'use client'

import { useState } from 'react'
import { Input, Select, Button } from 'antd'
import { PlusOutlined, SettingOutlined, ImportOutlined, SearchOutlined } from '@ant-design/icons'
import { FilterSummary } from './FilterSummary'
import type { EquipmentFilterState, EquipmentSortBy, EquipmentSortOrder } from '@/lib/api/equipment-query'
import type { EquipmentCategory, Location } from '@/types/equipment'
import type { DepartmentOption } from '@/lib/api/client/equipment'

/**
 * 设备台账筛选条。从 EquipmentTable 中外移到工具栏后，所有筛选交互集中在一行：
 * 状态 · 部门 · 关键词 · [flex:1 spacer] · inline 筛选摘要 · 列配置 · 导入 · 新增。
 *
 * 紧凑模式下的 FilterSummary 在没有筛选/排序/非法参数时返回 null，因此未筛选时整条占位
 * 自然塌缩成 [selects, input, spacer, buttons]。
 */
interface EquipmentFilterBarProps {
  /** 当前 URL 上的筛选状态（空串 = 不限） */
  filters: EquipmentFilterState
  /** 任一筛选变化都由入口统一写回 URL，并连带把页码归 1 */
  onFiltersChange: (patch: Partial<EquipmentFilterState>) => void
  sortBy: EquipmentSortBy
  sortOrder: EquipmentSortOrder
  onResetSort: () => void
  invalidSort: string[]
  locations: Location[]
  categories: EquipmentCategory[]
  departments: DepartmentOption[]
  onOpenColumnConfig: () => void
  onOpenImport: () => void
  onAddNew: () => void
}

const STATUS_OPTIONS = [
  { label: '在用', value: '在用' },
  { label: '备用', value: '备用' },
  { label: '维修中', value: '维修中' },
  { label: '停用', value: '停用' },
  { label: '报废', value: '报废' },
]

export function EquipmentFilterBar(props: EquipmentFilterBarProps) {
  const {
    filters, onFiltersChange,
    sortBy, sortOrder, onResetSort, invalidSort,
    locations, categories, departments,
    onOpenColumnConfig, onOpenImport, onAddNew,
  } = props

  // 关键词在本地草稿里编辑，回车/失焦/清空才落进 URL：
  // 直接拿 URL 当受控值会让每次按键都等一次路由跳转，输入会丢字。
  const [keywordDraft, setKeywordDraft] = useState(filters.keyword)
  const [keywordInUrl, setKeywordInUrl] = useState(filters.keyword)
  if (filters.keyword !== keywordInUrl) {
    // 前进/后退等外部改动 URL 时，在渲染期把草稿对齐到 URL，省掉一次 useEffect 同步
    setKeywordInUrl(filters.keyword)
    setKeywordDraft(filters.keyword)
  }

  const commitKeyword = (value: string) => {
    const next = value.trim()
    setKeywordInUrl(next)
    setKeywordDraft(next)
    if (next !== filters.keyword) onFiltersChange({ keyword: next })
  }

  return (
    <div
      className="equipment-filter-bar"
      style={{
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        flexWrap: 'wrap',
        rowGap: 8,
      }}
    >
      <Select
        placeholder="设备状态"
        allowClear
        style={{ width: 120, flexShrink: 0 }}
        value={filters.status || undefined}
        onChange={(v) => onFiltersChange({ status: v ?? '' })}
        options={STATUS_OPTIONS}
      />
      <Select
        placeholder="归属部门"
        allowClear
        style={{ width: 140, flexShrink: 0 }}
        value={filters.department_id || undefined}
        onChange={(v) => onFiltersChange({ department_id: v ?? '' })}
        options={departments.map((d) => ({ label: d.name, value: d.id }))}
      />
      <Input
        placeholder="搜索设备编号或名称"
        prefix={<SearchOutlined style={{ color: '#a4a097' }} />}
        style={{ 
          minWidth: 200, 
          maxWidth: 320, 
          flex: '1 1 auto',
          flexShrink: 1 
        }}
        value={keywordDraft}
        onChange={(e) => {
          const value = e.target.value
          setKeywordDraft(value)
          // allowClear 的清空没有 blur/回车可依，当场提交
          if (!value) commitKeyword('')
        }}
        onPressEnter={(e) => {
          // 中文输入法候选确认同样是 Enter，此时提交会把未上屏的拼音当成关键词
          if (e.nativeEvent.isComposing) return
          commitKeyword(e.currentTarget.value)
        }}
        onBlur={(e) => commitKeyword(e.currentTarget.value)}
        allowClear
      />
      <FilterSummary
        compact
        selectedLocation={filters.location_id}
        selectedCategory={filters.category_id}
        departmentFilter={filters.department_id}
        statusFilter={filters.status}
        sortBy={sortBy}
        sortOrder={sortOrder}
        onResetSort={onResetSort}
        invalidSort={invalidSort}
        total={0}
        locations={locations}
        categories={categories}
        departments={departments}
      />
      <div style={{ flex: '1 1 100%', minWidth: 0, order: 5 }} />
      <Button icon={<SettingOutlined />} onClick={onOpenColumnConfig}>列配置</Button>
      <Button icon={<ImportOutlined />} onClick={onOpenImport}>导入</Button>
      <Button icon={<PlusOutlined />} onClick={onAddNew}>新增设备</Button>
    </div>
  )
}
