'use client'

import { useMemo, useState } from 'react'
import { Card, Segmented } from 'antd'
import { Pie } from '@ant-design/charts'
import { DistributionDataPoint, EnergyType } from '@/types/energy'

interface DistributionChartProps {
  data: DistributionDataPoint[]
  loading?: boolean
}

// 扇区切片：在数据点基础上补一个唯一的图例/标签文本
type Slice = DistributionDataPoint & { label: string }

// 饼图按能源分类切换。跨类型把 kWh/m³/t 加在一起算百分比是没有意义的，
// 所以每张饼只在单一能源类型内比较各车间占比
const ENERGY_TABS: { value: EnergyType; label: string }[] = [
  { value: 'electricity', label: '电' },
  { value: 'water', label: '水' },
  { value: 'steam', label: '汽' },
  { value: 'natural_gas', label: '气' },
]

// 首尾交替排序：最大、最小、次大、次小...让标签均匀分布
function alternateSort(arr: Slice[]): Slice[] {
  const sorted = [...arr].sort((a, b) => b.value - a.value)
  const result: Slice[] = []
  let left = 0
  let right = sorted.length - 1

  while (left <= right) {
    if (left === right) {
      result.push(sorted[left])
    } else {
      result.push(sorted[left])
      result.push(sorted[right])
    }
    left++
    right--
  }

  return result
}

export function DistributionChart({
  data,
  loading = false,
}: DistributionChartProps) {
  const [picked, setPicked] = useState<EnergyType | null>(null)

  // 顶部能源下拉可能把数据过滤到只剩一类；该类别消失时回落到第一类，不用 effect 重置
  const availableTabs = useMemo(
    () => ENERGY_TABS.filter((t) => data.some((d) => d.energyType === t.value)),
    [data],
  )
  const activeType =
    picked && availableTabs.some((t) => t.value === picked)
      ? picked
      : availableTabs[0]?.value

  const { total, unit, sortedData } = useMemo(() => {
    const rows = data.filter((d) => d.energyType === activeType)

    // 后端按 (车间名, 单位, 能源类型) 分组，同名多项时把单位并进标签，
    // 保证切片标签与 colorField 一一对应、不共享颜色
    const countByName = new Map<string, number>()
    rows.forEach((d) => countByName.set(d.name, (countByName.get(d.name) ?? 0) + 1))

    const slices: Slice[] = rows.map((d) => ({
      ...d,
      label: (countByName.get(d.name) ?? 0) > 1 ? `${d.name}（${d.unit}）` : d.name,
    }))

    return {
      total: slices.reduce((sum, d) => sum + d.value, 0),
      unit: slices[0]?.unit ?? '',
      sortedData: alternateSort(slices),
    }
  }, [data, activeType])

  const config = {
    data: sortedData,
    angleField: 'value',
    colorField: 'label',
    radius: 0.6,
    innerRadius: 0.35,
    scale: {
      color: {
        palette: [
        '#5645d4', '#0075de', '#1aae39', '#dd5b00', '#7b3ff2',
        '#2a9d99', '#f5d75e', '#ff64c8', '#e63946', '#457b9d',
        '#2a9d8f', '#e9c46a', '#f4a261', '#264659', '#606c38',
        '#bc6c25', '#dda15e', '#6a994e', '#a7c957', '#386641'
      ],
      },
    },
    label: {
      text: (d: Slice) => {
        const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0'
        return `${d.label}: ${pct}%`
      },
      position: 'outside' as const,
      transform: [{ type: 'overlapDodgeY' }],
      style: { fill: '#5d5b54', fontSize: 11, fontWeight: 600 },
    },
    legend: false,
    
    tooltip: {
      title: 'label',
      items: [
        (d: Slice) => ({
          name: d.label,
          value: `${d.value.toFixed(2)} ${d.unit}`,
        }),
      ],
    },
    interaction: {
      elementHighlight: true,
    },
  }

  return (
    <Card
      title={
        <span style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>
          区域分布
          {activeType && (
            <span style={{ fontSize: 12, fontWeight: 400, color: '#a4a097', marginLeft: 8 }}>
              {ENERGY_TABS.find((t) => t.value === activeType)?.label}
              {unit ? ` · 合计 ${total.toLocaleString()} ${unit}` : ''}
            </span>
          )}
        </span>
      }
      extra={
        availableTabs.length > 1 ? (
          <Segmented
            size="small"
            value={activeType}
            onChange={(value) => setPicked(value as EnergyType)}
            options={availableTabs.map((t) => ({ label: t.label, value: t.value }))}
            style={{ background: '#f6f5f4', borderRadius: 8, padding: 2 }}
          />
        ) : undefined
      }
      loading={loading}
      styles={{
        header: { borderBottom: '1px solid #ede9e4', padding: '16px 20px' },
        body: { padding: '60px 20px 20px' },
      }}
      style={{
        borderRadius: 12,
        border: '1px solid #ede9e4',
        boxShadow: '0 1px 3px rgba(10, 10, 10, 0.04)',
        height: '100%',
      }}
    >
      {sortedData.length > 0 ? (
        <Pie {...config} height={450} autoFit style={{ marginTop: 80, marginLeft: -40 }} />
      ) : (
        <div
          style={{
            height: 450,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#a4a097',
            fontSize: 13,
          }}
        >
          该能源类型在当前时间范围内暂无数据
        </div>
      )}
    </Card>
  )
}
