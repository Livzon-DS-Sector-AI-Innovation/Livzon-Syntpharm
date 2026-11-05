'use client'

import type { CSSProperties } from 'react'
import { Tooltip } from 'antd'
import { T } from '@/components/safety/sharedStyles'

/** 未绑定系统用户时统一的说明文案：同名多人无法消歧、或系统里查无此人 */
export const PERSON_PENDING_HINT =
  '系统内未匹配到唯一用户（同名多人或查无此人），请在此处选择实际人员完成绑定'

const badgeStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  flex: 'none',
  padding: '1px 6px',
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 600,
  lineHeight: '16px',
  color: T.warning,
  background: T.yellow,
  whiteSpace: 'nowrap',
}

/** 「待确认」标记：姓名有值但没有对应的系统用户 UUID */
export function PersonPendingBadge({ text = '待确认' }: { text?: string }) {
  return (
    <Tooltip title={PERSON_PENDING_HINT}>
      <span style={badgeStyle}>{text}</span>
    </Tooltip>
  )
}

/** 表格/详情里的人员姓名单元：有姓名未绑定 → 姓名 + 待确认标记 */
export function PersonNameWithBadge({
  name,
  bound,
  fontSize = 13,
}: {
  name?: string | null
  bound?: string | null
  fontSize?: number
}) {
  if (!name) return <span style={{ color: T.muted }}>-</span>
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, maxWidth: '100%', fontSize }}>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{name}</span>
      {!bound ? <PersonPendingBadge /> : null}
    </span>
  )
}