'use client'

import { useState } from 'react'
import { Card, Row, Col, Typography, Button, Select, Tabs } from 'antd'
import { HomeOutlined, AppstoreOutlined, FilterOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import dayjs from 'dayjs'
import { WORKSHOPS } from '@/types/product-output'
import WorkshopRankingTrend from '@/components/production/WorkshopRankingTrend'
import AnnualReviewTab from '@/components/production/AnnualReviewTab'

const { Title, Text } = Typography

const YEAR_OPTIONS = Array.from({ length: 5 }, (_, i) => {
  const y = dayjs().year() - 2 + i
  return { label: `${y}年`, value: y }
})

export default function ProductOutputPage() {
  const router = useRouter()
  const [chartYear, setChartYear] = useState(dayjs().year())
  const [activeTab, setActiveTab] = useState('workshop')

  const handleWorkshopClick = (workshop: string) => {
    router.push(`/production/product-output/${encodeURIComponent(workshop)}`)
  }

  const handleFilterProducts = () => {
    router.push('/production/product-output/all-products')
  }

  const tabItems = [
    {
      key: 'workshop',
      label: '车间产量',
      children: (
        <>
          <WorkshopRankingTrend year={chartYear} />

          {/* Workshop cards */}
          <Row gutter={[16, 16]}>
            {WORKSHOPS.map((workshop) => (
              <Col key={workshop} xs={24} sm={12} md={8} lg={6}>
                <Card
                  hoverable
                  onClick={() => handleWorkshopClick(workshop)}
                  className="h-full"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-lg bg-blue-50 flex items-center justify-center">
                      <AppstoreOutlined className="text-2xl text-blue-500" />
                    </div>
                    <div>
                      <Text strong className="text-base">{workshop}</Text>
                      <br />
                      <Text type="secondary" className="text-sm">点击查看产品</Text>
                    </div>
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
        </>
      ),
    },
    {
      key: 'annual',
      label: '年度回顾',
      children: <AnnualReviewTab year={chartYear} />,
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <HomeOutlined style={{ marginRight: 8 }} />
            产品管理
          </Title>
          <Text type="secondary">选择车间查看产品产量</Text>
        </div>
        <div className="flex items-center gap-3">
          <Select
            value={chartYear}
            onChange={setChartYear}
            options={YEAR_OPTIONS}
            style={{ width: 110 }}
          />
          <Button
            type="primary"
            icon={<FilterOutlined />}
            onClick={handleFilterProducts}
            size="large"
          >
            筛选产品
          </Button>
        </div>
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="large"
      />
    </div>
  )
}
