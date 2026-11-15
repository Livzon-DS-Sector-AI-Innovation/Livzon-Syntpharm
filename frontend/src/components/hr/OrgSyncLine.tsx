'use client'

import { Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import type { OrgSyncStatusData } from '@/types/hr'

function formatTime(value?: string | null): string {
  if (!value) return '—'
  return dayjs(value).format('YYYY-MM-DD HH:mm')
}

export function OrgSyncLine({
  status,
  syncing,
  onSync,
}: {
  status: OrgSyncStatusData
  syncing: boolean
  onSync: () => void
}) {
  const failed = status.status === 'failed'
  const running = status.status === 'running'
  const never = status.status === 'never'
  const label = never ? '尚未同步' : running ? '同步中' : failed ? '失败' : '成功'
  const dotColor = never
    ? 'var(--color-stone)'
    : failed
      ? 'var(--color-error)'
      : running
        ? 'var(--color-warning)'
        : 'var(--color-success)'
  const labelColor = failed
    ? 'var(--color-error)'
    : running
      ? 'var(--color-warning)'
      : never
        ? 'var(--color-steel)'
        : 'var(--color-success)'

  return (
    <div className="flex items-start gap-3">
      <div className="text-right">
        <div className="text-xs text-[var(--color-steel)]">上次同步 {formatTime(status.last_synced_at)}</div>
        <div className="mt-0.5 text-xs">
          <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: dotColor }} />
          <span style={{ color: labelColor }}>{label}</span>
          {!never && (
            <span className="ml-1 text-[var(--color-stone)]">
              · 部门 {status.department_count} · 人员 {status.people_count}
            </span>
          )}
        </div>
        {failed && status.error_message && (
          <div
            className="mt-0.5 max-w-[360px] truncate text-xs"
            style={{ color: 'var(--color-error)' }}
            title={status.error_message}
          >
            {status.error_message}
          </div>
        )}
      </div>
      <Button size="small" icon={<ReloadOutlined />} loading={syncing} disabled={running} onClick={onSync}>
        立即同步
      </Button>
    </div>
  )
}
