'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Empty, Input, Popconfirm, Select, Space, Table, Tag, Tooltip, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'
import GrantCreateModal from './GrantCreateModal'
import RoleEditModal from './RoleEditModal'
import { createGrant, deleteGrant, deleteRole, fetchGrants, fetchPermissionTree, fetchRoles } from '@/actions/permission'
import { UserLabel } from '@/components/common/UserAvatar'
import { PersonMultiSelect } from '@/components/common/PersonSelect'
import {
  READONLY_ROLE_TYPES,
  ROLE_TYPE_META,
  SettingsListCard,
  isDelegateRoleType,
  isOwnerRoleType,
} from '@/components/settings'
import type { GrantItem, PermissionTreeNode, RoleDetail } from '@/types/permission'
import { formatFullTime, formatShortTime } from './runtimeSettingsMeta'

const { Text } = Typography

const GRANT_STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'active', label: '生效中' },
  { value: 'disabled', label: '已停用' },
]

/**
 * 三个区块（模块代表 / 岗位角色 / 授权）统一的标题样式：
 * 浅灰底 + 左侧 3px 主色竖条 + 分隔线，让不同区域一眼可分。
 * 只作用于本页卡片的 className，不改共享的 SettingsListCard。
 */
const SECTION_CARD_CLASS =
  '[&_.ant-card-head]:bg-[var(--color-surface-soft)]! [&_.ant-card-head]:border-l-[3px]! [&_.ant-card-head]:border-l-[var(--color-primary)]! [&_.ant-card-head]:border-b-[var(--color-hairline)]!'

interface ModulePermissionPanelProps {
  moduleCode: string
  moduleLabel: string
  canManage: boolean
  /** 当前登录账号 id（用于判断"我是不是本模块负责人"） */
  currentUserId: string
  /** 是否系统管理员（模块负责人由超管在系统管理页指派；代表不在此列） */
  isSystemAdmin: boolean
}

/**
 * 模块配置页的「权限管理」页签。
 *
 * 职责：本模块的岗位角色（新建/编辑/删除）+ 授权（授予/移除）+ 模块代表指派。
 * - 「模块代表」区域**只有本模块负责人可见**（2026-11-19 需求），超管也不渲染；
 * - 负责人/代表这两个内置角色的授权行按身份只读（负责人授权仅超管可动，
 *   代表授权仅本模块负责人可动，见后端 R2）；
 * - 权限树按模块过滤，模块管理入口码置灰不可勾选（后端另有硬校验）；
 * - 数据范围当前休眠，界面不暴露（统一 `all`）。
 *
 * 列表侧只做检索 / 筛选 / 分页 / 权限展开，只读判定与后端规则保持一致。
 */
export default function ModulePermissionPanel({
  moduleCode,
  moduleLabel,
  canManage,
  currentUserId,
  isSystemAdmin,
}: ModulePermissionPanelProps) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [roleModalOpen, setRoleModalOpen] = useState(false)
  const [editingRole, setEditingRole] = useState<RoleDetail | null>(null)
  const [grantModalOpen, setGrantModalOpen] = useState(false)
  const [roleKeyword, setRoleKeyword] = useState('')
  const [grantKeyword, setGrantKeyword] = useState('')
  const [grantStatus, setGrantStatus] = useState('all')
  const [delegateCandidates, setDelegateCandidates] = useState<Array<{ id: string; name: string }>>([])
  const [assigningDelegate, setAssigningDelegate] = useState(false)

  const { data: roles = [], isLoading: rolesLoading } = useQuery({
    queryKey: ['module-roles', moduleCode],
    queryFn: () => fetchRoles(moduleCode),
  })

  const { data: grants = [], isLoading: grantsLoading } = useQuery({
    queryKey: ['module-grants', moduleCode],
    queryFn: () => fetchGrants(undefined, moduleCode),
  })

  const { data: treeData, error: treeError } = useQuery({
    queryKey: ['permission-tree'],
    queryFn: () => fetchPermissionTree(),
    // 只有打开角色弹窗才需要权限树，避免进页面就多打一个大接口
    enabled: roleModalOpen,
  })

  /** 只保留本模块节点，并把「模块管理入口码」置灰（岗位角色不可持有） */
  const moduleTree = useMemo<PermissionTreeNode[]>(() => {
    const tree = treeData?.tree ?? []
    const findModule = (nodes: PermissionTreeNode[]): PermissionTreeNode | undefined => {
      for (const node of nodes) {
        if (node.type === 'module' && node.code === moduleCode) return node
        const hit = node.children?.length ? findModule(node.children) : undefined
        if (hit) return hit
      }
      return undefined
    }
    const node = findModule(tree)
    if (!node) return []
    const disableAdminEntry = (nodes: PermissionTreeNode[]): PermissionTreeNode[] =>
      nodes.map((child) => ({
        ...child,
        disabled: child.code === `${moduleCode}:admin:read` ? true : child.disabled,
        children: child.children?.length ? disableAdminEntry(child.children) : child.children,
      }))
    return disableAdminEntry([{ ...node, disabled: false }])
  }, [treeData, moduleCode])

  const roleById = useMemo(() => new Map(roles.map((role) => [role.id, role])), [roles])

  const ownerRole = useMemo(
    () => roles.find((role) => isOwnerRoleType(role.role_type)),
    [roles],
  )
  const delegateRole = useMemo(
    () => roles.find((role) => isDelegateRoleType(role.role_type)),
    [roles],
  )

  /**
   * 当前登录人是否为本模块负责人。
   *
   * 只认「持有 owner 角色且授权生效」：系统管理员也不算（需求：指派区只有负责人看得到，
   * 超管若要指派代表，先把负责人换给自己或让对方操作）。后端 `can_assign_delegates`
   * 是同一口径的最终守卫。
   */
  const isModuleOwner = useMemo(() => {
    if (!ownerRole) return false
    return grants.some(
      (grant) => grant.role_id === ownerRole.id && grant.user_id === currentUserId && grant.status === 'active',
    )
  }, [ownerRole, grants, currentUserId])

  /** 可授予的角色：岗位角色；负责人另外可以授予「模块代表」 */
  const grantableRoles = useMemo(
    () =>
      roles.filter((role) => {
        if (role.role_type === 'job') return true
        if (isDelegateRoleType(role.role_type)) return isModuleOwner
        return false
      }),
    [roles, isModuleOwner],
  )

  /** 已指派的模块代表（含已停用，停用态只读展示，便于追溯） */
  const delegateGrants = useMemo(
    () => (delegateRole ? grants.filter((grant) => grant.role_id === delegateRole.id) : []),
    [grants, delegateRole],
  )

  /** 「岗位角色」区只列岗位角色：内置的模块负责人 / 模块代表不在此表展示。 */
  const jobRoles = useMemo(() => roles.filter((role) => role.role_type === 'job'), [roles])

  const visibleRoles = useMemo(() => {
    const keyword = roleKeyword.trim().toLowerCase()
    if (!keyword) return jobRoles
    return jobRoles.filter((role) => [role.name, role.code].some((value) => value?.toLowerCase().includes(keyword)))
  }, [jobRoles, roleKeyword])

  const visibleGrants = useMemo(() => {
    const keyword = grantKeyword.trim().toLowerCase()
    return grants.filter((grant) => {
      if (grantStatus !== 'all' && grant.status !== grantStatus) return false
      if (!keyword) return true
      return [grant.user_name, grant.username, grant.role_name, grant.role_code].some((value) =>
        value?.toLowerCase().includes(keyword),
      )
    })
  }, [grants, grantKeyword, grantStatus])

  const openCreateRole = () => {
    setEditingRole(null)
    setRoleModalOpen(true)
  }

  const openEditRole = (role: RoleDetail) => {
    setEditingRole(role)
    setRoleModalOpen(true)
  }

  const refreshRoles = () => queryClient.invalidateQueries({ queryKey: ['module-roles', moduleCode] })
  const refreshGrants = () => queryClient.invalidateQueries({ queryKey: ['module-grants', moduleCode] })

  const removeRole = async (role: RoleDetail) => {
    const result = await deleteRole(role.id)
    if (!result.ok) {
      message.error(result.message)
      return
    }
    message.success('角色已删除，其授权已停用（可在授权管理中恢复）')
    await Promise.all([refreshRoles(), refreshGrants()])
  }

  const removeGrant = async (grant: GrantItem) => {
    try {
      await deleteGrant(grant.id)
      message.success('已移除授权')
      await refreshGrants()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '移除失败')
    }
  }

  /**
   * 指派模块代表：支持一次选多人，逐个复用单条授权接口（后端按 role_type=delegate
   * 做「仅本模块负责人」校验；批量接口要求平台级权限码，模块负责人走不了）。
   */
  const assignDelegate = async () => {
    if (!delegateRole) {
      message.error('未找到本模块的代表角色，请确认权限注册表已同步')
      return
    }
    if (delegateCandidates.length === 0) {
      message.warning('请先选择要指派的员工')
      return
    }
    setAssigningDelegate(true)
    const succeeded: string[] = []
    const failed: string[] = []
    try {
      for (const person of delegateCandidates) {
        try {
          await createGrant({ user_id: person.id, role_id: delegateRole.id, scope_type: 'all' })
          succeeded.push(person.name)
        } catch (error) {
          failed.push(`${person.name}（${error instanceof Error ? error.message : '失败'}）`)
        }
      }
      if (succeeded.length > 0) {
        message.success(`已指派 ${succeeded.length} 名模块代表`)
        setDelegateCandidates([])
        await refreshGrants()
      }
      if (failed.length > 0) {
        message.warning(`未指派 ${failed.length} 人：${failed.join('；')}`)
      }
    } finally {
      setAssigningDelegate(false)
    }
  }

  const roleColumns: ColumnsType<RoleDetail> = [
    {
      title: '角色',
      dataIndex: 'name',
      render: (_, role) => {
        const meta = ROLE_TYPE_META[role.role_type] ?? ROLE_TYPE_META.job
        return (
          <Space size={6} wrap>
            <Text strong>{role.name}</Text>
            <Tag color={meta?.color}>{meta?.text}</Tag>
            {role.is_builtin && <Tag>内置</Tag>}
          </Space>
        )
      },
    },
    { title: '编码', dataIndex: 'code', width: 240, render: (code: string) => <Text code>{code}</Text> },
    {
      title: '权限',
      dataIndex: 'permission_codes',
      width: 110,
      render: (codes: string[] | undefined) => <Text type="secondary">{codes?.length ?? 0} 项</Text>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 170,
      render: (_, role) => {
        if (READONLY_ROLE_TYPES.has(role.role_type)) {
          return (
            <Tooltip title="内置角色由代码生成，权限随注册表自动同步，不能手工编辑">
              <Text type="secondary">内置角色</Text>
            </Tooltip>
          )
        }
        return (
          <Space>
            <Button size="small" disabled={!canManage} onClick={() => openEditRole(role)}>
              编辑
            </Button>
            <Popconfirm
              title="删除该角色？"
              description="其名下授权会一并停用（可恢复），持有者将立即失去对应权限。"
              okText="删除"
              cancelText="取消"
              disabled={!canManage}
              onConfirm={() => removeRole(role)}
            >
              <Button size="small" danger disabled={!canManage}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        )
      },
    },
  ]

  const grantColumns: ColumnsType<GrantItem> = [
    {
      title: '用户',
      dataIndex: 'user_name',
      width: 220,
      // 头像来自 identity.users（授权列表接口已带回 avatar_url），缺失时回退姓名首字
      render: (_, g) => (
        <UserLabel
          name={g.user_name}
          src={g.avatar_url}
          fallback={g.username || g.user_id}
          avatarSize={24}
        />
      ),
    },
    {
      // 部门 / 职务取自 HR 员工档案（后端回填），无档案的账号显示「—」
      title: '部门',
      dataIndex: 'department_name',
      width: 170,
      ellipsis: { showTitle: false },
      render: (value: string | null | undefined, g) =>
        value ? (
          <Tooltip title={g.department_path_text || value}>
            <span>{value}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '岗位',
      dataIndex: 'position_name',
      width: 140,
      ellipsis: { showTitle: false },
      render: (value: string | null | undefined) =>
        value ? (
          <Tooltip title={value}>
            <span>{value}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '角色',
      dataIndex: 'role_name',
      render: (_, g) => {
        const role = roleById.get(g.role_id)
        const meta = role ? ROLE_TYPE_META[role.role_type] : undefined
        return (
          <Space size={6}>
            <span>{g.role_name ?? role?.name ?? g.role_code}</span>
            {meta && <Tag color={meta.color}>{meta.text}</Tag>}
          </Space>
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (status: string) =>
        status === 'active' ? <Tag color="green">生效中</Tag> : <Tag>已停用</Tag>,
    },
    {
      title: '授予时间',
      dataIndex: 'created_at',
      width: 130,
      render: (value: string | null | undefined) =>
        value ? (
          <Tooltip title={formatFullTime(value)}>
            <span className="text-[12px] text-[var(--color-steel)]">{formatShortTime(value)}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, grant) => {
        const role = roleById.get(grant.role_id)
        const isDelegateGrant = isDelegateRoleType(role?.role_type)
        const isOwnerGrant = isOwnerRoleType(role?.role_type) || role?.role_type === 'system'
        // 模块代表：只有本模块负责人可移除；模块负责人：只有系统管理员可动
        const readonly = isOwnerGrant ? !isSystemAdmin : isDelegateGrant ? !isModuleOwner : false
        if (readonly) {
          return (
            <Tooltip
              title={
                isDelegateGrant
                  ? '只有本模块负责人可以调整模块代表'
                  : '模块负责人由系统管理员在「系统管理 → 权限管理」中指派'
              }
            >
              <Text type="secondary">只读</Text>
            </Tooltip>
          )
        }
        return (
          <Popconfirm
            title="移除该授权？"
            okText="移除"
            cancelText="取消"
            disabled={!canManage}
            onConfirm={() => removeGrant(grant)}
          >
            <Button size="small" danger disabled={!canManage}>
              移除
            </Button>
          </Popconfirm>
        )
      },
    },
  ]

  const delegateColumns: ColumnsType<GrantItem> = [
    {
      title: '姓名',
      dataIndex: 'user_name',
      width: 220,
      render: (_, g) => (
        <UserLabel
          name={g.user_name}
          src={g.avatar_url}
          fallback={g.username || g.user_id}
          avatarSize={24}
        />
      ),
    },
    {
      // 与「授权」表同口径：部门 / 职务来自后端回填的 HR 档案字段
      title: '部门',
      dataIndex: 'department_name',
      width: 170,
      ellipsis: { showTitle: false },
      render: (value: string | null | undefined, g) =>
        value ? (
          <Tooltip title={g.department_path_text || value}>
            <span>{value}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '岗位',
      dataIndex: 'position_name',
      width: 140,
      ellipsis: { showTitle: false },
      render: (value: string | null | undefined) =>
        value ? (
          <Tooltip title={value}>
            <span>{value}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '授予时间',
      dataIndex: 'created_at',
      width: 130,
      render: (value: string | null | undefined) =>
        value ? (
          <Tooltip title={formatFullTime(value)}>
            <span className="text-[12px] text-[var(--color-steel)]">{formatShortTime(value)}</span>
          </Tooltip>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (status: string) =>
        status === 'active' ? <Tag color="green">生效中</Tag> : <Tag>已停用</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 90,
      render: (_, grant) =>
        grant.status === 'active' ? (
          <Popconfirm
            title="移除该模块代表？"
            description="移除后对方立即失去本模块的全部权限。"
            okText="移除"
            cancelText="取消"
            onConfirm={() => removeGrant(grant)}
          >
            <Button size="small" danger>
              移除
            </Button>
          </Popconfirm>
        ) : (
          <Text type="secondary">—</Text>
        ),
    },
  ]

  return (
    <div className="space-y-5">
      <Alert
        type="info"
        showIcon
        message={`这里是「${moduleLabel}」的权限管理：模块负责人由系统管理员指派，模块代表由本模块负责人指派；你可以维护岗位角色并授权给本模块员工。`}
      />

      {/* 模块代表指派区：只有本模块负责人可见（超管也不渲染） */}
      {isModuleOwner && (
        <SettingsListCard
          title="模块代表"
          extra={
            <span className="text-[12px] text-[var(--color-steel)]">
              共 {delegateGrants.filter((grant) => grant.status === 'active').length} 名
            </span>
          }
          className={SECTION_CARD_CLASS}
        >
          <div className="space-y-3">
            <Text type="secondary" className="text-[12px]">
              模块代表拥有与本模块负责人相同的业务权限和模块配置入口，但不能指派或移除模块代表。
            </Text>
            <div className="flex flex-wrap items-center gap-2">
              <div className="w-[360px] max-w-full">
                <PersonMultiSelect
                  placeholder="搜索姓名，可多选"
                  value={delegateCandidates.map((person) => person.id)}
                  onChange={(persons) =>
                    setDelegateCandidates(persons.map((person) => ({ id: person.id, name: person.name })))
                  }
                />
              </div>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                loading={assigningDelegate}
                disabled={delegateCandidates.length === 0}
                onClick={assignDelegate}
              >
                指派为代表{delegateCandidates.length > 0 ? `（${delegateCandidates.length}）` : ''}
              </Button>
            </div>
            <Table
              rowKey="id"
              size="small"
              columns={delegateColumns}
              dataSource={delegateGrants}
              pagination={{ pageSize: 10, size: 'small', hideOnSinglePage: true, showSizeChanger: false }}
              scroll={{ x: 'max-content' }}
              locale={{ emptyText: '尚未指派模块代表' }}
            />
          </div>
        </SettingsListCard>
      )}

      <SettingsListCard
        title="岗位角色"
        extra={
          <Space size={8} wrap>
            <span className="text-[12px] text-[var(--color-steel)]">共 {jobRoles.length} 个</span>
            <Button type="primary" icon={<PlusOutlined />} disabled={!canManage} onClick={openCreateRole}>
              新建角色
            </Button>
          </Space>
        }
        toolbar={
          <div className="flex w-full flex-wrap items-center gap-2">
            <Input
              allowClear
              prefix={<SearchOutlined className="text-[var(--color-stone)]" />}
              placeholder="搜索角色名称或编码"
              value={roleKeyword}
              onChange={(event) => setRoleKeyword(event.target.value)}
              style={{ width: 240 }}
            />
            <span className="text-[12px] text-[var(--color-steel)]">筛选出 {visibleRoles.length} 个</span>
          </div>
        }
        className={SECTION_CARD_CLASS}
      >
        <Table
          rowKey="id"
          size="small"
          loading={rolesLoading}
          columns={roleColumns}
          dataSource={visibleRoles}
          scroll={{ x: 'max-content' }}
          rowClassName="module-perm-row"
          pagination={{ pageSize: 10, size: 'small', hideOnSinglePage: true, showSizeChanger: false }}
          locale={{
            emptyText: roles.length === 0 ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="还没有岗位角色"
              >
                <Button size="small" type="primary" disabled={!canManage} onClick={openCreateRole}>
                  新建第一个角色
                </Button>
              </Empty>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的角色，换个关键词试试" />
            ),
          }}
        />
      </SettingsListCard>

      <SettingsListCard
        title="授权"
        extra={
          <Space size={8} wrap>
            <span className="text-[12px] text-[var(--color-steel)]">共 {grants.length} 条</span>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!canManage || grantableRoles.length === 0}
              onClick={() => setGrantModalOpen(true)}
            >
              新建授权
            </Button>
          </Space>
        }
        toolbar={
          <div className="flex w-full flex-wrap items-center gap-2">
            <Input
              allowClear
              prefix={<SearchOutlined className="text-[var(--color-stone)]" />}
              placeholder="搜索用户或角色"
              value={grantKeyword}
              onChange={(event) => setGrantKeyword(event.target.value)}
              style={{ width: 240 }}
            />
            <Select
              value={grantStatus}
              options={GRANT_STATUS_OPTIONS}
              onChange={setGrantStatus}
              style={{ width: 140 }}
            />
            <span className="text-[12px] text-[var(--color-steel)]">筛选出 {visibleGrants.length} 条</span>
          </div>
        }
        className={SECTION_CARD_CLASS}
      >
        <Table
          rowKey="id"
          size="small"
          loading={grantsLoading}
          columns={grantColumns}
          dataSource={visibleGrants}
          scroll={{ x: 'max-content' }}
          rowClassName="module-perm-row"
          pagination={{ pageSize: 10, size: 'small', hideOnSinglePage: true, showSizeChanger: false }}
          locale={{
            emptyText: grants.length === 0 ? (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="还没有授权">
                <Button
                  size="small"
                  type="primary"
                  disabled={!canManage || grantableRoles.length === 0}
                  onClick={() => setGrantModalOpen(true)}
                >
                  新建授权
                </Button>
              </Empty>
            ) : (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有匹配的授权，换个关键词试试" />
            ),
          }}
        />
      </SettingsListCard>

      <RoleEditModal
        open={roleModalOpen}
        moduleCode={moduleCode}
        moduleTree={moduleTree}
        treeError={treeError}
        editingRole={editingRole}
        onClose={() => setRoleModalOpen(false)}
        onSaved={refreshRoles}
      />

      <GrantCreateModal
        open={grantModalOpen}
        grantableRoles={grantableRoles}
        onClose={() => setGrantModalOpen(false)}
        onSaved={refreshGrants}
      />
    </div>
  )
}
