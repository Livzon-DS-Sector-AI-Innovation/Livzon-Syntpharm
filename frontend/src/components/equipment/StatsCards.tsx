'use client'

import { Card, Statistic } from 'antd'
import { EquipmentStatistics, EquipmentStatus } from '@/types/equipment/generated-bridge'
import { useEquipmentStore } from '@/stores/equipment'
import { useState } from 'react'

interface StatsCardsProps {
  statistics: EquipmentStatistics
  compact?: boolean
}

// 定义状态配置：包含颜色、标签和图标语义
const STATUS_CONFIG = [
  { key: '' as const, label: '总数', color: '#1a1a1a', bg: '#f5f5f5' },
  { key: '在用' as EquipmentStatus, label: '在用', color: '#10b981', bg: '#ecfdf5' },
  { key: '维修中' as EquipmentStatus, label: '维修中', color: '#f59e0b', bg: '#fffbeb' },
  { key: '停用' as EquipmentStatus, label: '停用', color: '#64748b', bg: '#f8fafc' },
  { key: '报废' as EquipmentStatus, label: '报废', color: '#ef4444', bg: '#fef2f2' },
]

export function StatsCards({ statistics, compact = false }: StatsCardsProps) {
  const { statusFilter, setStatusFilter } = useEquipmentStore()
  const [hoveredKey, setHoveredKey] = useState<string | null>(null)

  const handleClick = (status: EquipmentStatus | '') => {
    setStatusFilter(status)
  }

  // 紧凑型视图（用于导入弹窗等狭小空间）
  if (compact) {
    return (
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {STATUS_CONFIG.map(({ key, label, color }) => {
          const isActive = statusFilter === key
          const value = key === '' ? statistics.total : (statistics.by_status[key] || 0)
          return (
            <div
              key={key}
              onClick={() => handleClick(key)}
              style={{
                padding: '4px 12px',
                borderRadius: 20,
                background: isActive ? color : 'transparent',
                border: `1px solid ${isActive ? color : '#e5e7eb'}`,
                color: isActive ? '#fff' : '#6b7280',
                fontSize: 12,
                fontWeight: isActive ? 600 : 500,
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
            >
              {label}: <span style={{ fontWeight: 700 }}>{value}</span>
            </div>
          )
        })}
      </div>
    )
  }

  // 仪表盘型视图（主页面）- 大气舒展风格
  return (
    <div 
      style={{ 
        display: 'flex', 
        gap: 12,
        width: '100%',
      }}
    >
      {STATUS_CONFIG.map(({ key, label, color, bg }) => {
        const isActive = statusFilter === key
        const isDimmed = hoveredKey && hoveredKey !== key
        const value = key === '' ? statistics.total : (statistics.by_status[key] || 0)

        return (
          <div
            key={key}
            onMouseEnter={() => setHoveredKey(key)}
            onMouseLeave={() => setHoveredKey(null)}
            onClick={() => handleClick(key)}
            style={{
              flex: 1,
              minWidth: 0,
              padding: '10px 16px',
              background: isActive ? bg : '#FAFAF9',
              border: isActive ? `2px solid ${color}` : '1px solid #E7E5E4',
              borderRadius: 6,
              cursor: 'pointer',
              opacity: isDimmed ? 0.6 : 1,
              transition: 'all 0.2s ease',
              textAlign: 'center',
            }}
          >
            <div style={{ 
              fontSize: 12, 
              color: isActive ? color : '#78716C',
              fontWeight: 500,
              marginBottom: 4,
              letterSpacing: '0.02em',
            }}>
              {label}
            </div>
            <div style={{ 
              fontSize: 22, 
              fontWeight: 700, 
              color: isActive ? color : '#1C1917',
              lineHeight: 1,
              fontFamily: 'ui-monospace, SF Mono, Menlo, monospace',
            }}>
              {value.toLocaleString()}
            </div>
          </div>
        )
      })}
    </div>
  )
}

