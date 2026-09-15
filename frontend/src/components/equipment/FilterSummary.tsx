'use client'

import { Button } from 'antd'
import { EquipmentCategory, Location } from '@/types/equipment'
import type { DepartmentOption } from '@/lib/api/client/equipment'
import type { EquipmentSortBy, EquipmentSortOrder } from '@/lib/api/equipment-query'
import { formatSortLabel, isDefaultSort } from './sorting'

interface FilterSummaryProps {
  selectedLocation: string | null
  selectedCategory: string | null
  departmentFilter: string | null
  statusFilter: string
  sortBy: EquipmentSortBy
  sortOrder: EquipmentSortOrder
  onResetSort: () => void
  /** URL 里被丢弃的非法排序参数（D12：不得静默回落，需让用户看见） */
  invalidSort?: string[]
  total: number
  locations: Location[]
  categories: EquipmentCategory[]
  departments: DepartmentOption[]
  /** 紧凑模式：渲染为筛选条右侧的 inline 标签组，无外壳、无总数、无「恢复默认」 */
  compact?: boolean
}

// 递归查找树节点名称
function findNodeName(nodes: Location[] | EquipmentCategory[] | undefined, id: string): string | null {
  if (!nodes) return null
  
  for (const node of nodes) {
    if (node.id === id) {
      return node.name
    }
    if (node.children && node.children.length > 0) {
      const found = findNodeName(node.children, id)
      if (found) return found
    }
  }
  return null
}

export function FilterSummary({
  selectedLocation,
  selectedCategory,
  departmentFilter,
  statusFilter,
  sortBy,
  sortOrder,
  onResetSort,
  invalidSort = [],
  total,
  locations,
  categories,
  departments,
  compact = false,
}: FilterSummaryProps) {
  // 检查是否有任何筛选条件激活
  const hasFilters = selectedLocation || selectedCategory || departmentFilter || statusFilter
  const isCustomSort = !isDefaultSort(sortBy, sortOrder)
  const hasInvalidSort = invalidSort.length > 0

  // 无筛选但改了排序、或 URL 带了非法排序参数时同样要渲染：这里必须始终是「当前查询状态」的唯一出口
  if (!hasFilters && !isCustomSort && !hasInvalidSort) {
    return null
  }

  // 获取名称
  const locationName = selectedLocation ? findNodeName(locations, selectedLocation) : null
  const categoryName = selectedCategory ? findNodeName(categories, selectedCategory) : null
  const departmentName = departmentFilter
    ? departments.find(d => d.id === departmentFilter)?.name
    : null

  // 共享标签数据：default 与 compact 复用同一份，避免两份色/逻辑漂移
  const tags: Array<{ key: string; label: string; color: string; bg: string }> = []

  if (locationName) {
    tags.push({ key: 'location', label: `📍 ${locationName}`, color: '#7b3ff2', bg: '#e6e0f5' })
  }

  if (categoryName) {
    tags.push({ key: 'category', label: `🏷️ ${categoryName}`, color: '#1aae39', bg: '#d9f3e1' })
  }

  if (departmentName) {
    tags.push({ key: 'department', label: `👥 ${departmentName}`, color: '#dd5b00', bg: '#ffe8d4' })
  }

  if (statusFilter) {
    const statusColors: Record<string, { color: string; bg: string }> = {
      '在用': { color: '#1aae39', bg: '#d9f3e1' },
      '备用': { color: '#7b3ff2', bg: '#e6e0f5' },
      '维修中': { color: '#dd5b00', bg: '#ffe8d4' },
      '停用': { color: '#787671', bg: '#f0eeec' },
      '报废': { color: '#e03131', bg: '#fde0ec' },
    }
    const colors = statusColors[statusFilter] || { color: '#5d5b54', bg: '#f0eeec' }
    tags.push({ key: 'status', label: `状态: ${statusFilter}`, color: colors.color, bg: colors.bg })
  }

  if (isCustomSort) {
    tags.push({ key: 'sort', label: `排序: ${formatSortLabel(sortBy, sortOrder)}`, color: '#5645d4', bg: '#ede9f8' })
  }

  // 紧凑模式：筛选条右侧 inline 标签组，无外壳、无总数、无「恢复默认」。
  // max-width 防止标签挤掉右侧操作按钮；溢出由 overflow:hidden 截断。
  if (compact) {
    return (
      <div
        className="equipment-filter-summary-compact"
        style={{
          display: 'flex',
          gap: 4,
          alignItems: 'center',
          flexWrap: 'nowrap',
          overflow: 'hidden',
          maxWidth: 480,
          minWidth: 0,
        }}
      >
        {tags.map((t) => (
          <span
            key={t.key}
            style={{
              background: t.bg,
              color: t.color,
              padding: '1px 8px',
              borderRadius: 10,
              fontSize: 12,
              fontWeight: 500,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            {t.label}
          </span>
        ))}
        {hasInvalidSort ? (
          <span
            key="invalid"
            style={{
              background: '#fde0ec',
              color: '#e03131',
              padding: '1px 8px',
              borderRadius: 10,
              fontSize: 12,
              fontWeight: 500,
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            排序参数无效: {invalidSort.join('、')}
          </span>
        ) : null}
      </div>
    )
  }

  // 默认（block）模式：保留旧的卡片外壳与「恢复默认」/「共 N 台」尾巴
  return (
    <div
      style={{
        marginBottom: 16,
        padding: '8px 16px',
        background: '#f7f6f4',
        borderRadius: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 14,
        flexWrap: 'wrap',
      }}
    >
      {hasFilters ? <span style={{ color: '#5d5b54', fontWeight: 500 }}>📍 当前筛选：</span> : null}

      {tags.map((t) => (
        <span
          key={t.key}
          style={{
            background: t.bg,
            color: t.color,
            padding: '2px 10px',
            borderRadius: 4,
            fontWeight: 500,
            fontSize: 13,
          }}
        >
          {t.label}
        </span>
      ))}

      {isCustomSort ? (
        <Button type="link" size="small" onClick={onResetSort} style={{ padding: '0 4px', fontSize: 13 }}>
          恢复默认
        </Button>
      ) : null}

      {hasInvalidSort ? (
        <span
          style={{
            background: '#fde0ec',
            color: '#e03131',
            padding: '2px 10px',
            borderRadius: 4,
            fontWeight: 500,
            fontSize: 13,
          }}
        >
          {`排序参数无效：${invalidSort.join('、')}，已按 ${formatSortLabel(sortBy, sortOrder)} 展示`}
        </span>
      ) : null}

      <span
        style={{
          color: '#5d5b54',
          marginLeft: 'auto',
          fontWeight: 500,
        }}
      >
        共 <strong style={{ color: '#1a1a1a', fontSize: 15 }}>{total}</strong> 台设备
      </span>
    </div>
  )
}
