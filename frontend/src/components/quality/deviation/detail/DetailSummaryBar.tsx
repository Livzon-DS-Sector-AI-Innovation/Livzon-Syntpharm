'use client'

import { Button, Space, Tag } from 'antd'
import type { DeviationLedgerDetail } from '@/types/quality'
import { DEVIATION_LEVEL_COLORS, DEVIATION_STATUS_COLORS } from '../constants'
import { PeopleInline, PersonInline } from '../PersonInline'

interface DetailSummaryBarProps {
  ledger: DeviationLedgerDetail
  /** 是否有写操作正在执行 */
  busy?: boolean
}

/** 主操作锚点：按后端 allowed_actions 决定按钮，只负责滚动到对应卡片 */
const ACTION_ANCHORS: Record<string, { href: string; label: string; type: 'primary' | 'default' }> = {
  analyze: { href: '#ai-analysis', label: '开始 AI 分析', type: 'primary' },
  edit: { href: '#basic-info', label: '编辑基础信息', type: 'default' },
  investigate: { href: '#investigation', label: '提交调查报告', type: 'primary' },
  approve: { href: '#review', label: '审核处理', type: 'primary' },
  reject: { href: '#review', label: '审核处理', type: 'primary' },
  resubmit: { href: '#review', label: '重新提交', type: 'primary' },
  final_code: { href: '#final-code', label: '录入最终编号', type: 'primary' },
}

export function DetailSummaryBar({ ledger, busy = false }: DetailSummaryBarProps) {
  // approve / reject 等动作指向同一张卡片、同一文案，按 href+label 去重后只渲染一个按钮，
  // 否则「审核处理」会重复出现两次（通过/退回都在审核卡片里操作）
  const actions = [
    ...new Map(
      [...new Set(ledger.allowed_actions ?? [])]
        .map((action) => ACTION_ANCHORS[action])
        .filter((item): item is NonNullable<typeof item> => Boolean(item))
        .map((item) => [`${item.href}|${item.label}`, item]),
    ).values(),
  ]

  // 手机端不吸顶：摘要条较高，吸顶会占掉近三成屏幕并遮住下方卡片内容
  return (
    <section className="z-20 flex flex-col gap-3 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)]/95 p-4 shadow-sm backdrop-blur sm:sticky sm:top-0">
      <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1 basis-[280px]">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[15px] font-semibold text-[var(--color-ink)]">
              {ledger.display_code}
            </span>
            {ledger.final_code && ledger.final_code !== ledger.code && (
              <Tag color="cyan">最终编号 {ledger.final_code}</Tag>
            )}
            <Tag color={DEVIATION_STATUS_COLORS[ledger.status] ?? 'default'}>{ledger.status_label}</Tag>
            {ledger.is_overdue && <Tag color="red">超期 {ledger.overdue_days} 天</Tag>}
            {ledger.deviation_level && (
              <Tag color={DEVIATION_LEVEL_COLORS[ledger.deviation_level] ?? 'default'}>
                {ledger.level_label}
              </Tag>
            )}
            {ledger.reason_category && (
              <Tag className="max-w-full truncate" title={ledger.reason_category}>
                原因分类：{ledger.reason_category}
              </Tag>
            )}
          </div>
          <h1 className="mt-1 break-words text-[20px] font-semibold leading-7 text-[var(--color-ink)]">
            {ledger.title}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-1 text-[13px] text-[var(--color-slate)]">
            <span>
              {ledger.department} · 发现日期 {ledger.discovery_date} · 上报人
            </span>
            <PersonInline person={ledger.reporter ?? { name: ledger.reporter_name }} avatarSize={20} />
          </p>
        </div>
        <Space wrap size={8} className="shrink-0">
          {actions.map((action) => (
            <Button key={action.href + action.label} type={action.type} href={action.href} disabled={busy}>
              {action.label}
            </Button>
          ))}
        </Space>
      </div>

      <div className="flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-[var(--color-hairline)] pt-2 text-[13px]">
        <span className="text-[var(--color-slate)]">
          当前环节：
          <span className="font-medium text-[var(--color-ink)]">{ledger.current_step_label || '-'}</span>
        </span>
        <span className="flex flex-wrap items-center gap-1 text-[var(--color-slate)]">
          当前处理人：
          {ledger.current_handlers?.length ? (
            <PeopleInline people={ledger.current_handlers} avatarSize={20} gapClassName="gap-x-2" />
          ) : (
            <span className="font-medium text-[var(--color-ink)]">{ledger.current_handler || '暂无（自动跳过）'}</span>
          )}
        </span>
        {ledger.returned_step_label && (
          <span className="text-[var(--color-error)]">已退回至：{ledger.returned_step_label}</span>
        )}
        {!ledger.can_operate && (
          <span className="text-[var(--color-stone)]">当前登录人不是本环节处理人，仅可查看</span>
        )}
      </div>
    </section>
  )
}