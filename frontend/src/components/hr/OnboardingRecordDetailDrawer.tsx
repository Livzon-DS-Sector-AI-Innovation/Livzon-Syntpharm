'use client'

import { deleteOnboardingRecord } from '@/actions/hr'
import type { OnboardingRecord } from '@/types/hr'
import LedgerDetailDrawer, { type LedgerDetailRow } from './LedgerDetailDrawer'

interface OnboardingRecordDetailDrawerProps {
  open: boolean
  record: OnboardingRecord | null
  onClose: () => void
  onEdit: (record: OnboardingRecord) => void
  onDeleted: () => void
}

export default function OnboardingRecordDetailDrawer({
  open,
  record,
  onClose,
  onEdit,
  onDeleted,
}: OnboardingRecordDetailDrawerProps) {
  const rows: LedgerDetailRow[] = record
    ? [
        { label: '流水号', value: record.serial_no },
        { label: '姓名', value: record.name },
        { label: '一级部门', value: record.department_level1 },
        { label: '二级部门', value: record.department_level2 },
        { label: '岗位', value: record.position },
        { label: '岗位层级', value: record.position_level },
        { label: '人员身份', value: record.personnel_identity },
        { label: '入职日期', value: record.hire_date },
        { label: '入职类别', value: record.join_category },
        { label: '学历', value: record.education },
        { label: '性别', value: record.gender },
        { label: '年龄', value: record.age },
        { label: '手机号码', value: record.mobile },
        { label: '集团月报表人员分类', value: record.group_classification },
      ]
    : []

  return (
    <LedgerDetailDrawer
      open={open}
      title={record ? `${record.name} · 入职记录` : "入职记录"}
      avatarName={record?.name ?? ""}
      subtitle={record ? `流水号 ${record.serial_no}` : ""}
      rows={rows}
      deleteTitle="确认删除这条入职记录？"
      onClose={onClose}
      onEdit={() => record && onEdit(record)}
      onDelete={async () => {
        if (!record) return
        await deleteOnboardingRecord(record.id)
        onDeleted()
      }}
    />
  )
}
