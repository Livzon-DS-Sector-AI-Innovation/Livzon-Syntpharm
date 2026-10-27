'use client'

import type { ReactNode } from 'react'
import { Card } from 'antd'

interface SettingsListCardProps {
  /** 卡片标题（走 antd Card head，统一 16px/600），不传则不渲染头部 */
  title?: ReactNode
  /** 卡片右上角操作区 */
  extra?: ReactNode
  /**
   * 表格上方工具行（筛选/刷新/新建），统一 flex-wrap + gap-3 + mb-3。
   * 默认左起排列；如需「筛选左 + 计数右」，在内部再嵌一层
   * `div.flex.w-full.flex-wrap.items-center.justify-between.gap-3`。
   */
  toolbar?: ReactNode
  className?: string
  children: ReactNode
}

/**
 * 系统管理列表统一容器：强制 `[&_.ant-table]:!m-0` 消除卡片与表格的双层留白，
 * 并统一工具行布局。所有列表（含运维页）都应使用它包裹 Table。
 */
export function SettingsListCard({ title, extra, toolbar, className, children }: SettingsListCardProps) {
  return (
    <Card
      title={title}
      extra={extra}
      className={className ? `[&_.ant-table]:!m-0 ${className}` : '[&_.ant-table]:!m-0'}
    >
      {toolbar ? <div className="mb-3 flex flex-wrap items-center gap-3">{toolbar}</div> : null}
      {children}
    </Card>
  )
}