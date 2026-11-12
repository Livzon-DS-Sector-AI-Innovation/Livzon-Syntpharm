'use client'

import { useState } from 'react'
import { App, Button, Card, Input, Space, Tag, Typography } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined } from '@ant-design/icons'
import { approveDeviationCrossDeptRow } from '@/actions/quality'
import type { DeviationCrossDeptReviewer, DeviationLedgerDetail } from '@/types/quality'

const { Text } = Typography

interface CrossDeptReviewCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

function formatTime(value?: string | null): string {
  if (!value) return ''
  return value.replace('T', ' ').slice(0, 16)
}

/**
 * 跨部门会签逐行审批卡。
 * 规则：每行 = 部门 + 审核人（调查人为空回退部门负责人），行内任一人通过即该行通过；
 * 全部行通过后流程才流转到所属QA审核；本环节不支持整环节一键通过。
 * 退回重提后已通过的行保持通过（仅名单变化时由后端重置对应行）。
 */
export function CrossDeptReviewCard({ ledger, onUpdated }: CrossDeptReviewCardProps) {
  const { message } = App.useApp()
  const rows = (ledger.cross_dept_reviewers ?? []) as DeviationCrossDeptReviewer[]
  const [opinions, setOpinions] = useState<Record<string, string>>({})
  const [approving, setApproving] = useState<string | null>(null)

  const isCrossStep = ledger.current_step === 'cross_dept_head_review'
  const hasAnyRow = rows.length > 0
  if (!hasAnyRow || (!isCrossStep && !rows.some((row) => row.review_state === 'approved'))) {
    return null
  }
  const approvedCount = rows.filter((row) => row.review_state === 'approved').length

  const handleApprove = async (department: string) => {
    setApproving(department)
    const result = await approveDeviationCrossDeptRow(ledger.id, {
      department,
      opinion: opinions[department]?.trim() ?? '',
    })
    setApproving(null)
    if (result.code === 200 && result.data) {
      message.success(`「${department}」行已通过`)
      onUpdated(result.data)
    } else {
      message.error(result.message)
    }
  }

  return (
    <Card
      id="cross-dept-review"
      size="small"
      className="scroll-mt-6 shadow-sm"
      title={
        <Space size={8}>
          跨部门会签
          <Tag color={approvedCount === rows.length ? 'success' : 'processing'}>
            {approvedCount}/{rows.length} 行已通过
          </Tag>
        </Space>
      }
    >
      <div className="flex flex-col gap-3">
        {rows.map((row) => {
          const approved = row.review_state === 'approved'
          return (
            <div
              key={row.department}
              className="flex flex-col gap-2 rounded-lg border border-[var(--color-hairline)] p-3 sm:flex-row sm:items-center"
            >
              <div className="min-w-0 flex-1">
                <Space size={6} wrap>
                  <Text strong className="text-[13px]">
                    {row.department}
                  </Text>
                  <Tag color="blue" className="!mr-0">
                    跨部门
                  </Tag>
                  {approved ? (
                    <Tag color="success" icon={<CheckCircleOutlined />} className="!mr-0">
                      已通过
                    </Tag>
                  ) : (
                    <Tag color="gold" icon={<ClockCircleOutlined />} className="!mr-0">
                      待审核
                    </Tag>
                  )}
                </Space>
                <div className="mt-1 text-[12px] text-[var(--color-slate)]">
                  审核人：{(row.reviewer_names ?? []).join('、') || '部门负责人'}
                  {approved && (
                    <>
                      {' · '}
                      {row.approved_name ?? '已确认'}
                      {formatTime(row.approved_at) && `（${formatTime(row.approved_at)}）`}
                    </>
                  )}
                </div>
                {approved && row.opinion && (
                  <div className="mt-1 text-[12px] text-[var(--color-ink)]">审核意见：{row.opinion}</div>
                )}
              </div>
              {!approved && row.can_approve && (
                <Space.Compact className="w-full sm:w-[340px]">
                  <Input
                    placeholder="审核意见（可选）"
                    value={opinions[row.department] ?? ''}
                    onChange={(e) => setOpinions((prev) => ({ ...prev, [row.department]: e.target.value }))}
                    maxLength={500}
                  />
                  <Button type="primary" loading={approving === row.department} onClick={() => handleApprove(row.department)}>
                    通过
                  </Button>
                </Space.Compact>
              )}
            </div>
          )
        })}
      </div>
      {isCrossStep && (
        <p className="mt-3 text-[12px] text-[var(--color-stone)]">
          跨部门会签需逐行通过：每行任一审核人通过即该行通过，全部行通过后自动流转所属QA审核；退回重提后已通过的行保持通过。
        </p>
      )}
    </Card>
  )
}
