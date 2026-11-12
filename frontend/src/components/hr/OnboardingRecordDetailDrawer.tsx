'use client'

import { Avatar, Button, Drawer, Popconfirm } from 'antd'

import { deleteOnboardingRecord } from '@/actions/hr'
import type { OnboardingRecord } from '@/types/hr'
import { avatarColor } from './onboardingOptions'

interface OnboardingRecordDetailDrawerProps {
  open: boolean
  record: OnboardingRecord | null
  onClose: () => void
  onEdit: (record: OnboardingRecord) => void
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

export default function OnboardingRecordDetailDrawer({
  open,
  record,
  onClose,
  onEdit,
  onDeleted,
}: OnboardingRecordDetailDrawerProps) {
  const handleDelete = async () => {
    if (!record) return
    await deleteOnboardingRecord(record.id)
    onDeleted()
    onClose()
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={520}
      title={record ? `${record.name} · 入职记录` : '入职记录'}
      footer={
        record ? (
          <div className="flex justify-between">
            <Popconfirm title="确认删除这条入职记录？" okText="删除" cancelText="取消" onConfirm={handleDelete}>
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
              <div className="text-xs text-[#a4a097]">流水号 {record.serial_no}</div>
            </div>
          </div>
          <DetailRow label="流水号" value={record.serial_no} />
          <DetailRow label="姓名" value={record.name} />
          <DetailRow label="一级部门" value={record.department_level1} />
          <DetailRow label="二级部门" value={record.department_level2} />
          <DetailRow label="岗位" value={record.position} />
          <DetailRow label="岗位层级" value={record.position_level} />
          <DetailRow label="人员身份" value={record.personnel_identity} />
          <DetailRow label="入职日期" value={record.hire_date} />
          <DetailRow label="入职类别" value={record.join_category} />
          <DetailRow label="学历" value={record.education} />
          <DetailRow label="性别" value={record.gender} />
          <DetailRow label="年龄" value={record.age} />
          <DetailRow label="手机号码" value={record.mobile} />
          <DetailRow label="集团月报表人员分类" value={record.group_classification} />
        </div>
      )}
    </Drawer>
  )
}
