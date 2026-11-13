'use client'

import { useCallback, useState } from 'react'
import { App, Button, Input, Modal, Space, Tag, Typography } from 'antd'
import { CheckCircleOutlined, ClockCircleOutlined, FileTextOutlined, RollbackOutlined } from '@ant-design/icons'
import { approveDeviationCrossDeptRow, rejectDeviationCrossDeptRow } from '@/actions/quality'
import type { DeviationAttachment, DeviationCrossDeptReviewer, DeviationLedgerDetail } from '@/types/quality'
import { AttachmentPreviewDrawer } from './AttachmentPreviewDrawer'
import { InvestigationRecordForm } from './InvestigationRecordForm'
import { SectionCard } from './SectionCard'
import { isSectionVisible } from './detailSections'

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
 * 跨部门会签卡：每行两个节点——① 部门调查（行内调查人提交调查记录）→ ② 部门负责人审核。
 * 配置了调查人的行必须先提交调查才可出现审核操作；未配置调查人的行由负责人直接审核。
 * 全部行通过后流程才流转到所属QA审核；整环节退回上一节点时所有行重置为待审核。
 */
export function CrossDeptReviewCard({ ledger, onUpdated }: CrossDeptReviewCardProps) {
  const { message } = App.useApp()
  const rows = (ledger.cross_dept_reviewers ?? []) as DeviationCrossDeptReviewer[]
  const [opinions, setOpinions] = useState<Record<string, string>>({})
  const [approving, setApproving] = useState<string | null>(null)
  const [rejectingDept, setRejectingDept] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  //: 已通过的行没有意见输入框，退回时需在弹窗补填理由
  const rejectNeedsReason = rows.some((row) => row.department === rejectingDept && row.review_state === 'approved')
  const [investigatingDept, setInvestigatingDept] = useState<string | null>(null)
  // 附件预览抽屉：与调查记录卡片共用同一个抽屉组件（左文档 + 右批注）
  const [previewAttachment, setPreviewAttachment] = useState<DeviationAttachment | null>(null)
  const closePreview = useCallback(() => setPreviewAttachment(null), [])

  const isCrossStep = ledger.current_step === 'cross_dept_head_review'
  // 可见性判断与分区导航共用同一份规则（detailSections.isSectionVisible）
  if (!isSectionVisible('cross-dept-review', ledger)) {
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

  const handleReject = async () => {
    if (!rejectingDept) return
    // 退回意见优先取行内已填写的审核意见；已通过的行没有输入框，才在弹窗里补填
    const opinion = rejectNeedsReason ? rejectReason.trim() : (opinions[rejectingDept] ?? '').trim()
    if (!opinion) {
      message.warning('退回时必须填写退回意见')
      return
    }
    const result = await rejectDeviationCrossDeptRow(ledger.id, {
      department: rejectingDept,
      opinion,
    })
    if (result.code === 200 && result.data) {
      message.success(`「${rejectingDept}」已退回，等待该部门重新调查与审核`)
      setRejectingDept(null)
      setRejectReason('')
      setOpinions((prev) => ({ ...prev, [rejectingDept]: '' }))
      onUpdated(result.data)
    } else {
      message.error(result.message)
    }
  }

  return (
    <SectionCard
      section="cross-dept-review"
      ledger={ledger}
      badge={
        <Tag color={approvedCount === rows.length ? 'success' : 'processing'}>
          {approvedCount}/{rows.length} 行已通过
        </Tag>
      }
    >
      <div className="flex flex-col gap-3">
        {rows.map((row) => {
          const approved = row.review_state === 'approved'
          const investigated = row.investigate_state === 'submitted'
          const needsInvestigation = (row.investigator_ids ?? []).length > 0
          const investigating = investigatingDept === row.department
          // 本行本人草稿（department 精确匹配）：用于按钮文案与草稿提示
          const rowDraft =
            (ledger.investigation_drafts ?? []).find((draft) => (draft.department ?? null) === row.department) ??
            null
          return (
            <div
              key={row.department}
              className="flex flex-col gap-2 rounded-lg border border-[var(--color-hairline)] p-3"
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 flex-1">
                  <Space size={6} wrap>
                    <Text strong className="text-[13px]">
                      {row.department}
                    </Text>
                    <Tag color="blue" className="!mr-0">
                      跨部门
                    </Tag>
                    <Tag color={investigated || !needsInvestigation ? 'success' : 'default'} className="!mr-0">
                      {needsInvestigation
                        ? investigated
                          ? `调查已提交${row.investigate_submitted_name ? ` · ${row.investigate_submitted_name}` : ''}`
                          : '待调查'
                        : '无调查人（负责人直接审核）'}
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
                    调查人：{(row.investigator_names ?? []).join('、') || '未指定'} · 审核人：
                    {(row.reviewer_names ?? []).join('、') || '部门负责人'}
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
                  {!approved && row.opinion && (
                    <div className="mt-1 text-[12px] text-[#c0392b]">退回理由：{row.opinion}</div>
                  )}
                  {!approved && rowDraft && !investigating && (
                    <div className="mt-1 text-[12px] text-[#2f6fed]">
                      有未提交的草稿 · 暂存于 {formatTime(rowDraft.updated_at)}
                    </div>
                  )}
                </div>
                <Space size={6} wrap className="shrink-0">
                  {!approved && needsInvestigation && row.can_investigate && (
                    <Button
                      size="small"
                      icon={<FileTextOutlined />}
                      type={investigated ? 'default' : 'primary'}
                      onClick={() => setInvestigatingDept(investigating ? null : row.department)}
                    >
                      {investigated ? '补充调查记录' : rowDraft ? '继续填写草稿' : '提交本部门调查'}
                    </Button>
                  )}
                  {!approved && row.can_approve && (
                    <Space.Compact className="w-full sm:w-[320px]">
                      <Input
                        placeholder="审核意见（可选）"
                        value={opinions[row.department] ?? ''}
                        onChange={(e) => setOpinions((prev) => ({ ...prev, [row.department]: e.target.value }))}
                        maxLength={500}
                      />
                      <Button
                        type="primary"
                        loading={approving === row.department}
                        onClick={() => handleApprove(row.department)}
                      >
                        通过
                      </Button>
                    </Space.Compact>
                  )}
                  {row.can_reject && (
                    <Button
                      size="small"
                      danger
                      icon={<RollbackOutlined />}
                      onClick={() => {
                        if (!approved && !(opinions[row.department] ?? '').trim()) {
                          message.warning('请先在该行填写退回意见')
                          return
                        }
                        setRejectingDept(row.department)
                        setRejectReason('')
                      }}
                    >
                      退回
                    </Button>
                  )}
                  {!approved && needsInvestigation && !investigated && !row.can_investigate && !row.can_approve && (
                    <span className="text-[12px] text-[var(--color-stone)]">等待该部门调查人提交调查</span>
                  )}
                </Space>
              </div>
              {investigating && !approved && (
                <InvestigationRecordForm
                  key={`${row.department}-${rowDraft?.updated_at ?? 'new'}`}
                  ledger={ledger}
                  mode="cross-dept"
                  department={row.department}
                  initialDraft={rowDraft}
                  onPreviewAttachment={setPreviewAttachment}
                  onCancel={() => setInvestigatingDept(null)}
                  onSubmitted={(next) => {
                    setInvestigatingDept(null)
                    onUpdated(next)
                  }}
                  onLedgerChange={onUpdated}
                />
              )}
            </div>
          )
        })}
      </div>
      {isCrossStep && (
        <p className="mt-3 text-[12px] text-[var(--color-stone)]">
          每行两个节点：该部门调查人提交调查记录 → 该部门负责人审核通过。配置了调查人的行需先提交调查才可审核，
          全部行通过后自动流转所属QA审核；按部门退回只重置该部门，整环节退回到上一节点时所有行会重置为待审核。
        </p>
      )}
      <Modal
        open={rejectingDept !== null}
        title={`退回「${rejectingDept ?? ''}」`}
        okText="确认退回"
        cancelText="取消"
        okButtonProps={{ danger: true }}
        onOk={handleReject}
        onCancel={() => {
          setRejectingDept(null)
          setRejectReason('')
        }}
        destroyOnHidden
      >
        <div className="flex flex-col gap-2">
          <p className="text-[12px] text-[var(--color-slate)]">
            退回后该部门的调查与审核需要重做，其他部门已通过的结果保留，流程仍停留在跨部门审核环节。
          </p>
          {rejectNeedsReason ? (
            <Input.TextArea
              rows={3}
              value={rejectReason}
              maxLength={2000}
              showCount
              placeholder="退回理由（必填）"
              onChange={(event) => setRejectReason(event.target.value)}
            />
          ) : (
            <div className="max-h-[140px] overflow-auto whitespace-pre-wrap break-words rounded-lg border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] px-3 py-2 text-[13px] text-[var(--color-ink)]">
              {opinions[rejectingDept ?? ''] ?? ''}
            </div>
          )}
        </div>
      </Modal>
      <AttachmentPreviewDrawer
        open={previewAttachment !== null}
        ledgerId={ledger.id}
        attachment={previewAttachment}
        frozen={ledger.status === 'closed' || ledger.status === 'cancelled'}
        onClose={closePreview}
        onCommentCountChange={() => undefined}
      />
    </SectionCard>
  )
}
