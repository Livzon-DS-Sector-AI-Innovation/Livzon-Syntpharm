'use client'

import { useState } from 'react'
import { App, Button, Drawer, Empty, Flex, Input, Segmented, Skeleton, Space, Tabs, Tag, Typography } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { updateReportGenOpinion } from '@/actions/research/report-gen'
import { fetchReportGenOpinionDigests, fetchReportGenOpinions } from '@/lib/api/client/research/report-gen'
import {
  REPORT_GEN_DIGEST_STATUS_META,
  REPORT_GEN_OPINION_STATUS_META,
  type ReportGenOpinionStatus,
} from '@/types/research/report-gen'

interface Props {
  open: boolean
  onClose: () => void
}

type OpinionFilter = 'all' | ReportGenOpinionStatus

/**
 * 意见库抽屉：跨报告归并后的历史意见 + 每次生成前的汇总快照。
 *
 * 为什么要有这个入口：意见以前只在「哪一版报告」下能看到，换一份报告就再也找不到；
 * 而真正影响后续生成的恰恰是这些反复出现的要求，必须能集中看、能停用。
 */
export function ReportGenOpinionLibrary({ open, onClose }: Props) {
  const { message: msgApi } = App.useApp()
  const queryClient = useQueryClient()
  const [tab, setTab] = useState<'opinions' | 'digests'>('opinions')
  const [filter, setFilter] = useState<OpinionFilter>('all')
  const [keyword, setKeyword] = useState('')
  const [updating, setUpdating] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['report-gen-opinions', filter, keyword],
    queryFn: () =>
      fetchReportGenOpinions({
        status: filter === 'all' ? undefined : filter,
        keyword: keyword.trim() || undefined,
        limit: 200,
      }),
    enabled: open && tab === 'opinions',
    refetchOnWindowFocus: false,
  })

  const { data: digests, isLoading: digestsLoading } = useQuery({
    queryKey: ['report-gen-opinion-digests'],
    queryFn: () => fetchReportGenOpinionDigests(20),
    enabled: open && tab === 'digests',
    refetchOnWindowFocus: false,
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['report-gen-opinions'] })
    void queryClient.invalidateQueries({ queryKey: ['report-gen-opinion-digests'] })
  }

  const handleToggle = async (id: string, status: ReportGenOpinionStatus) => {
    setUpdating(id)
    try {
      await updateReportGenOpinion(id, status === 'active' ? 'disabled' : 'active')
      msgApi.success(status === 'active' ? '已停用，不再影响后续生成' : '已恢复参与汇总')
      refresh()
    } catch (e: unknown) {
      msgApi.error(e instanceof Error ? e.message : '更新失败')
    } finally {
      setUpdating('')
    }
  }

  const opinions = data?.items ?? []
  const digestItems = digests?.items ?? []

  return (
    <Drawer
      title="意见库"
      open={open}
      onClose={onClose}
      width={720}
      extra={
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          生效 {data?.active_count ?? 0} / 共 {data?.total ?? 0} 条
        </Typography.Text>
      }
    >
      <Tabs
        activeKey={tab}
        onChange={(key) => setTab(key as 'opinions' | 'digests')}
        items={[
          {
            key: 'opinions',
            label: '历史意见',
            children: (
              <Flex vertical gap={12}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  每条意见按相同写法归并并累计次数；次数越高越普遍。每次生成前 AI 会把生效中的意见
                  汇总成一段写作要求再交给写作模型；停用后不再参与。
                </Typography.Text>
                <Flex gap={8} wrap>
                  <Segmented
                    size="small"
                    value={filter}
                    onChange={(value) => setFilter(value as OpinionFilter)}
                    options={[
                      { value: 'all', label: '全部' },
                      { value: 'active', label: '生效中' },
                      { value: 'disabled', label: '已停用' },
                    ]}
                  />
                  <Input
                    size="small"
                    allowClear
                    value={keyword}
                    onChange={(event) => setKeyword(event.target.value)}
                    prefix={<SearchOutlined style={{ color: '#8C8C8C' }} />}
                    placeholder="搜意见内容"
                    style={{ flex: 1, minWidth: 200 }}
                  />
                </Flex>

                {isLoading && <Skeleton active paragraph={{ rows: 6 }} title={false} />}
                {!isLoading && opinions.length === 0 && (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有沉淀出意见" />
                )}
                <Flex vertical gap={8}>
                  {opinions.map((item, index) => {
                    const meta = REPORT_GEN_OPINION_STATUS_META[item.status as ReportGenOpinionStatus]
                    return (
                      <div
                        key={item.id}
                        style={{
                          border: '1px solid #EDEFF2',
                          borderRadius: 8,
                          padding: '10px 12px',
                          background: item.status === 'active' ? '#FFFFFF' : '#FAFBFC',
                        }}
                      >
                        <Flex justify="space-between" gap={12} wrap>
                          <Space size={8} wrap>
                            <Tag color={meta?.color ?? 'default'} style={{ margin: 0 }}>
                              {meta?.label ?? item.status}
                            </Tag>
                            <Tag color="blue" style={{ margin: 0 }}>
                              提出 {item.hit_count} 次
                            </Tag>
                            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                              第 {index + 1} 条
                            </Typography.Text>
                          </Space>
                          <Button
                            size="small"
                            loading={updating === item.id}
                            onClick={() => void handleToggle(item.id, item.status as ReportGenOpinionStatus)}
                          >
                            {item.status === 'active' ? '停用' : '恢复'}
                          </Button>
                        </Flex>
                        <div style={{ marginTop: 6, fontSize: 13, color: '#1F2329', whiteSpace: 'pre-wrap' }}>
                          {item.content}
                        </div>
                        {item.last_seen_at && (
                          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                            最近提出：{new Date(item.last_seen_at).toLocaleString()}
                          </Typography.Text>
                        )}
                      </div>
                    )
                  })}
                </Flex>
              </Flex>
            ),
          },
          {
            key: 'digests',
            label: '生成前汇总',
            children: (
              <Flex vertical gap={12}>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  每次生成前 AI 归并出的写作要求都会留档，详情页显示的就是这里最新的一份；
                  相同意见集合会复用上一份，避免措辞漂移。
                </Typography.Text>
                {digestsLoading && <Skeleton active paragraph={{ rows: 6 }} title={false} />}
                {!digestsLoading && digestItems.length === 0 && (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有生成过意见汇总" />
                )}
                <Flex vertical gap={8}>
                  {digestItems.map((item) => {
                    const meta = REPORT_GEN_DIGEST_STATUS_META[item.status] ?? REPORT_GEN_DIGEST_STATUS_META.ok
                    return (
                      <div key={item.id} style={{ border: '1px solid #EDEFF2', borderRadius: 8, padding: '10px 12px' }}>
                        <Space size={8} wrap style={{ marginBottom: 6 }}>
                          <Tag color={meta.color} style={{ margin: 0 }}>
                            {meta.label}
                          </Tag>
                          <Tag style={{ margin: 0 }}>{item.item_count} 条意见</Tag>
                          {item.model_name && <Tag style={{ margin: 0 }}>{item.model_name}</Tag>}
                          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                            {new Date(item.created_at).toLocaleString()}
                          </Typography.Text>
                        </Space>
                        <div style={{ fontSize: 13, color: '#1F2329', whiteSpace: 'pre-wrap' }}>{item.digest_text}</div>
                      </div>
                    )
                  })}
                </Flex>
              </Flex>
            ),
          },
        ]}
      />
    </Drawer>
  )
}