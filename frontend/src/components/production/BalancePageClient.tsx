'use client'

import { useState } from 'react'
import {
  Button,
  Space,
  Select,
  Card,
  Row,
  Col,
  Typography,
  Statistic,
  Progress,
  InputNumber,
  Alert,
  Switch,
  App,
} from 'antd'
import {
  CalculatorOutlined,
  ReloadOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { getBatches, getMaterialBalance, calculateMaterialBalance } from '@/actions/production'
import type { Batch } from '@/types/production'

const { Text } = Typography

export function BalancePageClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [selectedBatchId, setSelectedBatchId] = useState<string | undefined>()
  const [minBalanceRate, setMinBalanceRate] = useState<number>(95)
  const [editMode, setEditMode] = useState(false)
  const [manualInput, setManualInput] = useState({ input_qty: 0, output_qty: 0 })
  const [calculating, setCalculating] = useState(false)

  // Load batches for the dropdown
  const { data: batches = [] } = useQuery({
    queryKey: ['production-batches-balance'],
    queryFn: async () => {
      const response = await getBatches({ page: 1, page_size: 100 })
      if (response.code === 200) {
        return response.data
      }
      return []
    },
  })

  // Load material balance for the selected batch
  const { data: materialBalance = null, isLoading: materialBalanceLoading } = useQuery({
    queryKey: ['material-balance', selectedBatchId],
    queryFn: async () => {
      if (!selectedBatchId) return null
      const response = await getMaterialBalance(selectedBatchId)
      if (response.code === 200) {
        if (response.data) {
          setManualInput({
            input_qty: response.data.input_qty || 0,
            output_qty: response.data.output_qty || 0,
          })
        }
        return response.data
      } else if (response.code === 404) {
        return null
      }
      return null
    },
    enabled: !!selectedBatchId,
  })

  const handleCalculate = async () => {
    if (!selectedBatchId) {
      message.warning('请先选择批次')
      return
    }
    setCalculating(true)
    try {
      const response = await calculateMaterialBalance(selectedBatchId, minBalanceRate)
      if (response.code === 200) {
        message.success('计算成功')
        queryClient.invalidateQueries({ queryKey: ['material-balance'] })
        if (response.data) {
          setManualInput({
            input_qty: response.data.input_qty || 0,
            output_qty: response.data.output_qty || 0,
          })
        }
      } else {
        message.error(response.message || '计算失败')
      }
    } catch {
      message.error('计算失败')
    } finally {
      setCalculating(false)
    }
  }

  // 手动计算平衡（基于用户输入的值）
  const calculateManualBalance = () => {
    if (!materialBalance) return

    const input = manualInput.input_qty
    const output = manualInput.output_qty
    const loss = input - output
    const balanceRate = input > 0 ? (output / input * 100) : 0
    const isBalanced = balanceRate >= minBalanceRate
    const deviationRate = Math.abs(balanceRate - 100)

    // Update the cache with manually calculated values
    queryClient.setQueryData(['material-balance', selectedBatchId], {
      ...materialBalance,
      input_qty: input,
      output_qty: output,
      loss_qty: loss,
      balance_rate: Math.round(balanceRate * 100) / 100,
      is_balanced: isBalanced,
      deviation_rate: Math.round(deviationRate * 100) / 100,
      calculated_at: new Date().toISOString(),
    })
    setEditMode(false)
    message.success('已更新物料平衡数据')
  }

  return (
    <div className="p-6">
      <Card
        title="物料平衡"
        extra={
          <Space>
            <Text type="secondary">手动输入</Text>
            <Switch size="small" checked={editMode} onChange={setEditMode} />
            <Button
              size="small"
              icon={<EditOutlined />}
              onClick={() => setEditMode(!editMode)}
            >
              {editMode ? '取消编辑' : '编辑'}
            </Button>
          </Space>
        }
      >
        <Row gutter={16} className="mb-4">
          <Col span={8}>
            <Select
              placeholder="选择批次"
              value={selectedBatchId}
              onChange={(value) => setSelectedBatchId(value)}
              style={{ width: '100%' }}
              showSearch
              optionFilterProp="children"
              options={(batches as Batch[]).map((b) => ({
                value: b.id,
                label: `${b.batch_no} - ${b.product_name || b.product_code}`,
              }))}
            />
          </Col>
          <Col span={4}>
            <Space.Compact style={{ width: '100%' }}>
              <InputNumber
                min={0}
                max={100}
                value={minBalanceRate}
                onChange={(v) => setMinBalanceRate(v || 95)}
                style={{ width: '70%' }}
                addonAfter="%"
              />
              <Button
                icon={<CalculatorOutlined />}
                onClick={handleCalculate}
                loading={calculating}
                disabled={!selectedBatchId}
              >
                自动计算
              </Button>
            </Space.Compact>
          </Col>
          <Col span={4}>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['material-balance'] })}
              disabled={!selectedBatchId}
            >
              刷新
            </Button>
          </Col>
        </Row>

        {materialBalanceLoading ? (
          <div className="text-center py-12">
            <Text type="secondary">加载中...</Text>
          </div>
        ) : materialBalance ? (
          <>
            {editMode && (
              <Alert
                type="info"
                message="编辑模式"
                description="您可以手动修改投入总量和产出总量，系统将自动计算平衡率"
                style={{ marginBottom: 16 }}
                showIcon
              />
            )}

            <Row gutter={16} className="mb-4">
              <Col span={6}>
                <Card>
                  {editMode ? (
                    <>
                      <Text type="secondary">投入总量</Text>
                      <InputNumber
                        min={0}
                        value={manualInput.input_qty}
                        onChange={(v) => setManualInput({ ...manualInput, input_qty: v || 0 })}
                        style={{ width: '100%', marginTop: 4 }}
                        size="large"
                        precision={2}
                        prefix="≈"
                        suffix="kg"
                      />
                    </>
                  ) : (
                    <Statistic
                      title="投入总量"
                      value={materialBalance.input_qty || 0}
                      precision={2}
                      suffix="kg"
                    />
                  )}
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  {editMode ? (
                    <>
                      <Text type="secondary">产出总量</Text>
                      <InputNumber
                        min={0}
                        value={manualInput.output_qty}
                        onChange={(v) => setManualInput({ ...manualInput, output_qty: v || 0 })}
                        style={{ width: '100%', marginTop: 4 }}
                        size="large"
                        precision={2}
                        prefix="≈"
                        suffix="kg"
                      />
                    </>
                  ) : (
                    <Statistic
                      title="产出总量"
                      value={materialBalance.output_qty || 0}
                      precision={2}
                      suffix="kg"
                    />
                  )}
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="损耗总量"
                    value={materialBalance.loss_qty || 0}
                    precision={2}
                    suffix="kg"
                  />
                </Card>
              </Col>
              <Col span={6}>
                <Card>
                  <Statistic
                    title="平衡率"
                    value={materialBalance.balance_rate || 0}
                    precision={2}
                    suffix="%"
                  />
                  <Progress
                    percent={materialBalance.balance_rate || 0}
                    strokeColor={materialBalance.is_balanced ? '#52c41a' : '#faad14'}
                    showInfo={false}
                    className="mt-2"
                  />
                </Card>
              </Col>
            </Row>

            <Card title="平衡详情" className="mb-4">
              <Row gutter={16}>
                <Col span={8}>
                  <Text type="secondary">最低平衡率要求：</Text>
                  <Text strong>{materialBalance.min_balance_rate}%</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">偏差率：</Text>
                  <Text strong>{materialBalance.deviation_rate?.toFixed(2) || 0}%</Text>
                </Col>
                <Col span={8}>
                  <Text type="secondary">计算时间：</Text>
                  <Text>
                    {materialBalance.calculated_at
                      ? new Date(materialBalance.calculated_at).toLocaleString('zh-CN')
                      : '-'}
                  </Text>
                </Col>
              </Row>
              {materialBalance.notes && (
                <Row className="mt-4">
                  <Col span={24}>
                    <Text type="secondary">备注：</Text>
                    <Text>{materialBalance.notes}</Text>
                  </Col>
                </Row>
              )}
            </Card>

            {editMode && (
              <Button type="primary" onClick={calculateManualBalance}>
                保存手动输入
              </Button>
            )}
          </>
        ) : (
          <div className="text-center py-12">
            <Text type="secondary">
              {selectedBatchId
                ? '暂无物料平衡数据，请点击"自动计算"按钮进行计算'
                : '请选择批次查看物料平衡数据'}
            </Text>
          </div>
        )}
      </Card>

      <Card title="使用说明" className="mt-4">
        <Text type="secondary">
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            <li style={{ marginBottom: 8 }}>
              <strong>自动计算：</strong>根据批次关联的物料数据和批次产量自动计算投入产出平衡
            </li>
            <li style={{ marginBottom: 8 }}>
              <strong>手动输入：</strong>开启编辑模式后，可直接输入投入总量和产出总量进行计算
            </li>
            <li>
              <strong>平衡率标准：</strong>默认要求平衡率 ≥ 最低平衡率（默认95%），低于此值会触发预警
            </li>
          </ul>
        </Text>
      </Card>
    </div>
  )
}
