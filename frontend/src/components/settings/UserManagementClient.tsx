'use client'

import { useState, type Key, type PointerEvent as ReactPointerEvent } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Dropdown,
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
  Tooltip,
  Typography,
} from 'antd'
import type { MenuProps } from 'antd'
import {
  CopyOutlined,
  KeyOutlined,
  LogoutOutlined,
  MoreOutlined,
  PlusOutlined,
  ReloadOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons'
import {
  batchUpdateUserStatus,
  createUser,
  deleteUser,
  getUsers,
  listSessions,
  resetUserPassword,
  revokeSession,
  revokeUserSessions,
  unbindFeishuUser,
  updateUser,
} from '@/actions/users'
import { createGrant, fetchRoles } from '@/actions/permission'
import type {
  LocalUserCreate,
  UserBatchStatusResult,
  UserManagementItem,
  UserManagementUpdate,
  UserSession,
} from '@/types/users'
import type { RoleDetail } from '@/types/permission'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'
import { invalidateUserDirectoryQueries } from '@/lib/query/userDirectory'
import { SettingsListCard } from './SettingsListCard'

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

/** 统一时间展示：YYYY-MM-DD HH:mm（避免 toLocaleString 在不同环境格式不一致）。 */
function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
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
  const { can, isSuperuser, user: currentUser, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.userManage)
  // 删除账号仅限超级管理员：普通账号管理员有 platform:user:manage，但不能删除
  const canDelete = !permissionLoading && isSuperuser

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
  // 在线会话管理：查看某用户的会话列表 + 单条踢下线
  // 删除账号：仅超级管理员，弹窗内需输入用户名二次确认
  const [deleteTarget, setDeleteTarget] = useState<UserManagementItem | null>(null)
  const [deleteConfirmText, setDeleteConfirmText] = useState('')
  const [deleting, setDeleting] = useState(false)
  // 批量启用/禁用：选中行 + 结果汇总（失败项逐条列原因）
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([])
  const [batching, setBatching] = useState(false)
  const [batchResult, setBatchResult] = useState<UserBatchStatusResult | null>(null)
  const [sessionUser, setSessionUser] = useState<UserManagementItem | null>(null)
  const [sessions, setSessions] = useState<UserSession[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
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

  // 批量选择：自己 / 超管 / 系统内置账号不可选。只是体验层，后端批量接口会逐条校验
  // （当前用户来自 usePermission，避免重复请求 ['current-user']）
  const rowSelection = canManage
    ? {
        selectedRowKeys,
        onChange: (keys: Key[]) => setSelectedRowKeys(keys),
        getCheckboxProps: (record: UserManagementItem) => ({
          disabled:
            record.id === currentUser?.id ||
            !!record.is_superuser ||
            (record.username || '').toLowerCase() === 'system_admin',
        }),
      }
    : undefined

  if (error) {
    return (
      <Result
        status="403"
        title="无权限访问用户管理"
        subTitle={error instanceof Error ? error.message : '请联系管理员为你授权'}
      />
    )
  }

  const loadUsers = () => {
    // 刷新后行可能已变化，清掉选择避免批量操作指向旧数据
    setSelectedRowKeys([])
    refetchUsers()
  }

  /**
   * 按住表格拖动横向滚动（列多时不必再去拖底部滚动条）。
   *
   * - 只在横向确实溢出的容器上生效；
   * - 移动超过 4px 才认定为拖拽，避免影响单元格点击（编辑 / 启停 / 勾选）；
   * - 按钮、输入框、复选框、开关、下拉等交互元素上不启动，防止抢事件。
   */
  const handleTablePointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return

    const target = event.target as HTMLElement
    if (
      target.closest(
        'button, a, input, textarea, select, [role="checkbox"], .ant-checkbox-wrapper, .ant-switch, .ant-select, .ant-dropdown-trigger, .ant-pagination',
      )
    ) {
      return
    }

    // 向上找最近的可横向滚动容器，不依赖 antd 内部类名
    let node: HTMLElement | null = target
    while (node && node !== document.body) {
      const overflowX = getComputedStyle(node).overflowX
      if (node.scrollWidth > node.clientWidth + 1 && (overflowX === 'auto' || overflowX === 'scroll')) break
      node = node.parentElement
    }
    if (!node || node === document.body) return

    const scroller = node
    const startX = event.clientX
    const startScrollLeft = scroller.scrollLeft
    let dragging = false

    const onMove = (ev: PointerEvent) => {
      const delta = ev.clientX - startX
      if (!dragging && Math.abs(delta) < 4) return
      dragging = true
      scroller.scrollLeft = startScrollLeft - delta
      document.body.style.userSelect = 'none'
      document.body.style.cursor = 'grabbing'
    }
    const stop = () => {
      document.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerup', stop)
      document.removeEventListener('pointercancel', stop)
      document.body.style.userSelect = ''
      document.body.style.cursor = ''
    }

    document.addEventListener('pointermove', onMove)
    document.addEventListener('pointerup', stop)
    document.addEventListener('pointercancel', stop)
  }

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
          // 账号创建后不可修改：不提交 username
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
        // 自动生成的初始密码只在创建响应里出现一次：立刻弹窗展示，关掉后就无法再查看
        if (result.data.initial_password) {
          setOneTimePassword({
            name: result.data.name,
            username: result.data.username || '-',
            password: result.data.initial_password,
          })
        }
      }
      setModalOpen(false)
      invalidateUserDirectoryQueries(queryClient)
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
    invalidateUserDirectoryQueries(queryClient)
  }

  /** 批量启用 / 禁用：逐条校验由后端完成，失败项在结果弹窗里列原因。 */
  const handleBatchStatus = async (status: 'active' | 'disabled') => {
    if (!selectedRowKeys.length) return
    setBatching(true)
    try {
      const result = await batchUpdateUserStatus({
        user_ids: selectedRowKeys.map(String),
        status,
      })
      if (!result.ok) {
        message.error(result.message)
        return
      }
      setBatchResult(result.data)
      setSelectedRowKeys([])
      invalidateUserDirectoryQueries(queryClient)
      if (!result.data.failed.length) {
        message.success(`已${status === 'active' ? '启用' : '禁用'} ${result.data.succeeded.length} 个账号`)
      }
    } finally {
      setBatching(false)
    }
  }

  /** 删除账号：软删除不可恢复，需在弹窗里输入用户名二次确认。 */
  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      const result = await deleteUser(deleteTarget.id)
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success(`账号「${deleteTarget.username || deleteTarget.name}」已删除`)
      setDeleteTarget(null)
      setDeleteConfirmText('')
      invalidateUserDirectoryQueries(queryClient)
    } finally {
      setDeleting(false)
    }
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
      invalidateUserDirectoryQueries(queryClient)
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
    const userId = editingUser.id
    setUnbinding(true)
    try {
      const result = await unbindFeishuUser(userId)
      if (!result.ok) {
        message.error(result.message)
        return
      }
      message.success(
        result.data.account_deleted ? '已解绑并删除该飞书账号' : '已解绑飞书账号',
      )
      // 先把后端返回的最新行写回当前列表缓存，弹窗关闭后表格立即反映结果：
      // 飞书创建的账号已被软删 → 移除该行；本地账号 → 更新为「未绑定」。
      const listKey = ['users', keyword, authSource, pendingFilter] as const
      queryClient.setQueryData<UserManagementItem[]>(listKey, (prev) =>
        result.data.account_deleted
          ? prev?.filter((row) => row.id !== userId)
          : prev?.map((row) => (row.id === userId ? { ...row, ...result.data } : row)),
      )
      setModalOpen(false)
      setEditingUser(null)
      await invalidateUserDirectoryQueries(queryClient)
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

  /** 打开某用户的在线会话列表（拉全量会话后按 user_id 过滤）。 */
  const handleOpenSessions = async (record: UserManagementItem) => {
    setSessionUser(record)
    setSessions([])
    setSessionsLoading(true)
    try {
      const all = await listSessions()
      setSessions(all.filter((s) => s.user_id === record.id))
    } catch {
      message.error('获取在线会话失败，请稍后重试')
    } finally {
      setSessionsLoading(false)
    }
  }

  /** 踢掉单个会话。 */
  const handleKickSession = async (jti: string) => {
    const result = await revokeSession(jti)
    if (!result.ok) {
      message.error(result.message)
      return
    }
    message.success('已踢下线')
    setSessions((prev) => prev.filter((s) => s.jti !== jti))
  }

  /** 会话弹窗内的「全部下线」。 */
  const handleKickAllSessions = async () => {
    if (!sessionUser) return
    const result = await revokeUserSessions(sessionUser.id)
    if (!result.ok) {
      message.error(result.message)
      return
    }
    message.success(
      result.data.revoked > 0 ? `已强制下线 ${result.data.revoked} 个会话` : '该用户当前无在线会话',
    )
    setSessions([])
  }

  // 已绑定飞书的账号：人员资料由飞书同步，编辑时置灰
  const isFeishuUser = !!(editingUser?.feishu_open_id || editingUser?.feishu_user_id)
  // 角色只读展示：真实角色来自「授权管理」，不在此处编辑
  const editingRoles = editingUser?.roles ?? []

  const columns = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      width: 130,
      // 单行省略，避免长姓名把整行撑高；悬停看全名
      render: (name: string) => {
        const text = name || '-'
        return (
          <Tooltip title={text} placement="topLeft">
            <span className="block max-w-full truncate font-medium text-[var(--color-charcoal)]">{text}</span>
          </Tooltip>
        )
      },
    },
    {
      title: '账号',
      dataIndex: 'username',
      key: 'username',
      width: 150,
      render: (username: string | null) => (
        <span className="text-[12px] text-[var(--color-steel)]">{username || '未分配账号'}</span>
      ),
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      width: 140,
      ellipsis: true,
      render: (department: string | null) => <span className="text-[13px]">{department || '-'}</span>,
    },
    {
      title: '职位',
      dataIndex: 'position',
      key: 'position',
      width: 130,
      ellipsis: true,
      render: (position: string | null) => <span className="text-[13px]">{position || '-'}</span>,
    },
    {
      title: '角色',
      key: 'roles',
      width: 180,
      render: (_: unknown, record: UserManagementItem) => {
        const roles = record.roles ?? []
        if (!roles.length) {
          return <Tag>未授权</Tag>
        }
        return (
          <Space size={4} wrap>
            {roles.map((name) => (
              // 角色用中性灰：一屏多个角色时不再一片紫色，把颜色留给状态
              <Tag key={name}>{name}</Tag>
            ))}
          </Space>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 110,
      render: (status: string, record: UserManagementItem) => (
        <Space size={4}>
          {/* 只有「启用」用绿色；「禁用」是正常业务状态，不用红色制造紧张感 */}
          <Tag color={status === 'active' ? 'success' : undefined}>{status === 'active' ? '启用' : '禁用'}</Tag>
          {/* 管理员重置过密码但用户还没改 → 提示该账号仍在用初始密码 */}
          {record.must_change_password && <Tag color="warning">待改密</Tag>}
        </Space>
      ),
    },
    {
      title: '来源 / 飞书',
      key: 'source_feishu',
      width: 150,
      // 纯文字而非彩色 Tag：这一列是背景信息，不需要抢注意力
      render: (_: unknown, record: UserManagementItem) => {
        const source = AUTH_SOURCE_LABEL[record.auth_source ?? ''] ?? (record.auth_source || '-')
        const bound = !!(record.feishu_open_id || record.feishu_user_id)
        return (
          <span className="text-[12px] text-[var(--color-steel)]">
            {source} · {bound ? '已绑定' : '未绑定'}
          </span>
        )
      },
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (value: string | null) => (
        <span className="text-[12px] text-[var(--color-steel)]">{formatDateTime(value)}</span>
      ),
    },
    // 操作列：行内只留高频的「编辑 + 启停」；会话 / 删除收进「⋯」菜单
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'actions',
            width: 180,
            fixed: 'right' as const,
            render: (_: unknown, record: UserManagementItem) => {
              const menuItems: MenuProps['items'] = [
                {
                  key: 'sessions',
                  icon: <LogoutOutlined />,
                  label: '查看会话',
                  onClick: () => handleOpenSessions(record),
                },
              ]
              if (canDelete) {
                menuItems.push({ type: 'divider' })
                menuItems.push({
                  key: 'delete',
                  danger: true,
                  label: '删除账号',
                  onClick: () => {
                    setDeleteConfirmText('')
                    setDeleteTarget(record)
                  },
                })
              }
              return (
                <Space size={4} wrap={false} className="whitespace-nowrap">
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
                  <Dropdown trigger={['click']} menu={{ items: menuItems }}>
                    <Button size="small" icon={<MoreOutlined />} aria-label="更多操作" />
                  </Dropdown>
                </Space>
              )
            },
          },
        ]
      : []),
  ]

  return (
    <>
      <SettingsListCard
        toolbar={
          <>
            {canManage && selectedRowKeys.length > 0 && (
              <div className="flex w-full flex-wrap items-center gap-2 rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] px-3 py-2">
                <Text strong>已选 {selectedRowKeys.length} 项</Text>
                <Button size="small" loading={batching} onClick={() => handleBatchStatus('active')}>
                  批量启用
                </Button>
                <Button size="small" loading={batching} onClick={() => handleBatchStatus('disabled')}>
                  批量禁用
                </Button>
                <Button size="small" type="link" onClick={() => setSelectedRowKeys([])}>
                  取消选择
                </Button>
              </div>
            )}
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
          </>
        }
      >
        <div className="cursor-grab" onPointerDown={handleTablePointerDown}>
          <Table
            columns={columns}
            dataSource={users}
            rowKey="id"
            loading={loading}
            rowSelection={rowSelection}
            // 固定操作列需要明确的滚动宽度，否则「编辑 / 启停 / ⋯」会被挤断
            // 列宽合计：姓名 130 + 账号 150 + 部门 140 + 职位 130 + 角色 180 + 状态 110 + 来源/飞书 150 + 创建时间 170 + 操作 180 + 多选 50
            scroll={{ x: 1390 }}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (t) => `共 ${t} 条`,
            }}
          />
        </div>
      </SettingsListCard>

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
              状态仍可修改。
            </Text>
          )}
          <Form.Item
            name="username"
            label="账号"
            rules={
              editingUser
                ? []
                : [
                    { required: true, message: '请输入账号' },
                    {
                      pattern: /^[A-Za-z][A-Za-z0-9]{1,63}$/,
                      message: '只能使用字母和数字，且必须以字母开头（2-64 位）',
                    },
                  ]
            }
            extra={editingUser ? '账号创建后不可修改' : '仅支持字母和数字，需以字母开头'}
          >
            <Input placeholder="请输入登录账号" disabled={!!editingUser} />
          </Form.Item>
          {!editingUser && (
            <Text type="secondary" className="block -mt-2 mb-4 text-[12px]">
              初始密码由系统自动生成，创建成功后只显示一次，该用户首次登录需自行修改密码。
            </Text>
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
              <Space orientation="vertical" size={4}>
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
            <div className="mt-2 rounded-md border border-[var(--color-hairline)] p-3">
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
                    {editingUser.must_change_password && <Tag color="warning">待改密</Tag>}
                  </Space>
                  <div className="mt-2 text-[12px] text-[var(--color-steel)]">
                    飞书首次登录只自动分配账号（
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
                      <Tag color="success">已绑定飞书</Tag>
                      <Popconfirm
                        title={
                          editingUser.auth_source === 'feishu'
                            ? '该账号由飞书首次登录自动创建。解绑将删除此账号及其角色授权，且无法再用飞书登录。确认删除？'
                            : '解绑后该账号将无法用飞书登录，账号本体与角色授权保留。确认解绑？'
                        }
                        onConfirm={handleUnbind}
                        okText={editingUser.auth_source === 'feishu' ? '删除并解绑' : '解绑'}
                        okButtonProps={{ danger: editingUser.auth_source === 'feishu' }}
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

      {/* 批量启用/禁用结果：成功数 + 失败项逐条原因 */}
      <Modal
        title="批量操作结果"
        open={!!batchResult}
        onCancel={() => setBatchResult(null)}
        footer={[
          <Button key="ok" type="primary" onClick={() => setBatchResult(null)}>
            知道了
          </Button>,
        ]}
        width="min(520px, calc(100vw - 24px))"
      >
        {batchResult && (
          <>
            <Alert
              type={batchResult.failed.length ? 'warning' : 'success'}
              showIcon
              title={
                batchResult.failed.length
                  ? `成功 ${batchResult.succeeded.length} 项，失败 ${batchResult.failed.length} 项`
                  : `成功 ${batchResult.succeeded.length} 项`
              }
              className="mb-3"
            />
            {batchResult.failed.length > 0 && (
              <ul className="max-h-[280px] space-y-1 overflow-auto text-[13px]">
                {batchResult.failed.map((item) => (
                  <li key={item.id}>
                    <Text code>{item.username || item.id}</Text>：{item.reason}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </Modal>

      {/* 删除账号：仅超级管理员；软删除不可恢复，需输入用户名确认 */}
      <Modal
        title="删除账号"
        open={!!deleteTarget}
        onCancel={() => setDeleteTarget(null)}
        onOk={handleDelete}
        okText="确认删除"
        okButtonProps={{
          danger: true,
          disabled:
            !deleteConfirmText || deleteConfirmText !== (deleteTarget?.username || deleteTarget?.name || ''),
          loading: deleting,
        }}
        cancelText="取消"
        width="min(520px, calc(100vw - 24px))"
      >
        <Alert
          type="error"
          showIcon
          title="删除后该账号无法登录，且不可恢复"
          description="该账号的角色授权会被清空、在线会话会被强制下线；历史单据仍保留其姓名。账号名将被永久占用，不能再创建同名账号。"
          className="mb-4"
        />
        <div className="text-[13px]">
          请输入{deleteTarget?.username ? '账号' : '姓名'}{' '}
          <Text code>{deleteTarget?.username || deleteTarget?.name || '-'}</Text> 以确认删除：
        </div>
        <Input
          className="mt-2"
          value={deleteConfirmText}
          onChange={(e) => setDeleteConfirmText(e.target.value)}
          placeholder="输入账号"
          autoComplete="off"
        />
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
        mask={{ closable: false }}
        width="min(480px, calc(100vw - 24px))"
      >
        <Alert
          type="warning"
          showIcon
          title="此密码只显示这一次，关闭后无法再次查看"
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
            <div className="rounded-md border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] p-3 text-center">
              <Text
                strong
                className="text-[18px] tracking-wider"
                copyable={{ text: oneTimePassword.password }}
              >
                {oneTimePassword.password}
              </Text>
            </div>
            <div className="text-[12px] text-[var(--color-steel)]">
              该用户首次登录后会被要求立即修改密码（账号 / 邮箱 / 手机号 / 工号均可登录）。
            </div>
          </div>
        )}
      </Modal>

      {/* 在线会话管理：会话列表 + 单条踢下线 */}
      <Modal
        title={sessionUser ? `在线会话 — ${sessionUser.name}` : '在线会话'}
        open={!!sessionUser}
        onCancel={() => setSessionUser(null)}
        footer={[
          <Button key="close" onClick={() => setSessionUser(null)}>
            关闭
          </Button>,
          <Popconfirm
            key="kickall"
            title="强制下线其全部会话？"
            onConfirm={handleKickAllSessions}
            okText="全部下线"
            cancelText="取消"
          >
            <Button danger>全部下线</Button>
          </Popconfirm>,
        ]}
        width="min(720px, calc(100vw - 24px))"
      >
        <Table
          rowKey="jti"
          dataSource={sessions}
          loading={sessionsLoading}
          pagination={false}
          locale={{ emptyText: '该用户当前无在线会话' }}
          scroll={{ x: 'max-content' }}
          columns={[
            {
              title: '登录 IP',
              dataIndex: 'ip_address',
              width: 140,
              render: (v: string | null) => v || '-',
            },
            {
              title: '设备 / 浏览器',
              dataIndex: 'user_agent',
              ellipsis: true,
              render: (v: string | null) => v || '-',
            },
            {
              title: '登录时间',
              dataIndex: 'created_at',
              width: 180,
              render: (v: string) => new Date(v).toLocaleString(),
            },
            {
              title: '操作',
              key: 'action',
              width: 100,
              render: (_: unknown, record: UserSession) => (
                <Popconfirm
                  title="确认踢下线该会话？对应设备将立即失效。"
                  onConfirm={() => handleKickSession(record.jti)}
                  okText="踢下线"
                  cancelText="取消"
                >
                  <Button size="small" danger>
                    踢下线
                  </Button>
                </Popconfirm>
              ),
            },
          ]}
        />
      </Modal>
    </>
  )
}
