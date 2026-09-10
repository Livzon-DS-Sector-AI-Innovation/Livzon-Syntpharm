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

  // 仪表盘型视图（主页面）
  return (
    <div 
      style={{ 
        display: 'flex', 
        gap: 16, 
        marginBottom: 24,
        overflowX: 'auto',
        paddingBottom: 4
      }}
    >
      {STATUS_CONFIG.map(({ key, label, color, bg }) => {
        const isActive = statusFilter === key
        const isDimmed = hoveredKey && hoveredKey !== key
        const value = key === '' ? statistics.total : (statistics.by_status[key] || 0)

        return (
          <Card
            key={key}
            hoverable
            onMouseEnter={() => setHoveredKey(key)}
            onMouseLeave={() => setHoveredKey(null)}
            onClick={() => handleClick(key)}
            style={{
              flex: 1,
              minWidth: 140,
              opacity: isDimmed ? 0.5 : 1,
              transform: isActive ? 'translateY(-4px)' : 'none',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              border: isActive ? `2px solid ${color}` : '1px solid #f0f0f0',
              boxShadow: isActive ? `0 8px 24px -8px ${color}40` : 'none',
              borderRadius: 12,
            }}
            styles={{ body: { padding: '20px 16px', textAlign: 'center' } }}
          >
            <Statistic
              title={<span style={{ color: '#8c8c8c', fontSize: 14, fontWeight: 500 }}>{label}</span>}
              value={value}
              valueStyle={{ 
                color, 
                fontSize: 28, 
                fontWeight: 700,
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace'
              }}
            />
            {isActive && (
              <div style={{ marginTop: 8, fontSize: 12, color, fontWeight: 600 }}>
                已筛选
              </div>
            )}
          </Card>
        )
      })}
    </div>
  )
}
