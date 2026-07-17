'use client'

import { useEffect, useState } from 'react'
import { Card, Row, Col, Typography, Spin, Empty, Breadcrumb, Input, message } from 'antd'
import { HomeOutlined, AppstoreOutlined, SearchOutlined } from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { getProductOutputs } from '@/actions/product-output'
import type { ProductOutput } from '@/types/product-output'

const { Title, Text } = Typography

interface ProductInfo {
  product_id: string
  product_name: string
  total_weight: number
  total_batches: number
  workshops: Array<{
    workshop: string
    weight: number
    batches: number
  }>
}

export default function AllProductsPage() {
  const router = useRouter()
  const [products, setProducts] = useState<ProductInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [searchText, setSearchText] = useState('')

  useEffect(() => {
    loadAllProducts()
  }, [])

  const loadAllProducts = async () => {
    setLoading(true)
    try {
      console.log('开始加载产品数据...')
      const response = await getProductOutputs({ page_size: 200 })
      console.log('API 响应:', response)
      
      if (response.code === 200 && response.data) {
        const records = response.data as ProductOutput[]
        console.log('记录数量:', records.length)
        
        const productMap = new Map<string, ProductInfo>()
        
        records.forEach(record => {
          const key = record.product_name
          
          if (!productMap.has(key)) {
            productMap.set(key, {
              product_id: record.product_id || '',
              product_name: record.product_name,
              total_weight: 0,
              total_batches: 0,
              workshops: []
            })
          }
          
          const product = productMap.get(key)!
          product.total_weight += record.weight
          product.total_batches += 1
          
          const workshopIdx = product.workshops.findIndex(w => w.workshop === record.workshop)
          if (workshopIdx >= 0) {
            product.workshops[workshopIdx].weight += record.weight
            product.workshops[workshopIdx].batches += 1
          } else {
            product.workshops.push({
              workshop: record.workshop,
              weight: record.weight,
              batches: 1
            })
          }
        })
        
        const productList = Array.from(productMap.values())
        console.log('产品列表:', productList)
        setProducts(productList)
      } else {
        console.error('API 返回错误:', response)
        message.error(response.message || '加载数据失败')
      }
    } catch (error) {
      console.error('加载产品数据失败:', error)
      message.error('加载数据失败，请检查网络连接')
    } finally {
      setLoading(false)
    }
  }

  const filteredProducts = products.filter(p => 
    p.product_name.toLowerCase().includes(searchText.toLowerCase())
  )

  const handleProductClick = (product: ProductInfo) => {
    router.push(`/production/product-output/product/${encodeURIComponent(product.product_name)}`)
  }

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
        { title: '全部产品' },
      ]} />

      <div className="flex items-center justify-between mb-6">
        <div>
          <Title level={4} style={{ margin: 0 }}>
            <AppstoreOutlined style={{ marginRight: 8 }} />
            全部产品
          </Title>
          <Text type="secondary">跨车间查看产品产量统计</Text>
        </div>
        <Input
          placeholder="搜索产品名称"
          prefix={<SearchOutlined />}
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 250 }}
          allowClear
        />
      </div>

      {filteredProducts.length === 0 ? (
        <Empty description={products.length === 0 ? "暂无产品数据" : "没有找到匹配的产品"} />
      ) : (
        <Row gutter={[16, 16]}>
          {filteredProducts.map((product) => (
            <Col key={product.product_id || product.product_name} xs={24} sm={12} md={8} lg={6}>
              <Card
                hoverable
                onClick={() => handleProductClick(product)}
                className="h-full"
              >
                <Card.Meta
                  title={<Text strong style={{ fontSize: 16 }}>{product.product_name}</Text>}
                  description={
                    <div className="mt-2">
                      <div className="text-sm">
                        <span className="text-gray-500">总产量：</span>
                        <span className="font-semibold text-blue-600">{product.total_weight.toFixed(2)} kg</span>
                      </div>
                      <div className="text-sm">
                        <span className="text-gray-500">总批次：</span>
                        <span className="font-semibold text-green-600">{product.total_batches} 批</span>
                      </div>
                      <div className="text-sm mt-2">
                        <span className="text-gray-500">涉及车间：</span>
                        <span className="text-orange-600">{product.workshops.map(w => w.workshop).join('、')}</span>
                      </div>
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  )
}
