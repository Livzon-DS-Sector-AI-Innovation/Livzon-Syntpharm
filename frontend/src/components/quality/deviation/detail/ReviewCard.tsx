'use client'

import { useMemo, useState } from 'react'
import { Alert, App, Button, Input, Modal, Select, Tag } from 'antd'
import { CheckOutlined, RollbackOutlined, SendOutlined } from '@ant-design/icons'
import { resubmitDeviation, reviewDeviation } from '@/actions/quality'
import type { DeviationLedgerDetail } from '@/types/quality'
import { DEVIATION_LEVEL_OPTIONS } from '../constants'
import { SectionCard } from './SectionCard'
import { isSectionVisible } from './detailSections'

interface ReviewCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

/** 审核动作卡：意见 + 通过/退回、QA 审核原因分类、QA 负责人分级、退回后重新提交（历史数据） */
export function ReviewCard({ ledger, onUpdated }: ReviewCardProps) {
  const { message } = App.useApp()
  const [content, setContent] = useState('')
  const [reasonCategory, setReasonCategory] = useState<string | undefined>(ledger.reason_category ?? undefined)
  const [deviationLevel, setDeviationLevel] = useState<string | undefined>(ledger.deviation_level ?? undefined)
  const [pending, setPending] = useState<'approved' | 'rejected' | 'resubmit' | null>(null)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectTarget, setRejectTarget] = useState<string | undefined>(undefined)

  const actions = ledger.allowed_actions ?? []
  const canApprove = actions.includes('approve')
  const canReject = actions.includes('reject')
  const canResubmit = actions.includes('resubmit') && ledger.status === 'returned'
  const needReason = actions.includes('reason_category')
  const needLevel = actions.includes('grade')
  const returnTargets = ledger.return_targets ?? []

  const lastReject = useMemo(() => {
    const rejected = (ledger.review_opinions ?? []).filter((item) => item.result === 'rejected')
    return rejected.length > 0 ? rejected[rejected.length - 1] : null
  }, [ledger.review_opinions])
  // 新语义下退回直接落到目标环节待办，status 不再是 returned，需靠 returned_step 判断
  const returnedTo = ledger.status === 'returned' || ledger.returned_step ? ledger.returned_step_label : null

  // 可见性判断与分区导航共用同一份规则（detailSections.isSectionVisible）
  if (!isSectionVisible('review', ledger)) {
    return null
  }

  const runReview = async (result: 'approved' | 'rejected', targetStep?: string) => {
    const opinion = content.trim()
    if (result === 'rejected' && !targetStep && returnTargets.length > 0) {
      message.warning('请选择退回目标环节')
      return
    }
    if (result === 'rejected' && !opinion) {
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
      content: opinion,
      target_step: result === 'rejected' ? (targetStep ?? null) : undefined,
      reason_category: needReason ? (reasonCategory?.trim() || null) : undefined,
      deviation_level: needLevel ? (deviationLevel ?? null) : undefined,
    })
    setPending(null)
    if (response.code === 200 && response.data) {
      setContent('')
      onUpdated(response.data)
      if (result === 'approved') {
        message.success('已通过并流转至下一环节')
      } else {
        const label = returnTargets.find((item) => item.step === targetStep)?.label
        message.success(label ? `已退回到「${label}」` : '已退回')
      }
    } else {
      message.error(response.message)
    }
  }

  const openReject = () => {
    if (returnTargets.length === 0) {
      message.warning('当前环节没有可退回的前置环节')
      return
    }
    // 退回意见统一取上方「审核意见」，弹窗只做节点选择
    if (!content.trim()) {
      message.warning('请先在上方填写退回意见')
      return
    }
    setRejectTarget(returnTargets[returnTargets.length - 1]?.step)
    setRejectOpen(true)
  }

  const runReject = async () => {
    if (!rejectTarget) {
      message.warning('请选择退回目标环节')
      return
    }
    if (!content.trim()) {
      message.warning('退回时必须填写退回意见')
      return
    }
    await runReview('rejected', rejectTarget)
    setRejectOpen(false)
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
    <SectionCard
      section="review"
      ledger={ledger}
      badge={
        <Tag color={ledger.status === 'returned' ? 'red' : 'gold'}>
          {ledger.current_step_label ?? ledger.status_label}
        </Tag>
      }
    >
      <div className="flex flex-col gap-3">
        {(ledger.status === 'returned' || returnedTo) && lastReject && (
          <Alert
            type="warning"
            showIcon
            title={
              returnedTo
                ? `已从「${lastReject.step_label ?? ledger.current_step_label ?? '上一环节'}」退回到「${returnedTo}」`
                : `已从「${lastReject.step_label ?? '上一环节'}」退回`
            }
            description={
              <span className="whitespace-pre-wrap break-words">
                {lastReject.content || '未填写退回意见'}
                {lastReject.author_name ? `（${lastReject.author_name}）` : ''}
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
            <Button danger icon={<RollbackOutlined />} loading={pending === 'rejected'} onClick={openReject}>
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

      <Modal
        open={rejectOpen}
        title="退回到指定环节"
        okText="确认退回"
        cancelText="取消"
        okButtonProps={{ danger: true, loading: pending === 'rejected' }}
        onOk={runReject}
        onCancel={() => setRejectOpen(false)}
        destroyOnHidden
      >
        <div className="flex flex-col gap-3">
          <div>
            <p className="mb-1 text-[13px] text-[var(--color-slate)]">退回目标环节</p>
            <Select
              value={rejectTarget}
              className="w-full"
              placeholder="选择退回到哪个环节"
              options={returnTargets.map((item) => ({
                value: item.step,
                label: `${item.label}（${item.role_label}）`,
              }))}
              onChange={(value) => setRejectTarget(value)}
            />
            <p className="mt-1 text-[12px] text-[var(--color-stone)]">
              退回后记录直接落到该环节待办，由该环节处理人重新处理；默认退回到上一环节。
            </p>
          </div>
          <div>
            <p className="mb-1 text-[13px] text-[var(--color-slate)]">退回意见（取上方审核意见）</p>
            <div className="max-h-[140px] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] px-3 py-2 text-[13px] text-[var(--color-ink)]">
              {content.trim()}
            </div>
            <p className="mt-1 text-[12px] text-[var(--color-stone)]">
              如需修改，取消后在页面上方「审核意见」中编辑。
            </p>
          </div>
        </div>
      </Modal>
    </SectionCard>
  )
}