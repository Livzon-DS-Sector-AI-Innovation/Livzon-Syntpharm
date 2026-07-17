import { Skeleton } from 'antd'
import {
  ThunderboltOutlined,
  CloudOutlined,
  FireOutlined,
} from '@ant-design/icons'
import { EnergyStatistics } from '@/types/energy'

interface StatCardDef {
  key: keyof EnergyStatistics
  title: string
  suffix: string
  icon: React.ReactNode
  color: string
  tint: string
}

const cards: StatCardDef[] = [
  {
    key: 'total_electricity',
    title: '电力消耗',
    suffix: 'kWh',
    icon: <ThunderboltOutlined />,
    color: '#0075de',
    tint: '#dcecfa',
  },
  {
    key: 'total_water',
    title: '水消耗',
    suffix: 'm³',
    icon: <CloudOutlined />,
    color: '#1aae39',
    tint: '#d9f3e1',
  },
  {
    key: 'total_steam',
    title: '气体消耗',
    suffix: 'm³',
    icon: <FireOutlined />,
    color: '#dd5b00',
    tint: '#ffe8d4',
  },
]

// ── 格式化数值 ──
function formatValue(v: number): string {
  if (Math.abs(v) >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M'
  if (Math.abs(v) >= 10_000) return (v / 1_000).toFixed(1) + 'k'
  return v.toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

interface StatsCardsProps {
  statistics: EnergyStatistics
  loading?: boolean
}

export function StatsCards({ statistics, loading = false }: StatsCardsProps) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 16,
        marginBottom: 20,
      }}
    >
      {cards.map((c) => (
        <div
          key={c.key}
          style={{
            background: '#ffffff',
            borderRadius: 12,
            padding: '20px 24px',
            border: '1px solid #ede9e4',
            boxShadow: '0 1px 3px rgba(10, 10, 10, 0.04)',
            display: 'flex',
            alignItems: 'flex-start',
            gap: 16,
          }}
        >
          {/* 图标 — 彩色圆角方块 */}
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 8,
              background: c.tint,
              color: c.color,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 20,
              flexShrink: 0,
            }}
          >
            {c.icon}
          </div>

          {/* 数值 + 标签 */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {loading ? (
              <Skeleton.Input active size="small" style={{ width: 100, height: 22 }} />
            ) : (
              <div
                style={{
                  fontSize: 26,
                  fontWeight: 500,
                  color: '#1a1a1a',
                  lineHeight: 1.2,
                  letterSpacing: '-0.3px',
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {formatValue(statistics[c.key])}
                <span
                  style={{
                    fontSize: 14,
                    fontWeight: 400,
                    color: '#a4a097',
                    marginLeft: 4,
                  }}
                >
                  {c.suffix}
                </span>
              </div>
            )}
            <div
              style={{
                fontSize: 13,
                color: '#787671',
                marginTop: 2,
                lineHeight: 1.4,
              }}
            >
              {c.title}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
