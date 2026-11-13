'use client'

import type { ReactNode } from 'react'
import { UserLabel } from '@/components/common/UserAvatar'

/**
 * 偏差模块统一的「头像 + 姓名」内联展示。
 *
 * 后端在人名旁给出 avatar_url（identity.users 的飞书缩略图），
 * 没有头像时由 UserAvatar 用姓名首字 + 确定性色块兜底。
 */

export interface PersonLike {
  id?: string | null
  name?: string | null
  avatar_url?: string | null
}

interface PersonInlineProps {
  person?: PersonLike | null
  /** 无姓名时的占位文案 */
  fallback?: string
  avatarSize?: number
}

export function PersonInline({ person, fallback = '-', avatarSize = 22 }: PersonInlineProps) {
  return <UserLabel name={person?.name} src={person?.avatar_url} fallback={fallback} avatarSize={avatarSize} />
}

interface PeopleInlineProps {
  people?: PersonLike[] | null
  /** 列表为空时的占位文案 */
  emptyText?: ReactNode
  avatarSize?: number
  /** 多人之间的水平间距（Tailwind class） */
  gapClassName?: string
}

export function PeopleInline({
  people,
  emptyText = '-',
  avatarSize = 22,
  gapClassName = 'gap-x-3 gap-y-1',
}: PeopleInlineProps) {
  const list = (people ?? []).filter((person): person is PersonLike => Boolean(person?.name))
  if (list.length === 0) {
    return <span className="text-[var(--color-stone)]">{emptyText}</span>
  }
  return (
    <span className={`flex flex-wrap items-center ${gapClassName}`}>
      {list.map((person, index) => (
        <PersonInline key={person.id ?? `${person.name}-${index}`} person={person} avatarSize={avatarSize} />
      ))}
    </span>
  )
}

interface PeopleNamesInlineProps {
  /** 姓名数组（后端 names 字段） */
  names?: string[] | null
  /** 与 names 同序的头像数组（后端 avatars 字段），缺省时走首字兜底 */
  avatars?: (string | null)[] | null
  emptyText?: ReactNode
  avatarSize?: number
}

/** 用于「姓名 + 头像」平行数组的场景（如部门联系人的 QA / GMP 人员列表）。 */
export function PeopleNamesInline({
  names,
  avatars,
  emptyText = '-',
  avatarSize = 22,
}: PeopleNamesInlineProps) {
  const people: PersonLike[] = (names ?? [])
    .map((name, index) => ({ name, avatar_url: avatars?.[index] ?? null }))
    .filter((person) => Boolean(person.name))
  return <PeopleInline people={people} emptyText={emptyText} avatarSize={avatarSize} />
}