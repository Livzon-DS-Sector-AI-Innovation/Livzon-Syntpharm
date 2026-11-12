'use client'

import { Card, Steps, Tag } from 'antd'
import type { DeviationLedgerDetail } from '@/types/quality'
import { PeopleInline } from '../PersonInline'

interface FlowPanelProps {
  ledger: DeviationLedgerDetail
}

function stepsCurrent(ledger: DeviationLedgerDetail): number {
  const steps = ledger.steps ?? []
  const index = steps.findIndex((step) => step.step === ledger.current_step)
  if (index >= 0) return index
  if (ledger.status === 'closed') return steps.length
  return 0
}

function stepStatus(ledger: DeviationLedgerDetail, index: number): 'wait' | 'process' | 'finish' | 'error' {
  const current = stepsCurrent(ledger)
  if (ledger.status === 'returned' && index === current) return 'error'
  if (index < current) return 'finish'
  if (index === current && ledger.status !== 'closed') return 'process'
  return 'wait'
}

export function FlowPanel({ ledger }: FlowPanelProps) {
  const steps = ledger.steps ?? []
  return (
    <Card size="small" title="审核流程" className="shadow-sm">
      {steps.length === 0 ? (
        <p className="text-[13px] text-[var(--color-stone)]">流程信息加载失败，请刷新页面重试。</p>
      ) : (
        <Steps
          orientation="vertical"
          size="small"
          current={stepsCurrent(ledger)}
          items={steps.map((step, index) => {
            const applicable = step.applicable !== false
            const handlers = step.handlers ?? []
            const subItems = step.sub_items ?? []
            const description = !applicable ? (
              step.skip_reason ?? '本环节不适用'
            ) : handlers.length > 0 ? (
              <PeopleInline people={handlers} avatarSize={20} gapClassName="gap-x-2 gap-y-1" />
            ) : step.auto_skip ? (
              `责任角色：${step.role_label}，无处理人时自动跳过`
            ) : (
              `责任角色：${step.role_label}（未配置处理人）`
            )
            return {
              title: (
                <span className="flex flex-wrap items-center gap-1 text-[13px]">
                  {step.label}
                  {!applicable && <Tag className="!mr-0">不适用</Tag>}
                  {applicable && step.step === ledger.current_step && ledger.status !== 'closed' && (
                    <Tag color={ledger.status === 'returned' ? 'red' : 'processing'} className="!mr-0">
                      {ledger.status === 'returned' ? '待重提' : '进行中'}
                    </Tag>
                  )}
                </span>
              ),
              content: (
                <span className="flex flex-col gap-1 text-[12px] text-[var(--color-slate)]">
                  <span>{description}</span>
                  {subItems.map((row) => (
                    <span key={row.department} className="flex flex-wrap items-center gap-1">
                      <Tag color={row.state === 'approved' ? 'success' : 'gold'} className="!mr-0">
                        {row.department}
                      </Tag>
                      <span className="truncate">{(row.reviewer_names ?? []).join('、') || '部门负责人'}</span>
                      {row.state === 'approved' ? (
                        <span className="text-[var(--color-success)]">
                          已通过{row.approved_by_name ? ` · ${row.approved_by_name}` : ''}
                        </span>
                      ) : (
                        <span>待审核</span>
                      )}
                    </span>
                  ))}
                </span>
              ),
              status: applicable ? stepStatus(ledger, index) : ('wait' as const),
            }
          })}
        />
      )}
      {steps.length > 0 && (
        <p className="mt-2 text-[12px] text-[var(--color-stone)]">
          共 {steps.length} 个环节，全量展示以便追溯；标注「不适用」的环节本单不经过。
        </p>
      )}
    </Card>
  )
}