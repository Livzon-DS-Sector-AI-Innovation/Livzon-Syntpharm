'use client'

import type { CSSProperties, ReactNode } from 'react'
import { Avatar } from 'antd'
import type { AvatarProps } from 'antd'
import { UserOutlined } from '@ant-design/icons'

/**
 * 统一的用户头像 / 「头像 + 姓名」展示。
 *
 * 数据来源是 identity.users 的飞书头像（avatar_thumb → avatar_url 依次回退），
 * 加载失败或没有头像时用「姓名首字 + 确定性色块」兜底：
 * - antd `Avatar` 在 `src` 报错时会自动切到 `children`，所以色块始终挂在 style 上，
 *   图片盖住底色、加载失败则露出首字，不需要额外的 error state；
 * - 底色由姓名 hash 决定（纯函数），同一姓名永远同色，SSR/CSR 渲染一致。
 */

/** 6 色姓名色板（取自设计 token 派生色，同一姓名恒定同色）。 */
const AVATAR_COLORS = ['#5645d4', '#7b3ff2', '#dd5b00', '#0075de', '#1aae39', '#2a9d99']

/** 按姓名算兜底色（纯函数，禁止随机，避免 hydration 不一致）。 */
export function avatarColorOf(name?: string | null): string {
  const text = (name ?? '').trim()
  if (!text) return AVATAR_COLORS[0]
  let hash = 0
  for (let i = 0; i < text.length; i++) {
    hash = text.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

/** 姓名首字：中文取前 2 字，英文取首尾单词首字母；空姓名返回空串（由图标兜底）。 */
export function initialsOf(name?: string | null): string {
  const text = (name ?? '').trim()
  if (!text) return ''
  if (/[\u4e00-\u9fa5]/.test(text)) return text.slice(0, 2)
  const parts = text.split(/\s+/)
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
  }
  return text.slice(0, 2).toUpperCase()
}

export interface UserAvatarProps {
  /** 用户姓名，用于首字兜底与配色 */
  name?: string | null
  /** 头像地址：优先 avatar_thumb，其次 avatar_url；为空时直接走首字兜底 */
  src?: string | null
  size?: AvatarProps['size']
  className?: string
  /** 追加样式（边框、阴影等），会与内部样式合并 */
  style?: CSSProperties
}

export function UserAvatar({ name, src, size = 28, className, style }: UserAvatarProps) {
  const initials = initialsOf(name)
  const numericSize = typeof size === 'number' ? size : undefined

  return (
    <Avatar
      size={size}
      src={src || undefined}
      className={className}
      style={{
        backgroundColor: avatarColorOf(name),
        flexShrink: 0,
        fontWeight: 600,
        fontSize: numericSize ? Math.max(10, Math.round(numericSize * 0.4)) : undefined,
        ...style,
      }}
      icon={initials ? undefined : <UserOutlined />}
    >
      {initials || undefined}
    </Avatar>
  )
}

export interface UserLabelProps extends Omit<UserAvatarProps, 'size' | 'style'> {
  /** 头像右侧主文本（姓名）；为空时回退到 fallback */
  name?: string | null
  /** 姓名为空时的占位文案，默认「—」 */
  fallback?: ReactNode
  /** 可选次级文案（账号 / 部门），灰色小字换行显示 */
  secondary?: ReactNode
  /** 头像尺寸，默认 28 */
  avatarSize?: AvatarProps['size']
  /** 追加样式，例如去除默认换行 */
  style?: CSSProperties
}

/**
 * 头像 + 姓名（+ 可选次级文案）。表格列、列表项、下拉选项统一用它，
 * 保证全站「姓名左侧有头像」的视觉一致。
 */
export function UserLabel({
  name,
  src,
  fallback = '—',
  secondary,
  avatarSize = 28,
  className,
  style,
}: UserLabelProps) {
  const text = name?.trim() ? name : null

  return (
    <span className={['inline-flex min-w-0 items-center gap-2', className].filter(Boolean).join(' ')} style={style}>
      <UserAvatar name={text} src={src} size={avatarSize} />
      <span className="min-w-0 leading-tight">
        <span className="block truncate text-[13px] text-[var(--color-ink)]">{text ?? fallback}</span>
        {secondary ? (
          <span className="block truncate text-[12px] text-[var(--color-steel)]">{secondary}</span>
        ) : null}
      </span>
    </span>
  )
}