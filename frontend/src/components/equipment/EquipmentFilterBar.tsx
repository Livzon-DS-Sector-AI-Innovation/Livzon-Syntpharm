'use client'

import { Input, Select, Button } from 'antd'
import { PlusOutlined, SettingOutlined, ImportOutlined, SearchOutlined } from '@ant-design/icons'
import { useEquipmentStore } from '@/stores/equipment'
import { FilterSummary } from './FilterSummary'
import type { EquipmentSortBy, EquipmentSortOrder } from '@/lib/api/equipment-query'
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
    sortBy, sortOrder, onResetSort, invalidSort,
    locations, categories, departments,
    onOpenColumnConfig, onOpenImport, onAddNew,
  } = props

  const {
    statusFilter,
    keyword,
    departments: storeDepartments,
    departmentFilter,
    setDepartmentFilter,
    setStatusFilter,
    setKeyword,
    selectedLocation,
    selectedCategory,
  } = useEquipmentStore()

  // 优先用 store 里的部门；为空时回退到 props 传入（SSR 初始数据兜底）
  const departmentList = storeDepartments.length > 0 ? storeDepartments : departments

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
        value={statusFilter || undefined}
        onChange={(v) => setStatusFilter(v || '')}
        options={STATUS_OPTIONS}
      />
      <Select
        placeholder="归属部门"
        allowClear
        style={{ width: 140, flexShrink: 0 }}
        value={departmentFilter || undefined}
        onChange={(v) => setDepartmentFilter(v || null)}
        options={departmentList.map((d) => ({ label: d.name, value: d.id }))}
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
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        allowClear
      />
      <FilterSummary
        compact
        selectedLocation={selectedLocation}
        selectedCategory={selectedCategory}
        departmentFilter={departmentFilter}
        statusFilter={statusFilter}
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
      <Button type="primary" icon={<PlusOutlined />} onClick={onAddNew}>新增设备</Button>
    </div>
  )
}
