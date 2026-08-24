'use client'

import { EquipmentCategory, Location } from '@/types/equipment'
import type { DepartmentOption } from '@/lib/api/client/equipment'

interface FilterSummaryProps {
  selectedLocation: string | null
  selectedCategory: string | null
  departmentFilter: string | null
  statusFilter: string
  total: number
  locations: Location[]
  categories: EquipmentCategory[]
  departments: DepartmentOption[]
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
  total,
  locations,
  categories,
  departments,
}: FilterSummaryProps) {
  // 检查是否有任何筛选条件激活
  const hasFilters = selectedLocation || selectedCategory || departmentFilter || statusFilter
  
  if (!hasFilters) {
    return null
  }

  // 获取名称
  const locationName = selectedLocation ? findNodeName(locations, selectedLocation) : null
  const categoryName = selectedCategory ? findNodeName(categories, selectedCategory) : null
  const departmentName = departmentFilter 
    ? departments.find(d => d.id === departmentFilter)?.name 
    : null

  // 构建筛选标签
  const filters: Array<{ label: string; color: string; bg: string }> = []
  
  if (locationName) {
    filters.push({
      label: `📍 ${locationName}`,
      color: '#7b3ff2',
      bg: '#e6e0f5',
    })
  }
  
  if (categoryName) {
    filters.push({
      label: `🏷️ ${categoryName}`,
      color: '#1aae39',
      bg: '#d9f3e1',
    })
  }
  
  if (departmentName) {
    filters.push({
      label: `👥 ${departmentName}`,
      color: '#dd5b00',
      bg: '#ffe8d4',
    })
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
    filters.push({
      label: `状态: ${statusFilter}`,
      color: colors.color,
      bg: colors.bg,
    })
  }

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
      <span style={{ color: '#5d5b54', fontWeight: 500 }}>📍 当前筛选：</span>
      
      {filters.map((filter, index) => (
        <span
          key={index}
          style={{
            background: filter.bg,
            color: filter.color,
            padding: '2px 10px',
            borderRadius: 4,
            fontWeight: 500,
            fontSize: 13,
          }}
        >
          {filter.label}
        </span>
      ))}
      
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
