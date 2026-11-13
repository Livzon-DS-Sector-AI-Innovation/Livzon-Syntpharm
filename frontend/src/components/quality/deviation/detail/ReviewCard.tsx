'use client'

import { useMemo, useState } from 'react'
import { Alert, App, Button, Card, Input, Select, Tag } from 'antd'
import { CheckOutlined, RollbackOutlined, SendOutlined } from '@ant-design/icons'
import { resubmitDeviation, reviewDeviation } from '@/actions/quality'
import type { DeviationLedgerDetail } from '@/types/quality'
import { DEVIATION_LEVEL_OPTIONS } from '../constants'

interface ReviewCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

/** 审核动作卡：意见 + 通过/退回、QA 审核原因分类、QA 负责人分级、退回后重新提交 */
export function ReviewCard({ ledger, onUpdated }: ReviewCardProps) {
  const { message } = App.useApp()
  const [content, setContent] = useState('')
  const [reasonCategory, setReasonCategory] = useState<string | undefined>(ledger.reason_category ?? undefined)
  const [deviationLevel, setDeviationLevel] = useState<string | undefined>(ledger.deviation_level ?? undefined)
  const [pending, setPending] = useState<'approved' | 'rejected' | 'resubmit' | null>(null)

  const actions = ledger.allowed_actions ?? []
  const canApprove = actions.includes('approve')
  const canReject = actions.includes('reject')
  const canResubmit = actions.includes('resubmit') && ledger.status === 'returned'
  const needReason = actions.includes('reason_category')
  const needLevel = actions.includes('grade')

  const lastReject = useMemo(() => {
    const rejected = (ledger.review_opinions ?? []).filter((item) => item.result === 'rejected')
    return rejected.length > 0 ? rejected[rejected.length - 1] : null
  }, [ledger.review_opinions])

  if (!canApprove && !canReject && !canResubmit) {
    return null
  }

  const runReview = async (result: 'approved' | 'rejected') => {
    if (result === 'rejected' && !content.trim()) {
      message.warning('退回时必须填写退回意见')
      return
    }
    if (result === 'approved' && needReason && !reasonCategory?.trim()) {
      message.warning('QA 审核通过前必须填写原因分类')
      return
    }
    if (result === 'approved' && needLevel && !deviationLevel) {
      message.warning('QA 负责人通过前必须选择偏差分级')
      return
    }
    setPending(result)
    const response = await reviewDeviation(ledger.id, {
      step: ledger.current_step ?? undefined,
      result,
      content: content.trim(),
      reason_category: needReason ? (reasonCategory?.trim() || null) : undefined,
      deviation_level: needLevel ? (deviationLevel ?? null) : undefined,
    })
    setPending(null)
    if (response.code === 200 && response.data) {
      setContent('')
      onUpdated(response.data)
      message.success(result === 'approved' ? '已通过并流转至下一环节' : '已退回上一环节')
    } else {
      message.error(response.message)
    }
  }

  const runResubmit = async () => {
    setPending('resubmit')
    const response = await resubmitDeviation(ledger.id, { content: content.trim() })
    setPending(null)
    if (response.code === 200 && response.data) {
      setContent('')
      onUpdated(response.data)
      message.success('已重新提交')
    } else {
      message.error(response.message)
    }
  }

  return (
    <Card
      id="review"
      size="small"
      title="审核流转"
      className="scroll-mt-6 shadow-sm"
      extra={
        <Tag color={ledger.status === 'returned' ? 'red' : 'gold'}>
          {ledger.current_step_label ?? ledger.status_label}
        </Tag>
      }
    >
      <div className="flex flex-col gap-3">
        {ledger.status === 'returned' && (
          <Alert
            type="warning"
            showIcon
            title={`已从「${lastReject?.step_label ?? ledger.returned_step_label ?? '上一环节'}」退回`}
            description={
              <span className="whitespace-pre-wrap break-words">
                {lastReject?.content || '未填写退回意见'}
                {lastReject?.author_name ? `（${lastReject.author_name}）` : ''}
              </span>
            }
          />
        )}

        {canResubmit && (
          <p className="text-[12px] text-[var(--color-slate)]">
            修改后点击「重新提交」，将回到「{ledger.current_step_label ?? ledger.returned_step_label ?? '退回环节'}」继续处理。
          </p>
        )}

        {(needReason || needLevel) && (
          <div className={`grid gap-3 ${needReason && needLevel ? 'sm:grid-cols-2' : ''}`}>
            {needReason && (
              <div>
                <p className="mb-1 text-[12px] text-[var(--color-slate)]">原因分类（通过必填）</p>
                {/* 原因分类改为自由填写：后端只做非空与长度校验，不再限定枚举 */}
                <Input
                  value={reasonCategory}
                  placeholder="填写原因分类，如：人员、设施设备、文件、环境、其它"
                  maxLength={50}
                  allowClear
                  onChange={(event) => setReasonCategory(event.target.value)}
                />
              </div>
            )}

            {needLevel && (
              <div>
                <p className="mb-1 text-[12px] text-[var(--color-slate)]">偏差分级（通过必填）</p>
                <Select
                  value={deviationLevel}
                  placeholder="选择偏差分级"
                  className="w-full"
                  allowClear
                  options={DEVIATION_LEVEL_OPTIONS.map((item) => ({ value: item.value, label: item.label }))}
                  onChange={(value) => setDeviationLevel(value)}
                />
              </div>
            )}
          </div>
        )}

        <Input.TextArea
          rows={3}
          value={content}
          maxLength={2000}
          showCount
          placeholder={canResubmit ? '重新提交说明（可选）' : '审核意见（退回时必填）'}
          onChange={(event) => setContent(event.target.value)}
        />

        {/* 卡片内操作区统一：顶部细分隔线 + 右对齐，与调查/报告/最终编号三张卡一致 */}
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-[var(--color-hairline)] pt-3">
          {canReject && (
            <Button
              danger
              icon={<RollbackOutlined />}
              loading={pending === 'rejected'}
              onClick={() => runReview('rejected')}
            >
              退回
            </Button>
          )}
          {canApprove && (
            <Button
              type="primary"
              icon={<CheckOutlined />}
              loading={pending === 'approved'}
              onClick={() => runReview('approved')}
            >
              通过
            </Button>
          )}
          {canResubmit && (
            <Button
              type="primary"
              icon={<SendOutlined />}
              loading={pending === 'resubmit'}
              onClick={runResubmit}
            >
              重新提交
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}