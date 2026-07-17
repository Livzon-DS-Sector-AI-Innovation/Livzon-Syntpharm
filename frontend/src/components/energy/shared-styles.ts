/**
 * Energy 模块共享样式 — 与 Equipment 模块保持一致
 *
 * 使用方式：
 *   import { statusPill, actionLink } from '@/components/energy/shared-styles'
 *   <span style={statusPill('#1aae39', '#d9f3e1')}>启用</span>
 *   <span role="button" onClick={...} style={actionLink('#0075de')}>
 *     <EditOutlined />编辑
 *   </span>
 */

import type React from 'react'

export const statusPill = (color: string, bg: string): React.CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  padding: '2px 10px',
  borderRadius: 4,
  fontSize: 12,
  fontWeight: 600,
  lineHeight: '20px',
  color,
  background: bg,
})

export const pillSuccess = statusPill('#1aae39', '#d9f3e1')
export const pillWarning = statusPill('#dd5b00', '#ffe8d4')
export const pillError   = statusPill('#e03131', '#fde0ec')
export const pillNeutral = statusPill('#787671', '#f0eeec')
export const pillInfo    = statusPill('#0075de', '#dcecfa')
export const pillPurple  = statusPill('#5645d4', '#e6e0f5')

export const actionLink = (color: string): React.CSSProperties => ({
  color,
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
  background: 'transparent',
  border: 'none',
  padding: 0,
  lineHeight: '22px',
})

export const linkPrimary = actionLink('#0075de')
export const linkDanger  = actionLink('#e03131')
export const linkPurple  = actionLink('#5645d4')
