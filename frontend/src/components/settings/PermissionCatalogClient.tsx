'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Input, Table, Tabs, Tag, Typography } from 'antd'
import { fetchApiBindings, fetchPermissions } from '@/actions/permission'

const { Text } = Typography

function PermissionTable() {
  const [keyword, setKeyword] = useState('')
  const { data: permissions = [], isLoading } = useQuery({
    queryKey: ['permission-catalog'],
    queryFn: fetchPermissions,
  })

  const columns = [
    { title: '权限码', dataIndex: 'code', width: 260 },
    { title: '名称', dataIndex: 'name', width: 160 },
    { title: '模块', dataIndex: 'module', width: 120 },
    { title: '资源', dataIndex: 'resource', width: 140 },
    { title: '动作', dataIndex: 'action', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (v: string) => (
        <Tag color={v === 'active' ? 'success' : 'default'}>{v === 'active' ? '启用' : '已退役'}</Tag>
      ),
    },
    { title: '说明', dataIndex: 'description', render: (v: string | null) => v || '-' },
  ]

  // 列表搜索：权限码 / 名称 / 模块 / 资源 / 动作 / 说明
  const query = keyword.trim().toLowerCase()
  const visiblePermissions = query
    ? permissions.filter((item) =>
        [item.code, item.name, item.module, item.resource, item.action, item.description].some(
          (value) => (value ?? '').toLowerCase().includes(query),
        ),
      )
    : permissions

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <Input.Search
          allowClear
          placeholder="搜索权限码、名称、模块、资源"
          style={{ width: 320 }}
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Text className="text-[12px] text-[var(--color-steel)]">
          共 {permissions.length} 条，筛选后 {visiblePermissions.length} 条
        </Text>
      </div>
      <Table
        columns={columns}
        dataSource={visiblePermissions}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1000 }}
        pagination={{ pageSize: 15 }}
      />
    </div>
  )
}

function ApiBindingTable() {
  const [keyword, setKeyword] = useState('')
  const { data: bindings = [], isLoading } = useQuery({
    queryKey: ['permission-api-bindings'],
    queryFn: fetchApiBindings,
  })

  const columns = [
    { title: '方法', dataIndex: 'method', width: 90, render: (v: string) => <Tag color="geekblue">{v}</Tag> },
    { title: '路由模板', dataIndex: 'route_template', width: 360 },
    { title: '权限码', dataIndex: 'permission_code', width: 240 },
    {
      title: '需数据范围',
      dataIndex: 'scope_required',
      width: 110,
      render: (v: boolean) => (v ? <Tag color="orange">是</Tag> : '-'),
    },
  ]

  // 列表搜索：方法 / 路由模板 / 权限码
  const query = keyword.trim().toLowerCase()
  const visibleBindings = query
    ? bindings.filter((item) =>
        [item.method, item.route_template, item.permission_code].some((value) =>
          (value ?? '').toLowerCase().includes(query),
        ),
      )
    : bindings

  return (
    <div className="space-y-3">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <Input.Search
          allowClear
          placeholder="搜索路由模板、权限码"
          style={{ width: 320 }}
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
        />
        <Text className="text-[12px] text-[var(--color-steel)]">
          共 {bindings.length} 条，筛选后 {visibleBindings.length} 条
        </Text>
      </div>
      <Table
        columns={columns}
        dataSource={visibleBindings}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 900 }}
        pagination={{ pageSize: 15 }}
      />
    </div>
  )
}

export default function PermissionCatalogClient() {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="m-0 text-[20px] font-semibold text-[var(--color-charcoal)]">权限目录</h2>
        <Text className="text-[13px] text-[var(--color-steel)]">
          代码注册表为唯一权威，本页只读展示。权限码一经发布不可删除、只能退役。
        </Text>
      </div>

      <Tabs
        defaultActiveKey="permissions"
        items={[
          { key: 'permissions', label: '权限码', children: <PermissionTable /> },
          { key: 'bindings', label: '接口绑定登记簿', children: <ApiBindingTable /> },
        ]}
      />
    </div>
  )
}
