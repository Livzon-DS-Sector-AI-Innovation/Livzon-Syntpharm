'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, Empty, Breadcrumb, Table, Tag, DatePicker, Select } from 'antd'
import { HomeOutlined, AppstoreOutlined } from '@ant-design/icons'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { getProductOutputs } from '@/actions/product-output'
import type { ProductOutput } from '@/types/product-output'
import dayjs from 'dayjs'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

interface WorkshopStats {
  workshop: string
  total_weight: number
  batch_count: number
  batch_nos: string[]
  monthly: { [key: string]: { weight: number; batches: number } }
  yearly: { [key: string]: { weight: number; batches: number } }
}

export default function ProductDetailPage() {
  const _router = useRouter()
  const params = useParams()
  const productName = decodeURIComponent(params.productName as string)
  
  const [loading, setLoading] = useState(true)
  const [workshopStats, setWorkshopStats] = useState<WorkshopStats[]>([])
  const [totalWeight, setTotalWeight] = useState(0)
  const [totalBatches, setTotalBatches] = useState(0)
  
  // 筛选状态
  const [filterType, setFilterType] = useState<'all' | 'date' | 'month' | 'year'>('all')
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)
  const [selectedMonth, setSelectedMonth] = useState<dayjs.Dayjs | null>(null)
  const [selectedYear, setSelectedYear] = useState<number | null>(null)

  useEffect(() => {
    loadProductData()
  }, [productName, filterType, dateRange, selectedMonth, selectedYear])

  const loadProductData = async () => {
    setLoading(true)
    try {
      const queryParams: any = { 
        product_name: productName,
        page_size: 200 
      }
      
      if (filterType === 'date' && dateRange && dateRange[0] && dateRange[1]) {
        queryParams.start_date = dateRange[0].format('YYYY-MM-DD')
        queryParams.end_date = dateRange[1].format('YYYY-MM-DD')
      } else if (filterType === 'month' && selectedMonth) {
        queryParams.start_date = selectedMonth.startOf('month').format('YYYY-MM-DD')
        queryParams.end_date = selectedMonth.endOf('month').format('YYYY-MM-DD')
      } else if (filterType === 'year' && selectedYear) {
        queryParams.start_date = `${selectedYear}-01-01`
        queryParams.end_date = `${selectedYear}-12-31`
      }
      
      const response = await getProductOutputs(queryParams)
      
      if (response.code === 200 && response.data) {
        const records = response.data as ProductOutput[]
        const workshopMap = new Map<string, WorkshopStats>()
        let totalW = 0
        let totalB = 0
        
        records.forEach(record => {
          totalW += record.weight
          totalB += 1
          
          const dateStr = record.production_date || ''
          const year = dateStr.substring(0, 4)
          const month = dateStr.substring(0, 7)
          
          if (!workshopMap.has(record.workshop)) {
            workshopMap.set(record.workshop, {
              workshop: record.workshop,
              total_weight: 0,
              batch_count: 0,
              batch_nos: [],
              monthly: {},
              yearly: {}
            })
          }
          
          const stats = workshopMap.get(record.workshop)!
          stats.total_weight += record.weight
          stats.batch_count += 1
          if (record.batch_no && !stats.batch_nos.includes(record.batch_no)) {
            stats.batch_nos.push(record.batch_no)
          }
          
          if (month) {
            if (!stats.monthly[month]) stats.monthly[month] = { weight: 0, batches: 0 }
            stats.monthly[month].weight += record.weight
            stats.monthly[month].batches += 1
          }
          if (year) {
            if (!stats.yearly[year]) stats.yearly[year] = { weight: 0, batches: 0 }
            stats.yearly[year].weight += record.weight
            stats.yearly[year].batches += 1
          }
        })
        
        setWorkshopStats(Array.from(workshopMap.values()))
        setTotalWeight(totalW)
        setTotalBatches(totalB)
      }
    } catch (error) {
      console.error('加载产品数据失败:', error)
    } finally {
      setLoading(false)
    }
  }

  const columns = [
    {
      title: '车间',
      dataIndex: 'workshop',
      key: 'workshop',
      render: (text: string) => <Tag color="blue">{text}</Tag>
    },
    {
      title: '总产量 (kg)',
      dataIndex: 'total_weight',
      key: 'total_weight',
      render: (text: number) => <span className="font-semibold text-blue-600">{text.toFixed(2)}</span>
    },
    {
      title: '总批次',
      dataIndex: 'batch_count',
      key: 'batch_count',
      render: (text: number) => <span className="font-semibold text-green-600">{text} 批</span>
    },
    {
      title: '每月产量',
      key: 'monthly',
      render: (_: any, record: WorkshopStats) => (
        <div>
          {Object.entries(record.monthly)
            .sort(([a], [b]) => b.localeCompare(a))
            .map(([month, data]) => (
              <div key={month} className="text-sm">
                <Tag color="purple">{month}</Tag>
                <span className="text-blue-600 font-medium">{data.weight.toFixed(2)} kg</span>
                <span className="text-gray-400 mx-1">/</span>
                <span className="text-green-600">{data.batches} 批</span>
              </div>
            ))}
        </div>
      )
    },
    {
      title: '每年产量',
      key: 'yearly',
      render: (_: any, record: WorkshopStats) => (
        <div>
          {Object.entries(record.yearly)
            .sort(([a], [b]) => b.localeCompare(a))
            .map(([year, data]) => (
              <div key={year} className="text-sm">
                <Tag color="cyan">{year}年</Tag>
                <span className="text-blue-600 font-medium">{data.weight.toFixed(2)} kg</span>
                <span className="text-gray-400 mx-1">/</span>
                <span className="text-green-600">{data.batches} 批</span>
              </div>
            ))}
        </div>
      )
    },
    {
      title: '批号列表',
      dataIndex: 'batch_nos',
      key: 'batch_nos',
      render: (batchNos: string[]) => (
        <div className="flex flex-wrap gap-1">
          {batchNos.map(batchNo => (
            <Tag key={batchNo} color="orange">{batchNo}</Tag>
          ))}
        </div>
      )
    }
  ]

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div className="p-6">
      <Breadcrumb className="mb-4" items={[
        { title: <Link href="/production/product-output"><HomeOutlined /><span style={{ marginLeft: 4 }}>产品管理</span></Link> },
        { title: <Link href="/production/product-output/all-products">全部产品</Link> },
        { title: productName },
      ]} />

      <div className="mb-6">
        <Title level={4} style={{ margin: 0 }}>
          <AppstoreOutlined style={{ marginRight: 8 }} />
          {productName} - 生产详情
        </Title>
        <Text type="secondary">该产品在各车间的生产情况</Text>
      </div>

      {/* 筛选控件 */}
      <Card className="mb-6">
        <Row gutter={[16, 16]} align="middle">
          <Col>
            <Text strong>筛选方式：</Text>
          </Col>
          <Col>
            <Select
              value={filterType}
              onChange={(value) => {
                setFilterType(value)
                setDateRange(null)
                setSelectedMonth(null)
                setSelectedYear(null)
              }}
              style={{ width: 120 }}
              options={[
                { value: 'all', label: '全部' },
                { value: 'date', label: '按日期范围' },
                { value: 'month', label: '按月份' },
                { value: 'year', label: '按年份' },
              ]}
            />
          </Col>
          {filterType === 'date' && (
            <Col>
              <RangePicker
                value={dateRange}
                onChange={(dates) => setDateRange(dates)}
              />
            </Col>
          )}
          {filterType === 'month' && (
            <Col>
              <DatePicker
                picker="month"
                value={selectedMonth}
                onChange={(date) => setSelectedMonth(date)}
                placeholder="选择月份"
              />
            </Col>
          )}
          {filterType === 'year' && (
            <Col>
              <Select
                value={selectedYear}
                onChange={(value) => setSelectedYear(value)}
                placeholder="选择年份"
                style={{ width: 120 }}
                options={Array.from({ length: 10 }, (_, i) => 2020 + i).map(year => ({
                  value: year,
                  label: `${year}年`
                }))}
              />
            </Col>
          )}
        </Row>
      </Card>

      <Row gutter={[16, 16]} className="mb-6">
        <Col xs={24} sm={12} md={8}>
          <Card>
            <div className="text-center">
              <div className="text-sm text-gray-500">总产量</div>
              <div className="text-2xl font-bold text-blue-600">{totalWeight.toFixed(2)} <span className="text-sm">kg</span></div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <div className="text-center">
              <div className="text-sm text-gray-500">总批次</div>
              <div className="text-2xl font-bold text-green-600">{totalBatches} <span className="text-sm">批</span></div>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <div className="text-center">
              <div className="text-sm text-gray-500">涉及车间</div>
              <div className="text-2xl font-bold text-orange-600">{workshopStats.length} <span className="text-sm">个</span></div>
            </div>
          </Card>
        </Col>
      </Row>

      {workshopStats.length === 0 ? (
        <Empty description="暂无生产数据" />
      ) : (
        <Card title="各车间生产情况">
          <Table
            columns={columns}
            dataSource={workshopStats}
            rowKey="workshop"
            pagination={false}
          />
        </Card>
      )}
    </div>
  )
}
