'use client'

import { Card } from 'antd'
import { Pie } from '@ant-design/charts'
import { DistributionDataPoint } from '@/types/energy'

interface DistributionChartProps {
  data: DistributionDataPoint[]
  loading?: boolean
}

export function DistributionChart({
  data,
  loading = false,
}: DistributionChartProps) {

  const total = data.reduce((sum, d) => sum + d.value, 0)
  
  // 首尾交替排序：最大、最小、次大、次小...让标签均匀分布
  const alternateSort = (arr: DistributionDataPoint[]) => {
    const sorted = [...arr].sort((a, b) => b.value - a.value)
    const result: DistributionDataPoint[] = []
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
  
  const sortedData = alternateSort(data)

  const config = {
    data: sortedData,
    angleField: 'value',
    colorField: 'name',
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
      text: (d: DistributionDataPoint) => {
        const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0'
        return `${d.name}: ${pct}%`
      },
      position: 'outside' as const,
      transform: [{ type: 'overlapDodgeY' }],
      style: { fill: '#5d5b54', fontSize: 11, fontWeight: 600 },
    },
    legend: false,
    
    tooltip: {
      title: 'name',
      items: [
        (d: DistributionDataPoint) => ({
          name: d.name,
          value: `${d.value.toFixed(2)}`,
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
