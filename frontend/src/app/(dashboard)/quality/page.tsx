'use client'

export const dynamic = 'force-dynamic'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  Button,
  Tag,
  Spin,
  Empty,
} from 'antd'
import {
  ReloadOutlined,
  MonitorOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  SafetyCertificateOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  RightOutlined,
} from '@ant-design/icons'

const API_BASE_URL = '/api/v1'

interface InstrumentItem {
  id: string
  instrument_no: string
  instrument_name: string
  is_active: boolean
  valid_until: string
}

interface ReagentItem {
  id: string
  reagent_name: string
  lot_no: string
  expiration_date: string
  status: string
}

interface UpcomingInstrument {
  id: string
  instrument_no: string
  instrument_name: string
  valid_until: string
  days_remaining: number
}

interface ExpiringReagent {
  id: string
  reagent_name: string
  lot_no: string
  expiration_date: string
  days_remaining: number
}

export default function QualityDashboardPage() {
  // 加载仪器统计
  const { data: instrumentData, isLoading: instrumentLoading } = useQuery({
    queryKey: ['quality-dashboard-instruments'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/quality/instrument?page=1&page_size=100`)
      const data = await response.json()
      return (data.data?.items || []) as InstrumentItem[]
    },
  })

  const items = instrumentData || []
  const now = dayjs()

  const instrumentStats = {
    total: items.length,
    active: items.filter(i => i.is_active).length,
    overdue: items.filter(i => i.valid_until && dayjs(i.valid_until).isBefore(now)).length,
    warning: items.filter(i => {
      if (!i.valid_until) return false
      const isOverdue = dayjs(i.valid_until).isBefore(now)
      if (isOverdue) return false
      const daysUntil = dayjs(i.valid_until).diff(now, 'day')
      return daysUntil >= 0 && daysUntil <= 30
    }).length,
  }

  const upcomingInstruments = items
    .filter(i => {
      if (!i.valid_until) return false
      const isOverdue = dayjs(i.valid_until).isBefore(now)
      if (isOverdue) return false
      const daysUntil = dayjs(i.valid_until).diff(now, 'day')
      return daysUntil >= 0 && daysUntil <= 30
    })
    .sort((a, b) => dayjs(a.valid_until).unix() - dayjs(b.valid_until).unix())
    .slice(0, 5)
    .map(i => ({
      id: i.id,
      instrument_no: i.instrument_no,
      instrument_name: i.instrument_name,
      valid_until: i.valid_until,
      days_remaining: dayjs(i.valid_until).diff(now, 'day')
    }))

  // 加载试剂统计
  const { data: reagentData, isLoading: reagentLoading } = useQuery({
    queryKey: ['quality-dashboard-reagents'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE_URL}/quality/reagent/list?page=1&page_size=100`)
      const data = await response.json()
      return (data.data?.items || []) as ReagentItem[]
    },
  })

  const reagentItems = reagentData || []

  const reagentStats = {
    total: reagentItems.length,
    available: reagentItems.filter(i => i.status === 'available').length,
    expired: reagentItems.filter(i => i.expiration_date && dayjs(i.expiration_date).isBefore(now)).length,
    expiring_soon: reagentItems.filter(i => {
      if (!i.expiration_date) return false
      const isExpired = dayjs(i.expiration_date).isBefore(now)
      if (isExpired) return false
      const daysUntil = dayjs(i.expiration_date).diff(now, 'day')
      return daysUntil >= 0 && daysUntil <= 30
    }).length,
  }

  const expiringReagents = reagentItems
    .filter(i => {
      if (!i.expiration_date) return false
      const isExpired = dayjs(i.expiration_date).isBefore(now)
      if (isExpired) return false
      const daysUntil = dayjs(i.expiration_date).diff(now, 'day')
      return daysUntil >= 0 && daysUntil <= 30
    })
    .sort((a, b) => dayjs(a.expiration_date).unix() - dayjs(b.expiration_date).unix())
    .slice(0, 5)
    .map(i => ({
      id: i.id,
      reagent_name: i.reagent_name,
      lot_no: i.lot_no,
      expiration_date: i.expiration_date,
      days_remaining: dayjs(i.expiration_date).diff(now, 'day')
    }))

  const loading = instrumentLoading || reagentLoading

  const getDaysColor = (days: number) => {
    if (days <= 0) return '#ef4444'
    if (days <= 7) return '#ef4444'
    if (days <= 14) return '#f59e0b'
    return '#10b981'
  }

  return (
    <div className="quality-dashboard">
      {/* 顶部标题 */}
      <div className="dashboard-header">
        <div className="dashboard-header-left">
          <SafetyCertificateOutlined className="dashboard-icon" />
          <div>
            <h1>质量管理中心</h1>
            <p>仪器校准 · 试剂管理 · 合规监控</p>
          </div>
        </div>
        <Button
          icon={<ReloadOutlined />}
          onClick={loadAllStats}
          loading={loading}
          className="refresh-btn"
        >
          刷新
        </Button>
      </div>

      <Spin spinning={loading}>
        {/* 统计概览 - 三大模块 */}
        <div className="stats-grid">
          {/* 仪器校准 */}
          <div className="stat-module stat-module-blue">
            <div className="module-header">
              <MonitorOutlined className="module-icon" />
              <span className="module-title">仪器校准管理</span>
            </div>
            <div className="module-stats">
              <div className="stat-item">
                <div className="stat-label">仪器总数</div>
                <div className="stat-value stat-value-blue">{instrumentStats.total}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">在用仪器</div>
                <div className="stat-value stat-value-green">{instrumentStats.active}</div>
              </div>
            </div>
            <div className="module-alerts">
              <div className="alert-box alert-warning">
                <WarningOutlined />
                <div className="alert-content">
                  <div className="alert-num">{instrumentStats.warning}</div>
                  <div className="alert-text">即将到期</div>
                </div>
              </div>
              <div className="alert-box alert-danger">
                <ExclamationCircleOutlined />
                <div className="alert-content">
                  <div className="alert-num">{instrumentStats.overdue}</div>
                  <div className="alert-text">已超期</div>
                </div>
              </div>
            </div>
            <Link href="/quality/instrument/list" className="module-link">
              进入管理 <RightOutlined />
            </Link>
          </div>

          {/* 试剂/标准品 */}
          <div className="stat-module stat-module-green">
            <div className="module-header">
              <ExperimentOutlined className="module-icon" />
              <span className="module-title">试剂/标准品</span>
            </div>
            <div className="module-stats">
              <div className="stat-item">
                <div className="stat-label">试剂总数</div>
                <div className="stat-value stat-value-green">{reagentStats.total}</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">可用试剂</div>
                <div className="stat-value stat-value-blue">{reagentStats.available}</div>
              </div>
            </div>
            <div className="module-alerts">
              <div className="alert-box alert-warning">
                <ClockCircleOutlined />
                <div className="alert-content">
                  <div className="alert-num">{reagentStats.expiring_soon}</div>
                  <div className="alert-text">即将过期</div>
                </div>
              </div>
              <div className="alert-box alert-danger">
                <ExclamationCircleOutlined />
                <div className="alert-content">
                  <div className="alert-num">{reagentStats.expired}</div>
                  <div className="alert-text">已过期</div>
                </div>
              </div>
            </div>
            <Link href="/quality/reagent" className="module-link">
              进入管理 <RightOutlined />
            </Link>
          </div>

          {/* 偏差/合规 */}
          <div className="stat-module stat-module-purple">
            <div className="module-header">
              <FileTextOutlined className="module-icon" />
              <span className="module-title">偏差与合规</span>
            </div>
            <div className="module-stats">
              <div className="stat-item">
                <div className="stat-label">偏差记录</div>
                <div className="stat-value stat-value-purple">-</div>
              </div>
              <div className="stat-item">
                <div className="stat-label">待处理</div>
                <div className="stat-value stat-value-orange">-</div>
              </div>
            </div>
            <div className="module-alerts">
              <div className="alert-box alert-neutral">
                <DatabaseOutlined />
                <div className="alert-content">
                  <div className="alert-num">-</div>
                  <div className="alert-text">本月新增</div>
                </div>
              </div>
              <div className="alert-box alert-neutral">
                <CheckCircleOutlined />
                <div className="alert-content">
                  <div className="alert-num">-</div>
                  <div className="alert-text">已完成</div>
                </div>
              </div>
            </div>
            <Link href="/quality/deviation-automation/history" className="module-link">
              进入管理 <RightOutlined />
            </Link>
          </div>
        </div>

        {/* 预警区域 */}
        <div className="alerts-grid">
          {/* 仪器校准预警 */}
          <div className="alert-card">
            <div className="alert-card-header">
              <WarningOutlined style={{ color: '#f59e0b' }} />
              <span>仪器校准预警</span>
              {(instrumentStats.warning + instrumentStats.overdue) > 0 && (
                <Tag color="orange">{instrumentStats.warning + instrumentStats.overdue}</Tag>
              )}
            </div>
            <div className="alert-card-body">
              {upcomingInstruments.length > 0 ? (
                <div className="alert-list">
                  {upcomingInstruments.map(item => (
                    <div key={item.id} className="alert-list-item">
                      <div className="item-main">
                        <div className="item-title">{item.instrument_name}</div>
                        <div className="item-sub">{item.instrument_no}</div>
                      </div>
                      <div className="item-right">
                        <div className="item-date">{dayjs(item.valid_until).format('MM-DD')}</div>
                        <Tag color={getDaysColor(item.days_remaining)}>
                          {item.days_remaining}天
                        </Tag>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty description="暂无预警" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </div>

          {/* 试剂过期预警 */}
          <div className="alert-card">
            <div className="alert-card-header">
              <ExperimentOutlined style={{ color: '#f59e0b' }} />
              <span>试剂过期预警</span>
              {(reagentStats.expiring_soon + reagentStats.expired) > 0 && (
                <Tag color="orange">{reagentStats.expiring_soon + reagentStats.expired}</Tag>
              )}
            </div>
            <div className="alert-card-body">
              {expiringReagents.length > 0 ? (
                <div className="alert-list">
                  {expiringReagents.map(item => (
                    <div key={item.id} className="alert-list-item">
                      <div className="item-main">
                        <div className="item-title">{item.reagent_name}</div>
                        <div className="item-sub">{item.lot_no}</div>
                      </div>
                      <div className="item-right">
                        <div className="item-date">{dayjs(item.expiration_date).format('MM-DD')}</div>
                        <Tag color={getDaysColor(item.days_remaining)}>
                          {item.days_remaining}天
                        </Tag>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <Empty description="暂无预警" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </div>

          {/* 快捷入口 */}
          <div className="alert-card quick-links-card">
            <div className="alert-card-header">
              <DatabaseOutlined style={{ color: '#6366f1' }} />
              <span>快捷入口</span>
            </div>
            <div className="quick-links-grid">
              <Link href="/quality/static-data/hplc-reference" className="quick-link-item">
                <div className="quick-link-icon">🧪</div>
                <div className="quick-link-text">对照品管理</div>
              </Link>
              <Link href="/quality/static-data/medium" className="quick-link-item">
                <div className="quick-link-icon">🧫</div>
                <div className="quick-link-text">培养基管理</div>
              </Link>
              <Link href="/quality/static-data/chrom-column" className="quick-link-item">
                <div className="quick-link-icon">📊</div>
                <div className="quick-link-text">色谱柱管理</div>
              </Link>
              <Link href="/quality/static-data/storage-condition" className="quick-link-item">
                <div className="quick-link-icon">🌡️</div>
                <div className="quick-link-text">贮存条件</div>
              </Link>
              <Link href="/quality/reagent" className="quick-link-item">
                <div className="quick-link-icon">🧬</div>
                <div className="quick-link-text">试剂管理</div>
              </Link>
              <Link href="/quality/instrument/list" className="quick-link-item">
                <div className="quick-link-icon">🔬</div>
                <div className="quick-link-text">仪器管理</div>
              </Link>
            </div>
          </div>
        </div>
      </Spin>

      {/* 页面样式 */}
      <style jsx global>{`
        .quality-dashboard {
          padding: 12px;
          min-height: 100%;
          background: linear-gradient(180deg, #f0f9ff 0%, #f8fafc 200px);
        }

        @media (min-width: 768px) {
          .quality-dashboard {
            padding: 24px;
          }
        }

        .dashboard-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          flex-wrap: wrap;
          gap: 12px;
        }

        @media (min-width: 768px) {
          .dashboard-header {
            margin-bottom: 24px;
          }
        }

        .dashboard-header-left {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .dashboard-icon {
          font-size: 32px;
          color: #5645d4;
        }

        @media (min-width: 768px) {
          .dashboard-icon {
            font-size: 40px;
          }
        }

        .dashboard-header-left h1 {
          font-size: 20px;
          font-weight: 700;
          margin: 0;
          color: #1f2937;
        }

        @media (min-width: 768px) {
          .dashboard-header-left h1 {
            font-size: 26px;
          }
        }

        .dashboard-header-left p {
          font-size: 12px;
          color: #6b7280;
          margin: 2px 0 0 0;
        }

        @media (min-width: 768px) {
          .dashboard-header-left p {
            font-size: 14px;
          }
        }

        .refresh-btn {
          border-radius: 8px;
        }

        /* 统计模块网格 */
        .stats-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
          margin-bottom: 16px;
        }

        @media (min-width: 768px) {
          .stats-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
          }
        }

        .stat-module {
          background: white;
          border-radius: 12px;
          padding: 16px;
          border: 1px solid #e5e7eb;
          transition: all 0.2s;
        }

        @media (min-width: 768px) {
          .stat-module {
            padding: 20px;
          }
        }

        .stat-module:hover {
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          transform: translateY(-2px);
        }

        .stat-module-blue .module-header { color: #3b82f6; }
        .stat-module-blue .module-icon { color: #3b82f6; }
        .stat-module-green .module-header { color: #10b981; }
        .stat-module-green .module-icon { color: #10b981; }
        .stat-module-purple .module-header { color: #8b5cf6; }
        .stat-module-purple .module-icon { color: #8b5cf6; }

        .module-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 12px;
        }

        .module-icon {
          font-size: 20px;
        }

        @media (min-width: 768px) {
          .module-icon {
            font-size: 24px;
          }
        }

        .module-title {
          font-size: 15px;
          font-weight: 600;
        }

        @media (min-width: 768px) {
          .module-title {
            font-size: 17px;
          }
        }

        .module-stats {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
          margin-bottom: 12px;
        }

        .stat-item {
          text-align: center;
        }

        .stat-label {
          font-size: 12px;
          color: #6b7280;
          margin-bottom: 4px;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
        }

        @media (min-width: 768px) {
          .stat-value {
            font-size: 32px;
          }
        }

        .stat-value-blue { color: #3b82f6; }
        .stat-value-green { color: #10b981; }
        .stat-value-purple { color: #8b5cf6; }
        .stat-value-orange { color: #f59e0b; }

        .module-alerts {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }

        @media (min-width: 768px) {
          .module-alerts {
            gap: 12px;
          }
        }

        .alert-box {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 8px;
          font-size: 12px;
        }

        @media (min-width: 768px) {
          .alert-box {
            padding: 10px 12px;
            font-size: 13px;
          }
        }

        .alert-warning {
          background: #fef3c7;
          color: #92400e;
        }

        .alert-danger {
          background: #fee2e2;
          color: #991b1b;
        }

        .alert-neutral {
          background: #f3f4f6;
          color: #6b7280;
        }

        .alert-content {
          flex: 1;
        }

        .alert-num {
          font-size: 18px;
          font-weight: 700;
        }

        .alert-text {
          font-size: 11px;
        }

        .module-link {
          display: flex;
          justify-content: flex-end;
          align-items: center;
          gap: 4px;
          font-size: 13px;
          color: #5645d4;
          text-decoration: none;
          padding-top: 8px;
          border-top: 1px solid #f3f4f6;
        }

        .module-link:hover {
          color: #7c3aed;
        }

        /* 预警网格 */
        .alerts-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 12px;
        }

        @media (min-width: 768px) {
          .alerts-grid {
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
          }
        }

        .alert-card {
          background: white;
          border-radius: 12px;
          border: 1px solid #e5e7eb;
          overflow: hidden;
        }

        .alert-card-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          background: #f9fafb;
          border-bottom: 1px solid #e5e7eb;
          font-size: 14px;
          font-weight: 600;
        }

        .alert-card-body {
          padding: 12px;
          max-height: 240px;
          overflow-y: auto;
        }

        @media (min-width: 768px) {
          .alert-card-body {
            padding: 16px;
          }
        }

        .alert-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .alert-list-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 8px 10px;
          background: #f9fafb;
          border-radius: 8px;
          gap: 8px;
        }

        .item-main {
          flex: 1;
          min-width: 0;
        }

        .item-title {
          font-size: 13px;
          font-weight: 600;
          color: #1f2937;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .item-sub {
          font-size: 11px;
          color: #6b7280;
          font-family: monospace;
        }

        .item-right {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-shrink: 0;
        }

        .item-date {
          font-size: 11px;
          color: #6b7280;
        }

        /* 快捷入口 */
        .quick-links-card {
          grid-column: 1;
        }

        @media (min-width: 768px) {
          .quick-links-card {
            grid-column: auto;
          }
        }

        .quick-links-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 8px;
        }

        @media (min-width: 768px) {
          .quick-links-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
          }
        }

        .quick-link-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          padding: 12px;
          background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
          border-radius: 8px;
          text-decoration: none;
          transition: all 0.2s;
          border: 1px solid transparent;
        }

        .quick-link-item:hover {
          background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
          border-color: #8b5cf6;
          transform: scale(1.02);
        }

        .quick-link-icon {
          font-size: 24px;
        }

        .quick-link-text {
          font-size: 12px;
          color: #1f2937;
          text-align: center;
        }

        @media (min-width: 768px) {
          .quick-link-text {
            font-size: 13px;
          }
        }
      `}</style>
    </div>
  )
}