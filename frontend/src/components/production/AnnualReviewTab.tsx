'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Table, Spin, Empty, Alert, Button, Tag } from 'antd'
import { ArrowUpOutlined, ArrowDownOutlined, DownloadOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { fetchAnnualReview, fetchExportAnnualReview } from '@/actions/product-output'
import type { AnnualReviewData, TopProduct } from '@/types/product-output'

interface Props {
  year: number
}

export default function AnnualReviewTab({ year }: Props) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<AnnualReviewData | null>(null)

  useEffect(() => {
    loadData()
  }, [year])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchAnnualReview(year)
      if (res.code !== 200) {
        setError(res.message || '加载数据失败')
        return
      }
      setData(res.data)
    } catch (err) {
      console.error('Failed to load annual review:', err)
      setError('加载年度回顾数据失败')
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async () => {
    try {
      const response = await fetchExportAnnualReview(year)
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `年度回顾_${year}年.xlsx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Failed to export:', err)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  if (error) {
    return <Alert message={error} type="error" showIcon />
  }

  if (!data) {
    return <Empty description="暂无数据" />
  }

  const { overview, monthly_trend, workshop_ranking, top_products } = data || {}
  const safeOverview = overview || { total_weight: 0, previous_year_weight: 0, weight_yoy: 0, total_batches: 0, previous_year_batches: 0, batch_yoy: 0, active_workshops: 0, active_products: 0 }
  const safeMonthlyTrend = monthly_trend || []
  const safeWorkshopRanking = workshop_ranking || []
  const safeTopProducts = top_products || []

  // 月度趋势图配置
  const trendOption: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const month = params[0].name
        let html = `<strong>${month}月</strong><br/>`
        params.forEach((p: any) => {
          html += `${p.marker} ${p.seriesName}: ${p.value.toLocaleString()} kg<br/>`
        })
        return html
      },
    },
    legend: {
      data: [`${year}年`, `${year - 1}年`],
      bottom: 0,
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category',
      data: safeMonthlyTrend.map((m: { month: number }) => `${m.month}月`),
    },
    yAxis: {
      type: 'value',
      name: 'kg',
    },
    series: [
      {
        name: `${year}年`,
        type: 'line',
        data: safeMonthlyTrend.map((m: { current_year_weight: number }) => m.current_year_weight),
        smooth: true,
        itemStyle: { color: '#5645d4' },
      },
      {
        name: `${year - 1}年`,
        type: 'line',
        data: safeMonthlyTrend.map((m: { previous_year_weight: number }) => m.previous_year_weight),
        smooth: true,
        itemStyle: { color: '#1aae39' },
        lineStyle: { type: 'dashed' },
      },
    ],
  }

  // 车间排名图配置
  const rankingOption: EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = params[0]
        const item = safeWorkshopRanking.find((w: { workshop: string }) => w.workshop === p.name)
        return `<strong>${p.name}</strong><br/>产量: ${p.value.toLocaleString()} kg<br/>批次: ${item?.batch_count || 0}`
      },
    },
    grid: { left: 100, right: 60, top: 10, bottom: 20 },
    xAxis: {
      type: 'value',
      name: 'kg',
    },
    yAxis: {
      type: 'category',
      data: safeWorkshopRanking.map((w: { workshop: string }) => w.workshop).reverse(),
    },
    series: [
      {
        type: 'bar',
        data: safeWorkshopRanking.map((w: { total_weight: number }) => w.total_weight).reverse(),
        itemStyle: {
          color: (params: any) => {
            const colors = ['#5645d4', '#1aae39', '#dd5b00', '#e03131', '#13c2c2']
            return colors[params.dataIndex % colors.length]
          },
        },
        label: {
          show: true,
          position: 'right',
          formatter: (params: any) => `${params.value.toLocaleString()} kg`,
        },
      },
    ],
  }

  // TOP产品饼图配置
  const pieOption: EChartsOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} kg ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { fontSize: 12 },
    },
    series: [
      {
        name: '产量分布',
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 11,
        },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
        },
        data: safeTopProducts.map((p: { product_name: string; workshop: string; total_weight: number }, i: number) => ({
          name: `${p.product_name}(${p.workshop})`,
          value: p.total_weight,
          itemStyle: {
            color: ['#5645d4', '#1aae39', '#dd5b00', '#e03131', '#13c2c2', '#8b5cf6', '#f59e0b', '#0075de', '#ff64c8', '#2a9d99'][i % 10],
          },
        })),
      },
    ],
  }

  // TOP产品表格列
  const topProductColumns = [
    {
      title: '排名',
      dataIndex: 'rank',
      key: 'rank',
      width: 80,
      render: (rank: number) => {
        const colors = ['#f59e0b', '#9ca3af', '#d97706']
        return (
          <Tag color={rank <= 3 ? colors[rank - 1] : 'default'}>
            {rank}
          </Tag>
        )
      },
    },
    {
      title: '产品名称',
      dataIndex: 'product_name',
      key: 'product_name',
    },
    {
      title: '车间',
      dataIndex: 'workshop',
      key: 'workshop',
      width: 120,
    },
    {
      title: '总产量(kg)',
      dataIndex: 'total_weight',
      key: 'total_weight',
      sorter: (a: TopProduct, b: TopProduct) => a.total_weight - b.total_weight,
      render: (val: number) => val.toLocaleString(),
    },
    {
      title: '批次数',
      dataIndex: 'batch_count',
      key: 'batch_count',
      width: 100,
    },
    {
      title: '平均批次重量(kg)',
      dataIndex: 'avg_weight',
      key: 'avg_weight',
      width: 150,
      render: (val: number) => val.toFixed(1),
    },
  ]

  return (
    <div className="space-y-6">
      {/* 年度概览卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="年度总产量"
              value={safeOverview.total_weight}
              suffix="kg"
              precision={0}
              valueStyle={{ color: '#5645d4' }}
            />
            <div className="mt-2">
              {safeOverview.weight_yoy >= 0 ? (
                <span className="text-green-600 text-sm">
                  <ArrowUpOutlined /> {safeOverview.weight_yoy}% 同比
                </span>
              ) : (
                <span className="text-red-600 text-sm">
                  <ArrowDownOutlined /> {Math.abs(safeOverview.weight_yoy)}% 同比
                </span>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="年度总批次"
              value={safeOverview.total_batches}
              valueStyle={{ color: '#1aae39' }}
            />
            <div className="mt-2">
              {safeOverview.batch_yoy >= 0 ? (
                <span className="text-green-600 text-sm">
                  <ArrowUpOutlined /> {safeOverview.batch_yoy}% 同比
                </span>
              ) : (
                <span className="text-red-600 text-sm">
                  <ArrowDownOutlined /> {Math.abs(safeOverview.batch_yoy)}% 同比
                </span>
              )}
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃车间"
              value={safeOverview.active_workshops}
              suffix="个"
              valueStyle={{ color: '#dd5b00' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="活跃产品"
              value={safeOverview.active_products}
              suffix="个"
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 月度趋势图 */}
      <Card title="月度产量趋势" extra={<Button icon={<DownloadOutlined />} onClick={handleExport}>导出Excel</Button>}>
        <ReactECharts option={trendOption} style={{ height: 350 }} />
      </Card>

      {/* 车间排名图 */}
      {safeWorkshopRanking.length > 0 && (
        <Card title="车间年度产量排名">
          <ReactECharts option={rankingOption} style={{ height: Math.max(280, safeWorkshopRanking.length * 42 + 60) }} />
        </Card>
      )}

      {/* TOP产品饼图 + 表格 */}
      {safeTopProducts.length > 0 && (
        <Card title={`年度 TOP ${safeTopProducts.length} 产品产量分布`}>
          <Row gutter={24}>
            <Col xs={24} md={12}>
              <ReactECharts option={pieOption} style={{ height: 380 }} />
            </Col>
            <Col xs={24} md={12}>
              <Table
                columns={topProductColumns}
                dataSource={safeTopProducts}
                rowKey="rank"
                pagination={false}
                size="middle"
              />
            </Col>
          </Row>
        </Card>
      )}

      {safeWorkshopRanking.length === 0 && safeTopProducts.length === 0 && (
        <Empty description={`${year}年暂无生产数据`} />
      )}
    </div>
  )
}
