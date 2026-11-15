'use client'

import { useState } from 'react'
import { App, Button, Card, Empty, Flex, Input, Space, Tag, Typography } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createReportGenFeedback, updateReportGenFeedback } from '@/actions/research/report-gen'
import { fetchReportGenFeedback } from '@/lib/api/client/research/report-gen'
import type { ReportGenFeedback } from '@/types/research/report-gen'
import { ReportGenOpinionLibrary } from './ReportGenOpinionLibrary'

interface Props {
  jobId: string
  /** 生成中禁写：意见是对已成稿的评审，跑的时候提了也没处落 */
  disabled?: boolean
}

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
export function ReportGenFeedbackPanel({ jobId, disabled }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [updating, setUpdating] = useState('')
  const [libraryOpen, setLibraryOpen] = useState(false)

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
      // 填充项清单已下线，意见统一按整篇提；slot_key 留空由后端按整篇处理
      await createReportGenFeedback(jobId, { slot_key: null, content: text })
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

  return (
    <Card
      title="修改意见"
      extra={
        <Space size={8}>
          <Tag color={openCount > 0 ? 'processing' : 'default'} style={{ margin: 0 }}>
            待落实 {openCount} 条
          </Tag>
          <Button size="small" onClick={() => setLibraryOpen(true)}>
            意见库
          </Button>
        </Space>
      }
      style={{ borderRadius: 12 }}
    >
      <Flex vertical gap={12}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          意见写成「哪里不对 + 要改成什么」最有用。每条意见都会归入「意见库」并累计出现次数；
          下次生成时 AI 会先把意见库汇总成写作要求再动笔，未落实的具体条目也会一并带上。
        </Typography.Text>

        <Flex gap={8} wrap>
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

      <ReportGenOpinionLibrary open={libraryOpen} onClose={() => setLibraryOpen(false)} />
    </Card>
  )
}