'use client'

import { useEffect, useMemo, useState } from 'react'
import { App, Select, Button, Segmented } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { StatsCards } from './StatsCards'
import { TrendChart } from './TrendChart'
import { DistributionChart } from './DistributionChart'
import { useEnergyStore } from '@/stores/energy'
import { EnergyOverviewData, EnergyStatistics, EnergyType, TrendDataPoint } from '@/types/energy'
import { fetchEnergyOverviewClient } from '@/lib/api/client/energy'

type OverviewTimeRange = 'today' | 'week' | 'month'

const EMPTY_STATISTICS: EnergyStatistics = {
  total_electricity: 0,
  total_water: 0,
  total_steam: 0,
  total_natural_gas: 0,
}
const EMPTY_TREND: TrendDataPoint[] = []
const EMPTY_DISTRIBUTION: EnergyOverviewData['distribution'] = []

// 时间窗随挂载日固化进 queryKey：若把 new Date() 直接放进 key，每次渲染 key 都变，会导致无限重取
function resolveStartTime(range: OverviewTimeRange, now: Date): Date {
  if (range === 'today') {
    return new Date(new Date(now).setHours(0, 0, 0, 0))
  }
  const days = range === 'week' ? 7 : 30
  return new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
}

export function EnergyOverview() {
  const { message } = App.useApp()
  const {
    overviewTimeRange,
    setOverviewTimeRange,
    selectedEnergyType,
    setSelectedEnergyType,
  } = useEnergyStore()

  const [today] = useState(() => {
    const now = new Date()
    return `${now.getFullYear()}-${now.getMonth()}-${now.getDate()}`
  })

  const { data, isFetching, isLoading, refetch, error } = useQuery({
    queryKey: ['energy-overview', overviewTimeRange, selectedEnergyType, today],
    queryFn: () => {
      const endTime = new Date()
      return fetchEnergyOverviewClient({
        start_time: resolveStartTime(overviewTimeRange, endTime).toISOString(),
        end_time: endTime.toISOString(),
        energy_type: selectedEnergyType === 'all' ? undefined : selectedEnergyType,
      })
    },
  })

  useEffect(() => {
    if (error) message.error('获取能源数据失败')
  }, [error, message])

  const statistics = data?.summary ?? EMPTY_STATISTICS
  const trendData = data?.trend ?? EMPTY_TREND
  const distributionData = useMemo(
    () =>
      (data?.distribution ?? EMPTY_DISTRIBUTION).map((d) => ({
        name: d.group_key,
        value: d.total_value,
        unit: d.unit,
        energyType: d.energy_type as EnergyType,
      })),
    [data?.distribution],
  )

  return (
    <div
      style={{
        padding: '28px 32px',
        maxWidth: 1600,
        minHeight: '100%',
        background: '#fafaf9',
      }}
    >
      {/* ════ 标题区 ════ */}
      <h1
        style={{
          fontSize: 28,
          fontWeight: 500,
          color: '#1a1a1a',
          margin: 0,
          letterSpacing: '-0.3px',
          lineHeight: 1.3,
        }}
      >
        能源总览
      </h1>
      <p
        style={{
          fontSize: 13,
          color: '#a4a097',
          margin: '4px 0 0',
          lineHeight: 1.5,
        }}
      >
        实时监控全厂能耗数据，追踪趋势与分布
      </p>

      {/* 渐变分割线 */}
      <div
        style={{
          height: 1,
          marginTop: 18,
          marginBottom: 20,
          background:
            'linear-gradient(to right, #5645d4 0%, #e6e0f5 40%, transparent 100%)',
        }}
      />

      {/* ════ 筛选卡片 ════ */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          alignItems: 'center',
          flexWrap: 'wrap',
          background: '#ffffff',
          borderRadius: 12,
          padding: '10px 18px',
          boxShadow: '0 1px 3px rgba(10, 10, 10, 0.04)',
          border: '1px solid #ede9e4',
          marginBottom: 20,
        }}
      >
        <Segmented
          value={overviewTimeRange}
          onChange={(value) => setOverviewTimeRange(value as OverviewTimeRange)}
          options={[
            { label: '今日', value: 'today' },
            { label: '近7天', value: 'week' },
            { label: '近30天', value: 'month' },
          ]}
          style={{
            background: '#f6f5f4',
            borderRadius: 8,
            padding: 2,
          }}
        />

        <div
          style={{
            width: 1,
            height: 20,
            background: '#ede9e4',
            margin: '0 4px',
          }}
        />

        <Select
          value={selectedEnergyType}
          onChange={setSelectedEnergyType}
          variant="filled"
          style={{
            width: 100,
            background: '#f6f5f4',
            border: 'none',
            borderRadius: 8,
            height: 32,
          }}
          options={[
            { label: '全部能源', value: 'all' },
            { label: '电力', value: 'electricity' },
            { label: '自来水', value: 'water' },
            { label: '蒸汽', value: 'steam' },
            { label: '天然气', value: 'natural_gas' },
          ]}
        />

        <div style={{ flex: 1 }} />

        <Button
          icon={<ReloadOutlined />}
          onClick={() => refetch()}
          loading={isFetching}
          style={{
            color: '#787671',
            borderColor: '#c8c4be',
            borderRadius: 8,
            fontWeight: 500,
            fontSize: 13,
            height: 32,
          }}
        >
          刷新
        </Button>
      </div>

      {/* ════ 统计卡片 ════ */}
      <StatsCards statistics={statistics} loading={isLoading} />

      {/* ════ 图表区 ════ */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 16,
        }}
      >
        <TrendChart data={trendData} loading={isLoading} />
        <DistributionChart data={distributionData} loading={isLoading} />
      </div>
    </div>
  )
}
