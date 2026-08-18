'use client'

import { useState, useEffect } from 'react'
import {Modal, InputNumber, Typography, Space, App} from 'antd'
import {createTarget, updateTarget, type UnitConsumptionTarget} from '@/lib/api/client/energy'

const { Text } = Typography

interface TargetModalProps {
  open: boolean
  workshopId: string | null
  workshopName: string
  targetMonth: string
  existingTarget?: UnitConsumptionTarget | null
  onClose: () => void
  onSuccess: (target: UnitConsumptionTarget) => void
}

export default function TargetModal({
  open,
  workshopId,
  workshopName,
  targetMonth,
  existingTarget,
  onClose,
  onSuccess,
}: TargetModalProps) {
  const { message } = App.useApp()
  const [loading, setLoading] = useState(false)
  const [targetValue, setTargetValue] = useState<number | null>(null)

  // 当 Modal 打开时，初始化目标值
  useEffect(() => {
    if (open && existingTarget) {
      setTargetValue(existingTarget.target_unit_consumption)
    } else if (open) {
      setTargetValue(null)
    }
  }, [open, existingTarget])

  const handleOk = async () => {
    if (!workshopId || !targetValue || targetValue <= 0) {
      message.error('请输入有效的目标单耗值')
      return
    }

    setLoading(true)
    try {
      let result: UnitConsumptionTarget

      if (existingTarget) {
        // 更新已有目标
        result = await updateTarget(existingTarget.id, {
          target_unit_consumption: Number(targetValue),
        })
        message.success('目标修改成功')
      } else {
        // 创建新目标
        result = await createTarget({
          workshop_id: workshopId,
          target_month: targetMonth,
          target_unit_consumption: Number(targetValue),
        })
        message.success('目标设定成功')
      }

      onSuccess(result)
      onClose()
    } catch (error: any) {
      message.error(error.message || '操作失败')
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    onClose()
  }

  return (
    <Modal
      title={existingTarget ? '修改单耗目标' : '设定单耗目标'}
      open={open}
      onOk={handleOk}
      onCancel={handleCancel}
      confirmLoading={loading}
      okText="确认设定"
      cancelText="取消"
      width={500}
    >
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        <div>
          <Text strong>车间：</Text>
          <Text>{workshopName}</Text>
        </div>

        <div>
          <Text strong>目标月份：</Text>
          <Text>{targetMonth}</Text>
        </div>

        <div>
          <Text strong>目标单耗（kWh/kg）：</Text>
          <InputNumber
            value={targetValue}
            onChange={(val) => setTargetValue(val)}
            min={0.0001}
            max={9999.9999}
            precision={4}
            step={0.1}
            placeholder="请输入目标单耗"
            style={{ width: '100%', marginTop: 8 }}
            addonAfter="kWh/kg"
          />
          <Text type="secondary" style={{ fontSize: 12, marginTop: 4, display: 'block' }}>
            💡 建议参考过去 3 个月平均值
          </Text>
        </div>

        {/* 参考数据区域 - 可以从后端获取或硬编码 */}
{/*
        <div style={{ background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
          <Text strong>💡 参考数据：</Text>
          <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
            <li>上月实际单耗：待加载</li>
            <li>近 3 月平均：待加载</li>
            <li>行业标杆：2.20 kWh/kg</li>
          </ul>
        </div>
*/}
      </Space>
    </Modal>
  )
}
