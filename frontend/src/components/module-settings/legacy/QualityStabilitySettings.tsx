'use client'

import { Card, Typography } from 'antd'

const { Title, Text } = Typography

export default function StabilitySettingsPage({ embedded = false }: { embedded?: boolean }) {
  return (
    <Card>
      {/* 嵌入「模块配置」页签时标题由外层页头承担 */}
      {embedded ? null : <Title level={4}>稳定性实验管理 - 提醒设置</Title>}
      <Text type="secondary">功能开发中...</Text>
    </Card>
  )
}
