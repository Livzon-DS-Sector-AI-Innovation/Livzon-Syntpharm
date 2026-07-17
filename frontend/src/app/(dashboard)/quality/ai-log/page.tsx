'use client'

import React, { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  DatePicker,
  Input,
  Select,
  Row,
  Col,
  Statistic,
  Modal,
  Descriptions,
  Typography,
  Alert,
  Empty,
} from 'antd'
import {
  SearchOutlined,
  RobotOutlined,
  EyeOutlined,
 ReloadOutlined,
  ClockCircleOutlined,
  UserOutlined,
  FileTextOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { getAiLogs, AiLogItem, AiLogFilter } from '@/actions/quality'

const { RangePicker } = DatePicker
const { TextArea } = Input
const { Text } = Typography

// 操作类型映射
const operateTypeLabels: Record<string, string> = {
  '领用事由生成': 'primary',
  '报废原因生成': 'warning',
  '试剂异常分析': 'success',
}

export default function AiLogPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<AiLogItem[]>([])
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  })
  const [filter, setFilter] = useState<AiLogFilter>({})
  const [selectedLog, setSelectedLog] = useState<AiLogItem | null>(null)
  const [detailModalVisible, setDetailModalVisible] = useState(false)

  // 统计数据
  const [statistics, setStatistics] = useState({
    total: 0,
    today: 0,
    reason_count: 0,
    scrap_count: 0,
    analyse_count: 0,
  })

  // 获取AI日志列表
  const fetchData = async (params?: { page?: number; page_size?: number }) => {
    setLoading(true)
    try {
      const response = await getAiLogs({
        ...filter,
        page: params?.page || pagination.current,
        page_size: params?.page_size || pagination.pageSize,
      })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setPagination({
          current: response.data.page || 1,
          pageSize: response.data.page_size || 20,
          total: response.data.total || 0,
        })

        // 更新统计
        const items = response.data.items || []
        const today = dayjs().format('YYYY-MM-DD')
        setStatistics({
          total: response.data.total || 0,
          today: items.filter((item: AiLogItem) => dayjs(item.created_at).format('YYYY-MM-DD') === today).length,
          reason_count: items.filter((item: AiLogItem) => item.operate_type === '领用事由生成').length,
          scrap_count: items.filter((item: AiLogItem) => item.operate_type === '报废原因生成').length,
          analyse_count: items.filter((item: AiLogItem) => item.operate_type === '试剂异常分析').length,
        })
      }
    } catch (error) {
      console.error('获取AI日志失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  // 搜索
  const handleSearch = () => {
    setPagination({ ...pagination, current: 1 })
    fetchData({ page: 1, page_size: pagination.pageSize })
  }

  // 重置
  const handleReset = () => {
    setFilter({})
    setPagination({ ...pagination, current: 1 })
    fetchData({ page: 1, page_size: pagination.pageSize })
  }

  // 分页变化
  const handleTableChange = (newPagination: any) => {
    fetchData({ page: newPagination.current, page_size: newPagination.pageSize })
  }

  // 查看详情
  const handleViewDetail = (record: AiLogItem) => {
    setSelectedLog(record)
    setDetailModalVisible(true)
  }

  // 刷新
  const handleRefresh = () => {
    fetchData()
  }

  // 表格列定义
  const columns: ColumnsType<AiLogItem> = [
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (value: string) => dayjs(value).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作类型',
      dataIndex: 'operate_type',
      key: 'operate_type',
      width: 130,
      render: (value: string) => (
        <Tag color={operateTypeLabels[value] || 'default'}>
          {value}
        </Tag>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
      width: 100,
    },
    {
      title: '关联单据',
      dataIndex: 'bill_no',
      key: 'bill_no',
      width: 150,
      render: (value: string) => value || '-',
    },
    {
      title: '用户输入',
      dataIndex: 'user_input',
      key: 'user_input',
      ellipsis: true,
      render: (value: string) => value || '-',
    },
    {
      title: 'AI响应',
      dataIndex: 'ai_response',
      key: 'ai_response',
      ellipsis: true,
      render: (value: string) => value || '-',
    },
    {
      title: '延迟(ms)',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      width: 100,
      render: (value: number) => value ? `${value}ms` : '-',
    },
    {
      title: 'Token数',
      dataIndex: 'tokens_used',
      key: 'tokens_used',
      width: 100,
      render: (value: number) => value || '-',
    },
    {
      title: '状态',
      dataIndex: 'error_message',
      key: 'status',
      width: 100,
      render: (_, record) => (
        record.error_message ? (
          <Tag color="error">失败</Tag>
        ) : (
          <Tag color="success">成功</Tag>
        )
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          详情
        </Button>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: 24 }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <RobotOutlined />
          AI交互日志
        </h2>
        <p style={{ margin: '8px 0 0 0', color: '#666' }}>
          查看AI辅助生成领用事由、报废原因及异常分析的交互记录
        </p>
      </div>

      {/* GMP合规提示 */}
      <Alert
        message="GMP合规说明"
        description="AI生成的领用事由、报废原因及异常分析建议仅供人工参考，需经过质量人员审核确认后方可生效。AI不参与任何业务决策。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="总调用次数"
              value={statistics.total}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic
              title="今日调用"
              value={statistics.today}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="领用事由"
              value={statistics.reason_count}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="报废原因"
              value={statistics.scrap_count}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title="异常分析"
              value={statistics.analyse_count}
              prefix={<RobotOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 搜索条件 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜索关键字"
                value={filter.keyword || ''}
                onChange={(e) => setFilter({ ...filter, keyword: e.target.value })}
                style={{ width: 200 }}
                allowClear
              />
              <Select
                placeholder="操作类型"
                value={filter.operate_type}
                onChange={(value) => setFilter({ ...filter, operate_type: value })}
                style={{ width: 150 }}
                allowClear
                options={[
                  { label: '领用事由生成', value: '领用事由生成' },
                  { label: '报废原因生成', value: '报废原因生成' },
                  { label: '试剂异常分析', value: '试剂异常分析' },
                ]}
              />
              <Input
                placeholder="操作人"
                value={filter.operator || ''}
                onChange={(e) => setFilter({ ...filter, operator: e.target.value })}
                style={{ width: 120 }}
                allowClear
              />
              <RangePicker
                onChange={(dates) => {
                  setFilter({
                    ...filter,
                    start_date: dates?.[0]?.format('YYYY-MM-DD'),
                    end_date: dates?.[1]?.format('YYYY-MM-DD'),
                  })
                }}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
                查询
              </Button>
              <Button onClick={handleReset}>重置</Button>
              <Button icon={<ReloadOutlined />} onClick={handleRefresh}>
                刷新
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card>
        {data.length > 0 ? (
          <Table
            columns={columns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            pagination={{
              ...pagination,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 条`,
            }}
            onChange={handleTableChange}
            scroll={{ x: 1300 }}
          />
        ) : (
          <Empty description="暂无AI交互日志记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="AI交互详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
        ]}
        width={800}
      >
        {selectedLog && (
          <div>
            <Descriptions bordered column={2} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="操作时间" span={2}>
                {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="操作类型">
                <Tag color={operateTypeLabels[selectedLog.operate_type] || 'default'}>
                  {selectedLog.operate_type}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="操作人">
                {selectedLog.operator}
              </Descriptions.Item>
              <Descriptions.Item label="关联单据">
                {selectedLog.bill_no || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="响应延迟">
                {selectedLog.latency_ms ? `${selectedLog.latency_ms}ms` : '-'}
              </Descriptions.Item>
              <Descriptions.Item label="Token使用">
                {selectedLog.tokens_used || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {selectedLog.error_message ? (
                  <Tag color="error">失败: {selectedLog.error_message}</Tag>
                ) : (
                  <Tag color="success">成功</Tag>
                )}
              </Descriptions.Item>
            </Descriptions>

            {selectedLog.system_prompt && (
              <div style={{ marginBottom: 16 }}>
                <Text strong>系统提示词:</Text>
                <div
                  style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    marginTop: 8,
                    whiteSpace: 'pre-wrap',
                    fontSize: 12,
                  }}
                >
                  {selectedLog.system_prompt}
                </div>
              </div>
            )}

            {selectedLog.user_input && (
              <div style={{ marginBottom: 16 }}>
                <Text strong>用户输入:</Text>
                <div
                  style={{
                    background: '#e6f7ff',
                    padding: 12,
                    borderRadius: 4,
                    marginTop: 8,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {selectedLog.user_input}
                </div>
              </div>
            )}

            {selectedLog.ai_response && (
              <div style={{ marginBottom: 16 }}>
                <Text strong>AI响应:</Text>
                <div
                  style={{
                    background: '#f6ffed',
                    padding: 12,
                    borderRadius: 4,
                    marginTop: 8,
                    whiteSpace: 'pre-wrap',
                    border: '1px solid #b7eb8f',
                  }}
                >
                  {selectedLog.ai_response}
                </div>
              </div>
            )}

            {selectedLog.error_message && (
              <div>
                <Text strong>错误信息:</Text>
                <div
                  style={{
                    background: '#fff2f0',
                    padding: 12,
                    borderRadius: 4,
                    marginTop: 8,
                    border: '1px solid #ffccc7',
                    color: '#ff4d4f',
                  }}
                >
                  {selectedLog.error_message}
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}