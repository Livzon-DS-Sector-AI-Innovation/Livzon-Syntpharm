'use client'

import { Avatar, Button, Drawer, Popconfirm } from 'antd'

import { deleteDepartureRecord } from '@/actions/hr'
import type { DepartureRecord } from '@/types/hr'
import { avatarColor } from './onboardingOptions'

interface DepartureRecordDetailDrawerProps {
  open: boolean
  record: DepartureRecord | null
  onClose: () => void
  onEdit: (record: DepartureRecord) => void
  onDeleted: () => void
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex gap-3 border-b border-[#f0eeec] py-2.5 text-[13px]">
      <span className="w-[130px] shrink-0 text-[#a4a097]">{label}</span>
      <span className="min-w-0 flex-1 text-[#37352f]">{value || '—'}</span>
    </div>
  )
}

export default function DepartureRecordDetailDrawer({
  open,
  record,
  onClose,
  onEdit,
  onDeleted,
}: DepartureRecordDetailDrawerProps) {
  const handleDelete = async () => {
    if (!record) return
    await deleteDepartureRecord(record.id)
    onDeleted()
    onClose()
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={520}
      title={record ? `${record.name} · 离职记录` : '离职记录'}
      footer={
        record ? (
          <div className="flex justify-between">
            <Popconfirm title="确认删除这条离职记录？" okText="删除" cancelText="取消" onConfirm={handleDelete}>
              <Button danger>删除</Button>
            </Popconfirm>
            <Button type="primary" onClick={() => onEdit(record)}>
              编辑
            </Button>
          </div>
        ) : null
      }
    >
      {record && (
        <div>
          <div className="mb-3 flex items-center gap-3 border-b border-[#f0eeec] pb-3">
            <Avatar size={44} style={{ backgroundColor: avatarColor(record.name), fontSize: 16 }}>
              {record.name.slice(0, 1)}
            </Avatar>
            <div>
              <div className="text-[15px] font-semibold text-[#37352f]">{record.name}</div>
              <div className="text-xs text-[#a4a097]">离职日期 {record.leave_date}</div>
            </div>
          </div>
          <DetailRow label="一级部门" value={record.department_level1} />
          <DetailRow label="二级部门" value={record.department_level2} />
          <DetailRow label="姓名" value={record.name} />
          <DetailRow label="性别" value={record.gender} />
          <DetailRow label="岗位" value={record.position} />
          <DetailRow label="岗位层级" value={record.position_level} />
          <DetailRow label="人员身份" value={record.personnel_identity} />
          <DetailRow label="入职日期" value={record.hire_date} />
          <DetailRow label="离职日期" value={record.leave_date} />
          <DetailRow label="离职类别" value={record.leave_category} />
          <DetailRow label="离职原因" value={record.leave_reason} />
          <DetailRow label="学历" value={record.education} />
          <DetailRow label="年龄" value={record.age} />
          <DetailRow label="司龄" value={`${Number(record.tenure_years).toFixed(1)} 年`} />
          <DetailRow label="集团月报表人员分类" value={record.group_classification} />
        </div>
      )}
    </Drawer>
  )
}
