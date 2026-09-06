'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Card, Row, Col, Tag, Button, Space, App, Spin, Badge } from 'antd'
import {
  CheckCircleOutlined, ArrowRightOutlined, SyncOutlined, CalendarOutlined,
  DownOutlined, UpOutlined, FileTextOutlined, AlertOutlined,
} from '@ant-design/icons'
import dynamic from 'next/dynamic'
import dayjs from 'dayjs'
import Link from 'next/link'
import {
  DashboardData, PriorityDocument,
  fetchDashboard,
} from '@/lib/api/client/regulatory-tracker'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

const IMPACT_CONFIG: Record<string, { color: string; label: string }> = {
  high: { color: '#ff4d4f', label: '高影响' },
  medium: { color: '#faad14', label: '中影响' },
  low: { color: '#1890ff', label: '低影响' },
  none: { color: '#8c8c8c', label: '无影响' },
}

export default function RegulationDashboardClient() {
  const router = useRouter()
  const { message } = App.useApp()
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [secondaryExpanded, setSecondaryExpanded] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await fetchDashboard()
      setData(result)
    } catch {
      message.error('加载仪表盘数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spin size="large" />
      </div>
    )
  }

  if (!data) return null

  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 40, right: 20, top: 20, bottom: 30 },
    xAxis: {
      type: 'category' as const,
      data: data.trend7Days.map(t => dayjs(t.date).format('MM/DD')),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#666' },
    },
    yAxis: {
      type: 'value' as const,
      minInterval: 1,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#999' },
    },
    series: [{
      data: data.trend7Days.map(t => t.count),
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color: '#1890ff', width: 2 },
      itemStyle: { color: '#1890ff' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(24,144,255,0.25)' },
            { offset: 1, color: 'rgba(24,144,255,0.02)' },
          ],
        },
      },
    }],
  }

  const topClassifications = Object.entries(data.byClassification)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)

  const classOption = {
    tooltip: { trigger: 'axis' as const },
    grid: { left: 80, right: 20, top: 10, bottom: 30 },
    xAxis: {
      type: 'value' as const,
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
      axisLabel: { color: '#999' },
    },
    yAxis: {
      type: 'category' as const,
      data: topClassifications.map(([name]) => name.length > 8 ? name.slice(0, 8) + '…' : name),
      axisLine: { lineStyle: { color: '#e8e8e8' } },
      axisLabel: { color: '#666' },
    },
    series: [{
      data: topClassifications.map(([, count]) => count),
      type: 'bar',
      barWidth: 14,
      itemStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 1, y2: 0,
          colorStops: [
            { offset: 0, color: '#1890ff' },
            { offset: 1, color: '#69c0ff' },
          ],
        },
        borderRadius: [0, 4, 4, 0],
      },
    }],
  }

  const renderSourceStatus = () => {
    if (!data.sourceStatus || data.sourceStatus.length === 0) {
      return <span className="text-gray-400 text-sm">暂无数据源</span>
    }
    
    return (
      <div className="flex flex-wrap gap-3">
        {data.sourceStatus.map((source) => {
          const isOk = source.lastSyncStatus === 'success'
          const syncTime = source.lastSyncTime ? dayjs(source.lastSyncTime).format('MM/DD HH:mm') : '未知'
          return (
            <div key={source.code} className="flex items-center gap-2 text-sm">
              <Badge status={isOk ? 'success' : 'error'} />
              <span className="font-medium">{source.code}</span>
              <span className="text-gray-500">{syncTime}</span>
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-800">法规看板</h1>
        <Button
          icon={<SyncOutlined spin={loading} />}
          onClick={loadData}
          loading={loading}
        >
          刷新
        </Button>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Link href="/registration/regulation/list?date=today">
            <Card hoverable className="h-full cursor-pointer">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-gray-500 mb-1">今日新增</div>
                  <div className="text-3xl font-bold text-blue-600">{data.todayNewCount}</div>
                </div>
                <FileTextOutlined className="text-2xl text-blue-400" />
              </div>
              <div className="mt-3 text-xs text-gray-400">
                {data.todayNewHighImpact > 0 && (
                  <span className="text-red-500">高影响 {data.todayNewHighImpact} 条</span>
                )}
                {data.todayNewHighImpact > 0 && data.todayNewGeneralCount > 0 && ' · '}
                {data.todayNewGeneralCount > 0 && (
                  <span>一般法规 {data.todayNewGeneralCount} 条</span>
                )}
                {data.todayNewCount === 0 && '暂无新增'}
              </div>
            </Card>
          </Link>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Link href="/registration/regulation/list?documentCategory=attention">
            <Card hoverable className="h-full cursor-pointer">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-gray-500 mb-1">重点关注</div>
                  <div className="text-3xl font-bold text-red-600">{data.attentionCount}</div>
                </div>
                <AlertOutlined className="text-2xl text-red-400" />
              </div>
              <div className="mt-3 text-xs text-gray-400">
                需要重点关注的法规
              </div>
            </Card>
          </Link>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Link href="/registration/regulation/list?date=7days">
            <Card hoverable className="h-full cursor-pointer">
              <div className="flex items-start justify-between">
                <div>
                  <div className="text-sm text-gray-500 mb-1">近7天动态</div>
                  <div className="text-3xl font-bold text-purple-600">{data.weekTotal}</div>
                </div>
                <CalendarOutlined className="text-2xl text-purple-400" />
              </div>
              <div className="mt-3 text-xs text-gray-400">
                高影响 {data.weekHighImpact} 条
              </div>
            </Card>
          </Link>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card className="h-full">
            <div className="flex items-start justify-between mb-2">
              <div className="text-sm text-gray-500">数据源状态</div>
              <CheckCircleOutlined className="text-lg text-green-500" />
            </div>
            <div className="mt-1">
              {renderSourceStatus()}
            </div>
          </Card>
        </Col>
      </Row>

      <Card
        title={
          <span className="text-lg font-medium">
            重点关注法规
          </span>
        }
        extra={
          data.priorityDocuments.length > 0 && (
            <Button type="link" size="small" onClick={() => router.push('/registration/regulation/list?documentCategory=attention')}>
              查看全部 <ArrowRightOutlined />
            </Button>
          )
        }
      >
        {data.priorityDocuments.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <FileTextOutlined className="text-4xl mb-3" />
            <div>暂无重点关注法规，系统将持续监测新法规</div>
          </div>
        ) : (
          <div className="space-y-4">
            {data.priorityDocuments.map((doc: PriorityDocument) => {
              const impactConfig = IMPACT_CONFIG[doc.impactLevel] || IMPACT_CONFIG.low
              return (
                <div
                  key={doc.id}
                  className="border-l-4 border-red-500 pl-4 py-3 hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => router.push(`/registration/regulation/${doc.id}`)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Tag color={impactConfig.color} className="mr-0">
                          {impactConfig.label}
                        </Tag>
                        {doc.regulationType && (
                          <Tag className="mr-0">{doc.regulationType}</Tag>
                        )}
                        {doc.sourceName && (
                          <span className="text-xs text-gray-400">{doc.sourceName}</span>
                        )}
                      </div>
                      <div className="text-base font-medium text-gray-800 hover:text-blue-600 transition-colors line-clamp-2">
                        {doc.title}
                      </div>
                      {doc.aiSummary && (
                        <div className="mt-2 text-sm text-gray-600 line-clamp-2">
                          {doc.aiSummary}
                        </div>
                      )}
                      <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                        {doc.publishDate && (
                          <span>{dayjs(doc.publishDate).format('YYYY-MM-DD')}</span>
                        )}
                        {doc.aiRelevanceScore != null && (
                          <span>相关性 {(doc.aiRelevanceScore * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    </div>
                    <div className="flex-shrink-0">
                      <Space>
                        {doc.originalUrl && (
                          <Button
                            size="small"
                            href={doc.originalUrl}
                            target="_blank"
                          >
                            原文
                          </Button>
                        )}
                        <Button type="primary" size="small" onClick={(e) => { e.stopPropagation(); router.push(`/registration/regulation/${doc.id}`); }}>
                          查看详情
                        </Button>
                      </Space>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      <div>
        <Button
          type="text"
          onClick={() => setSecondaryExpanded(!secondaryExpanded)}
          className="text-gray-500 hover:text-gray-700"
        >
          {secondaryExpanded ? <UpOutlined /> : <DownOutlined />}
          <span className="ml-2">{secondaryExpanded ? '收起详细信息' : '查看更多统计'}</span>
        </Button>
      </div>

      {secondaryExpanded && (
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Card title="近 7 天新增趋势" size="small">
              <ReactECharts option={trendOption} style={{ height: 200 }} />
            </Card>
          </Col>
          <Col xs={24} md={12}>
            <Card title="分类分布" size="small">
              <ReactECharts option={classOption} style={{ height: 200 }} />
            </Card>
          </Col>
        </Row>
      )}
    </div>
  )
}
