'use client'

import { useState, type Key } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Alert,
  App,
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Result,
  Select,
  Space,
  Table,
  Tag,
} from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import {
  batchDeleteRoles,
  batchUpdateRoleStatus,
  createRole,
  deleteRole,
  fetchPermissionTree,
  fetchRoles,
  updateRole,
} from '@/actions/permission'
import PermissionTreePanel from './PermissionTreePanel'
import { SettingsListCard } from './SettingsListCard'
import { BatchActionBar, BatchDeleteConfirmModal, BatchResultModal } from './BatchOperations'
import type { BatchResult, RoleCreateInput, RoleDetail, RoleUpdateInput } from '@/types/permission'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'

const categoryOptions = [
  { value: 'platform', label: '平台角色' },
  { value: 'module', label: '模块角色' },
]

// 模块角色的编码档位（与后端 registry 的 MODULE_ROLE_ACTIONS 对齐）
const suffixOptions = [
  { value: 'admin', label: '管理员（admin）' },
  { value: 'operator', label: '操作员（operator）' },
  { value: 'approver', label: '审批员（approver）' },
  { value: 'viewer', label: '只读（viewer）' },
]

export default function RoleManagementClient() {
  const { message } = App.useApp()

  // 权限：无「角色管理」权限时隐藏全部写操作入口
  // （前端隐藏只是体验优化，后端 require_permission 仍会拦截绕过前端的调用）
  // 注意：必须放在任何 early return 之前
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.roleManage)
  const queryClient = useQueryClient()
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<RoleDetail | null>(null)
  const [saving, setSaving] = useState(false)
  const [keyword, setKeyword] = useState('')
  // 批量操作：选中项 + 结果汇总 + 删除强确认
  const [selectedRowKeys, setSelectedRowKeys] = useState<Key[]>([])
  const [batching, setBatching] = useState(false)
  const [batchResult, setBatchResult] = useState<BatchResult | null>(null)
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [form] = Form.useForm()

  const category = Form.useWatch('category', form)
  const moduleCode = Form.useWatch('module_code', form)
  const suffix = Form.useWatch('code_suffix', form)

  const { data: roles = [], isLoading, error: rolesError } = useQuery({
    queryKey: ['permission-roles'],
    queryFn: fetchRoles,
  })

  const { data: treeData, isLoading: treeLoading, error: treeError } = useQuery({
    queryKey: ['permission-tree'],
    queryFn: fetchPermissionTree,
  })
  const tree = treeData?.tree ?? []

  const permissionError = rolesError ?? treeError
  if (permissionError) {
    return (
      <Result
        status="403"
        title="无权限访问角色管理"
        subTitle={
          permissionError instanceof Error ? permissionError.message : '请联系管理员为你授权'
        }
      />
    )
  }

  // 模块下拉：取自权限树的业务模块节点（含尚未接入权限码的模块）
  const moduleOptions = tree.flatMap((node) =>
    node.type === 'module' && node.kind === 'business' && node.code
      ? [{ value: node.code, label: node.title }]
      : [],
  )
  const moduleLabels = new Map(moduleOptions.map((option) => [option.value, option.label]))

  // 列表搜索：角色编码 / 名称 / 所属模块 / 说明（角色总量不大，前端过滤即可）
  const query = keyword.trim().toLowerCase()
  const visibleRoles = query
    ? roles.filter((role) =>
        [
          role.code,
          role.name,
          role.module_code ? (moduleLabels.get(role.module_code) ?? role.module_code) : '',
          role.description,
        ].some((value) => (value ?? '').toLowerCase().includes(query)),
      )
    : roles

  // 内置角色 / 超管：权限由代码注册表决定，界面只读
  const permissionsReadonly = Boolean(editing && (editing.is_builtin || editing.is_superuser))

  const handleOpen = (record: RoleDetail | null) => {
    setEditing(record)
    form.resetFields()
    if (record) {
      form.setFieldsValue({
        name: record.name,
        description: record.description,
        permission_codes: record.permission_codes,
      })
    } else {
      form.setFieldsValue({ category: 'module', permission_codes: [] })
    }
    setModalOpen(true)
  }

  const handleSave = async () => {
    const values = await form.validateFields().catch(() => null)
    if (!values) return // 表单校验失败：antd 已在字段上提示
    setSaving(true)
    try {
      if (editing) {
        const payload: RoleUpdateInput = {
          name: values.name,
          description: values.description || null,
        }
        if (!permissionsReadonly) payload.permission_codes = values.permission_codes ?? []
        const result = await updateRole(editing.id, payload)
        if (!result.ok) {
          message.error(result.message)
          return
        }
        message.success('角色已更新')
      } else {
        const isModuleRole = values.category === 'module'
        const payload: RoleCreateInput = {
          code: isModuleRole ? `${values.module_code}:${values.code_suffix}` : values.code,
          name: values.name,
          category: values.category,
          module_code: isModuleRole ? values.module_code : null,
          description: values.description || null,
          permission_codes: values.permission_codes ?? [],
        }
        const result = await createRole(payload)
        if (!result.ok) {
          message.error(result.message)
          return
        }
        message.success('角色已创建')
      }
      setModalOpen(false)
      queryClient.invalidateQueries({ queryKey: ['permission-roles'] })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (record: RoleDetail) => {
    const result = await deleteRole(record.id)
    if (!result.ok) {
      message.error(result.message)
      return
    }
    message.success('角色已删除')
    queryClient.invalidateQueries({ queryKey: ['permission-roles'] })
  }

  const clearSelection = () => setSelectedRowKeys([])

  /** 批量启用 / 停用：内置与超管角色在前端已不可选，后端仍会逐条校验。 */
  const handleBatchStatus = async (status: 'active' | 'disabled') => {
    if (!selectedRowKeys.length) return
    setBatching(true)
    try {
      const result = await batchUpdateRoleStatus(selectedRowKeys.map(String), status)
      if (!result.ok) {
        message.error(result.message)
        return
      }
      setBatchResult(result.data)
      clearSelection()
      queryClient.invalidateQueries({ queryKey: ['permission-roles'] })
      queryClient.invalidateQueries({ queryKey: ['permission-tree'] })
      if (!result.data.failed.length) {
        message.success(`已${status === 'active' ? '启用' : '停用'} ${result.data.succeeded.length} 个角色`)
      }
    } finally {
      setBatching(false)
    }
  }

  /** 批量删除：弹窗列出影响项 + 输入「删除」确认。 */
  const handleBatchDelete = async () => {
    if (!selectedRowKeys.length) return
    setBatching(true)
    try {
      const result = await batchDeleteRoles(selectedRowKeys.map(String))
      if (!result.ok) {
        message.error(result.message)
        return
      }
      setDeleteConfirmOpen(false)
      setBatchResult(result.data)
      clearSelection()
      queryClient.invalidateQueries({ queryKey: ['permission-roles'] })
      queryClient.invalidateQueries({ queryKey: ['permission-tree'] })
    } finally {
      setBatching(false)
    }
  }

  // 内置 / 超管角色不能改状态也不能删除，直接不允许勾选
  const rowSelection = canManage
    ? {
        selectedRowKeys,
        onChange: (keys: Key[]) => setSelectedRowKeys(keys),
        getCheckboxProps: (record: RoleDetail) => ({
          disabled: Boolean(record.is_builtin || record.is_superuser),
        }),
      }
    : undefined

  const selectedRoles = roles.filter((role) => selectedRowKeys.some((key) => String(key) === role.id))

  const columns = [
    { title: '角色编码', dataIndex: 'code', width: 200 },
    { title: '名称', dataIndex: 'name', width: 180 },
    {
      title: '类型',
      dataIndex: 'category',
      width: 110,
      render: (value: string) => (
        <Tag color={value === 'platform' ? 'purple' : 'blue'}>
          {value === 'platform' ? '平台角色' : '模块角色'}
        </Tag>
      ),
    },
    {
      title: '模块',
      dataIndex: 'module_code',
      width: 140,
      render: (value: string | null) =>
        value ? (moduleLabels.get(value) ?? value) : '-',
    },
    {
      title: '权限数',
      key: 'permCount',
      width: 90,
      render: (_: unknown, record: RoleDetail) => record.permission_codes.length,
    },
    {
      title: '内置',
      dataIndex: 'is_builtin',
      width: 80,
      render: (value: boolean) => (value ? <Tag color="gold">内置</Tag> : '-'),
    },
    // 操作列：无管理权限时整列不出现
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'actions',
            width: 160,
            fixed: 'right' as const,
            render: (_: unknown, record: RoleDetail) => (
              <Space>
                <Button size="small" onClick={() => handleOpen(record)}>
                  编辑
                </Button>
                {!record.is_builtin && (
                  <Popconfirm title="确认删除该角色？" onConfirm={() => handleDelete(record)}>
                    <Button size="small" danger>
                      删除
                    </Button>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]
      : []),
  ]

  return (
    <div className="space-y-4">
      <div>
        <h2 className="m-0 text-[20px] font-semibold text-[var(--color-charcoal)]">角色管理</h2>
        <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">
          角色编码由「模块 + 档位」生成（也可手填平台角色编码），权限在目录树上勾选；内置角色只剩超级管理员，不可删除。
        </p>
      </div>

      <SettingsListCard
        toolbar={
          <>
            <BatchActionBar count={selectedRowKeys.length} loading={batching} onClear={clearSelection}>
              <Button size="small" loading={batching} onClick={() => handleBatchStatus('active')}>
                批量启用
              </Button>
              <Button size="small" loading={batching} onClick={() => handleBatchStatus('disabled')}>
                批量停用
              </Button>
              <Button size="small" danger loading={batching} onClick={() => setDeleteConfirmOpen(true)}>
                批量删除
              </Button>
            </BatchActionBar>
            <div className="w-full sm:w-[260px]">
              <Input.Search
                allowClear
                placeholder="搜索角色编码、名称、模块"
                style={{ width: '100%' }}
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
              />
            </div>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => queryClient.invalidateQueries({ queryKey: ['permission-roles'] })}
            >
              刷新
            </Button>
            {canManage && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => handleOpen(null)}>
                新建角色
              </Button>
            )}
          </>
        }
      >
        <Table
          columns={columns}
          dataSource={visibleRoles}
          rowKey="id"
          loading={isLoading}
          rowSelection={rowSelection}
          scroll={{ x: 1000 }}
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </SettingsListCard>

      <BatchResultModal result={batchResult} onClose={() => setBatchResult(null)} />
      <BatchDeleteConfirmModal
        open={deleteConfirmOpen}
        items={selectedRoles.map((role) => ({ key: role.id, label: `${role.name}（${role.code}）` }))}
        loading={batching}
        onCancel={() => setDeleteConfirmOpen(false)}
        onConfirm={handleBatchDelete}
      />

      <Modal
        title={editing ? '编辑角色' : '新建角色'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        width="min(780px, calc(100vw - 24px))"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {editing ? (
            <Space size="large" align="start" wrap>
              <Form.Item label="角色编码" style={{ width: '100%', maxWidth: 260 }}>
                <Input value={editing.code} disabled />
              </Form.Item>
              <Form.Item label="角色类型" style={{ width: '100%', maxWidth: 200 }}>
                <Input
                  value={editing.category === 'platform' ? '平台角色' : '模块角色'}
                  disabled
                />
              </Form.Item>
            </Space>
          ) : (
            <>
              <Form.Item
                name="category"
                label="角色类型"
                rules={[{ required: true, message: '请选择角色类型' }]}
                style={{ width: '100%', maxWidth: 220 }}
              >
                <Select
                  options={categoryOptions}
                  onChange={(value) => {
                    if (value === 'platform') {
                      form.setFieldsValue({ module_code: undefined, code_suffix: undefined })
                    }
                  }}
                />
              </Form.Item>

              {category !== 'platform' ? (
                <Space size="large" align="start" wrap>
                  <Form.Item
                    name="module_code"
                    label="所属模块"
                    rules={[{ required: true, message: '请选择模块' }]}
                    style={{ width: '100%', maxWidth: 220 }}
                  >
                    <Select
                      options={moduleOptions}
                      placeholder="选择业务模块"
                      showSearch
                      optionFilterProp="label"
                    />
                  </Form.Item>
                  <Form.Item
                    name="code_suffix"
                    label="角色档位"
                    rules={[{ required: true, message: '请选择档位' }]}
                    style={{ width: '100%', maxWidth: 200 }}
                  >
                    <Select options={suffixOptions} placeholder="选择档位" />
                  </Form.Item>
                  <Form.Item label="角色编码（自动生成）" style={{ width: '100%', maxWidth: 260 }}>
                    <Input
                      value={moduleCode && suffix ? `${moduleCode}:${suffix}` : ''}
                      disabled
                      placeholder="选择模块与档位后生成"
                    />
                  </Form.Item>
                </Space>
              ) : (
                <Form.Item
                  name="code"
                  label="角色编码"
                  rules={[{ required: true, message: '请输入角色编码' }]}
                  extra="平台角色编码无固定规律，如 permission_admin"
                >
                  <Input placeholder="如 permission_admin" />
                </Form.Item>
              )}
            </>
          )}

          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: '请输入角色名称' }]}
          >
            <Input placeholder="如 质量管理员" />
          </Form.Item>

          <Form.Item name="description" label="说明">
            <Input.TextArea rows={2} placeholder="角色用途说明" />
          </Form.Item>

          {permissionsReadonly && (
            <Alert
              type="info"
              showIcon
              className="mb-3"
              title={
                editing?.is_superuser
                  ? '超级管理员按「直接放行」判定，不需要权限码'
                  : '内置角色的权限由代码注册表（registry.py）定义，界面不可修改'
              }
            />
          )}

          <Form.Item name="permission_codes" label="权限配置（按模块 / 功能勾选）">
            <PermissionTreePanel tree={tree} disabled={permissionsReadonly || treeLoading} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
