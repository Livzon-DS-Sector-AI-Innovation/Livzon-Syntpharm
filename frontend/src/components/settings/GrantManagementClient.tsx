'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  App,
  Button,
  Checkbox,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  createGrant,
  deleteGrant,
  fetchGrants,
  fetchRoles,
  fetchUserOptions,
  updateGrant,
} from '@/actions/permission'
import type { GrantCreateInput, GrantItem, ScopeType } from '@/types/permission'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'

const { Text } = Typography

const scopeOptions: Array<{ value: ScopeType; label: string }> = [
  { value: 'all', label: '全部数据都能看' },
  { value: 'self', label: '只能看自己录入或负责的' },
  { value: 'department', label: '只能看指定部门的' },
  { value: 'department_and_children', label: '只能看指定部门及其下级的（当前等同上一项）' },
]

export default function GrantManagementClient() {
  const { message } = App.useApp()

  // 权限：无「授权管理」权限时隐藏全部写操作入口
  // （前端隐藏只是体验优化，后端 require_permission 仍会拦截绕过前端的调用）
  // 注意：必须放在任何 early return 之前
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.grantManage)
  const queryClient = useQueryClient()
  const router = useRouter()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<GrantItem | null>(null)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()
  // 默认不限制可见数据（固定 all），需要限制时才展开范围选择
  const [limitScope, setLimitScope] = useState(false)
  const [keyword, setKeyword] = useState('')
  const scopeType = Form.useWatch('scope_type', form)

  const { data: grants = [], isLoading } = useQuery({
    queryKey: ['permission-grants'],
    queryFn: () => fetchGrants(),
  })

  const { data: roles = [] } = useQuery({
    queryKey: ['permission-roles'],
    queryFn: fetchRoles,
  })

  const { data: users = [] } = useQuery({
    queryKey: ['permission-user-options'],
    queryFn: fetchUserOptions,
  })

  const roleOptions = roles.map((r) => ({ value: r.id, label: `${r.name}（${r.code}）` }))
  const userOptions = users.map((u) => ({
    value: u.id,
    label: `${u.name}${u.username ? `（${u.username}）` : ''}`,
  }))

  // 列表搜索：用户（姓名/ID）/ 角色（名称/编码）（授权量小，前端过滤即可）
  const query = keyword.trim().toLowerCase()
  const visibleGrants = query
    ? grants.filter((grant) =>
        [grant.user_name, grant.user_id, grant.role_name, grant.role_code].some((value) =>
          (value ?? '').toLowerCase().includes(query),
        ),
      )
    : grants

  const handleCreate = () => {
    setEditing(null)
    form.resetFields()
    form.setFieldsValue({ scope_type: 'all', scope_dept_codes: [] })
    setLimitScope(false)
    setModalOpen(true)
  }

  const handleEdit = (record: GrantItem) => {
    setEditing(record)
    // 编辑 = 调整该用户当前生效的全部角色（预填已授角色，可增可减）
    const ownedRoleIds = grants
      .filter((g) => g.user_id === record.user_id && g.status === 'active')
      .map((g) => g.role_id)
    form.setFieldsValue({
      user_id: record.user_id,
      role_ids: ownedRoleIds,
      scope_type: record.scope_type,
      scope_dept_codes: record.scope_dept_codes ?? [],
      status: record.status,
    })
    setLimitScope(record.scope_type !== 'all')
    setModalOpen(true)
  }

  const handleSave = async () => {
    try {
      const values = (await form.validateFields()) as {
        user_id: string
        role_ids: string[]
        scope_type: ScopeType
        scope_dept_codes: string[]
        status?: string
      }
      setSaving(true)
      // 未勾选「限制可见数据」＝ 不限范围（固定 all）
      const scopeTypeValue: ScopeType = limitScope ? values.scope_type : 'all'
      const scopeCodes = limitScope ? values.scope_dept_codes : []
      if (editing) {
        // 编辑：把该用户的角色集合调整成勾选结果 —— 多出的移除、新勾的新增、保留的更新范围/状态
        const targetUserId = editing.user_id
        const userGrants = grants.filter((g) => g.user_id === targetUserId && g.status === 'active')
        const currentRoleIds = new Set(userGrants.map((g) => g.role_id))
        const picked = new Set(values.role_ids ?? [])

        const toAdd = [...picked].filter((id) => !currentRoleIds.has(id))
        const toRemove = userGrants.filter((g) => !picked.has(g.role_id))
        const toKeep = userGrants.filter((g) => picked.has(g.role_id))

        const roleNameOf = (id: string) => roles.find((r) => r.id === id)?.name ?? id
        const failures: string[] = []
        let added = 0
        let removed = 0
        let updated = 0

        for (const g of toRemove) {
          try {
            await deleteGrant(g.id)
            removed += 1
          } catch (error) {
            failures.push(`移除「${g.role_name || roleNameOf(g.role_id)}」：${error instanceof Error ? error.message : '失败'}`)
          }
        }

        for (const roleId of toAdd) {
          try {
            await createGrant({
              user_id: targetUserId,
              role_id: roleId,
              scope_type: scopeTypeValue,
              scope_dept_codes: scopeCodes,
            })
            added += 1
          } catch (error) {
            failures.push(`新增「${roleNameOf(roleId)}」：${error instanceof Error ? error.message : '失败'}`)
          }
        }

        for (const g of toKeep) {
          const scopeChanged =
            g.scope_type !== scopeTypeValue ||
            JSON.stringify(g.scope_dept_codes ?? []) !== JSON.stringify(scopeCodes)
          const statusChanged = values.status !== undefined && g.status !== values.status
          if (!scopeChanged && !statusChanged) continue
          try {
            await updateGrant(g.id, {
              scope_type: scopeTypeValue,
              scope_dept_codes: scopeCodes,
              status: values.status,
            })
            updated += 1
          } catch (error) {
            failures.push(`更新「${g.role_name || roleNameOf(g.role_id)}」：${error instanceof Error ? error.message : '失败'}`)
          }
        }

        if (added + removed + updated === 0 && failures.length > 0) {
          message.error(`保存失败：${failures.join('；')}`)
          return
        }
        const summary = `新增 ${added}，移除 ${removed}，更新 ${updated}`
        if (failures.length > 0) {
          message.warning(`已保存（${summary}）；失败 ${failures.length} 项：${failures.join('；')}`)
        } else {
          message.success(`已保存（${summary}）`)
        }
      } else {
        // 一次可授多个角色：逐个创建；该用户已拥有的角色自动跳过
        const picked = values.role_ids ?? []
        const ownedRoleIds = new Set(
          grants.filter((g) => g.user_id === values.user_id && g.status === 'active').map((g) => g.role_id),
        )
        const roleIds = picked.filter((id) => !ownedRoleIds.has(id))
        const skipped = picked.length - roleIds.length

        let created = 0
        const failures: string[] = []
        for (const roleId of roleIds) {
          const payload: GrantCreateInput = {
            user_id: values.user_id,
            role_id: roleId,
            scope_type: scopeTypeValue,
            scope_dept_codes: scopeCodes,
          }
          try {
            await createGrant(payload)
            created += 1
          } catch (error) {
            const roleName = roles.find((r) => r.id === roleId)?.name ?? roleId
            failures.push(`${roleName}：${error instanceof Error ? error.message : '创建失败'}`)
          }
        }

        if (created === 0 && failures.length > 0) {
          // 全部失败：保留弹窗方便调整
          message.error(`授权创建失败：${failures.join('；')}`)
          return
        }
        if (failures.length > 0) {
          message.warning(`已创建 ${created} 个授权；失败 ${failures.length} 个：${failures.join('；')}`)
        } else if (skipped > 0) {
          message.success(`已创建 ${created} 个授权（${skipped} 个角色该用户已拥有，已跳过）`)
        } else {
          message.success(`已创建 ${created} 个授权`)
        }
      }
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['permission-grants'] })
      // 授权变更会同时影响两处，这里一并刷新，避免用户还要手动刷页面：
      // ① 用户管理页的「角色」列（同一个 QueryClient，跨页失效）；
      // ② 该用户的可见菜单（dashboard layout 是 RSC，必须 refresh 才会重新下发权限视图）。
      queryClient.invalidateQueries({ queryKey: ['users'] })
      router.refresh()
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (record: GrantItem) => {
    try {
      await deleteGrant(record.id)
      message.success('授权已删除')
      queryClient.invalidateQueries({ queryKey: ['permission-grants'] })
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    }
  }

  const columns = [
    {
      title: '用户',
      key: 'user',
      width: 180,
      render: (_: unknown, r: GrantItem) => r.user_name || r.user_id,
    },
    {
      title: '角色',
      key: 'role',
      width: 200,
      render: (_: unknown, r: GrantItem) => (
        <div>
          <div className="font-medium text-[var(--color-charcoal)]">{r.role_name || '-'}</div>
          <Text className="text-[12px] text-[var(--color-steel)]">{r.role_code || '-'}</Text>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => <Tag color={v === 'active' ? 'success' : 'default'}>{v === 'active' ? '启用' : '禁用'}</Tag>,
    },
    // 操作列：无管理权限时整列不出现
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'actions',
            width: 160,
            fixed: 'right' as const,
            render: (_: unknown, r: GrantItem) => (
              <Space>
                <Button size="small" onClick={() => handleEdit(r)}>
                  编辑
                </Button>
                <Popconfirm title="确认删除该授权？" onConfirm={() => handleDelete(r)}>
                  <Button size="small" danger>
                    删除
                  </Button>
                </Popconfirm>
              </Space>
            ),
          },
        ]
      : []),
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="m-0 text-[20px] font-semibold text-[var(--color-charcoal)]">授权管理</h2>
          <Text className="text-[13px] text-[var(--color-steel)]">
            给用户发角色，他就拥有该角色的全部权限；一次可选择多个角色。默认不限制可见数据；需要限制时勾选「限制可见数据」。
          </Text>
        </div>
        <Space>
          <Input.Search
            allowClear
            placeholder="搜索用户或角色"
            style={{ width: 240 }}
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['permission-grants'] })}
          >
            刷新
          </Button>
          {canManage && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建授权
            </Button>
          )}
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={visibleGrants}
        rowKey="id"
        loading={isLoading}
        scroll={{ x: 1000 }}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editing ? '编辑该用户的角色授权' : '新建授权'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {editing ? (
            <>
              <Form.Item label="用户">
                <Input value={editing.user_name || editing.user_id} disabled />
              </Form.Item>
              <Text className="text-[12px] text-[var(--color-steel)]">
                这里调整的是该用户的全部角色授权：勾选＝新增角色，取消勾选＝移除角色。
              </Text>
            </>
          ) : (
            <Form.Item
              name="user_id"
              label="用户"
              rules={[{ required: true, message: '请选择用户' }]}
              style={{ width: 260 }}
            >
              <Select showSearch optionFilterProp="label" options={userOptions} placeholder="选择用户" />
            </Form.Item>
          )}
          <Form.Item
            name="role_ids"
            label="角色（可多选）"
            rules={[{ required: true, message: '请选择角色' }]}
          >
            {/* 不设 maxTagCount：已选角色全部显示（标签自动换行），不折叠成 +N */}
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              options={roleOptions}
              placeholder="可一次选择多个角色"
            />
          </Form.Item>
          <Form.Item
            label="可见数据"
            extra="默认不限制（能看全部数据）。该限制会在各业务模块接入数据权限后生效。"
          >
            <Space direction="vertical" size={8} style={{ width: '100%' }}>
              <Checkbox
                checked={limitScope}
                onChange={(event) => setLimitScope(event.target.checked)}
              >
                限制可见数据
              </Checkbox>
              {limitScope && (
                <Form.Item
                  name="scope_type"
                  noStyle
                  rules={[{ required: true, message: '请选择可见数据范围' }]}
                >
                  <Select options={scopeOptions} style={{ width: 360 }} />
                </Form.Item>
              )}
            </Space>
          </Form.Item>
          {limitScope && (scopeType === 'department' || scopeType === 'department_and_children') && (
            <Form.Item name="scope_dept_codes" label="范围部门编码">
              <Select mode="tags" placeholder="输入部门编码后回车，可多个" />
            </Form.Item>
          )}
          {editing && (
            <Form.Item name="status" label="状态">
              <Select
                options={[
                  { value: 'active', label: '启用' },
                  { value: 'disabled', label: '禁用' },
                ]}
              />
            </Form.Item>
          )}
        </Form>
      </Modal>
    </div>
  )
}
