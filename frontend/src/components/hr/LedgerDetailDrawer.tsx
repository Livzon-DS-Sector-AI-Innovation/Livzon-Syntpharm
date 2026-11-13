'use client'

import type { ReactNode } from 'react'
import { Button, Drawer, Popconfirm } from 'antd'


export interface LedgerDetailRow {
  label: string
  value: ReactNode
}

interface LedgerDetailDrawerProps {
  open: boolean
  title: string
  avatarName: string
  subtitle: string
  rows: LedgerDetailRow[]
  deleteTitle: string
  onClose: () => void
  onEdit: () => void
  onDelete: () => Promise<void>
}

function DetailRow({ label, value }: LedgerDetailRow) {
  return (
    <div className="flex gap-3 border-b border-[var(--color-hairline-soft)] py-2.5 text-[13px]">
      <span className="w-[130px] shrink-0 text-[var(--color-stone)]">{label}</span>
      <span className="min-w-0 flex-1 text-[var(--color-charcoal)]">{value || '—'}</span>
    </div>
  )
}

/** Shared read-only drawer for one 入职/离职 ledger record. */
export default function LedgerDetailDrawer({
  open,
  title,
  avatarName,
  subtitle,
  rows,
  deleteTitle,
  onClose,
  onEdit,
  onDelete,
}: LedgerDetailDrawerProps) {
  const handleDelete = async () => {
    await onDelete()
    onClose()
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={520}
      title={title}
      footer={
        <div className="flex justify-between">
          <Popconfirm title={deleteTitle} okText="删除" cancelText="取消" onConfirm={handleDelete}>
            <Button danger>删除</Button>
          </Popconfirm>
          <Button type="primary" onClick={onEdit}>
            编辑
          </Button>
        </div>
      }
    >
      <div>
        <div className="mb-3 border-b border-[var(--color-hairline-soft)] pb-3">
          <div className="text-[15px] font-semibold text-[var(--color-charcoal)]">{avatarName}</div>
          <div className="text-xs text-[var(--color-stone)]">{subtitle}</div>
        </div>
        {rows.map((row) => (
          <DetailRow key={row.label} label={row.label} value={row.value} />
        ))}
      </div>
    </Drawer>
  )
}
