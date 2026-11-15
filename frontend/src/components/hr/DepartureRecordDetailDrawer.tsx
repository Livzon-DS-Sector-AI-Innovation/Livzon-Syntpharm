'use client'

import { deleteDepartureRecord } from '@/actions/hr'
import type { DepartureRecord } from '@/types/hr'
import LedgerDetailDrawer, { type LedgerDetailRow } from './LedgerDetailDrawer'

interface DepartureRecordDetailDrawerProps {
  open: boolean
  record: DepartureRecord | null
  onClose: () => void
  onEdit: (record: DepartureRecord) => void
  onDeleted: () => void
}

export default function DepartureRecordDetailDrawer({
  open,
  record,
  onClose,
  onEdit,
  onDeleted,
}: DepartureRecordDetailDrawerProps) {
  const rows: LedgerDetailRow[] = record
    ? [
        { label: '一级部门', value: record.department_level1 },
        { label: '二级部门', value: record.department_level2 },
        { label: '姓名', value: record.name },
        { label: '性别', value: record.gender },
        { label: '岗位', value: record.position },
        { label: '岗位层级', value: record.position_level },
        { label: '人员身份', value: record.personnel_identity },
        { label: '入职日期', value: record.hire_date },
        { label: '离职日期', value: record.leave_date },
        { label: '离职类别', value: record.leave_category },
        { label: '离职原因', value: record.leave_reason },
        { label: '学历', value: record.education },
        { label: '年龄', value: record.age },
        { label: '司龄', value: `${Number(record.tenure_years).toFixed(1)} 年` },
        { label: '集团月报表人员分类', value: record.group_classification },
      ]
    : []

  return (
    <LedgerDetailDrawer
      open={open}
      title={record ? `${record.name} · 离职记录` : '离职记录'}
      avatarName={record?.name ?? ''}
      subtitle={record ? `离职日期 ${record.leave_date}` : ''}
      rows={rows}
      deleteTitle="确认删除这条离职记录？"
      onClose={onClose}
      onEdit={() => record && onEdit(record)}
      onDelete={async () => {
        if (!record) return
        await deleteDepartureRecord(record.id)
        onDeleted()
      }}
    />
  )
}
