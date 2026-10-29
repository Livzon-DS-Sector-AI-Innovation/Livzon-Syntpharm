'use client'

import { Button, Result } from 'antd'
import { ExclamationCircleOutlined } from '@ant-design/icons'

/**
 * 数据区块的降级占位（取数失败 / 后端不可用）。
 *
 * 与 `BoundaryResult` 的分工：
 * - `BoundaryResult` 面向**整页边界**（未登录 / 无权限 / 404 / 500），自带跳转动作；
 * - 本组件面向**页内某一区块**（列表、表格、看板卡片）取数失败，只给一句人话 + 重试，
 *   不抢整页的导航决定权。
 *
 * 为什么需要它：改造前这些页面在 `catch` 里只 `message.error` 然后把数据置空，
 * 界面上与「确实没有数据」完全一样，故障被伪装成空表（#169）。
 * 文案遵循项目降级约定：外部数据源不可用 → 显示「数据暂时不可用」，不阻塞其他功能。
 */
export const DATA_UNAVAILABLE_TITLE = '数据暂时不可用'
export const DATA_UNAVAILABLE_DESCRIPTION = '请稍后重试；若反复出现，请联系管理员。'

export interface DataUnavailableProps {
  /** 覆盖默认文案，默认「数据暂时不可用」 */
  title?: string
  /** 补充说明，默认提示稍后重试 */
  description?: string
  /** 重试回调，通常传 React Query 的 `refetch` */
  onRetry: () => void
  /** 紧凑模式：用于表格内嵌 / `Table.locale.emptyText`，而非整块区域 */
  compact?: boolean
  /** 额外类名，用于局部间距微调 */
  className?: string
}

/**
 * 取数失败时渲染的降级区块。
 *
 * 注意：**不要**用它替代「确实没有数据」的空态。空态交给 antd 的 `Empty`
 * （或表格自带的 `locale.emptyText`），否则会把「暂无数据」显示成故障。
 */
export function DataUnavailable({
  title = DATA_UNAVAILABLE_TITLE,
  description = DATA_UNAVAILABLE_DESCRIPTION,
  onRetry,
  compact = false,
  className,
}: DataUnavailableProps) {
  if (compact) {
    return (
      <div
        className={['flex flex-col items-center justify-center gap-2 py-8 text-center', className]
          .filter(Boolean)
          .join(' ')}
      >
        <ExclamationCircleOutlined style={{ fontSize: 20, color: '#faad14' }} />
        <span className="text-[13px] text-gray-600">{title}</span>
        <span className="text-[12px] text-gray-400">{description}</span>
        <Button size="small" onClick={onRetry}>
          重试
        </Button>
      </div>
    )
  }

  return (
    <Result
      status="warning"
      title={title}
      subTitle={description}
      className={className}
      extra={
        <Button type="primary" onClick={onRetry}>
          重试
        </Button>
      }
    />
  )
}