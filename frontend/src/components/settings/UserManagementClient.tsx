'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Card,
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
import {
  CopyOutlined,
  KeyOutlined,
  LogoutOutlined,
  PlusOutlined,
  ReloadOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons'
import {
  createUser,
  getUsers,
  resetUserPassword,
  revokeUserSessions,
  unbindFeishuUser,
  updateUser,
} from '@/actions/users'
import { createGrant, fetchRoles } from '@/actions/permission'
import type {
  LocalUserCreate,
  UserManagementItem,
  UserManagementUpdate,
} from '@/types/users'
import type { RoleDetail } from '@/types/permission'
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

/**
 * 复制到剪贴板。
 *
 * `navigator.clipboard` 只在安全上下文（https / localhost）可用；本系统常以
 * `http://<内网IP>:3000` 访问，此时它是 undefined，必须回退到 textarea + execCommand，
 * 否则「复制密码」按钮在真实环境下直接失效（而随机密码只显示一次，抄错就没了）。
 */
async function copyToClipboard(text: string): Promise<boolean> {
  if (typeof navigator !== 'undefined' && navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text)
      return true
    } catch {
      // 落到下面的兜底方案
    }
  }

  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', '')
    textarea.style.position = 'fixed'
    textarea.style.top = '-1000px'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(textarea)
    return ok
  } catch {
    return false
  }
}

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
  // 编辑弹窗内的「账号操作」：生成随机密码 / 解绑飞书
  const [resetting, setResetting] = useState(false)
  const [unbinding, setUnbinding] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  // 一次性展示的随机密码：后端不落库明文，关掉弹窗就再也看不到
  const [oneTimePassword, setOneTimePassword] = useState<{
    name: string
    username: string
    password: string
  } | null>(null)
  const [copying, setCopying] = useState(false)
  const [keyword, setKeyword] = useState('')
  const [authSource, setAuthSource] = useState<AuthSourceValue | undefined>()
  // 运营筛选：待改密 / 未绑定飞书（互斥单选）
  const [pendingFilter, setPendingFilter] = useState<'pending_change' | 'unbound' | undefined>()
  const [form] = Form.useForm()

  const { data: users = [], isLoading: loading, error, refetch: refetchUsers } = useQuery({
    queryKey: ['users', keyword, authSource, pendingFilter],
    queryFn: async () => {
      const result = await getUsers({
        keyword: keyword || undefined,
        auth_source: authSource,
        must_change_password: pendingFilter === 'pending_change' ? true : undefined,
        unbound_only: pendingFilter === 'unbound' ? true : undefined,
      })
      return result.items || []
    },
    // 每次进入页面都取最新（在「授权管理」改了角色后回到本页，不该看到旧角色）
    refetchOnMount: 'always',
    staleTime: 0,
  })

  // 新建用户时可「同时授予角色」：拉角色列表供多选
  const { data: roles = [] } = useQuery<RoleDetail[]>({
    queryKey: ['permission-roles'],
    queryFn: fetchRoles,
    staleTime: 5 * 60_000,
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
    form.resetFields()
    form.setFieldsValue({ status: 'active' })
    setModalOpen(true)
  }

  const handleEdit = (record: UserManagementItem) => {
    setEditingUser(record)
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
        // 一站式授权：表单里「同时授予角色」不作为用户字段提交，单独走 create_grant
        const roleIds: string[] = values.role_ids ?? []
        const createData = { ...values } as LocalUserCreate & { role_ids?: string[] }
        delete createData.role_ids
        const result = await createUser(createData)
        if (!result.ok) {
          message.error(result.message)
          return
        }
        let grantFailed = false
        for (const roleId of roleIds) {
          try {
            await createGrant({
              user_id: result.data.id,
              role_id: roleId,
              scope_type: 'all',
              scope_dept_codes: [],
            })
          } catch (e) {
            grantFailed = true
            message.error(e instanceof Error ? e.message : '授权失败')
          }
        }
        message.success(grantFailed ? '用户已创建，但部分角色授权失败' : '用户已创建')
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

  /** 生成随机初始密码：明文只在本响应里返回一次，必须当场展示。 */
  const handleGeneratePassword = async () => {
    if (!editingUser) return
    setResetting(true)
    try {
      const result = await resetUserPassword(editingUser.id, {})
      if (!result.ok) {
        message.error(result.message)
        return
      }
      const generated = result.data.password
      if (!generated) {
        // 后端未回传明文（理论上只在「指定密码」时发生）→ 不要假装看到了密码
        message.warning(result.data.message || '密码已重置')
        return
      }
      setOneTimePassword({
        name: editingUser.name,
        username: editingUser.username || '-',
        password: generated,
      })
      queryClient.invalidateQueries({ queryKey: ['users'] })
    } finally {
      setResetting(false)
    }
  }

  const handleCopyPassword = async () => {
    if (!oneTimePassword) return
    setCopying(true)
    try {
      const ok = await copyToClipboard(oneTimePassword.password)
      if (ok) {
        message.success('密码已复制')
      } else {
        message.error('复制失败，请手动选中密码复制')
      }
    } finally {
      setCopying(false)
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

  const handleForceLogout = async () => {
    if (!editingUser) return
    setLoggingOut(true)
    try {
      const result = await revokeUserSessions(editingUser.id)
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success(
        result.data.revoked > 0 ? `已强制下线 ${result.data.revoked} 个会话` : '该用户当前无在线会话',
      )
    } finally {
      setLoggingOut(false)
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
      width: 140,
      render: (status: string, record: UserManagementItem) => (
        <Space size={4}>
          <Tag color={status === 'active' ? 'success' : 'error'}>
            {status === 'active' ? '启用' : '禁用'}
          </Tag>
          {/* 管理员重置过密码但用户还没改 → 提示该账号仍在用初始密码 */}
          {record.must_change_password && <Tag color="orange">待改密</Tag>}
        </Space>
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
        <div className="flex flex-wrap items-center gap-3">
          <div className="w-full sm:w-[130px]">
            <Select
              allowClear
              placeholder="登录来源"
              style={{ width: '100%' }}
              value={authSource}
              onChange={(value) => setAuthSource(value)}
              options={authSourceOptions}
            />
          </div>
          <div className="w-full sm:w-[140px]">
            <Select
              allowClear
              placeholder="账号属性"
              style={{ width: '100%' }}
              value={pendingFilter}
              onChange={(value) => setPendingFilter(value)}
              options={[
                { value: 'pending_change', label: '待改密' },
                { value: 'unbound', label: '未绑定飞书' },
              ]}
            />
          </div>
          <div className="w-full sm:w-[260px]">
            <Input.Search
              allowClear
              placeholder="搜索姓名、账号、邮箱"
              onSearch={(value) => setKeyword(value)}
              style={{ width: '100%' }}
            />
          </div>
          <Button icon={<ReloadOutlined />} onClick={loadUsers}>
            刷新
          </Button>
          {canManage && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建用户
            </Button>
          )}
        </div>
      </div>

      <Card className="[&_.ant-table]:!m-0">
      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        scroll={{ x: 1050 }}
        pagination={{ pageSize: 10 }}
      />
      </Card>

      <Modal
        title={editingUser ? '编辑用户' : '新建本地用户'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width="min(640px, calc(100vw - 24px))"
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
              rules={[
                { required: true, message: '请输入初始密码' },
                { min: 8, message: '密码至少 8 位' },
                { pattern: /(?=.*[A-Za-z])(?=.*\d)/, message: '需同时包含字母和数字' },
              ]}
            >
              <Input.Password placeholder="至少 8 位，含字母和数字" />
            </Form.Item>
          )}
          <Form.Item
            name="name"
            label="姓名"
            rules={[{ required: true, message: '请输入姓名' }]}
          >
            <Input placeholder="用户姓名" disabled={isFeishuUser} />
          </Form.Item>
          <Space size="large" align="start" wrap>
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
            <Form.Item name="status" label="状态" style={{ width: '100%', maxWidth: 160 }}>
              <Select options={statusOptions} />
            </Form.Item>
          </Space>
          {!editingUser && (
            <Form.Item name="role_ids" label="同时授予角色" className="mb-1">
              <Select
                mode="multiple"
                allowClear
                placeholder="可选：创建后立即授予角色（可在授权管理中调整）"
                options={roles
                  .filter((r) => !r.is_superuser)
                  .map((r) => ({ value: r.id, label: `${r.name}（${r.code}）` }))}
              />
            </Form.Item>
          )}
          <Form.Item name="email" label="邮箱">
            <Input placeholder="name@example.com" disabled={isFeishuUser} />
          </Form.Item>
          <Space size="large" align="start" wrap>
            <Form.Item name="mobile" label="手机号" style={{ width: '100%', maxWidth: 180 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
            <Form.Item name="employee_no" label="工号" style={{ width: '100%', maxWidth: 180 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
          </Space>
          <Space size="large" align="start" wrap>
            <Form.Item name="department" label="部门" style={{ width: '100%', maxWidth: 220 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
            <Form.Item name="position" label="职位" style={{ width: '100%', maxWidth: 220 }}>
              <Input disabled={isFeishuUser} />
            </Form.Item>
          </Space>

          {/* 账号操作：随机密码 / 飞书解绑（仅编辑已有用户时） */}
          {editingUser && (
            <div className="mt-2 rounded-md border border-[var(--color-mist)] p-3">
              <Text strong className="text-[13px]">
                账号操作
              </Text>
              <div className="mt-3 space-y-3">
                <div>
                  <Space>
                    <Button
                      icon={<KeyOutlined />}
                      onClick={handleGeneratePassword}
                      loading={resetting}
                      type={editingUser.must_change_password ? 'primary' : 'default'}
                    >
                      生成随机密码
                    </Button>
                    {editingUser.must_change_password && <Tag color="orange">待改密</Tag>}
                  </Space>
                  <div className="mt-2 text-[12px] text-[var(--color-steel)]">
                    飞书首次登录只自动分配用户名（
                    <Text code>{editingUser.username || '未分配'}</Text>
                    ），不发密码；需要账号密码登录时点这里生成。随机密码
                    <Text strong className="text-[12px]">
                      只显示一次
                    </Text>
                    ，请当场复制并发给本人；本人首次登录会被要求修改。
                  </div>
                </div>
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
                <div>
                  <Popconfirm
                    title="强制下线会使其所有登录会话立即失效，确认？"
                    onConfirm={handleForceLogout}
                    okText="强制下线"
                    cancelText="取消"
                  >
                    <Button danger loading={loggingOut} icon={<LogoutOutlined />}>
                      强制下线
                    </Button>
                  </Popconfirm>
                </div>
              </div>
            </div>
          )}
        </Form>
      </Modal>

      {/* 一次性密码展示：明文只存在这一刻，后端不落库，关闭后无法查看 */}
      <Modal
        title="随机密码已生成"
        open={!!oneTimePassword}
        onCancel={() => setOneTimePassword(null)}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} loading={copying} onClick={handleCopyPassword}>
            复制密码
          </Button>,
          <Button key="close" type="primary" onClick={() => setOneTimePassword(null)}>
            我已保存
          </Button>,
        ]}
        maskClosable={false}
        width="min(480px, calc(100vw - 24px))"
      >
        <Alert
          type="warning"
          showIcon
          message="此密码只显示这一次，关闭后无法再次查看"
          description="数据库只保存密码哈希，管理员也无法再看到明文。请立即复制并通过可靠渠道发给本人。"
          className="mb-4"
        />
        {oneTimePassword && (
          <div className="space-y-2">
            <div className="text-[13px] text-[var(--color-steel)]">
              账号：<Text strong>{oneTimePassword.name}</Text>
              <Text className="ml-2" code>
                {oneTimePassword.username}
              </Text>
            </div>
            <div className="rounded-md border border-[var(--color-mist)] bg-[var(--color-cloud)] p-3 text-center">
              <Text
                strong
                className="text-[18px] tracking-wider"
                copyable={{ text: oneTimePassword.password }}
              >
                {oneTimePassword.password}
              </Text>
            </div>
            <div className="text-[12px] text-[var(--color-steel)]">
              该用户首次登录后会被要求立即修改密码（用户名 / 邮箱 / 手机号均可作为登录账号）。
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
