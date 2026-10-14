'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Input, Result, Select, Space, Table, Tag, Typography } from 'antd'
import { ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import { getAuditLogs } from '@/actions/audit'
import type { AuditLogItem } from '@/types/audit'

const { Text } = Typography

const ACTION_LABEL: Record<string, string> = {
  'user.create': '新建用户',
  'user.update': '修改用户',
  'user.reset_password': '重置密码',
  'user.unbind_feishu': '解绑飞书',
  'user.change_password': '修改密码',
  'role.create': '新建角色',
  'role.update': '修改角色',
  'role.delete': '删除角色',
  'grant.create': '新增授权',
  'grant.update': '修改授权',
  'grant.delete': '删除授权',
  'menu.config.save': '保存菜单配置',
}

const RESOURCE_LABEL: Record<string, string> = {
  user: '用户',
  role: '角色',
  grant: '授权',
  menu: '菜单',
}

function formatValue(value: Record<string, unknown> | null | undefined): string {
  if (!value) return '-'
  try {
    return JSON.stringify(value, null, 2)
  } catch {
    return String(value)
  }
}

/**
 * 操作审计（谁、何时、对什么资源做了什么、改前/改后值）。
 *
 * 数据源：`audit.logs`（接口 `GET /api/v1/audit/logs`，权限 `platform:audit:read`）。
 * 页面级守卫在 `app/(dashboard)/settings/audit/page.tsx`（RSC）。
 */
export default function AuditLogsClient() {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [action, setAction] = useState<string | undefined>()
  const [resourceType, setResourceType] = useState<string | undefined>()
  const [keyword, setKeyword] = useState('')

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['audit-logs', { page, pageSize, action, resourceType, keyword }],
    queryFn: async () => {
      const result = await getAuditLogs({
        page,
        page_size: pageSize,
        action,
        resource_type: resourceType,
        keyword: keyword || undefined,
      })
      return result
    },
  })

  if (error) {
    return (
      <Result
        status="403"
        title="操作审计加载失败"
        subTitle={
          error instanceof Error && error.message
            ? error.message
            : '请确认账号拥有「审计日志查看」权限，或稍后重试。'
        }
      />
    )
  }

  const columns = [
    {
      title: '操作者',
      dataIndex: 'user_name',
      key: 'user_name',
      width: 140,
      render: (text: string | null, record: AuditLogItem) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text || '-'}</Text>
          {record.username && <Text type="secondary" className="text-[12px]">{record.username}</Text>}
        </Space>
      ),
    },
    {
      title: '动作',
      dataIndex: 'action',
      key: 'action',
      width: 130,
      render: (action: string) => ACTION_LABEL[action] || action,
    },
    {
      title: '对象',
      key: 'resource',
      width: 110,
      render: (_: unknown, record: AuditLogItem) => (
        <Tag>{record.resource_type ? RESOURCE_LABEL[record.resource_type] || record.resource_type : '-'}</Tag>
      ),
    },
    {
      title: '变更内容',
      key: 'summary',
      ellipsis: true,
      render: (_: unknown, record: AuditLogItem) => {
        if (record.action === 'user.reset_password' || record.action === 'user.change_password') {
          return <Text type="secondary">口令已更新（内容不展示）</Text>
        }
        return <Text type="secondary">点击行展开查看改前 / 改后详情</Text>
      },
    },
    {
      title: '操作时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => new Date(text).toLocaleString(),
    },
  ]

  return (
    <div className="space-y-4">
      <Space wrap>
        <Select
          placeholder="动作类型"
          allowClear
          style={{ width: 160 }}
          value={action}
          onChange={(v) => { setAction(v); setPage(1) }}
          options={Object.entries(ACTION_LABEL).map(([value, label]) => ({ value, label }))}
        />
        <Select
          placeholder="对象类型"
          allowClear
          style={{ width: 140 }}
          value={resourceType}
          onChange={(v) => { setResourceType(v); setPage(1) }}
          options={Object.entries(RESOURCE_LABEL).map(([value, label]) => ({ value, label }))}
        />
        <Input
          placeholder="搜索操作者姓名 / 用户名"
          prefix={<SearchOutlined />}
          style={{ width: 220 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onPressEnter={() => setPage(1)}
          allowClear
        />
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          刷新
        </Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={data?.items || []}
        loading={isLoading}
        expandable={{
          expandedRowRender: (record: AuditLogItem) => (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Text type="secondary" className="text-[12px]">改前（old_value）</Text>
                <pre className="m-0 mt-1 whitespace-pre-wrap rounded bg-[var(--color-mist)] p-3 text-[12px]">
                  {formatValue(record.old_value)}
                </pre>
              </div>
              <div>
                <Text type="secondary" className="text-[12px]">改后（new_value）</Text>
                <pre className="m-0 mt-1 whitespace-pre-wrap rounded bg-[var(--color-mist)] p-3 text-[12px]">
                  {formatValue(record.new_value)}
                </pre>
              </div>
            </div>
          ),
        }}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
        size="middle"
      />
    </div>
  )
}
