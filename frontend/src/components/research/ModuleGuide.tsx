'use client'

import { Card, Steps } from 'antd'
import type { GuideStep } from '@/lib/ui/research-copy'

interface ModuleGuideProps {
  title: string
  steps: readonly GuideStep[]
  /** 已经有数据时传 true：标题保留、步骤收起成一行，避免每次进页面都被占掉半屏 */
  compact?: boolean
}

/**
 * 模块顶部的「三步就能用」引导。
 *
 * 这三个页面原先只有零散的 Tooltip，新用户要自己拼出「先做什么、再做什么」。这里把
 * 主流程固定成 1-2-3 摆出来；有数据之后自动收成一行，不干扰熟练用户。
 */
export function ModuleGuide({ title, steps, compact = false }: ModuleGuideProps) {
  if (compact) {
    return (
      <div
        style={{
          marginBottom: 12,
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 8,
          fontSize: 12,
          color: '#595959',
        }}
      >
        <span style={{ color: '#8C8C8C' }}>{title}：</span>
        {steps.map((step, index) => (
          <span
            key={step.title}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '2px 10px',
              borderRadius: 12,
              background: '#F5F5F5',
            }}
          >
            <span
              style={{
                width: 16,
                height: 16,
                borderRadius: '50%',
                border: '1px solid #BFBFBF',
                background: '#FFFFFF',
                color: '#595959',
                fontSize: 11,
                lineHeight: '14px',
                fontWeight: 600,
                textAlign: 'center',
                flex: '0 0 auto',
              }}
            >
              {index + 1}
            </span>
            {step.title}
          </span>
        ))}
      </div>
    )
  }
  return (
    <Card size="small" style={{ marginBottom: 12 }} styles={{ body: { padding: '16px 20px' } }}>
      <Steps
        size="small"
        items={steps.map((step) => ({ title: step.title, description: step.description }))}
      />
    </Card>
  )
}