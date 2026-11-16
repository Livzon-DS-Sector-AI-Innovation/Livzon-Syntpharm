'use client'

import type { ReactNode } from 'react'
import { Progress, Tag } from 'antd'
import {
  CheckCircleFilled,
  ClockCircleFilled,
  ExclamationCircleFilled,
  MinusCircleOutlined,
} from '@ant-design/icons'
import type { DeviationLedgerDetail } from '@/types/quality'
import { PeopleInline } from '../PersonInline'
import { SectionCard } from './SectionCard'

interface FlowPanelProps {
  ledger: DeviationLedgerDetail
}

type StepState = 'finish' | 'process' | 'wait' | 'error' | 'skip'

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

// 图标颜色用内联 style：@ant-design/icons 自带 `.anticon { color: inherit }`（未分层），
// 会盖掉 Tailwind 的 text-* 工具类
const STEP_ICON: Record<StepState, ReactNode> = {
  finish: <CheckCircleFilled style={{ color: '#1AAE39' }} />,
  process: <ClockCircleFilled style={{ color: '#5645D4' }} />,
  error: <ExclamationCircleFilled style={{ color: '#E03131' }} />,
  wait: <MinusCircleOutlined style={{ color: '#A4A097' }} />,
  skip: <MinusCircleOutlined style={{ color: '#C8C4BE' }} />,
}

/** 环节卡片配色：进行中高亮、退回告警、待处理留白、不适用虚线置灰 */
const STEP_BOX: Record<StepState, string> = {
  finish: 'border-[var(--color-hairline)] bg-[var(--color-surface-soft)]',
  process: 'border-[#5645D4] bg-[#F6F4FE] shadow-sm',
  error: 'border-[#E03131] bg-[#FEF2F2]',
  wait: 'border-[var(--color-hairline)] bg-[var(--color-canvas)]',
  skip: 'border-dashed border-[var(--color-hairline)] bg-[var(--color-surface-soft)]',
}

const STEP_TITLE: Record<StepState, string> = {
  finish: 'text-[var(--color-ink)]',
  process: 'font-semibold text-[#4534B3]',
  error: 'font-semibold text-[var(--color-error)]',
  wait: 'text-[var(--color-slate)]',
  skip: 'text-[var(--color-stone)]',
}

/**
 * 审核流程：右栏常驻，头部显示整体进度，每个环节按「已完成 / 进行中 / 待处理 / 不适用」四种形态区分，
 * 当前环节使用主色边框 + 浅底高亮，避免整列灰色文字难以定位。
 */
export function FlowPanel({ ledger }: FlowPanelProps) {
  const steps = ledger.steps ?? []
  const applicableSteps = steps.filter((step) => step.applicable !== false)
  // 已关闭时 stepsCurrent 返回 length，所有环节都会被判定为 finish
  const finishedCount = steps.filter(
    (step, index) => step.applicable !== false && stepStatus(ledger, index) === 'finish',
  ).length
  const percent = applicableSteps.length > 0 ? Math.round((finishedCount / applicableSteps.length) * 100) : 0
  const allDone = applicableSteps.length > 0 && finishedCount === applicableSteps.length

  return (
    <SectionCard
      section="flow"
      ledger={ledger}
      badge={
        steps.length > 0 ? (
          <Tag color={allDone ? 'success' : 'processing'} className="!mr-0">
            已完成 {finishedCount}/{applicableSteps.length}
          </Tag>
        ) : null
      }
    >
      {steps.length === 0 ? (
        <p className="text-[13px] text-[var(--color-stone)]">流程信息加载失败，请刷新页面重试。</p>
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between text-[12px]">
              <span className="text-[var(--color-slate)]">环节进度</span>
              <span className="font-medium text-[var(--color-ink)]">{percent}%</span>
            </div>
            <Progress
              percent={percent}
              showInfo={false}
              size="small"
              strokeColor="#5645D4"
              railColor="#EEECFB"
            />
          </div>

          <ol className="flex flex-col">
            {steps.map((step, index) => {
              const applicable = step.applicable !== false
              const state: StepState = applicable ? stepStatus(ledger, index) : 'skip'
              const handlers = step.handlers ?? []
              const subItems = step.sub_items ?? []
              const isLast = index === steps.length - 1

              return (
                <li key={`${step.step}-${index}`} className="flex gap-2">
                  <div className="relative flex w-4 shrink-0 flex-col items-center">
                    <span className="z-10 flex h-4 w-4 items-center justify-center bg-[var(--color-canvas)] text-[13px] leading-none">
                      {STEP_ICON[state]}
                    </span>
                    {!isLast && <span className="absolute bottom-0 top-4 w-px bg-[var(--color-hairline-strong)]" />}
                  </div>

                  <div
                    className={`mb-2 min-w-0 flex-1 rounded-lg border px-2.5 py-2 ${STEP_BOX[state]} ${
                      isLast ? 'mb-0' : ''
                    }`}
                  >
                    <div className="flex flex-wrap items-center gap-x-1.5 gap-y-1">
                      <span className={`text-[13px] leading-4 ${STEP_TITLE[state]}`}>{step.label}</span>
                      {!applicable && (
                        <Tag className="!mr-0 !px-1 !text-[11px] !leading-4">不适用</Tag>
                      )}
                      {applicable && step.step === ledger.current_step && ledger.status !== 'closed' && (
                        <Tag
                          color={ledger.status === 'returned' ? 'red' : 'processing'}
                          className="!mr-0 !px-1 !text-[11px] !leading-4"
                        >
                          {ledger.status === 'returned' ? '待重提' : '进行中'}
                        </Tag>
                      )}
                    </div>

                    <div className="mt-1 flex flex-col gap-1 text-[12px] leading-4 text-[var(--color-slate)]">
                      <span>
                        {!applicable ? (
                          step.skip_reason ?? '本环节不适用'
                        ) : handlers.length > 0 ? (
                          <PeopleInline people={handlers} avatarSize={18} gapClassName="gap-x-2 gap-y-1" />
                        ) : step.auto_skip ? (
                          `责任角色：${step.role_label}，无处理人时自动跳过`
                        ) : (
                          `责任角色：${step.role_label}（未配置处理人）`
                        )}
                      </span>
                      {subItems.map((row) => (
                        <span key={row.department} className="flex flex-wrap items-center gap-1">
                          <Tag
                            color={row.state === 'approved' ? 'success' : 'gold'}
                            className="!mr-0 !px-1 !text-[11px] !leading-4"
                          >
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
                    </div>
                  </div>
                </li>
              )
            })}
          </ol>

          <p className="text-[12px] leading-4 text-[var(--color-stone)]">
            共 {steps.length} 个环节，全量展示以便追溯；标注「不适用」的环节本单不经过。
          </p>
        </div>
      )}
    </SectionCard>
  )
}