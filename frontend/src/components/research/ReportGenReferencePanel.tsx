'use client'

import { Empty, Flex, Skeleton, Tag, Tooltip } from 'antd'
import type { ReportGenOutline } from '@/types/research/report-gen'

interface Props {
  data?: ReportGenOutline
  loading: boolean
  /** 点一条位置：跳到正文对应处并高亮 */
  onLocate: (key: string) => void
}

/**
 * 参考资料（引用源）：只展示，不写进 Word 文档。
 *
 * 引用源属于审阅信息，写进正文会挤占母本版面、让成稿多出一章；这里按来源聚合，
 * 点位置标签可以回到正文对应处核对。
 */
export function ReportGenReferencePanel({ data, loading, onLocate }: Props) {
  const references = data?.references ?? []

  if (loading && !data) {
    return (
      <div style={{ padding: 16 }}>
        <Skeleton active paragraph={{ rows: 6 }} title={false} />
      </div>
    )
  }

  return (
    <Flex vertical style={{ height: '100%', minHeight: 0 }}>
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid #EDEFF2',
          fontSize: 12,
          color: '#5A6472',
          lineHeight: 1.6,
        }}
      >
        引用源不写进 Word 正文，只在这里作参考；点位置可跳到正文对应处。
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '4px 0 16px' }}>
        {references.length === 0 && (
          <div style={{ padding: 32 }}>
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description={data ? '本次生成没有带来源的填写内容' : '正在读取参考资料'}
            />
          </div>
        )}
        {references.map((group) => (
          <div key={group.index} style={{ padding: '10px 16px', borderBottom: '1px dashed #F0F0F0' }}>
            <Flex gap={8} align="center" wrap>
              <Tag color="processing" style={{ margin: 0 }}>
                [{group.index}]
              </Tag>
              <span style={{ fontSize: 13, fontWeight: 500, color: '#1F2329' }}>{group.name}</span>
              <span style={{ fontSize: 11, color: '#8C8C8C' }}>共 {group.total ?? 0} 处</span>
            </Flex>
            <Flex gap={6} wrap style={{ marginTop: 8 }}>
              {(group.locations ?? []).map((location, index) => {
                const key = location.key
                return key ? (
                  <Tooltip key={`${key}-${index}`} title="定位到正文这一处">
                    <Tag color="blue" style={{ margin: 0, cursor: 'pointer' }} onClick={() => onLocate(key)}>
                      {location.label}
                    </Tag>
                  </Tooltip>
                ) : (
                  <Tag key={`${location.label}-${index}`} style={{ margin: 0 }}>
                    {location.label}
                  </Tag>
                )
              })}
            </Flex>
          </div>
        ))}
      </div>

      <div style={{ padding: '8px 16px', borderTop: '1px solid #EDEFF2', fontSize: 11, color: '#8C8C8C' }}>
        共 {references.length} 条来源
      </div>
    </Flex>
  )
}