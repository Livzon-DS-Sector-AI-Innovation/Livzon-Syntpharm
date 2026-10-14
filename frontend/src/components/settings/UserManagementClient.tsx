'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  App,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Result,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { PlusOutlined, ReloadOutlined, UserSwitchOutlined } from '@ant-design/icons'
import {
  createUser,
  getUsers,
  resetUserPassword,
  unbindFeishuUser,
  updateUser,
} from '@/actions/users'
import type {
  LocalUserCreate,
  UserManagementItem,
  UserManagementUpdate,
} from '@/types/users'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'

const { Text } = Typography

const statusOptions = [
  { value: 'active', label: '启用' },
  { value: 'disabled', label: '禁用' },
]

// 登录来源：值由后端登录链路写入（本地建号 = local、飞书首次登录自动建号 = feishu），
// 属代码决定的技术字段，这里只做显示层中文映射，不做成可配字典。
const AUTH_SOURCE_LABEL: Record<string, string> = {
  local: '本地账号',
  feishu: '飞书',
}

type AuthSourceValue = 'local' | 'feishu'

// 选项从上面的映射派生，中文名只写一份
const authSourceOptions = (['local', 'feishu'] as const).map((value) => ({
  value,
  label: AUTH_SOURCE_LABEL[value],
}))

export default function UserManagementClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()

  // 权限：无「用户管理」权限时隐藏全部写操作入口
  // （前端隐藏只是体验优化，后端 require_permission 仍会拦截绕过前端的调用）
  // 注意：必须放在任何 early return 之前，否则违反 Hooks 调用顺序规则
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.userManage)

  const [modalOpen, setModalOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserManagementItem | null>(null)
  const [saving, setSaving] = useState(false)
  // 编辑弹窗内的「账号操作」：重置密码 / 解绑飞书
  const [newPassword, setNewPassword] = useState('')
  const [resetting, setResetting] = useState(false)
  const [unbinding, setUnbinding] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [authSource, setAuthSource] = useState<AuthSourceValue | undefined>()
  const [form] = Form.useForm()

  const { data: users = [], isLoading: loading, error, refetch: refetchUsers } = useQuery({
    queryKey: ['users', keyword, authSource],
    queryFn: async () => {
      const result = await getUsers({ keyword: keyword || undefined, auth_source: authSource })
      return result.items || []
    },
    // 每次进入页面都取最新（在「授权管理」改了角色后回到本页，不该看到旧角色）
    refetchOnMount: 'always',
    staleTime: 0,
  })

  if (error) {
    return (
      <Result
        status="403"
        title="无权限访问用户管理"
        subTitle={error instanceof Error ? error.message : '请联系管理员为你授权'}
      />
    )
  }

  const loadUsers = () => { refetchUsers() }

  const handleCreate = () => {
    setEditingUser(null)
    setNewPassword('')
    form.resetFields()
    form.setFieldsValue({ status: 'active' })
    setModalOpen(true)
  }

  const handleEdit = (record: UserManagementItem) => {
    setEditingUser(record)
    setNewPassword('')
    form.setFieldsValue({
      username: record.username,
      name: record.name,
      email: record.email,
      mobile: record.mobile,
      employee_no: record.employee_no,
      department: record.department,
      position: record.position,
      status: record.status,
    })
    setModalOpen(true)
  }

  const handleSave = async () => {
    const values = await form.validateFields().catch(() => null)
    if (!values) return // 表单校验失败：antd 已在字段上提示
    setSaving(true)
    try {
      if (editingUser) {
        const boundToFeishu = !!(editingUser.feishu_open_id || editingUser.feishu_user_id)
        const updateData: UserManagementUpdate = {
          username: values.username,
          status: values.status,
          // 已绑定飞书的账号：人员资料以飞书为准，不提交（后端同样会拒绝修改）
          ...(boundToFeishu
            ? {}
            : {
                name: values.name,
                email: values.email || null,
                mobile: values.mobile || null,
                employee_no: values.employee_no || null,
                department: values.department || null,
                position: values.position || null,
              }),
        }
        const result = await updateUser(editingUser.id, updateData)
        if (!result.ok) {
          message.error(result.message)
          return
        }
        message.success('用户已更新')
      } else {
        const result = await createUser(values as LocalUserCreate)
        if (!result.ok) {
          message.error(result.message)
          return
        }
        message.success('用户已创建')
      }
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    } finally {
      setSaving(false)
    }
  }

  const handleStatus = async (record: UserManagementItem) => {
    const nextStatus = record.status === 'active' ? 'disabled' : 'active'
    const result = await updateUser(record.id, { status: nextStatus })
    if (!result.ok) {
      message.error(result.message)
      return
    }
    message.success(nextStatus === 'active' ? '用户已启用' : '用户已禁用')
    queryClient.invalidateQueries({ queryKey: ['users'] })
  }

  const handleResetPassword = async () => {
    if (!editingUser) return
    if (newPassword.trim().length < 6) {
      message.warning('新密码至少 6 位')
      return
    }
    setResetting(true)
    try {
      const result = await resetUserPassword(editingUser.id, { password: newPassword })
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success('密码已重置')
      setNewPassword('')
    } finally {
      setResetting(false)
    }
  }

  const handleUnbind = async () => {
    if (!editingUser) return
    setUnbinding(true)
    try {
      const result = await unbindFeishuUser(editingUser.id)
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success('已解绑飞书账号')
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['users'] })
    } finally {
      setUnbinding(false)
    }
  }

  // 已绑定飞书的账号：人员资料由飞书同步，编辑时置灰
  const isFeishuUser = !!(editingUser?.feishu_open_id || editingUser?.feishu_user_id)
  // 角色只读展示：真实角色来自「授权管理」，不在此处编辑
  const editingRoles = editingUser?.roles ?? []

  const columns = [
    {
      title: '用户',
      key: 'user',
      width: 220,
      render: (_: unknown, record: UserManagementItem) => (
        <div>
          <div className="font-medium text-[var(--color-charcoal)]">
            {record.name}
          </div>
          <Text className="text-[12px] text-[var(--color-steel)]">
            {record.username || record.email || record.mobile || '-'}
          </Text>
        </div>
      ),
    },
    {
      title: '角色',
      key: 'roles',
      width: 200,
      render: (_: unknown, record: UserManagementItem) => {
        const roles = record.roles ?? []
        if (!roles.length) {
          return <Tag>未授权</Tag>
        }
        return (
          <Space size={4} wrap>
            {roles.map((name) => (
              <Tag color="purple" key={name}>
                {name}
              </Tag>
            ))}
          </Space>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'active' ? 'success' : 'error'}>
          {status === 'active' ? '启用' : '禁用'}
        </Tag>
      ),
    },
    { title: '部门', dataIndex: 'department', width: 160 },
    { title: '职位', dataIndex: 'position', width: 160 },
    {
      title: '登录来源',
      dataIndex: 'auth_source',
      width: 120,
      render: (value: string) => (
        <Tag color={value === 'feishu' ? 'geekblue' : 'default'}>
          {AUTH_SOURCE_LABEL[value] ?? (value || '-')}
        </Tag>
      ),
    },
    {
      title: '飞书绑定',
      key: 'feishu',
      width: 120,
      render: (_: unknown, record: UserManagementItem) =>
        record.feishu_open_id || record.feishu_user_id ? (
          <Tag color="green">已绑定</Tag>
        ) : (
          <Tag>未绑定</Tag>
        ),
    },
    // 操作列：只保留「编辑」与「是否启用」；重置密码 / 飞书解绑在编辑弹窗里
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'actions',
            width: 180,
            fixed: 'right' as const,
            render: (_: unknown, record: UserManagementItem) => (
              <Space>
                <Button size="small" onClick={() => handleEdit(record)}>
                  编辑
                </Button>
                <Popconfirm
                  title={
                    record.status === 'active'
                      ? '确认禁用该用户？禁用后无法登录。'
                      : '确认启用该用户？'
                  }
                  onConfirm={() => handleStatus(record)}
                  okText="确定"
                  cancelText="取消"
                >
                  <Switch
                    size="small"
                    checked={record.status === 'active'}
                    checkedChildren="启用"
                    unCheckedChildren="禁用"
                  />
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
          <h2 className="m-0 text-[20px] font-semibold text-[var(--color-charcoal)]">
            用户管理
          </h2>
          <Text className="text-[13px] text-[var(--color-steel)]">
            管理开发阶段本地账号，并为飞书 SSO 用户分配平台角色。
          </Text>
        </div>
        <Space>
          <Select
            allowClear
            placeholder="登录来源"
            style={{ width: 130 }}
            value={authSource}
            onChange={(value) => setAuthSource(value)}
            options={authSourceOptions}
          />
          <Input.Search
            allowClear
            placeholder="搜索姓名、账号、邮箱"
            onSearch={(value) => setKeyword(value)}
            style={{ width: 260 }}
          />
          <Button icon={<ReloadOutlined />} onClick={loadUsers}>
            刷新
          </Button>
          {canManage && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建用户
            </Button>
          )}
        </Space>
      </div>

      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1050 }}
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title={editingUser ? '编辑用户' : '新建本地用户'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width={640}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {isFeishuUser && (
            <Text type="warning" className="text-[13px]">
              该账号已绑定飞书：姓名 / 邮箱 / 手机号 / 工号 / 部门 / 职位由飞书自动同步，不能手工编辑；
              用户名与状态仍可修改。
            </Text>
          )}
          <Form.Item
            name="username"
            label="用户名"
            rules={[{ required: !editingUser, message: '请输入用户名' }]}
            extra={editingUser ? '修改后，原用户名将不能再用于登录' : undefined}
          >
            <Input placeholder="例如：admin" />
          </Form.Item>
          {!editingUser && (
            <Form.Item
              name="password"
              label="初始密码"
              rules={[{ required: true, min: 6, message: '请输入至少 6 位密码' }]}
            >
              <Input.Password placeholder="至少 6 位" />
            </Form.Item>
          )}
          <Form.Item
            name="name"
            label="姓名"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input placeholder="用户姓名" disabled={isFeishuUser} />
          </Form.Item>
          <Space size="large" align="start">
            <Form.Item label="角色">
              <Space direction="vertical" size={4}>
                <Space size={4} wrap>
                  {editingRoles.length ? (
                    editingRoles.map((name) => (
                      <Tag color="purple" key={name}>
                        {name}
                      </Tag>
                    ))
                  ) : (
                    <Tag>未授权</Tag>
                  )}
                </Space>
                <Text className="text-[12px] text-[var(--color-steel)]">
                  角色由「权限管理 → 授权管理」分配，此处不可修改 ·{' '}
                  <Link
                    href="/settings/permission?tab=grants"
                    className="text-[var(--color-primary)] hover:underline"
                  >
                    前往授权管理
                  </Link>
                </Text>
              </Space>
            </Form.Item>
            <Form.Item name="status" label="状态" style={{ width: 160 }}>
              <Select options={statusOptions} />
            </Form.Item>
          </Space>
          <Form.Item name="email" label="邮箱">
            <Input placeholder="name@example.com" disabled={isFeishuUser} />
          </Form.Item>
          <Space size="large" align="start">
            <Form.Item name="mobile" label="手机号" style={{ width: 180 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
            <Form.Item name="employee_no" label="工号" style={{ width: 180 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
          </Space>
          <Space size="large" align="start">
            <Form.Item name="department" label="部门" style={{ width: 220 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
            <Form.Item name="position" label="职位" style={{ width: 220 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
          </Space>

          {/* 账号操作：重置密码 / 飞书解绑（仅编辑已有用户时） */}
          {editingUser && (
            <div className="mt-2 rounded-md border border-[var(--color-mist)] p-3">
              <Text strong className="text-[13px]">
                账号操作
              </Text>
              <div className="mt-3 space-y-3">
                <Space>
                  <Input.Password
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    placeholder="新密码（至少 6 位）"
                    style={{ width: 220 }}
                    autoComplete="new-password"
                  />
                  <Button onClick={handleResetPassword} loading={resetting}>
                    重置密码
                  </Button>
                </Space>
                <div>
                  {isFeishuUser ? (
                    <Space>
                      <Tag color="green">已绑定飞书</Tag>
                      <Popconfirm
                        title="解绑后该账号将无法用飞书登录，确认解绑？"
                        onConfirm={handleUnbind}
                        okText="解绑"
                        cancelText="取消"
                      >
                        <Button danger loading={unbinding} icon={<UserSwitchOutlined />}>
                          解绑飞书
                        </Button>
                      </Popconfirm>
                    </Space>
                  ) : (
                    <Text className="text-[12px] text-[var(--color-steel)]">
                      未绑定飞书。用户本人首次用飞书登录时自动绑定，管理员不代绑。
                    </Text>
                  )}
                </div>
              </div>
            </div>
          )}
        </Form>
      </Modal>
    </div>
  )
}
