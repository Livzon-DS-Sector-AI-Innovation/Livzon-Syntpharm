'use client'

import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Empty, Popconfirm, Skeleton, Space, Table, Tag, Tooltip, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import PersonSelect from '@/components/common/PersonSelect'
import { disableAllUserAccess, fetchUserAccess } from '@/actions/permission'
import { ROLE_TYPE_META } from './roleMeta'
import type { UserAccessItem } from '@/types/permission'

const { Text } = Typography

/**
 * 按人查权限：列出某员工在**所有模块**的授权，并支持一键停用。
 *
 * 用途是离职 / 调岗收权兜底：权限被下放到各模块管理员后，
 * 没有这个视图就没人能确认"人走了权限收干净没有"。
 *
 * 取数走 React Query（按 userId 做 queryKey）：重复选中同一员工直接命中缓存，
 * 一键停用后 invalidate 即可刷新，不再手写 loading + setState。
 */
export default function UserAccessPanel() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [userId, setUserId] = useState<string | undefined>()
  const [disabling, setDisabling] = useState(false)

  const { data: raw, isFetching } = useQuery({
    queryKey: ['user-access', userId],
    queryFn: () => fetchUserAccess(userId as string),
    enabled: Boolean(userId),
  })
  const data = raw ?? null
  const items = data?.items ?? []
  const notFound = Boolean(userId) && !isFetching && data === null

  const disableAll = async () => {
    if (!data) return
    setDisabling(true)
    try {
      const result = await disableAllUserAccess(data.user_id)
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success(`已停用 ${result.data} 条授权`)
      await queryClient.invalidateQueries({ queryKey: ['user-access', data.user_id] })
    } finally {
      setDisabling(false)
    }
  }

  const columns: ColumnsType<UserAccessItem> = [
    {
      title: '模块',
      dataIndex: 'module_code',
      render: (code: string | null) => code ?? <Text type="secondary">平台</Text>,
    },
    {
      title: '角色',
      dataIndex: 'role_name',
      ellipsis: { showTitle: false },
      render: (name: string | null | undefined) =>
        name ? (
          <Tooltip title={name}>
            <span className="block max-w-[280px] truncate">{name}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '类型',
      dataIndex: 'role_type',
      render: (type: string) => {
        const meta = ROLE_TYPE_META[type]
        return meta ? <Tag color={meta.color}>{meta.text}</Tag> : <Tag>{type}</Tag>
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (status: string) => (status === 'active' ? <Tag color="green">生效中</Tag> : <Tag>已停用</Tag>),
    },
  ]

  return (
    <div className="space-y-4">
      <Card size="small">
        <Space direction="vertical" size={8} className="w-full">
          <Text type="secondary">
            选择员工后可查看其在全部模块的授权；离职、调岗时用「一键停用」收口（系统管理员授权需单独移除）。
          </Text>
          <Space.Compact className="w-full max-w-[520px]">
            <PersonSelect placeholder="搜索姓名查询权限" value={userId} onChange={(person) => setUserId(person?.id)} />
            <Button loading={isFetching} disabled={!userId} onClick={() => void queryClient.invalidateQueries({ queryKey: ['user-access', userId] })}>
              刷新
            </Button>
          </Space.Compact>
          {notFound && <Alert type="warning" showIcon message="未找到该员工的账号" />}
        </Space>
      </Card>

      {isFetching && !data ? (
        <Card size="small">
          <Skeleton active paragraph={{ rows: 5 }} />
        </Card>
      ) : data ? (
        <Card
          size="small"
          title={`${data.name || data.username || data.user_id} 的模块权限（${items.length} 项）`}
          extra={
            <Popconfirm
              title="停用该员工的全部模块授权？"
              description="系统管理员授权不会被停用，需要单独在授权管理中移除。"
              okText="停用"
              cancelText="取消"
              disabled={items.length === 0 || data.is_superuser}
              onConfirm={disableAll}
            >
              <Button danger loading={disabling} disabled={items.length === 0 || data.is_superuser}>
                一键停用
              </Button>
            </Popconfirm>
          }
        >
          <Table
            rowKey="grant_id"
            size="small"
            columns={columns}
            dataSource={items}
            pagination={false}
            scroll={{ x: 'max-content' }}
            locale={{
              emptyText: (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="该员工没有任何模块授权，权限是干净的"
                />
              ),
            }}
          />
        </Card>
      ) : (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="先在上方搜索并选择员工，再查看其在全部模块的授权"
        />
      )}
    </div>
  )
}
