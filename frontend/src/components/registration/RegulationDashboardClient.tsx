'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { Space, App, Spin, Badge } from 'antd'
import {
  CheckCircleOutlined, SyncOutlined, CalendarOutlined,
  FileTextOutlined, AlertOutlined,
} from '@ant-design/icons'
import dynamic from 'next/dynamic'
import dayjs from 'dayjs'
import Link from 'next/link'
import {
  DashboardData, PriorityDocument,
  fetchDashboard,
} from '@/lib/api/client/regulatory-tracker'
import { RegistrationPageHeader } from './RegistrationPageHeader'
import { tagClassOf } from './registration-ui'
import ui from './registration-ui.module.css'
import { IconActivity, IconRefresh, IconWarn } from './registration-icons'

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false })

// 影响等级 → 设计令牌标签类
const IMPACT_TAG: Record<string, string> = {
  high: ui.tagRisk,
  medium: ui.tagWarn,
  low: ui.tagInfo,
  none: ui.tagPlain,
}
const IMPACT_LABEL: Record<string, string> = {
  high: '高影响',
  medium: '中影响',
  low: '低影响',
  none: '无影响',
}

function accentStyle(accent: string, accentBg: string): React.CSSProperties {
  return { '--accent': accent, '--accent-bg': accentBg } as React.CSSProperties
}

export default function RegulationDashboardClient() {
  const router = useRouter()
  const { message } = App.useApp()
  const [secondaryExpanded, setSecondaryExpanded] = useState(false)
  const queryClient = useQueryClient()

  const { data, isLoading: loading, refetch: _refetch } = useQuery<DashboardData | null>({
    queryKey: ['regulation-dashboard'],
    queryFn: async () => {
      try {
        const result = await fetchDashboard()
        return result
      } catch {
        message.error('加载仪表盘数据失败')
        return null
      }
    },
  })

  const loadData = () => {
    queryClient.invalidateQueries({ queryKey: ['regulation-dashboard'] })
  }

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
      lineStyle: { color: '#5F56D6', width: 2 },
      itemStyle: { color: '#5F56D6' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(95,86,214,0.25)' },
            { offset: 1, color: 'rgba(95,86,214,0.02)' },
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
            { offset: 0, color: '#5F56D6' },
            { offset: 1, color: '#A5A0EC' },
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

  const kpis = [
    {
      key: 'today',
      label: '今日新增',
      icon: <FileTextOutlined />,
      accent: 'var(--info-600)',
      accentBg: 'var(--info-50)',
      href: '/registration/regulation/list?date=today',
      num: data.todayNewCount,
      sub: (
        <>
          {data.todayNewHighImpact > 0 && <span className="text-red-500">高影响 {data.todayNewHighImpact} 条</span>}
          {data.todayNewHighImpact > 0 && data.todayNewGeneralCount > 0 && ' · '}
          {data.todayNewGeneralCount > 0 && <span>一般法规 {data.todayNewGeneralCount} 条</span>}
          {data.todayNewCount === 0 && '暂无新增'}
        </>
      ),
    },
    {
      key: 'attention',
      label: '重点关注',
      icon: <AlertOutlined />,
      accentBg: 'var(--risk-50)',
      accent: 'var(--risk-600)',
      href: '/registration/regulation/list?documentCategory=attention',
      num: data.attentionCount,
      sub: '需要重点关注的法规',
    },
    {
      key: 'week',
      label: '近7天动态',
      icon: <CalendarOutlined />,
      accent: 'var(--brand-600)',
      accentBg: 'var(--brand-50)',
      href: '/registration/regulation/list?date=7days',
      num: data.weekTotal,
      sub: `高影响 ${data.weekHighImpact} 条`,
    },
  ]

  return (
    <div className={ui.regUi}>
      <RegistrationPageHeader
        icon={IconActivity}
        title="法规跟踪"
        sub="CDE 法规动态监测与影响分析"
        actions={
          <button type="button" className={ui.btn} onClick={loadData} disabled={loading}>
            {IconRefresh}
            刷新
          </button>
        }
      />

      {/* KPI 卡 */}
      <section className={ui.kpiRow}>
        {kpis.map(kpi => (
          <Link href={kpi.href} key={kpi.key} style={{ textDecoration: 'none' }}>
            <div className={ui.kpi} style={accentStyle(kpi.accent, kpi.accentBg)}>
              <div className={ui.kpiTop}>
                <div className={ui.kpiChip}>{kpi.icon}</div>
                <div className={ui.kpiLabel}>{kpi.label}</div>
                <div className={ui.kpiLink}>明细 ›</div>
              </div>
              <div className={ui.kpiNum}>{kpi.num}</div>
              <div className={ui.kpiSub}>{kpi.sub}</div>
            </div>
          </Link>
        ))}
        {/* 数据源状态卡（无跳转） */}
        <div className={ui.kpi} style={accentStyle('var(--ok-600)', 'var(--ok-50)')}>
          <div className={ui.kpiTop}>
            <div className={ui.kpiChip}><CheckCircleOutlined /></div>
            <div className={ui.kpiLabel}>数据源状态</div>
          </div>
          <div className="mt-1">{renderSourceStatus()}</div>
        </div>
      </section>

      {/* 重点关注法规 */}
      <div className={ui.panel}>
        <div className={ui.panelHead}>
          <div className={ui.panelIco} style={{ background: 'var(--risk-50)', color: 'var(--risk-600)' }}>
            {IconWarn}
          </div>
          <div className={ui.panelTitle}>重点关注法规</div>
          {data.priorityDocuments.length > 0 && (
            <Link className={ui.panelMore} href="/registration/regulation/list?documentCategory=attention">
              查看全部 ›
            </Link>
          )}
        </div>
        {data.priorityDocuments.length === 0 ? (
          <div className="text-center py-12 text-gray-400">
            <FileTextOutlined className="text-4xl mb-3" />
            <div>暂无重点关注法规，系统将持续监测新法规</div>
          </div>
        ) : (
          <div className="p-4 space-y-3">
            {data.priorityDocuments.map((doc: PriorityDocument) => {
              const tagClass = IMPACT_TAG[doc.impactLevel] || ui.tagInfo
              return (
                <div
                  key={doc.id}
                  className="pl-4 py-3 hover:bg-gray-50 transition-colors cursor-pointer rounded-r-lg"
                  style={{ borderLeft: '3px solid var(--risk-600)' }}
                  onClick={() => router.push(`/registration/regulation/${doc.id}`)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={tagClass}>
                          {IMPACT_LABEL[doc.impactLevel] || doc.impactLevel}
                        </span>
                        {doc.regulationType && (
                          <span className={ui.tagPlain}>{doc.regulationType}</span>
                        )}
                        {doc.sourceName && (
                          <span className="text-xs text-gray-400">{doc.sourceName}</span>
                        )}
                      </div>
                      <div className="text-base font-medium text-gray-800 line-clamp-2">
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
                      <Space size={10}>
                        {doc.originalUrl && (
                          <button
                            type="button"
                            className={ui.btn}
                            onClick={(e) => { e.stopPropagation(); window.open(doc.originalUrl, '_blank') }}
                          >
                            原文
                          </button>
                        )}
                        <button
                          type="button"
                          className={ui.opLink}
                          onClick={(e) => { e.stopPropagation(); router.push(`/registration/regulation/${doc.id}`) }}
                        >
                          查看详情
                        </button>
                      </Space>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* 次级统计（默认收起） */}
      <div>
        <button
          type="button"
          onClick={() => setSecondaryExpanded(!secondaryExpanded)}
          className="text-gray-500 hover:text-gray-700 text-sm"
        >
          {secondaryExpanded ? '收起详细信息 ▲' : '查看更多统计 ▼'}
        </button>
      </div>

      {secondaryExpanded && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className={ui.panel}>
            <div className={ui.panelHead}>
              <div className={ui.panelTitle}>近 7 天新增趋势</div>
            </div>
            <div className="p-4">
              <ReactECharts option={trendOption} style={{ height: 200 }} />
            </div>
          </div>
          <div className={ui.panel}>
            <div className={ui.panelHead}>
              <div className={ui.panelTitle}>分类分布</div>
            </div>
            <div className="p-4">
              <ReactECharts option={classOption} style={{ height: 200 }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
