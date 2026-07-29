'use client'

import { Card } from 'antd'
import { Line } from '@ant-design/charts'
import { TrendDataPoint } from '@/types/energy'

interface TrendChartProps {
  data: TrendDataPoint[]
  loading?: boolean
}

export function TrendChart({ data, loading = false }: TrendChartProps) {

  const config = {
    data,
    xField: 'time',
    yField: 'value',
    colorField: 'type',
    shapeField: 'smooth',
    scale: {
      y: {
        domainMin: 0,
      },
    },
    axis: {
      y: {
        title: {
          text: '消耗量',
          style: { fill: '#a4a097', fontSize: 12 },
        },
        labelStyle: { fill: '#a4a097', fontSize: 11, fontWeight: 600 },
        grid: {
          stroke: '#ede9e4',
          lineWidth: 0.5,
        },
      },
      x: {
        labelStyle: { fill: '#a4a097', fontSize: 11 }, fontWeight: 600,
        line: { stroke: '#ede9e4' },
      },
    },
    style: {
      view: { fill: 'transparent' },
    },
    theme: {
      colors: ['#5645d4', '#0075de', '#1aae39', '#dd5b00'],
    },
    legend: {
      position: 'top' as const,
      itemLabelFill: '#5d5b54',
      itemLabelFontSize: 12,
    },
    interaction: {
      tooltip: {
        marker: false,
      },
    },
    point: {
      shapeField: 'circle',
      sizeField: 2,
    },
  }

  return (
    <Card
      title={
        <span style={{ fontSize: 15, fontWeight: 700, color: '#1a1a1a' }}>
          能耗趋势
        </span>
      }
      loading={loading}
      styles={{
        header: { borderBottom: '1px solid #ede9e4', padding: '16px 20px' },
        body: { padding: '16px 20px 20px' },
      }}
      style={{
        borderRadius: 12,
        border: '1px solid #ede9e4',
        boxShadow: '0 1px 3px rgba(10, 10, 10, 0.04)',
        height: '100%',
      }}
    >
      <Line {...config} height={280} />
    </Card>
  )
}
