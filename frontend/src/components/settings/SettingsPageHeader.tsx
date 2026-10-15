import type { ReactNode } from 'react'

interface SettingsPageHeaderProps {
  /** 页面主标题，统一 h1 24px/600 */
  title: ReactNode
  /** 副标题说明，统一 13px steel；不传则不渲染 */
  description?: ReactNode
  /** 右侧操作区（按钮等），窄屏自动换行到标题下方 */
  extra?: ReactNode
}

/**
 * 系统管理各页面统一的页头：标题 + 副标题 + 可选右侧操作区。
 * 间距固定 mb-5，避免各页 mb-5 / mb-6 / 无 的漂移。
 */
export function SettingsPageHeader({ title, description, extra }: SettingsPageHeaderProps) {
  return (
    <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
      <div className="min-w-0">
        <h1 className="m-0 text-[24px] font-semibold text-[var(--color-charcoal)]">{title}</h1>
        {description ? (
          <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">{description}</p>
        ) : null}
      </div>
      {extra ? <div className="shrink-0">{extra}</div> : null}
    </div>
  )
}