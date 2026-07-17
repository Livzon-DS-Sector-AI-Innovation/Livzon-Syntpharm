'use client'

import { useEffect, useState, useMemo } from 'react'
import { Card, Checkbox, Spin, Segmented, Empty, Alert } from 'antd'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { getProductOutputs } from '@/actions/product-output'
import type { ProductOutput } from '@/types/product-output'

const CHART_COLORS = [
  '#5645d4', '#1aae39', '#dd5b00', '#e03131', '#13c2c2',
  '#8b5cf6', '#f59e0b', '#0075de', '#ff64c8', '#2a9d99', '#523410',
]

interface WorkshopMonthData {
  workshop: string
  months: number[]
  total: number
  batches: number
}

interface Props {
  year: number
}

export default function WorkshopRankingTrend({ year }: Props) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [ranking, setRanking] = useState<WorkshopMonthData[]>([])
  const [visibleSet, setVisibleSet] = useState<Set<string>>(new Set())
  const [trendType, setTrendType] = useState<string>('折线图')

  useEffect(() => {
    loadData()
  }, [year])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getProductOutputs({
        start_date: `${year}-01-01`,
        end_date: `${year}-12-31`,
        page_size: 5000,
      })

      if (res.code !== 200) {
        setError(res.message || '加载数据失败')
        setRanking([])
        return
      }

      const records = res.data || []
      const workshopMap = new Map<string, { months: number[]; total: number; batches: number }>()

      for (const r of records as ProductOutput[]) {
        if (!workshopMap.has(r.workshop)) {
          workshopMap.set(r.workshop, { months: Array(12).fill(0), total: 0, batches: 0 })
        }
        const entry = workshopMap.get(r.workshop)!
        const monthIdx = parseInt(r.production_date.substring(5, 7), 10) - 1
        if (monthIdx >= 0 && monthIdx < 12) {
          entry.months[monthIdx] += r.weight
        }
        entry.total += r.weight
        entry.batches += 1
      }

      const sorted = Array.from(workshopMap.entries())
        .map(([workshop, data]) => ({ workshop, ...data }))
        .sort((a, b) => b.total - a.total)

      setRanking(sorted)
      setVisibleSet(new Set(sorted.slice(0, 3).map((w) => w.workshop)))
    } catch (err) {
      console.error('Failed to load workshop ranking data:', err)
      setError('加载车间产量数据失败')
      setRanking([])
    } finally {
      setLoading(false)
    }
  }

  const months = useMemo(
    () => Array.from({ length: 12 }, (_, i) => `${i + 1}月`),
    [],
  )

  const rankingOption: EChartsOption = useMemo(() => {
    const workshops = ranking.map((w) => w.workshop)
    const totals = ranking.map((w) => Math.round(w.total * 100) / 100)
    const height = Math.max(280, workshops.length * 42 + 80)

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: any) => {
          const p = Array.isArray(params) ? params[0] : params
          const item = ranking.find((w) => w.workshop === p.name)
          return `<strong>${p.name}</strong><br/>${p.marker} 总产量: ${p.value.toLocaleString()} kg<br/>批次: ${item?.batches || 0} 批`
        },
      },
      grid: { left: '3%', right: '12%', bottom: '3%', top: '3%', containLabel: true },
      xAxis: { type: 'value', name: 'kg' },
      yAxis: {
        type: 'category',
        data: workshops,
        inverse: true,
        axisLabel: { fontSize: 12 },
      },
      series: [
        {
          type: 'bar',
          data: totals.map((v, i) => ({
            value: v,
            itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
          })),
          barMaxWidth: 28,
          label: {
            show: true,
            position: 'right',
            formatter: (p: any) => `${p.value.toLocaleString()} kg`,
            fontSize: 11,
          },
        },
      ],
      __height: height,
    } as EChartsOption
  }, [ranking])

  const trendOption: EChartsOption = useMemo(() => {
    const visible = ranking.filter((w) => visibleSet.has(w.workshop))
    const series = visible.map((w, i) => ({
      name: w.workshop,
      type: trendType === '折线图' ? 'line' : 'bar',
      data: w.months.map((v) => Math.round(v * 100) / 100),
      smooth: true,
      lineStyle: { width: 2 },
      itemStyle: { color: CHART_COLORS[ranking.indexOf(w) % CHART_COLORS.length] },
      symbolSize: 4,
    }))

    return {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const items = Array.isArray(params) ? params : [params]
          let result = `<strong>${items[0]?.axisValue}</strong><br/>`
          for (const item of items) {
            if (item.value != null) {
              result += `${item.marker} ${item.seriesName}: ${Number(item.value).toLocaleString()} kg<br/>`
            }
          }
          return result
        },
      },
      legend: { data: visible.map((w) => w.workshop), top: 0 },
      grid: { left: '3%', right: '4%', bottom: '15%', top: '12%', containLabel: true },
      xAxis: { type: 'category', data: months, boundaryGap: trendType !== '折线图' },
      yAxis: { type: 'value', name: 'kg' },
      dataZoom: [
        { type: 'inside', start: 0, end: 100 },
        { type: 'slider', start: 0, end: 100 },
      ],
      series,
    } as EChartsOption
  }, [ranking, visibleSet, months, trendType])

  const toggleWorkshop = (workshop: string) => {
    setVisibleSet((prev) => {
      const next = new Set(prev)
      if (next.has(workshop)) next.delete(workshop)
      else next.add(workshop)
      return next
    })
  }

  if (loading) {
    return (
      <Card variant="borderless" className="shadow-sm">
        <div className="flex items-center justify-center py-16">
          <Spin />
          <span className="ml-2 text-[var(--color-muted)]">加载产量数据…</span>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card variant="borderless" className="shadow-sm">
        <Alert
          title="加载失败"
          description={error}
          type="warning"
          showIcon
          action={
            <button
              onClick={loadData}
              className="px-3 py-1 text-sm bg-[var(--color-primary)] text-white rounded hover:opacity-90"
            >
              重试
            </button>
          }
        />
      </Card>
    )
  }

  if (ranking.length === 0) {
    return (
      <Card variant="borderless" className="shadow-sm">
        <Empty description={`${year}年暂无产量数据`} />
      </Card>
    )
  }

  const rankingHeight = Math.max(280, ranking.length * 42 + 80)

  return (
    <Card variant="borderless" className="shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-semibold mb-0">车间产量排名与趋势</h3>
          <span className="text-sm text-[var(--color-muted)]">{year}年各车间产量对比</span>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-4">
        {/* Left: Ranking bar chart */}
        <div className="lg:w-1/2">
          <div className="text-sm font-medium mb-2 text-[var(--color-slate)]">产量排名（从高到低）</div>
          <ReactECharts
            option={rankingOption}
            style={{ height: `${rankingHeight}px` }}
            notMerge
            opts={{ renderer: 'svg' }}
          />
        </div>

        {/* Right: Trend chart */}
        <div className="lg:w-1/2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-[var(--color-slate)]">产量趋势</span>
            <Segmented
              size="small"
              options={['折线图', '柱状图']}
              value={trendType}
              onChange={(v) => setTrendType(v as string)}
            />
          </div>
          <ReactECharts
            option={trendOption}
            style={{ height: '280px' }}
            notMerge
            opts={{ renderer: 'svg' }}
          />

          {/* Workshop checkboxes */}
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
            {ranking.map((w, i) => (
              <label key={w.workshop} className="flex items-center gap-1.5 cursor-pointer text-sm">
                <input
                  type="checkbox"
                  checked={visibleSet.has(w.workshop)}
                  onChange={() => toggleWorkshop(w.workshop)}
                  style={{ accentColor: CHART_COLORS[i % CHART_COLORS.length] }}
                />
                <span
                  className="inline-block w-2.5 h-2.5 rounded-full"
                  style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
                />
                {w.workshop}
              </label>
            ))}
          </div>
        </div>
      </div>
    </Card>
  )
}
