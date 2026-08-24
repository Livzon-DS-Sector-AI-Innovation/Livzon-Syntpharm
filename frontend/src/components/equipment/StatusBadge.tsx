'use client'

import { EquipmentStatus } from '@/types/equipment/generated-bridge'

interface StatusBadgeProps {
  status: EquipmentStatus
}

const statusBadgeMap: Record<EquipmentStatus, { icon: string; color: string; bg: string; label: string }> = {
  '在用':   { icon: '🟢', color: '#10b981', bg: '#d1fae5', label: '运行中' },
  '备用':   { icon: '🔵', color: '#6366f1', bg: '#e0e7ff', label: '待命' },
  '维修中': { icon: '🟠', color: '#f97316', bg: '#ffedd5', label: '维护' },
  '停用':   { icon: '⚪', color: '#94a3b8', bg: '#f1f5f9', label: '离线' },
  '报废':   { icon: '🔴', color: '#ef4444', bg: '#fee2e2', label: '已报废' },
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusBadgeMap[status] || { 
    icon: '⚪', 
    color: '#94a3b8', 
    bg: '#f1f5f9', 
    label: status 
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '4px 8px',
        borderRadius: 12,
        backgroundColor: config.bg,
        color: config.color,
        fontSize: 12,
        fontWeight: 500,
        whiteSpace: 'nowrap',
      }}
    >
      <span>{config.icon}</span>
      <span>{config.label}</span>
    </span>
  )
}
