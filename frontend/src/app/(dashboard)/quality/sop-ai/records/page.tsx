'use client'

import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Card,
  Table,
  Button,
  Space,
  Tag,
  Input,
  Select,
  DatePicker,
  Typography,
  Modal,
  Descriptions,
  List,
  Divider,
  message,
  Tooltip,
  Empty,
} from 'antd'
import {
  EyeOutlined,
  ExportOutlined,
  ReloadOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons'
import { getCheckRecords, getCheckRecordDetail, exportCheckReport } from '@/actions/sop-ai'
import {
  CheckMain,
  CheckMainDetail,
  CheckProblem,
  CheckRecordFilter,
  CheckStatus,
} from '@/types/sop-ai'
import dayjs from 'dayjs'

const { Title, Text, Paragraph } = Typography
const { RangePicker } = DatePicker

type SopAiRecordsPageProps = Record<string, never>

/**
 * 记录台账页面
 */
export default function SopAiRecordsPage(_props: SopAiRecordsPageProps) {
  const [filter, setFilter] = useState<CheckRecordFilter>({
    page: 1,
    page_size: 20,
  })
  const [detailVisible, setDetailVisible] = useState(false)
  const [currentDetail, setCurrentDetail] = useState<CheckMainDetail | null>(null)

  // 加载记录
  const { data: queryResult, isLoading: loading, refetch } = useQuery({
    queryKey: ['sop-ai-records', filter],
    queryFn: async () => {
      const response = await getCheckRecords(filter)
      return response
    },
  })

  const records = queryResult?.items || []
  const total = queryResult?.total || 0

  // 查看详情
  const handleViewDetail = async (id: string) => {
    try {
      const detail = await getCheckRecordDetail(id)
      setCurrentDetail(detail)
      setDetailVisible(true)
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '加载详情失败')
    }
  }

  // 导出报告
  const handleExport = async (id: string) => {
    try {
      const result = await exportCheckReport(id, 'excel', true)
      message.success(`导出成功: ${result.download_url}`)
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '导出失败')
    }
  }

  // 筛选变化
  const handleFilterChange = (key: keyof CheckRecordFilter, value: unknown) => {
    setFilter({ ...filter, [key]: value, page: 1 })
  }

  // 获取风险标签颜色
  const _getRiskTagColor = (level?: number) => {
    if (level && level > 0) return 'red'
    return 'default'
  }

  // 表格列定义
  const columns = [
    {
      title: '文件名',
      dataIndex: 'file_name',
      key: 'file_name',
      render: (text: string, record: CheckMain) => (
        <Space>
          <FileTextOutlined />
          <Text>{text || record.file_code}</Text>
        </Space>
      ),
    },
    {
      title: '文件类型',
      dataIndex: 'file_type',
      key: 'file_type',
      render: (type: string) => (
        <Tag>{type?.toUpperCase() || '-'}</Tag>
      ),
    },
    {
      title: '校验类型',
      dataIndex: 'check_type',
      key: 'check_type',
      render: (type: string) => (
        <Tag color={type === 'single' ? 'blue' : 'purple'}>
          {type === 'single' ? '单文件预审' : type === 'batch' ? '批量巡检' : '定时任务'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: CheckStatus) => {
        const colorMap: Record<string, string> = {
          pending: 'default',
          running: 'processing',
          completed: 'success',
          failed: 'error',
          cancelled: 'default',
        }
        const textMap: Record<string, string> = {
          pending: '待处理',
          running: '处理中',
          completed: '已完成',
          failed: '失败',
          cancelled: '已取消',
        }
        return <Tag color={colorMap[status]}>{textMap[status]}</Tag>
      },
    },
    {
      title: '问题统计',
      key: 'problems',
      render: (_: unknown, record: CheckMain) => (
        <Space>
          {record.risk_high > 0 && (
            <Tooltip title="高风险">
              <Tag color="red">
                <WarningOutlined /> {record.risk_high}
              </Tag>
            </Tooltip>
          )}
          {record.risk_medium > 0 && (
            <Tooltip title="中风险">
              <Tag color="orange">
                <WarningOutlined /> {record.risk_medium}
              </Tag>
            </Tooltip>
          )}
          {record.risk_low > 0 && (
            <Tooltip title="低风险">
              <Tag color="green">
                <CheckCircleOutlined /> {record.risk_low}
              </Tag>
            </Tooltip>
          )}
          {record.total_problems === 0 && (
            <Tag>无问题</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '操作人',
      dataIndex: 'operator',
      key: 'operator',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: CheckMain) => (
        <Space>
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDetail(record.id)}
            />
          </Tooltip>
          <Tooltip title="导出报告">
            <Button
              type="text"
              icon={<ExportOutlined />}
              onClick={() => handleExport(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ]

  return (
    <div className="sop-ai-records-page">
      <Card>
        <Title level={4}>校验记录台账</Title>
        <Paragraph type="secondary">
          查看历史校验记录和问题详情
        </Paragraph>

        <Divider />

        {/* 筛选条件 */}
        <Space wrap style={{ marginBottom: 16 }}>
          <Input.Search
            placeholder="文件编号/文件名"
            allowClear
            onSearch={(value) => handleFilterChange('file_code', value)}
            style={{ width: 200 }}
          />
          <Select
            placeholder="状态"
            allowClear
            onChange={(value) => handleFilterChange('status', value)}
            style={{ width: 120 }}
            options={[
              { label: '待处理', value: 'pending' },
              { label: '处理中', value: 'running' },
              { label: '已完成', value: 'completed' },
              { label: '失败', value: 'failed' },
            ]}
          />
          <RangePicker
            onChange={(dates) => {
              handleFilterChange('start_date', dates?.[0]?.toISOString())
              handleFilterChange('end_date', dates?.[1]?.toISOString())
            }}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
          >
            刷新
          </Button>
        </Space>

        {/* 表格 */}
        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          pagination={{
            current: filter.page,
            pageSize: filter.page_size,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (page, pageSize) => {
              setFilter({ ...filter, page, page_size: pageSize })
            },
          }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title="校验详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={null}
        width={800}
      >
        {currentDetail && (
          <>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="文件名称">
                {currentDetail.file_name}
              </Descriptions.Item>
              <Descriptions.Item label="文件编号">
                {currentDetail.file_code}
              </Descriptions.Item>
              <Descriptions.Item label="文件类型">
                {currentDetail.file_type}
              </Descriptions.Item>
              <Descriptions.Item label="校验类型">
                {currentDetail.check_type}
              </Descriptions.Item>
              <Descriptions.Item label="状态">
                {currentDetail.status}
              </Descriptions.Item>
              <Descriptions.Item label="操作人">
                {currentDetail.operator}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {dayjs(currentDetail.created_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
              <Descriptions.Item label="更新时间">
                {dayjs(currentDetail.updated_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            </Descriptions>

            <Divider />

            <Title level={5}>问题明细</Title>
            {currentDetail.problems.length > 0 ? (
              <List
                bordered
                dataSource={currentDetail.problems}
                renderItem={(item: CheckProblem) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        item.risk_level === 'high' ? (
                          <CloseCircleOutlined style={{ fontSize: 24, color: '#ff4d4f' }} />
                        ) : item.risk_level === 'medium' ? (
                          <WarningOutlined style={{ fontSize: 24, color: '#fa8c16' }} />
                        ) : (
                          <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
                        )
                      }
                      title={
                        <Space>
                          <Text strong>{item.problem_type}</Text>
                          <Tag color={item.risk_level === 'high' ? 'red' : item.risk_level === 'medium' ? 'orange' : 'green'}>
                            {item.risk_level}
                          </Tag>
                        </Space>
                      }
                      description={
                        <div>
                          <div>位置: {item.location}</div>
                          <div>描述: {item.description}</div>
                          {item.suggestion && (
                            <div>建议: {item.suggestion}</div>
                          )}
                          {item.source_file && (
                            <div>源文件: {item.source_file}</div>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            ) : (
              <Empty description="没有问题" />
            )}
          </>
        )}
      </Modal>
    </div>
  )
}