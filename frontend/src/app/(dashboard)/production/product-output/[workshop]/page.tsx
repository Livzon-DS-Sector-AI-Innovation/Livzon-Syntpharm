'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, Empty, Button, Modal, Form, Input, App, Breadcrumb, Select, DatePicker } from 'antd'
const { RangePicker } = DatePicker
import { PlusOutlined, AppstoreOutlined, HomeOutlined } from '@ant-design/icons'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { getProductsByWorkshop, createWorkshopProduct, deleteProduct } from '@/actions/product'
import { getSummary, getBatchCount } from '@/actions/product-output'
import type { WorkshopProduct } from '@/types/workshop-product'
import dayjs from 'dayjs'

const { Title, Text } = Typography

const MONTHS = Array.from({ length: 12 }, (_, i) => ({
  label: `${i + 1}月`,
  value: i + 1,
}))

const YEARS = Array.from({ length: 5 }, (_, i) => ({
  label: `${dayjs().year() - 2 + i}年`,
  value: dayjs().year() - 2 + i,
}))

interface ProductSummary {
  daily: number
  monthly: number
  yearly: number
  dailyBatches: number
  monthlyBatches: number
  yearlyBatches: number
}

type ViewMode = 'day' | 'month' | 'year' | 'range'

export default function WorkshopProductsPage() {
  const router = useRouter()
  const params = useParams()
  const workshop = decodeURIComponent(params.workshop as string)
  const { message, modal } = App.useApp()

  const [products, setProducts] = useState<WorkshopProduct[]>([])
  const [summaries, setSummaries] = useState<Record<string, ProductSummary>>({})
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<ViewMode>('month')
  const [selectedDate, setSelectedDate] = useState(dayjs())
  const [selectedMonth, setSelectedMonth] = useState(dayjs().month() + 1)
  const [selectedYear, setSelectedYear] = useState(dayjs().year())
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null]>([dayjs().startOf('month'), dayjs()])
  const [modalVisible, setModalVisible] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form] = Form.useForm()

  const loadProducts = async () => {
    setLoading(true)
    try {
      const response = await getProductsByWorkshop(workshop)
      if (response.code === 200) {
        setProducts(response.data || [])
        loadSummaries(response.data || [])
      }
    } catch {
      message.error('加载产品列表失败')
    } finally {
      setLoading(false)
    }
  }

  const loadSummaries = async (productList: WorkshopProduct[]) => {
    const newSummaries: Record<string, ProductSummary> = {}

    const promises = productList.map(async (product) => {
      let dailyRes, monthlyRes, yearlyRes
      let dailyBatchRes, monthlyBatchRes, yearlyBatchRes

      if (viewMode === 'day') {
        const targetDate = selectedDate.format('YYYY-MM-DD')
        const monthStr = selectedDate.format('YYYY-MM')
        const year = selectedDate.year()
        ;[dailyRes, monthlyRes, yearlyRes] = await Promise.all([
          getSummary({ target_date: targetDate, product_id: product.id }),
          getSummary({ month: monthStr, product_id: product.id }),
          getSummary({ year, product_id: product.id }),
        ])
        ;[dailyBatchRes, monthlyBatchRes, yearlyBatchRes] = await Promise.all([
          getBatchCount({ target_date: targetDate, product_id: product.id }),
          getBatchCount({ month: monthStr, product_id: product.id }),
          getBatchCount({ year, product_id: product.id }),
        ])
      } else if (viewMode === 'month') {
        const monthStr = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}`
        const year = selectedYear
        monthlyRes = await getSummary({ month: monthStr, product_id: product.id })
        yearlyRes = await getSummary({ year, product_id: product.id })
        monthlyBatchRes = await getBatchCount({ month: monthStr, product_id: product.id })
        yearlyBatchRes = await getBatchCount({ year, product_id: product.id })
      } else if (viewMode === 'year') {
        yearlyRes = await getSummary({ year: selectedYear, product_id: product.id })
        yearlyBatchRes = await getBatchCount({ year: selectedYear, product_id: product.id })
      } else if (viewMode === 'range' && dateRange[0] && dateRange[1]) {
        const startDate = dateRange[0].format('YYYY-MM-DD')
        const endDate = dateRange[1].format('YYYY-MM-DD')
        monthlyRes = await getSummary({ start_date: startDate, end_date: endDate, product_id: product.id })
        monthlyBatchRes = await getBatchCount({ start_date: startDate, end_date: endDate, product_id: product.id })
      }

      const extractBatchCount = (res: any) => {
        const data = res.data
        if (Array.isArray(data)) {
          const item = data.find((d: any) => d.product_id === product.id)
          return item?.batch_count || 0
        }
        return 0
      }

      newSummaries[product.id] = {
        daily: dailyRes?.data?.grand_total || 0,
        monthly: monthlyRes?.data?.grand_total || 0,
        yearly: yearlyRes?.data?.grand_total || 0,
        dailyBatches: dailyBatchRes ? extractBatchCount(dailyBatchRes) : 0,
        monthlyBatches: monthlyBatchRes ? extractBatchCount(monthlyBatchRes) : 0,
        yearlyBatches: yearlyBatchRes ? extractBatchCount(yearlyBatchRes) : 0,
      }
    })

    await Promise.all(promises)
    setSummaries(newSummaries)
  }

  useEffect(() => {
    loadProducts()
  }, [workshop])

  useEffect(() => {
    if (products.length > 0) {
      loadSummaries(products)
    }
  }, [viewMode, selectedDate, selectedMonth, selectedYear, dateRange, loadSummaries, products])

  const handleAddProduct = async () => {
    try {
      const values = await form.validateFields()
      setSubmitting(true)
      const response = await createWorkshopProduct({
        workshop,
        name: values.name,
        description: values.description,
      })
      if (response.code === 200) {
        message.success('产品创建成功')
        setModalVisible(false)
        form.resetFields()
        loadProducts()
      } else {
        message.error(response.message || '创建失败')
      }
    } catch {
      message.error('创建失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteProduct = (product: WorkshopProduct) => {
    modal.confirm({
      title: '确认删除',
      content: `确定要删除产品"${product.name}"吗？`,
      onOk: async () => {
        try {
          const response = await deleteProduct(product.id)
          if (response.code === 200) {
            message.success('删除成功')
            loadProducts()
          } else {
            message.error(response.message || '删除失败')
          }
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const handleProductClick = (product: WorkshopProduct) => {
    router.push(`/production/product-output/${encodeURIComponent(workshop)}/${product.id}`)
  }

  const renderDateSelector = () => {
    if (viewMode === 'day') {
      return (
        <DatePicker
          value={selectedDate}
          onChange={(date) => date && setSelectedDate(date)}
          style={{ width: 150 }}
        />
      )
    } else if (viewMode === 'month') {
      return (
        <div className="flex items-center gap-2">
          <Select
            value={selectedYear}
            onChange={setSelectedYear}
            options={YEARS}
            style={{ width: 100 }}
          />
          <Select
            value={selectedMonth}
            onChange={setSelectedMonth}
            options={MONTHS}
            style={{ width: 100 }}
          />
        </div>
      )
    } else if (viewMode === 'year') {
      return (
        <Select
          value={selectedYear}
          onChange={setSelectedYear}
          options={YEARS}
          style={{ width: 120 }}
        />
      )
    } else {
      return (
        <RangePicker
          value={dateRange}
          onChange={(dates) => setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null])}
          style={{ width: 250 }}
        />
      )
    }
  }

  const renderStats = (s: ProductSummary) => {
    if (viewMode === 'range') {
      const startLabel = dateRange[0] ? dateRange[0].format('MM-DD') : ''
      const endLabel = dateRange[1] ? dateRange[1].format('MM-DD') : ''
      return (
        <Row gutter={8}>
          <Col span={24} className="text-center">
            <div className="text-xs text-gray-400">{startLabel} ~ {endLabel}</div>
            <div className="text-base font-semibold text-purple-600">{s.monthly} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-purple-500">{s.monthlyBatches} 批</div>
          </Col>
        </Row>
      )
    }
    if (viewMode === 'day') {
      return (
        <Row gutter={8}>
          <Col span={8} className="text-center">
            <div className="text-xs text-gray-400">今日</div>
            <div className="text-base font-semibold text-blue-600">{s.daily} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-blue-500">{s.dailyBatches} 批</div>
          </Col>
          <Col span={8} className="text-center">
            <div className="text-xs text-gray-400">本月</div>
            <div className="text-base font-semibold text-green-600">{s.monthly} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-green-500">{s.monthlyBatches} 批</div>
          </Col>
          <Col span={8} className="text-center">
            <div className="text-xs text-gray-400">本年</div>
            <div className="text-base font-semibold text-orange-600">{s.yearly} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-orange-500">{s.yearlyBatches} 批</div>
          </Col>
        </Row>
      )
    } else if (viewMode === 'month') {
      return (
        <Row gutter={8}>
          <Col span={12} className="text-center">
            <div className="text-xs text-gray-400">{selectedMonth}月</div>
            <div className="text-base font-semibold text-green-600">{s.monthly} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-green-500">{s.monthlyBatches} 批</div>
          </Col>
          <Col span={12} className="text-center">
            <div className="text-xs text-gray-400">本年</div>
            <div className="text-base font-semibold text-orange-600">{s.yearly} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-orange-500">{s.yearlyBatches} 批</div>
          </Col>
        </Row>
      )
    } else {
      return (
        <Row gutter={8}>
          <Col span={24} className="text-center">
            <div className="text-xs text-gray-400">{selectedYear}年</div>
            <div className="text-base font-semibold text-orange-600">{s.yearly} <span className="text-xs font-normal text-gray-400">kg</span></div>
            <div className="text-xs text-orange-500">{s.yearlyBatches} 批</div>
          </Col>
        </Row>
      )
    }
  }

  return (
    <div className="p-6">
      <Breadcrumb className="mb-4" items={[
        { title: <Link href="/production/product-output"><HomeOutlined /><span style={{ marginLeft: 4 }}>产品管理</span></Link> },
        { title: workshop },
      ]} />

      <div className="flex items-center justify-between mb-6">
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <AppstoreOutlined style={{ marginRight: 8 }} />
            {workshop} - 产品列表
          </Title>
          <Text type="secondary">选择产品查看产量记录</Text>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={viewMode}
            onChange={setViewMode}
            options={[
              { label: '按日', value: 'day' },
              { label: '按月', value: 'month' },
              { label: '按年', value: 'year' },
              { label: '自定义', value: 'range' },
            ]}
            style={{ width: 100 }}
          />
          {renderDateSelector()}
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalVisible(true)}>
            新增产品
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Spin size="large" />
        </div>
      ) : products.length === 0 ? (
        <Empty description="暂无产品，请点击新增产品" />
      ) : (
        <Row gutter={[16, 16]}>
          {products.map((product) => {
            const s = summaries[product.id] || { daily: 0, monthly: 0, yearly: 0, dailyBatches: 0, monthlyBatches: 0, yearlyBatches: 0 }
            return (
              <Col key={product.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  onClick={() => handleProductClick(product)}
                  className="h-full"
                  actions={[
                    <Button
                      type="link"
                      danger
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteProduct(product)
                      }}
                    >
                      删除
                    </Button>,
                  ]}
                >
                  <Card.Meta
                    title={<Text strong style={{ fontSize: 16 }}>{product.name}</Text>}
                    description={product.description || '暂无描述'}
                  />
                  <div className="mt-4 pt-3 border-t border-gray-100">
                    {renderStats(s)}
                  </div>
                </Card>
              </Col>
            )
          })}
        </Row>
      )}

      <Modal
        title="新增产品"
        open={modalVisible}
        onOk={handleAddProduct}
        onCancel={() => {
          setModalVisible(false)
          form.resetFields()
        }}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="产品名称"
            rules={[{ required: true, message: '请输入产品名称' }]}
          >
            <Input placeholder="例如：7-ACP" />
          </Form.Item>
          <Form.Item name="description" label="产品描述">
            <Input.TextArea rows={3} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
