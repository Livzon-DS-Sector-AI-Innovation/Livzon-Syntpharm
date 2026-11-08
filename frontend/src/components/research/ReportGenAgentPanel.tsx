'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, Card, Col, Row, Segmented, Space, Statistic, Tag, Typography, theme } from 'antd'
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
 * 配置页的「Agent 运行情况」：不点进单个任务也能看出这个 Agent 最近跑得怎么样。
 *
 * 只读：不写配置、不改任务；口径全部由后端聚合接口给定，前端只做展示换算。
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
  const empty = !unavailable && metrics.total === 0

  const stats = metrics
    ? [
        {
          label: '任务数',
          value: String(metrics.total),
          hint: `完成 ${metrics.completed} · 失败 ${metrics.failed} · 终止 ${metrics.cancelled}`,
        },
        { label: '成功率', value: formatRate(metrics.success_rate), hint: '完成 ÷ 终态任务' },
        {
          label: '平均轮次',
          value: metrics.avg_rounds === null || metrics.avg_rounds === undefined ? '—' : String(metrics.avg_rounds),
          hint: '仅统计已完成任务',
        },
        { label: '平均耗时', value: formatSeconds(metrics.avg_duration_seconds), hint: '起止时间差，仅已完成' },
        { label: '缺口率', value: formatRate(metrics.gap_rate), hint: '缺口槽位 ÷ 槽位总数' },
        { label: '降级率', value: formatRate(metrics.fallback_rate), hint: '已完成任务里触发兜底的比例' },
      ]
    : []

  return (
    <Card
      size="small"
      title="Agent 运行情况"
      extra={
        <Space size={8}>
          {isFetching && <Typography.Text type="secondary" style={{ fontSize: 12 }}>统计中…</Typography.Text>}
          <Segmented
            size="small"
            value={days}
            options={REPORT_GEN_METRIC_WINDOWS.map((value) => ({ value, label: `近 ${value} 天` }))}
            onChange={(value) => setDays(value as ReportGenMetricWindow)}
          />
        </Space>
      }
    >
      <Space size={6} wrap>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          提示词版本
        </Typography.Text>
        <Tag>正文 {metrics?.agent_prompt_version ?? '—'}</Tag>
        <Tag>结构 {metrics?.structure_prompt_version ?? '—'}</Tag>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          由提示词与工具清单内容自动生成，文字一改就会变
        </Typography.Text>
      </Space>

      {unavailable && (
        <Alert
          style={{ marginTop: 12 }}
          type="warning"
          showIcon
          message="指标暂时取不到"
          description="后端聚合接口调用失败，可稍后切一次时间窗重试；不影响生成任务本身。"
        />
      )}

      {empty && (
        <Alert
          style={{ marginTop: 12 }}
          type="info"
          showIcon
          message={`近 ${metrics.window_days} 天还没有已结束的任务`}
          description="跑一次生成后，这里会显示成功率、平均轮次、平均耗时与缺口率。"
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
                <Statistic
                  title={item.label}
                  value={item.value}
                  valueStyle={{ fontSize: 20, fontWeight: 600 }}
                />
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {item.hint}
                </Typography.Text>
              </div>
            </Col>
          ))}
        </Row>
      )}

      <Typography.Paragraph type="secondary" style={{ fontSize: 12, margin: '12px 0 0' }}>
        窗口按任务结束时间落（历史任务没有结束时间则按创建时间）；成功率、轮次、耗时、缺口率、降级率都只算已完成任务，避免失败任务拉偏均值。
        历史任务无法追溯当时用的提示词版本，这里只显示当前在用的版本。
      </Typography.Paragraph>
    </Card>
  )
}