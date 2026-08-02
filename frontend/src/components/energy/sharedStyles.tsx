import type { CSSProperties } from 'react'

export function statusPill(bg: string, fg: string): CSSProperties {
  return {
    display: 'inline-block',
    padding: '0 8px',
    borderRadius: 9999,
    background: bg,
    color: fg,
    fontSize: 13,
    fontWeight: 500,
    lineHeight: '22px',
  }
}

export const pillSuccess: CSSProperties = statusPill('#d9f3e1', '#1aae39')
export const pillWarning: CSSProperties = statusPill('#fff7e6', '#dd5b00')
export const pillError: CSSProperties = statusPill('#fde0ec', '#e03131')
export const pillNeutral: CSSProperties = statusPill('#f0eeec', '#787671')
export const pillPurple: CSSProperties = statusPill('#ede9f7', '#5645d4')
export const pillInfo: CSSProperties = statusPill('#dcecfa', '#0075de')

export const actionLink: CSSProperties = {
  cursor: 'pointer',
  fontSize: 14,
  fontWeight: 500,
  userSelect: 'none',
}
export const linkPrimary: CSSProperties = { ...actionLink, color: '#3370ff' }
export const linkDanger: CSSProperties = { ...actionLink, color: '#e03131' }
export const linkPurple: CSSProperties = { ...actionLink, color: '#5645d4' }
