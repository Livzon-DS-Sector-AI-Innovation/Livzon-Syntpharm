'use client'

import { useMemo } from 'react'
import { Card } from 'antd'
import { Pie } from '@ant-design/charts'
import { DistributionDataPoint } from '@/types/energy'

interface DistributionChartProps {
  data: DistributionDataPoint[]
  loading?: boolean
}

// 扇区切片：在数据点基础上补一个唯一的图例/标签文本
type Slice = DistributionDataPoint & { label: string }

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

  const { total, sortedData } = useMemo(() => {
    // 后端按 (车间名, 单位) 分组，同名车间的电/水/蒸汽会是多个切片。
    // 直接用 name 做标签会重复、做 colorField 会让重复项共享颜色，
    // 所以同名多项时把单位并进标签，保证每张切片标识唯一。
    const countByName = new Map<string, number>()
    data.forEach((d) => countByName.set(d.name, (countByName.get(d.name) ?? 0) + 1))

    const slices: Slice[] = data.map((d) => ({
      ...d,
      label: (countByName.get(d.name) ?? 0) > 1 ? `${d.name}（${d.unit}）` : d.name,
    }))

    return {
      total: slices.reduce((sum, d) => sum + d.value, 0),
      sortedData: alternateSort(slices),
    }
  }, [data])

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
        </span>
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
      <Pie {...config} height={450} autoFit style={{ marginTop: 80, marginLeft: -40 }} />
    </Card>
  )
}
