'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Col, Collapse, Row, Segmented, Space, Statistic, Tag, Typography, theme } from 'antd'
import { fetchReportGenMetrics } from '@/lib/api/client/research/report-gen'
import {
  REPORT_GEN_METRIC_DEFAULT_WINDOW,
  REPORT_GEN_METRIC_WINDOWS,
  formatRate,
  formatSeconds,
  type ReportGenMetricWindow,
  type ReportGenMetrics,
} from '@/types/research/report-gen'

const QUERY_KEY = 'report-gen-metrics'

interface Props {
  /** 服务端首屏取到的近 30 天指标；取失败传 null，面板会用浏览器端请求补一次 */
  initialMetrics: ReportGenMetrics | null
}

/**
 * 配置页的「高级信息」：给管理员看这个 AI 生成器最近跑得怎么样。
 *
 * 默认折叠：这些数字（成功率、轮次、未填比例、提示词版本）对普通用户没有意义，
 * 铺在页面上只会增加困惑。只读，不写配置、不改任务。
 */
export function ReportGenAgentPanel({ initialMetrics }: Props) {
  const { token } = theme.useToken()
  const [days, setDays] = useState<ReportGenMetricWindow>(REPORT_GEN_METRIC_DEFAULT_WINDOW)

  const { data, isFetching } = useQuery({
    queryKey: [QUERY_KEY, days],
    queryFn: () => fetchReportGenMetrics(days),
    // 首屏数据只对默认窗口有效，切到 7/90 天必须重取
    initialData: days === REPORT_GEN_METRIC_DEFAULT_WINDOW ? initialMetrics ?? undefined : undefined,
    staleTime: 60_000,
    retry: false,
  })

  const metrics = data ?? null
  const unavailable = metrics === null
  const empty = !unavailable && metrics.total === 0 && metrics.feedback_total === 0
  const slotTop = metrics?.feedback_slot_top ?? []

  const stats = metrics
    ? [
        {
          label: '生成次数',
          value: String(metrics.total),
          hint: `已完成 ${metrics.completed} · 失败 ${metrics.failed} · 已停止 ${metrics.cancelled}`,
        },
        {
          label: '成功率',
          value: formatRate(metrics.success_rate),
          hint: '已完成 ÷ 已结束的生成任务',
        },
        {
          label: '平均轮次',
          value: metrics.avg_rounds === null || metrics.avg_rounds === undefined ? '—' : String(metrics.avg_rounds),
          hint: 'AI 平均来回几轮把内容填完，只看已完成的任务',
        },
        {
          label: '平均用时',
          value: formatSeconds(metrics.avg_duration_seconds),
          hint: '从开始到结束的平均时间，只看已完成的任务',
        },
        { label: '未填比例', value: formatRate(metrics.gap_rate), hint: '找不到依据的填充项 ÷ 全部填充项' },
        {
          label: '自动补齐比例',
          value: formatRate(metrics.fallback_rate),
          hint: '已完成的任务里，主模型失败、改用自动补齐的比例',
        },
        {
          label: '意见采纳率',
          value: formatRate(metrics.feedback_adoption_rate),
          hint: `已落实 ${metrics.feedback_applied} · 未采纳 ${metrics.feedback_ignored}`,
        },
        {
          label: '待落实意见',
          value: String(metrics.feedback_open),
          hint: `这段时间共提了 ${metrics.feedback_total} 条别人写的意见`,
        },
      ]
    : []

  const panel = (
    <>
      <Space size={8} wrap>
        <Segmented
          size="small"
          value={days}
          options={REPORT_GEN_METRIC_WINDOWS.map((value) => ({ value, label: `近 ${value} 天` }))}
          onChange={(value) => setDays(value as ReportGenMetricWindow)}
        />
        {isFetching && (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            正在统计…
          </Typography.Text>
        )}
      </Space>

      <Space size={6} wrap style={{ marginTop: 12 }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          规则版本
        </Typography.Text>
        <Tag>正文 {metrics?.agent_prompt_version ?? '—'}</Tag>
        <Tag>分析结构 {metrics?.structure_prompt_version ?? '—'}</Tag>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          由提示词和动作清单内容自动生成，内容一改就会变，用来确认线上跑的是哪一版
        </Typography.Text>
      </Space>

      {unavailable && (
        <Alert
          style={{ marginTop: 12 }}
          type="warning"
          showIcon
          message="暂时取不到这些统计"
          description="统计接口调用失败，可以换个时间范围再试一次；不影响报告生成本身。"
        />
      )}

      {empty && (
        <Alert
          style={{ marginTop: 12 }}
          type="info"
          showIcon
          message={`近 ${metrics.window_days} 天还没有跑完过生成任务`}
          description="生成过一次之后，这里会显示成功率、平均轮次、平均用时、未填比例和意见采纳情况。"
        />
      )}

      {!unavailable && !empty && (
        <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
          {stats.map((item) => (
            <Col xs={12} md={8} key={item.label}>
              <div
                style={{
                  padding: '10px 12px',
                  border: `1px solid ${token.colorBorderSecondary}`,
                  borderRadius: token.borderRadius,
                }}
              >
                <Statistic title={item.label} value={item.value} valueStyle={{ fontSize: 20, fontWeight: 600 }} />
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {item.hint}
                </Typography.Text>
              </div>
            </Col>
          ))}
        </Row>
      )}

      {!unavailable && slotTop.length > 0 && (
        <Space size={6} wrap style={{ marginTop: 12 }}>
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            意见集中在这些填充项
          </Typography.Text>
          {slotTop.map((item) => (
            <Tag key={item.slot_key}>
              {item.slot_key} × {item.count}
            </Tag>
          ))}
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            同一个填充项总被提意见，说明该改规则或补示例写法，而不是一篇篇改
          </Typography.Text>
        </Space>
      )}

      <Typography.Paragraph type="secondary" style={{ fontSize: 12, margin: '12px 0 0' }}>
        时间范围按任务结束时间算（老任务没有结束时间就按创建时间）。成功率、轮次、用时、未填比例、自动补齐比例都只统计已完成的任务，避免失败任务把平均值拉偏。
        老任务没法追溯当时用的规则版本，这里只显示当前正在用的版本。
      </Typography.Paragraph>
    </>
  )

  return (
    <Collapse
      items={[
        {
          key: 'advanced',
          label: '高级信息（管理员查看）',
          children: panel,
        },
      ]}
      defaultActiveKey={[]}
    />
  )
}