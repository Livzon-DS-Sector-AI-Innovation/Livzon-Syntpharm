'use client'

import { useEffect, useRef } from 'react'
import { Card, Collapse, Flex, Spin, Typography } from 'antd'
import type { ReparseProgress } from './useTemplateSlotsEditor'

/** 思考文本只留尾部：堆到几万字会让抽屉滚动变卡，看最新的增量就够了 */
const THINKING_TAIL_CHARS = 3000

function formatSeconds(total: number): string {
  if (total < 60) return `${total} 秒`
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return seconds ? `${minutes} 分 ${seconds} 秒` : `${minutes} 分`
}

/**
 * 重新分析结构时的进度面板。
 *
 * 分析要等模型几十秒到几分钟，只转一个圈会让人以为卡死：这里把「现在做到哪一步」
 * 「已经等了多久」「比预计快还是慢」和模型思考增量都摆出来，模型不返回思考内容时
 * 退化成「已输出 N 字」的活性指示。
 */
export function ReparseProgressPanel({ progress }: { progress: ReparseProgress | null }) {
  const thinkingBoxRef = useRef<HTMLDivElement>(null)
  const thinking = progress?.thinking ?? ''
  const tail = thinking.length > THINKING_TAIL_CHARS ? thinking.slice(-THINKING_TAIL_CHARS) : thinking

  useEffect(() => {
    const node = thinkingBoxRef.current
    if (node) node.scrollTop = node.scrollHeight
  }, [tail])

  if (!progress) return null

  const { stage, elapsedSeconds, estimateSeconds, contentChars } = progress
  const overdue = estimateSeconds > 0 && elapsedSeconds > estimateSeconds
  const etaHint =
    estimateSeconds > 0
      ? overdue
        ? `预计 ${formatSeconds(estimateSeconds)}，现在比预期慢，还在跑`
        : `预计 1~${formatSeconds(estimateSeconds)}`
      : ''

  return (
    <Card size="small" styles={{ body: { padding: '10px 12px' } }}>
      <Flex vertical gap={6}>
        <Flex align="center" gap={8} wrap>
          <Spin size="small" />
          <Typography.Text strong>{stage}</Typography.Text>
          <Typography.Text type="secondary">已用 {formatSeconds(elapsedSeconds)}</Typography.Text>
          {etaHint && (
            <Typography.Text type={overdue ? 'warning' : 'secondary'}>{etaHint}</Typography.Text>
          )}
        </Flex>
        {contentChars > 0 && (
          <Typography.Text type="secondary">
            模型已输出 {contentChars} 字，正在整理成填充项
          </Typography.Text>
        )}
        <Collapse
          ghost
          size="small"
          defaultActiveKey={thinking ? ['thinking'] : []}
          items={[
            {
              key: 'thinking',
              label: (
                <Typography.Text type="secondary">
                  {thinking ? '模型思考过程（实时）' : '模型思考过程（这个模型不返回思考内容）'}
                </Typography.Text>
              ),
              children: (
                <div
                  ref={thinkingBoxRef}
                  style={{
                    maxHeight: 180,
                    overflowY: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    fontSize: 12,
                    lineHeight: 1.6,
                    color: 'rgba(0, 0, 0, 0.65)',
                    background: 'rgba(0, 0, 0, 0.02)',
                    borderRadius: 6,
                    padding: 8,
                  }}
                >
                  {tail || '还没有思考内容返回，稍等几秒…'}
                </div>
              ),
            },
          ]}
        />
      </Flex>
    </Card>
  )
}