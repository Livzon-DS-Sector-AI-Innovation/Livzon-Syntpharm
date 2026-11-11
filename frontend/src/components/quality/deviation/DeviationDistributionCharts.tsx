'use client'

import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { Empty } from 'antd'
import type { DeviationLedgerStatistics } from '@/types/quality'
import { DEVIATION_CHART_COLORS } from './constants'

interface DeviationDistributionChartsProps {
  statistics: DeviationLedgerStatistics | null
}

/** 部门分布最多展示的条数：超出部分在台账里筛，不在图上堆 */
const MAX_DEPARTMENT_BARS = 10

const CARD_CLASS =
  'rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-5 shadow-[0_1px_2px_rgba(26,26,26,0.04)]'

export function DeviationDistributionCharts({ statistics }: DeviationDistributionChartsProps) {
  const departments = statistics?.department_distribution ?? []
  const statuses = statistics?.status_distribution ?? []

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className={CARD_CLASS}>
        <header className="mb-3">
          <h2 className="text-[15px] font-semibold text-[var(--color-ink)]">部门分布</h2>
          <p className="mt-1 text-[12px] text-[var(--color-stone)]">按发生部门统计偏差数量，取前 {MAX_DEPARTMENT_BARS} 个部门</p>
        </header>
        {departments.length === 0 ? (
          <div className="flex h-[300px] items-center justify-center">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
          </div>
        ) : (
          <DepartmentBarChart
            data={departments.slice(0, MAX_DEPARTMENT_BARS).map((item) => ({ name: item.name, value: item.count }))}
          />
        )}
      </section>

      <section className={CARD_CLASS}>
        <header className="mb-3">
          <h2 className="text-[15px] font-semibold text-[var(--color-ink)]">状态分布</h2>
          <p className="mt-1 text-[12px] text-[var(--color-stone)]">按当前所处环节统计，含已关闭与已取消</p>
        </header>
        {statuses.length === 0 ? (
          <div className="flex h-[300px] items-center justify-center">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无数据" />
          </div>
        ) : (
          <StatusDonutChart
            data={statuses.map((item) => ({ name: item.label, value: item.count }))}
          />
        )}
      </section>

      </div>
  )
}

function DepartmentBarChart({ data }: { data: { name: string; value: number }[] }) {
  const total = data.reduce((sum, item) => sum + item.value, 0)
  const option: EChartsOption = {
    grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: unknown) => {
        const rows = Array.isArray(params) ? params : [params]
        const first = rows[0] as { name?: string; value?: number } | undefined
        const value = first?.value ?? 0
        const percent = total > 0 ? ((value / total) * 100).toFixed(1) : '0.0'
        return `${first?.name ?? ''}<br/>偏差数 <strong>${value}</strong> 条（${percent}%）`
      },
    },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#ede9e4' } },
      axisLabel: { color: '#787671' },
    },
    yAxis: {
      type: 'category',
      // 倒序：数量最多的排在最上方
      data: [...data].reverse().map((item) => item.name),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5d5b54', width: 96, overflow: 'truncate' },
    },
    series: [
      {
        type: 'bar',
        data: [...data].reverse().map((item, index) => ({
          value: item.value,
          itemStyle: {
            borderRadius: [0, 4, 4, 0],
            color: DEVIATION_CHART_COLORS[(data.length - 1 - index) % DEVIATION_CHART_COLORS.length],
          },
        })),
        barMaxWidth: 18,
        label: { show: true, position: 'right', color: '#5d5b54', fontSize: 12 },
      },
    ],
  }

  // 部门条数越多越高，避免 10 条时挤在 300px 内
  const height = Math.max(300, data.length * 34)

  return <ReactECharts option={option} style={{ height }} opts={{ renderer: 'svg' }} notMerge />
}

function StatusDonutChart({ data }: { data: { name: string; value: number }[] }) {
  const option: EChartsOption = {
    color: DEVIATION_CHART_COLORS,
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>偏差数 <strong>{c}</strong> 条（{d}%）',
    },
    legend: {
      type: 'scroll',
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#5d5b54', fontSize: 12 },
    },
    series: [
      {
        type: 'pie',
        radius: ['44%', '66%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#ffffff', borderWidth: 2, borderRadius: 4 },
        label: { show: false },
        labelLine: { show: false },
        emphasis: { scale: true, scaleSize: 6 },
        data,
      },
    ],
  }

  return <ReactECharts option={option} style={{ height: 320 }} opts={{ renderer: 'svg' }} notMerge />
}