'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Input, Result, Select, Table, Tag } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { getLoginLogs } from '@/actions/identity'
import { SettingsListCard } from './SettingsListCard'

const LOGIN_TYPE_LABEL: Record<string, string> = {
  feishu_sso: '飞书登录',
  local: '账号密码',
}

/**
 * 登录记录（用户登录历史）。
 *
 * 数据源：`identity.login_logs`（接口 `GET /api/v1/identity/login-logs`，权限 `platform:audit:read`）。
 * 页面级守卫在 `app/(dashboard)/settings/login-logs/page.tsx`（RSC）。
 */
export default function LoginLogsClient() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [status, setStatus] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['login-logs', { page, pageSize, status, keyword }],
    queryFn: async () => {
      const result = await getLoginLogs({ page, page_size: pageSize, status, keyword: keyword || undefined })
      return result
    },
  })

  // 接口不可用 / 无权限时给出明确提示，而不是静默显示空表
  // （空表会让人误以为「登录没有被记录」）
  if (error) {
    return (
      <Result
        status="403"
        title="登录记录加载失败"
        subTitle={
          error instanceof Error && error.message
            ? error.message
            : '请确认账号拥有「操作记录查看」权限，或稍后重试。'
        }
      />
    )
  }

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
      render: (type: string) => LOGIN_TYPE_LABEL[type] || type,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'success' ? 'success' : 'error'}>
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
    <SettingsListCard
      toolbar={
        <>
          <div className="w-full sm:w-[140px]">
            <Select
              placeholder="登录状态"
              allowClear
              style={{ width: '100%' }}
              value={status}
              onChange={(v) => { setStatus(v); setPage(1) }}
              options={[
                { value: 'success', label: '成功' },
                { value: 'failed', label: '失败' },
              ]}
            />
          </div>
          <div className="w-full sm:w-[200px]">
            <Input
              placeholder="搜索账号"
              prefix={<SearchOutlined />}
              style={{ width: '100%' }}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              onPressEnter={() => { setPage(1) }}
              allowClear
            />
          </div>
          <Button icon={<ReloadOutlined />} onClick={() => refetch()} className="shrink-0">
            刷新
          </Button>
        </>
      }
    >
      <Table
        rowKey="id"
        columns={columns}
        dataSource={data?.items || []}
        loading={isLoading}
        scroll={{ x: 'max-content' }}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
    </SettingsListCard>
  )
}
