'use client'

import { useState } from 'react'
import { App, Button, Card, Empty, Flex, Input, Select, Space, Tag, Typography } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createReportGenFeedback,
  promoteReportGenFeedback,
  updateReportGenFeedback,
} from '@/actions/research/report-gen'
import { fetchReportGenFeedback } from '@/lib/api/client/research/report-gen'
import type { ReportGenFeedback, ReportGenSlot } from '@/types/research/report-gen'

interface Props {
  jobId: string
  slots: ReportGenSlot[]
  /** 生成中禁写：意见是对已成稿的评审，跑的时候提了也没处落 */
  disabled?: boolean
}

/** 范围下拉的「整篇」哨兵值：antd Select 不接受 null 作为选中值 */
const WHOLE = '__whole__'

const STATUS_META: Record<string, { label: string; color: string }> = {
  open: { label: '待落实', color: 'processing' },
  applied: { label: '已落实', color: 'success' },
  ignored: { label: '不采纳', color: 'default' },
}

/**
 * 评审修改意见：对某一版报告逐条提具体改法。
 *
 * 为什么值得单独做一块而不是让人把意见抄进补充说明：抄进补充说明的意见是一次性的，
 * 没人记得住哪条改了、哪条没改；这里每条都有状态，未落实的会在下次生成时自动带上。
 */
export function ReportGenFeedbackPanel({ jobId, slots, disabled }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [scope, setScope] = useState<string>(WHOLE)
  const [submitting, setSubmitting] = useState(false)
  const [updating, setUpdating] = useState('')
  const [promoting, setPromoting] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['report-gen-feedback', jobId],
    queryFn: () => fetchReportGenFeedback(jobId),
    refetchOnWindowFocus: false,
  })

  const items = data?.items ?? []
  const openCount = data?.open_count ?? 0

  const refresh = () => queryClient.invalidateQueries({ queryKey: ['report-gen-feedback', jobId] })

  const handleSubmit = async () => {
    const text = content.trim()
    if (!text) {
      msgApi.warning('先写清楚要改什么')
      return
    }
    setSubmitting(true)
    try {
      await createReportGenFeedback(jobId, {
        slot_key: scope === WHOLE ? null : scope,
        content: text,
      })
      setContent('')
      msgApi.success('已记录，下次生成会带上')
      refresh()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleStatus = async (item: ReportGenFeedback, status: 'open' | 'ignored') => {
    setUpdating(item.id)
    try {
      await updateReportGenFeedback(item.id, status)
      msgApi.success(status === 'ignored' ? '已标为不采纳' : '已重新打开')
      refresh()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '更新失败')
    } finally {
      setUpdating('')
    }
  }

  const handlePromote = async (item: ReportGenFeedback) => {
    setPromoting(item.id)
    try {
      await promoteReportGenFeedback(item.id)
      msgApi.success('已存成示例写法，下次用同一个模板生成时会参考它')
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '存成示例失败，请稍后重试')
    } finally {
      setPromoting('')
    }
  }

  return (
    <Card
      title="修改意见"
      extra={
        <Tag color={openCount > 0 ? 'processing' : 'default'} style={{ margin: 0 }}>
          待落实 {openCount} 条
        </Tag>
      }
      style={{ borderRadius: 12 }}
    >
      <Flex vertical gap={12}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          意见写成「哪里不对 + 要改成什么」最有用。还没落实的意见，会在下次生成（包括点「重新生成」）时自动交给
          AI 处理，并在「待补充」说明里逐条回应。已经落实、你也认可的意见，可以点「存成示例写法」，下次用同一个模板生成就照这个写法填。
        </Typography.Text>

        <Flex gap={8} wrap>
          <Select
            value={scope}
            onChange={setScope}
            style={{ width: 200 }}
            disabled={disabled || submitting}
            options={[
              { value: WHOLE, label: '整篇' },
              ...slots.map((slot) => ({ value: slot.slot_key, label: slot.slot_label || slot.slot_key })),
            ]}
          />
          <Input.TextArea
            value={content}
            onChange={(event) => setContent(event.target.value)}
            placeholder="例如：结果与讨论只写了现象，补一句工艺参数与收率的关系"
            autoSize={{ minRows: 1, maxRows: 4 }}
            maxLength={1000}
            showCount
            disabled={disabled || submitting}
            style={{ flex: 1, minWidth: 260 }}
          />
          <Button loading={submitting} disabled={disabled} onClick={handleSubmit}>
            提意见
          </Button>
        </Flex>

        {items.length === 0 && !isLoading && (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有意见" />
        )}

        <Flex vertical gap={8}>
          {items.map((item) => {
            const meta = STATUS_META[item.status] ?? STATUS_META.open
            return (
              <div
                key={item.id}
                style={{
                  border: '1px solid #EDEFF2',
                  borderRadius: 8,
                  padding: '10px 12px',
                  background: item.status === 'open' ? '#FFFFFF' : '#FAFBFC',
                }}
              >
                <Flex justify="space-between" gap={12} wrap>
                  <Space size={8} wrap>
                    <Tag color={meta.color} style={{ margin: 0 }}>{meta.label}</Tag>
                    <Tag style={{ margin: 0 }}>{item.slot_key || '整篇'}</Tag>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {new Date(item.created_at).toLocaleString()}
                    </Typography.Text>
                    {item.applied_job_id && (
                      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                        已由后续生成落实
                      </Typography.Text>
                    )}
                  </Space>
                  <Space size={6}>
                    {item.status === 'applied' && item.slot_key && (
                      <Button
                        size="small"
                        type="link"
                        style={{ paddingInline: 0 }}
                        loading={promoting === item.id}
                        onClick={() => handlePromote(item)}
                      >
                        存成示例写法
                      </Button>
                    )}
                    {item.status === 'open' ? (
                      <Button
                        size="small"
                        loading={updating === item.id}
                        onClick={() => handleStatus(item, 'ignored')}
                      >
                        不采纳
                      </Button>
                    ) : (
                      <Button
                        size="small"
                        loading={updating === item.id}
                        onClick={() => handleStatus(item, 'open')}
                      >
                        重新打开
                      </Button>
                    )}
                  </Space>
                </Flex>
                <div style={{ marginTop: 6, fontSize: 13, color: '#1F2329', whiteSpace: 'pre-wrap' }}>
                  {item.content}
                </div>
              </div>
            )
          })}
        </Flex>
      </Flex>
    </Card>
  )
}