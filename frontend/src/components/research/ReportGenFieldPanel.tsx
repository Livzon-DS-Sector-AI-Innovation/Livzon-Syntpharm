'use client'

import { useMemo, useState } from 'react'
import { Empty, Flex, Input, Segmented, Skeleton, Tag, Typography } from 'antd'
import { DownOutlined, RightOutlined, SearchOutlined } from '@ant-design/icons'
import {
  APPENDED_ITEM_KINDS,
  REPORT_GEN_FIELD_FILTERS,
  fieldKeyLabel,
  fieldStateMeta,
  matchFieldFilter,
  type ReportGenFieldFilter,
  type ReportGenFieldItem,
  type ReportGenOutline,
  type ReportGenOutlineSection,
} from '@/types/research/report-gen'

interface Props {
  data?: ReportGenOutline
  loading: boolean
  error?: Error | null
  selectedKey: string | null
  onSelect: (item: ReportGenFieldItem) => void
}

interface FieldGroup {
  key: string
  /** null = AI 追加内容（母本里没有对应位置） */
  section: ReportGenOutlineSection | null
  items: ReportGenFieldItem[]
}

// 参考资料只在「参考资料」页签展示，不混进位置清单
const APPENDED_KINDS = APPENDED_ITEM_KINDS

function isAppended(item: ReportGenFieldItem): boolean {
  return APPENDED_KINDS.includes(item.kind)
}

function summaryOf(item: ReportGenFieldItem): string {
  const value = (item.value ?? '').trim()
  if (value) return value.replace(/\s+/g, ' ')
  const text = (item.text ?? '').trim()
  if (text) return text
  return item.reason ?? '（空）'
}

function matchKeyword(item: ReportGenFieldItem, keyword: string): boolean {
  if (!keyword) return true
  const haystack = [item.label, item.section, item.value, item.text, item.source_name, item.key]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
  return haystack.includes(keyword.toLowerCase())
}

/**
 * 可写字段清单：详情页右栏的主视图，未选中任何位置时显示。
 *
 * 为什么必须由后端合并：`rd_report_gen_slots` 只记「写过的地方」，没写的位置没有行，
 * 只查写入记录会得到一份「全都写完了」的假象。这里展示的是母本全量位置 + 写入状态。
 */
export function ReportGenFieldPanel({ data, loading, error, selectedKey, onSelect }: Props) {
  const [filter, setFilter] = useState<ReportGenFieldFilter>('all')
  const [keyword, setKeyword] = useState('')
  const [collapsed, setCollapsed] = useState<string[]>([])
  const [hovered, setHovered] = useState<string | null>(null)

  const groups = useMemo<FieldGroup[]>(() => {
    const items = (data?.items ?? []).filter(
      (item) => matchFieldFilter(item, filter) && matchKeyword(item, keyword.trim()),
    )
    const bySection = new Map<number, ReportGenFieldItem[]>()
    const appended: ReportGenFieldItem[] = []
    for (const item of items) {
      if (isAppended(item)) {
        appended.push(item)
        continue
      }
      const sectionIndex = item.section_index ?? -1
      const list = bySection.get(sectionIndex) ?? []
      list.push(item)
      bySection.set(sectionIndex, list)
    }
    const result: FieldGroup[] = (data?.sections ?? [])
      .filter((section) => bySection.has(section.index))
      .map((section) => ({
        key: `s${section.index}`,
        section,
        items: bySection.get(section.index) ?? [],
      }))
    if (appended.length) result.push({ key: 'appended', section: null, items: appended })
    return result
  }, [data, filter, keyword])

  const stats = data?.stats
  const needsReview = (stats?.needs_verify ?? 0) + (stats?.conflict ?? 0) + (stats?.anchor_unresolved ?? 0)

  const toggle = (key: string) => {
    setCollapsed((prev) => (prev.includes(key) ? prev.filter((item) => item !== key) : [...prev, key]))
  }

  if (loading && !data) {
    return (
      <div style={{ padding: 16 }}>
        <Skeleton active paragraph={{ rows: 8 }} title={false} />
      </div>
    )
  }

  if (error && !data) {
    return (
      <div style={{ padding: 24 }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description={`可写字段清单取不到：${error.message}`}
        />
      </div>
    )
  }

  return (
    <Flex vertical style={{ height: '100%', minHeight: 0 }}>
      <div style={{ padding: '12px 16px 10px', borderBottom: '1px solid #EDEFF2' }}>
        <Flex gap={12} wrap style={{ fontSize: 12, color: '#5A6472' }}>
          <span>AI 可写 {stats?.writable_total ?? 0}</span>
          <span style={{ color: '#1677FF' }}>已写 {stats?.written ?? 0}</span>
          <span style={{ color: '#8C8C8C' }}>空位 {stats?.blank ?? 0}</span>
          {needsReview > 0 && <span style={{ color: '#D97706' }}>需核对 {needsReview}</span>}
          {(stats?.manual ?? 0) > 0 && <span style={{ color: '#16A34A' }}>人工改过 {stats?.manual}</span>}
          <span>母本固定 {stats?.locked ?? 0}</span>
        </Flex>
        <Flex gap={8} align="center" style={{ marginTop: 10 }} wrap>
          <Segmented
            size="small"
            value={filter}
            onChange={(value) => setFilter(value as ReportGenFieldFilter)}
            options={[...REPORT_GEN_FIELD_FILTERS]}
          />
          <Input
            size="small"
            allowClear
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            prefix={<SearchOutlined style={{ color: '#8C8C8C' }} />}
            placeholder="搜位置、内容或来源"
            style={{ flex: 1, minWidth: 180 }}
          />
        </Flex>
      </div>

      <div style={{ flex: 1, minHeight: 0, overflow: 'auto', padding: '4px 0 16px' }}>
        {groups.length === 0 && (
          <div style={{ padding: 32 }}>
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有符合条件的位置" />
          </div>
        )}
        {groups.map((group) => {
          const folded = collapsed.includes(group.key)
          const label = group.section?.label ?? 'AI 追加内容'
          const written = group.items.filter((item) => item.state !== 'blank').length
          return (
            <div key={group.key}>
              <button
                type="button"
                onClick={() => toggle(group.key)}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '10px 16px 6px',
                  border: 'none',
                  background: 'transparent',
                  cursor: 'pointer',
                  textAlign: 'left',
                }}
              >
                {folded ? (
                  <RightOutlined style={{ fontSize: 10, color: '#8C8C8C' }} />
                ) : (
                  <DownOutlined style={{ fontSize: 10, color: '#8C8C8C' }} />
                )}
                <span style={{ fontSize: 12, fontWeight: 600, color: '#1F2329' }}>{label}</span>
                <span style={{ fontSize: 11, color: '#8C8C8C' }}>
                  {written}/{group.items.length}
                </span>
              </button>
              {!folded &&
                group.items.map((item) => {
                  const meta = fieldStateMeta(item.state, item.edit_source)
                  const selected = selectedKey === item.key
                  return (
                    <button
                      type="button"
                      key={item.key}
                      onClick={() => onSelect(item)}
                      onMouseEnter={() => setHovered(item.key)}
                      onMouseLeave={() => setHovered(null)}
                      style={{
                        width: '100%',
                        display: 'flex',
                        alignItems: 'stretch',
                        gap: 10,
                        padding: '8px 12px',
                        border: 'none',
                        borderLeft: `3px solid ${meta.text}`,
                        background: selected ? '#E6F4FF' : hovered === item.key ? '#F5F7FA' : 'transparent',
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <span style={{ flex: 1, minWidth: 0 }}>
                        <Flex gap={6} align="center" wrap>
                          <span style={{ fontSize: 13, fontWeight: 500, color: '#1F2329' }}>{item.label}</span>
                          <Tag
                            color={meta.color}
                            style={{ margin: 0, fontSize: 11, lineHeight: '18px', borderStyle: meta.dashed ? 'dashed' : undefined }}
                          >
                            {meta.label}
                          </Tag>
                          {item.kind === 'table_cell' && (
                            <Tag style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}>表格</Tag>
                          )}
                          {item.writable === false && (
                            <Tag style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}>母本固定</Tag>
                          )}
                          {item.human_locked && (
                            <Tag color="green" style={{ margin: 0, fontSize: 11, lineHeight: '18px' }}>
                              人工确认
                            </Tag>
                          )}
                        </Flex>
                        <div
                          style={{
                            marginTop: 3,
                            fontSize: 12,
                            color: item.state === 'blank' ? '#8C8C8C' : '#5A6472',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {summaryOf(item)}
                        </div>
                        {item.source_name && (
                          <div style={{ marginTop: 2, fontSize: 11, color: '#8C8C8C' }}>
                            来源：{item.source_name}
                            {item.confidence !== null && item.confidence !== undefined
                              ? ` · 置信度 ${Math.round(item.confidence * 100)}%`
                              : ''}
                          </div>
                        )}
                      </span>
                      <span
                        style={{
                          alignSelf: 'center',
                          fontSize: 11,
                          color: '#8C8C8C',
                          whiteSpace: 'nowrap',
                          fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                        }}
                      >
                        {fieldKeyLabel(item.key)}
                      </span>
                    </button>
                  )
                })}
            </div>
          )
        })}
      </div>

      {data && (
        <div style={{ padding: '8px 16px', borderTop: '1px solid #EDEFF2', fontSize: 11, color: '#8C8C8C' }}>
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            母本 {data.template_paragraph_count} 段 + {data.template_table_count} 张表
            {data.document_paragraph_count !== null && data.document_paragraph_count !== undefined
              ? ` · 成品 ${data.document_paragraph_count} 段`
              : ''}
          </Typography.Text>
        </div>
      )}
    </Flex>
  )
}