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

  const config = {
    data,
    angleField: 'value',
    colorField: 'name',
    radius: 0.85,
    innerRadius: 0.55,
    scale: {
      color: {
        palette: ['#5645d4', '#0075de', '#1aae39', '#dd5b00', '#7b3ff2', '#2a9d99', '#f5d75e', '#ff64c8'],
      },
    },
    label: {
      text: (d: DistributionDataPoint) => {
        const pct = total > 0 ? ((d.value / total) * 100).toFixed(1) : '0'
        return `${d.name}: ${pct}%`
      },
      position: 'outside' as const,
      transform: [{ type: 'overlapDodgeY' }],
      style: { fill: '#5d5b54', fontSize: 11 },
    },
    legend: {
      color: {
        position: 'bottom' as const,
        title: false,
        itemLabelFill: '#5d5b54',
        itemLabelFontSize: 12,
      },
    },
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
        <span style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a' }}>
          区域分布
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
      <Pie {...config} height={280} />
    </Card>
  )
}
