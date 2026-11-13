'use client'

import { useState } from 'react'
import { Alert, App, Button, Descriptions, Input, Tag } from 'antd'
import { NumberOutlined } from '@ant-design/icons'
import { submitDeviationFinalCode } from '@/actions/quality'
import type { DeviationLedgerDetail } from '@/types/quality'
import { SectionCard } from './SectionCard'
import { isSectionVisible } from './detailSections'

interface FinalCodeCardProps {
  ledger: DeviationLedgerDetail
  onUpdated: (ledger: DeviationLedgerDetail) => void
}

/** 最终编号：质量负责人归档前填写，写入后偏差关闭 */
export function FinalCodeCard({ ledger, onUpdated }: FinalCodeCardProps) {
  const { message } = App.useApp()
  const [finalCode, setFinalCode] = useState('')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const canSubmit = (ledger.allowed_actions ?? []).includes('final_code')
  const closed = Boolean(ledger.final_code)

  // 可见性判断与分区导航共用同一份规则（detailSections.isSectionVisible）
  if (!isSectionVisible('final-code', ledger)) {
    return null
  }

  const handleSubmit = async () => {
    if (!finalCode.trim()) {
      message.warning('请输入最终编号')
      return
    }
    setSubmitting(true)
    const response = await submitDeviationFinalCode(ledger.id, {
      final_code: finalCode.trim(),
      content: content.trim(),
    })
    setSubmitting(false)
    if (response.code === 200 && response.data) {
      setFinalCode('')
      setContent('')
      onUpdated(response.data)
      message.success('最终编号已保存，偏差已关闭')
    } else {
      message.error(response.message)
    }
  }

  return (
    <SectionCard section="final-code" ledger={ledger}>
      <div className="flex flex-col gap-3">
        {closed && (
          <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} bordered>
            <Descriptions.Item label="最终编号">
              <span className="font-mono text-[13px] font-semibold">{ledger.final_code}</span>
            </Descriptions.Item>
            <Descriptions.Item label="当前状态">
              <Tag color="green">{ledger.status_label}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="系统编号">
              <span className="whitespace-nowrap font-mono text-[13px]">{ledger.code}</span>
            </Descriptions.Item>
          </Descriptions>
        )}

        {canSubmit && (
          <>
            <Alert
              type="info"
              showIcon
              title="填写最终编号后，该偏差将关闭并完成本次流转。"
              description="最终编号会作为台账展示编号，请与纸质/系统归档编号保持一致。"
            />
            <div>
              <p className="mb-1 text-[12px] text-[var(--color-slate)]">最终编号</p>
              <Input
                value={finalCode}
                maxLength={32}
                placeholder="如 DEV-2026-0001"
                prefix={<NumberOutlined />}
                onChange={(event) => setFinalCode(event.target.value)}
              />
            </div>
            <div>
              <p className="mb-1 text-[12px] text-[var(--color-slate)]">备注（可选）</p>
              <Input.TextArea
                rows={3}
                value={content}
                maxLength={2000}
                showCount
                placeholder="归档说明"
                onChange={(event) => setContent(event.target.value)}
              />
            </div>
            <div className="flex flex-wrap justify-end gap-2 border-t border-[var(--color-hairline)] pt-3">
              <Button type="primary" loading={submitting} onClick={handleSubmit}>
                提交并关闭
              </Button>
            </div>
          </>
        )}
      </div>
    </SectionCard>
  )
}