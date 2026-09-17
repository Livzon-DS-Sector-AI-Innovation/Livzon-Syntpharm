'use client'

import { useEffect, useState, useCallback } from 'react'
import { Table, Tag, Input, Select, Space, Button } from 'antd'
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons'
import { getLoginLogs } from '@/actions/identity'
import type { LoginLog } from '@/types/identity'

export default function LoginLogsPage() {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<LoginLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [status, setStatus] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getLoginLogs({ page, page_size: pageSize, status, keyword: keyword || undefined })
      setData(result.items)
      setTotal(result.total)
    } catch (error) {
      console.error('获取登录记录失败:', error)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, status, keyword])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const columns = [
    {
      title: '用户',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 120,
      render: (text: string | null) => text || '-',
    },
    {
      title: '登录方式',
      dataIndex: 'login_type',
      key: 'login_type',
      width: 120,
      render: (type: string) => {
        const map: Record<string, string> = { feishu_sso: '飞书登录' }
        return map[type] || type
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'success' ? 'green' : 'red'}>
          {status === 'success' ? '成功' : '失败'}
        </Tag>
      ),
    },
    {
      title: 'IP 地址',
      dataIndex: 'ip_address',
      key: 'ip_address',
      width: 140,
      render: (text: string | null) => text || '-',
    },
    {
      title: '失败原因',
      dataIndex: 'error_message',
      key: 'error_message',
      ellipsis: true,
      render: (text: string | null) => text || '-',
    },
    {
      title: '浏览器',
      dataIndex: 'user_agent',
      key: 'user_agent',
      width: 200,
      ellipsis: true,
      render: (text: string | null) => {
        if (!text) return '-'
        if (text.includes('Chrome')) return 'Chrome'
        if (text.includes('Firefox')) return 'Firefox'
        if (text.includes('Safari')) return 'Safari'
        if (text.includes('Edge')) return 'Edge'
        return text.substring(0, 30)
      },
    },
    {
      title: '登录时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
  ]

  return (
    <div style={{ padding: '28px 32px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>
        登录记录
      </h1>
      <p style={{ fontSize: 13, color: '#a4a097', margin: '4px 0 0' }}>
        查看系统登录历史，包括成功和失败的登录尝试
      </p>

      <div style={{ height: 1, marginTop: 18, marginBottom: 20, background: 'linear-gradient(to right, #5645d4 0%, #e6e0f5 40%, transparent 100%)' }} />

      <Space style={{ marginBottom: 16 }} wrap>
        <Select
          placeholder="登录状态"
          allowClear
          style={{ width: 140 }}
          value={status}
          onChange={(v) => { setStatus(v); setPage(1) }}
          options={[
            { value: 'success', label: '成功' },
            { value: 'failed', label: '失败' },
          ]}
        />
        <Input
          placeholder="搜索用户名"
          prefix={<SearchOutlined />}
          style={{ width: 200 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => { setPage(1); fetchData() }}
          allowClear
        />
        <Button icon={<ReloadOutlined />} onClick={fetchData}>
          刷新
        </Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data}
        loading={loading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
        size="middle"
      />
    </div>
  )
}
