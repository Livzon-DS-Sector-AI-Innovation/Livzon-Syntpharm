'use client'

import { useMemo } from 'react'
import {
  RemoteUserSelect,
  type RemoteUserSelectOption,
} from '@/components/common/RemoteUserSelect'

/**
 * 系统用户选择器（安全模块的对外门面）。
 *
 * 取数与分页逻辑已统一收口到 `components/common/RemoteUserSelect`：
 * 打开即 50 条、滚到底自动续载、关键字走服务端搜索。
 * 这里只保留历史 props 形状，让隐患登记、隐患详情、设备巡检抽屉等既有调用点零改动。
 *
 * 业务口径：台账里的人员字段以 uuid 为准、姓名为展示快照，因此选择后要同时回写 id 与 name；
 * 只列已绑定飞书身份的系统用户（审批人/整改负责人要能收到飞书通知）。
 */

export interface PersonnelSelectProps {
  /** 已绑定的系统用户 UUID */
  value?: string | null
  /** 已保存的姓名，用于未搜索时回显（避免直接显示 UUID） */
  label?: string | null
  /** 已保存的头像地址（可选），用于未搜索时回显真实头像；缺省走姓名首字兜底 */
  avatarSrc?: string | null
  placeholder?: string
  disabled?: boolean
  onChange: (person: { id: string; name: string } | null) => void
}

/** 系统用户选择器（单选），委托通用远端组件。 */
export default function PersonnelSelect({
  value,
  label,
  avatarSrc,
  placeholder = '搜索姓名选择系统用户',
  disabled,
  onChange,
}: PersonnelSelectProps) {
  // 历史 props 只有姓名/头像快照，转成统一组件的 fallbackOptions
  const fallbackOptions = useMemo<RemoteUserSelectOption[]>(
    () => (value && label ? [{ value, label, avatar: avatarSrc ?? undefined }] : []),
    [value, label, avatarSrc],
  )

  return (
    <RemoteUserSelect
      value={value}
      fallbackOptions={fallbackOptions}
      feishuBoundOnly
      // 台账里的人员多为必填，保持原有「不可清空」行为
      allowClear={false}
      placeholder={placeholder}
      disabled={disabled}
      onChange={(next, picked) => {
        const id = typeof next === 'string' ? next : null
        if (!id) {
          onChange(null)
          return
        }
        // onChange 第二参给出本次选中的行，姓名快照与头像一次拿全
        const row = Array.isArray(picked) ? picked[0] : picked
        onChange({ id, name: row?.label ?? label ?? id })
      }}
    />
  )
}

export interface PersonnelMultiSelectProps {
  /** 已选系统用户 UUID 列表 */
  value?: string[]
  /** 已保存的姓名快照（与 value 顺序一致），未搜索时用于回显 */
  labels?: string[]
  /** 已保存的头像快照（与 value 顺序一致），未搜索时用于回显；缺省走姓名首字兜底 */
  avatarSrcs?: Array<string | null | undefined>
  placeholder?: string
  disabled?: boolean
  onChange: (persons: { id: string; name: string }[]) => void
}

/**
 * 系统用户选择器（多选）。
 *
 * 用于「整改负责人」这类多人字段：提交时同时回写 UUID 列表与姓名快照，
 * 保证台账在不额外查用户表的情况下展示姓名；下拉项与已选标签均带头像。
 */
export function PersonnelMultiSelect({
  value,
  labels,
  avatarSrcs,
  placeholder = '搜索姓名，可多选',
  disabled,
  onChange,
}: PersonnelMultiSelectProps) {
  const selectedIds = useMemo(() => value ?? [], [value])

  const fallbackOptions = useMemo<RemoteUserSelectOption[]>(
    () =>
      selectedIds.map((id, index) => ({
        value: id,
        label: labels?.[index] ?? id,
        avatar: avatarSrcs?.[index] ?? undefined,
      })),
    [selectedIds, labels, avatarSrcs],
  )
  const nameById = useMemo(
    () => new Map(fallbackOptions.map((option) => [option.value, option.label])),
    [fallbackOptions],
  )

  return (
    <RemoteUserSelect
      mode="multiple"
      value={selectedIds}
      fallbackOptions={fallbackOptions}
      feishuBoundOnly
      placeholder={placeholder}
      disabled={disabled}
      onChange={(next, picked) => {
        const nextIds = Array.isArray(next) ? next : []
        const rows = Array.isArray(picked) ? picked : []
        const pickedById = new Map(rows.map((row) => [row.value, row.label]))
        onChange(
          nextIds.map((id) => ({ id, name: pickedById.get(id) ?? nameById.get(id) ?? id })),
        )
      }}
    />
  )
}