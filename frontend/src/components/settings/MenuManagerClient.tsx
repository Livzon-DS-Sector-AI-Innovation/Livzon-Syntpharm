'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import {
  App,
  Button,
  Card,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import { CheckOutlined, EditOutlined, PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { moduleMenus, type SubMenuItem } from '@/lib/menu-config'
import { getMenuConfig, saveMenuConfig } from '@/actions/menu'
import { fetchPermissions } from '@/actions/permission'
import { MODULE_ACCESS_PERMS, SUBMENU_ACCESS_PERMS } from '@/lib/permissions/modules'
import { CUSTOM_DEFAULT_SORT, PROTECTED_MENU_KEYS } from '@/lib/menu/resolve'
import { isKnownRoute } from '@/lib/navigation/known-routes'
import type { CustomMenuItem, MenuConfigData, MenuItemOverride } from '@/types/menu-admin'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'

const { Text } = Typography
const SORT_STEP = 10

const ICON_OPTIONS = [
  { value: 'link', label: '链接' },
  { value: 'dashboard', label: '仪表盘' },
  { value: 'chart', label: '图表' },
  { value: 'check-circle', label: '对勾' },
  { value: 'experiment', label: '实验' },
  { value: 'file-text', label: '文档' },
  { value: 'team', label: '团队' },
  { value: 'setting', label: '设置' },
  { value: 'shopping-cart', label: '采购' },
  { value: 'database', label: '数据库' },
  { value: 'global', label: '地球' },
]

/** 表格里的行（树形：模块 → 子菜单，支持折叠展开） */
interface MenuRow {
  key: string
  level: number
  label: string
  /** 代码里的默认名：用于判断是否被改过，以及「清空名称」= 恢复默认 */
  defaultLabel: string
  path: string
  icon: string
  isCustom: boolean
  parent: string | null
  visible: boolean
  sort: number
  perms: string[]
  defaultSort: number
  defaultPerms: readonly string[]
  children?: MenuRow[]
}

const bySortThenDefault = (a: MenuRow, b: MenuRow) => a.sort - b.sort || a.defaultSort - b.defaultSort

function makeBuiltinMenuNode(item: SubMenuItem, level: number, index: number, config: MenuConfigData): MenuRow {
  const override = config.items[item.key]
  const defaultSort = (index + 1) * SORT_STEP
  const defaultPerms = level === 0 ? (MODULE_ACCESS_PERMS[item.key] ?? []) : (SUBMENU_ACCESS_PERMS[item.key] ?? [])

  const children = collectBuiltinChildren(item.children ?? [], item.key, level + 1, config).concat(
    config.custom.filter((c) => c.parent === item.key).map((c, i) => makeCustomNode(c, level + 1, i)),
  )

  return {
    key: item.key,
    level,
    label: override?.label?.trim() ? override.label : item.label,
    defaultLabel: item.label,
    path: item.path,
    icon: 'link',
    isCustom: false,
    parent: null,
    visible: override?.visible !== false,
    sort: typeof override?.sort === 'number' ? override.sort : defaultSort,
    perms: override?.perms ? [...override.perms] : [...defaultPerms],
    defaultSort,
    defaultPerms,
    children: children.length > 0 ? children.sort(bySortThenDefault) : undefined,
  }
}

function collectBuiltinChildren(
  items: SubMenuItem[],
  parentKey: string,
  level: number,
  config: MenuConfigData,
): MenuRow[] {
  return items.map((item, index) => {
    const node = makeBuiltinMenuNode(item, level, index, config)
    return { ...node, parent: parentKey }
  })
}

function makeCustomNode(item: CustomMenuItem, level: number, index: number): MenuRow {
  return {
    key: item.id,
    level,
    label: item.title,
    // 自定义项的名称就是它自己的配置，没有「代码默认」概念
    defaultLabel: item.title,
    path: item.path,
    icon: item.icon,
    isCustom: true,
    parent: item.parent,
    visible: item.visible,
    sort: item.sort,
    perms: [...item.perms],
    defaultSort: CUSTOM_DEFAULT_SORT + index,
    defaultPerms: [],
  }
}

/** 构建树形数据：每层按生效权重排序（与导航渲染顺序一致），模块 / 自定义项都支持折叠 */
function buildTree(config: MenuConfigData): MenuRow[] {
  const nodes: MenuRow[] = moduleMenus.map((mod, index) => {
    const override = config.items[mod.key]
    const defaultSort = (index + 1) * SORT_STEP
    const defaultPerms = MODULE_ACCESS_PERMS[mod.key] ?? []
    const children = collectBuiltinChildren(mod.children, mod.key, 1, config).concat(
      config.custom.filter((c) => c.parent === mod.key).map((c, i) => makeCustomNode(c, 1, i)),
    )
    return {
      key: mod.key,
      level: 0,
      label: override?.label?.trim() ? override.label : mod.label,
      defaultLabel: mod.label,
      path: mod.path,
      icon: mod.icon,
      isCustom: false,
      parent: null,
      visible: override?.visible !== false,
      sort: typeof override?.sort === 'number' ? override.sort : defaultSort,
      perms: override?.perms ? [...override.perms] : [...defaultPerms],
      defaultSort,
      defaultPerms,
      children: children.length > 0 ? children.sort(bySortThenDefault) : undefined,
    }
  })

  config.custom
    .filter((c) => c.parent === null)
    .forEach((c, index) => nodes.push(makeCustomNode(c, 0, index)))

  return nodes.sort(bySortThenDefault)
}

/** 递归抽取保存所需的 items / custom */
function extract(nodes: MenuRow[], items: Record<string, MenuItemOverride>, custom: CustomMenuItem[]): void {
  nodes.forEach((node) => {
    if (node.isCustom) {
      custom.push({
        id: node.key,
        parent: node.parent,
        title: node.label,
        path: node.path,
        icon: node.icon,
        sort: node.sort,
        perms: node.perms,
        visible: node.visible,
      })
    } else {
      const override: MenuItemOverride = {}
      if (!node.visible) override.visible = false
      if (node.sort !== node.defaultSort) override.sort = node.sort
      // 名称：偏离代码默认名时才写（改成空 = 恢复默认，不写 override）
      if (node.label.trim() && node.label !== node.defaultLabel) override.label = node.label
      const samePerms =
        JSON.stringify([...node.perms].sort()) === JSON.stringify([...node.defaultPerms].sort())
      if (!samePerms) override.perms = node.perms
      if (Object.keys(override).length > 0) items[node.key] = override
    }
    if (node.children) extract(node.children, items, custom)
  })
}

/**
 * 补全「父级上下文」。
 *
 * 后端校验要求：自定义项的父级必须可识别（同一批次的其它自定义项 id、或 items 里出现过的内置 key）。
 * 而 `extract` 只在**菜单项有覆盖**时才把它写进 items —— 于是往一个「从没改过」的模块下挂自定义项时，
 * 该模块不在 items 里，后端会误报「父级不存在」。这里把被当作父级的内置 key 补一个空 override。
 */
function ensureBuiltinParents(
  nodes: MenuRow[],
  items: Record<string, MenuItemOverride>,
  custom: CustomMenuItem[],
): void {
  const builtinKeys = new Set<string>()
  const walk = (list: MenuRow[]) => {
    list.forEach((node) => {
      if (!node.isCustom) builtinKeys.add(node.key)
      if (node.children) walk(node.children)
    })
  }
  walk(nodes)

  const customIds = new Set(custom.map((item) => item.id))
  custom.forEach((item) => {
    const parent = item.parent
    if (parent && builtinKeys.has(parent) && !customIds.has(parent) && !(parent in items)) {
      items[parent] = {}
    }
  })
}

/** 由当前树生成完整配置（含父级上下文补全） */
function buildConfig(rows: MenuRow[]): MenuConfigData {
  const items: Record<string, MenuItemOverride> = {}
  const custom: CustomMenuItem[] = []
  extract(rows, items, custom)
  ensureBuiltinParents(rows, items, custom)
  return { items, custom }
}

export default function MenuManagerClient() {
  const { message, modal } = App.useApp()
  const router = useRouter()
  // 注意：hook 必须写在任何 early return 之前
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.opsManage)

  // 查看 / 编辑模式：查看模式下整表只读，点「编辑」后逐项修改并立即提交（没有全局保存）
  const [mode, setMode] = useState<'view' | 'edit'>('view')
  const [editRow, setEditRow] = useState<MenuRow | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const [committing, setCommitting] = useState(false)
  // 展开态：默认**全部折叠**，用户手动展开/收起后保留
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])
  const [createForm] = Form.useForm()
  const [editForm] = Form.useForm()

  const { data: config, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['menu-config'],
    queryFn: getMenuConfig,
  })

  // 权限目录：用于把权限码渲染成中文名称（与「权限目录」Tab 共用同一份缓存）。
  // 读不到目录（如当前账号没有权限目录读权限）时不阻塞菜单编辑，回退显示权限码。
  const { data: permissions = [] } = useQuery({
    queryKey: ['permission-catalog'],
    queryFn: async () => {
      try {
        return await fetchPermissions()
      } catch {
        return []
      }
    },
  })

  /** 权限码 → 名称；目录里没有该码（如预留的业务权限码）时原样显示权限码 */
  const permNameByCode = useMemo(
    () => new Map(permissions.map((item) => [item.code, item.name])),
    [permissions],
  )
  const permLabel = (code: string) => permNameByCode.get(code) ?? code

  /**
   * 「可见权限」只读展示用的选项：权限目录全部（显示名称，hover 显示权限码）
   * + 该项上已有但目录中还没有的权限码。
   */
  const buildPermOptions = (selected: readonly string[]) => {
    const known = new Set(permissions.map((item) => item.code))
    const extras = selected.filter((code) => !known.has(code))
    return [
      ...extras.map((code) => ({ value: code, label: permLabel(code), title: code })),
      ...permissions.map((item) => ({ value: item.code, label: permLabel(item.code), title: item.code })),
    ]
  }

  const rows = useMemo(() => (config ? buildTree(config) : []), [config])

  /** 可以当父级的选项：模块级（null）+ 内置模块 / 分组 + 自定义项 */
  const parentOptions = useMemo(
    () => [
      { value: '__root__', label: '（模块级 → 顶部一个 Tab）' },
      ...collectFlatOptions(rows),
    ],
    [rows],
  )

  /** 菜单 key → 该菜单的路径（新建时用来给父级路径前缀） */
  const parentPathByKey = useMemo(() => {
    const map = new Map<string, string>()
    const walk = (list: MenuRow[]) => {
      list.forEach((node) => {
        map.set(node.key, node.path)
        if (node.children) walk(node.children)
      })
    }
    walk(rows)
    return map
  }, [rows])

  // 新建时选中的父级路径：非空表示「跳转路径只能加在它后面」
  const createParentKey = Form.useWatch('parent', createForm) as string | undefined
  const createParentPath =
    createParentKey && createParentKey !== '__root__'
      ? (parentPathByKey.get(createParentKey) ?? '').replace(/\/+$/, '')
      : ''

  /** 提交整份配置：行编辑 / 新建 / 删除都走这里，所以不需要全局「保存」按钮 */
  const commit = async (next: MenuConfigData, successMsg: string): Promise<boolean> => {
    setCommitting(true)
    try {
      const result = await saveMenuConfig(next)
      if (!result.ok) {
        message.error(result.message)
        return false
      }
      message.success(successMsg)
      await refetch()
      // 菜单配置影响 dashboard layout（RSC），必须 refresh 才会重新下发 PermissionView
      router.refresh()
      return true
    } finally {
      setCommitting(false)
    }
  }

  /**
   * 路径不在「已知页面清单」里时让用户确认（**只提示不阻止**）。
   * 不阻止的原因：清单是构建期扫描生成的，可能有尚未登记的页面（如别人正在开发的）。
   */
  const confirmUnknownPath = async (path: string): Promise<boolean> => {
    if (!path.startsWith('/') || isKnownRoute(path)) return true
    return new Promise<boolean>((resolve) => {
      modal.confirm({
        title: '该路径没有对应页面',
        content: `未在已知页面清单里找到 ${path}，创建/保存后点击该菜单会打开 404 页。仍要继续吗？`,
        okText: '仍然继续',
        okType: 'danger',
        cancelText: '返回修改',
        onOk: () => resolve(true),
        onCancel: () => resolve(false),
      })
    })
  }

  const openRowEdit = (row: MenuRow) => {
    setEditRow(row)
    editForm.setFieldsValue({
      label: row.label,
      path: row.path,
      icon: row.icon,
      visible: row.visible,
      sort: row.sort,
      perms: row.perms,
    })
  }

  const applyRowEdit = async () => {
    if (!editRow) return
    const values = await editForm.validateFields().catch(() => null)
    if (!values) return

    // 自定义项改了路径 → 同样做一次「有没有对应页面」的提示
    if (editRow.isCustom) {
      const nextPath = String(values.path ?? '').trim()
      if (nextPath !== editRow.path && !(await confirmUnknownPath(nextPath))) return
    }

    const next = buildConfig(rows)

    if (editRow.isCustom) {
      const index = next.custom.findIndex((c) => c.id === editRow.key)
      if (index >= 0) {
        next.custom[index] = {
          ...next.custom[index],
          title: values.label,
          path: values.path,
          icon: values.icon || 'link',
          visible: values.visible !== false,
          sort: typeof values.sort === 'number' ? values.sort : next.custom[index].sort,
          perms: values.perms ?? [],
        }
      }
    } else {
      const override: MenuItemOverride = { ...(next.items[editRow.key] ?? {}) }

      // 显示：改回「显示」= 默认行为 → 删掉覆盖，保持配置干净
      if (values.visible) delete override.visible
      else override.visible = false

      // 名称：清空 = 恢复代码默认名
      const label = String(values.label ?? '').trim()
      if (label && label !== editRow.defaultLabel) override.label = label
      else delete override.label

      // 排列权重：与代码顺序一致时不写覆盖
      if (typeof values.sort === 'number' && values.sort !== editRow.defaultSort) {
        override.sort = values.sort
      } else {
        delete override.sort
      }

      // 可见范围：与代码默认一致时不写覆盖（显式 [] = 不限制）
      const perms: string[] = values.perms ?? []
      const samePerms =
        JSON.stringify([...perms].sort()) === JSON.stringify([...editRow.defaultPerms].sort())
      if (samePerms) delete override.perms
      else override.perms = perms

      if (Object.keys(override).length > 0) next.items[editRow.key] = override
      else delete next.items[editRow.key]
    }

    if (await commit(next, '菜单已更新')) setEditRow(null)
  }

  const handleCreate = async () => {
    const values = await createForm.validateFields().catch(() => null)
    if (!values) return

    const parent = values.parent === '__root__' ? null : values.parent
    const suffix = String(values.path ?? '').trim()
    // 选了父级 → 最终路径 = 父级路径 + 用户填的名称段；
    // 容错：用户直接粘贴了完整路径（已含父级前缀）时不重复拼接。
    const basePath = parent ? (parentPathByKey.get(parent) ?? '').replace(/\/+$/, '') : ''
    const finalPath = (() => {
      if (!basePath) return suffix
      if (suffix === basePath || suffix.startsWith(`${basePath}/`)) return suffix
      return `${basePath}/${suffix.replace(/^\/+/, '')}`
    })()

    // 路径没有对应页面 → 先提示（不阻止保存）
    if (!(await confirmUnknownPath(finalPath))) return

    const next = buildConfig(rows)
    next.custom = [
      ...next.custom,
      {
        id: `cm_${Date.now().toString(36)}`,
        parent,
        title: values.title,
        path: finalPath,
        icon: values.icon || 'link',
        sort: typeof values.sort === 'number' ? values.sort : CUSTOM_DEFAULT_SORT,
        perms: values.perms ?? [],
        visible: values.visible !== false,
      },
    ]
    // 注意：buildConfig 里的父级补全只覆盖「新增之前」就存在的自定义项，
    // 新项的父级（可能是从没被改过的内置模块，如 settings）必须在这里再补一次，
    // 否则后端会报「自定义菜单项「xx」的父级不存在」。
    ensureBuiltinParents(rows, next.items, next.custom)

    if (await commit(next, '自定义菜单已创建')) setCreateOpen(false)
  }

  const handleDeleteCustom = async (key: string) => {
    const next = buildConfig(rows)
    next.custom = next.custom.filter((item) => item.id !== key)
    await commit(next, '自定义菜单已删除')
  }

  const columns = [
    {
      title: '菜单项',
      key: 'label',
      render: (_: unknown, row: MenuRow) => (
        <div className="flex items-center gap-2">
          <span className="text-[var(--color-charcoal)]">{row.label}</span>
          {!row.isCustom && row.label !== row.defaultLabel && (
            <Text className="text-[12px] text-[var(--color-steel)]">（原名：{row.defaultLabel}）</Text>
          )}
          {row.isCustom && <Tag color="blue">自定义</Tag>}
          {!row.isCustom && row.children && <Tag>分组</Tag>}
        </div>
      ),
    },
    {
      title: '路径 / 编码',
      key: 'path',
      width: 240,
      render: (_: unknown, row: MenuRow) => (
        <Text className="text-[12px] text-[var(--color-steel)]">{row.path || row.key}</Text>
      ),
    },
    {
      title: '显示',
      key: 'visible',
      width: 90,
      render: (_: unknown, row: MenuRow) =>
        row.visible ? <Tag color="green">显示</Tag> : <Tag>隐藏</Tag>,
    },
    {
      title: '排列权重',
      dataIndex: 'sort',
      width: 100,
      align: 'right' as const,
    },
    {
      title: '可见范围',
      key: 'perms',
      width: 380,
      render: (_: unknown, row: MenuRow) =>
        row.perms.length > 0 ? (
          <Space size={4} wrap>
            {row.perms.map((code) => (
              <Tag color="blue" key={code} title={code}>
                {permLabel(code)}
              </Tag>
            ))}
          </Space>
        ) : (
          <Text className="text-[12px] text-[var(--color-steel)]">不限制</Text>
        ),
    },
    // 操作列只在编辑模式出现
    ...(canManage && mode === 'edit'
      ? [
          {
            title: '操作',
            key: 'actions',
            width: 150,
            fixed: 'right' as const,
            render: (_: unknown, row: MenuRow) => (
              <Space>
                <Button size="small" icon={<EditOutlined />} onClick={() => openRowEdit(row)}>
                  编辑
                </Button>
                {row.isCustom && (
                  <Popconfirm
                    title="确认删除该自定义菜单项？"
                    onConfirm={() => handleDeleteCustom(row.key)}
                    okText="删除"
                    cancelText="取消"
                  >
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
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Text className="text-[13px] text-[var(--color-steel)]">
          权重数字越小排越前；「显示」关掉后所有人（含超管）都看不到该项 —— 系统管理入口、系统设置与菜单管理本身受保护，不可隐藏。
          {mode === 'view' ? '点「编辑」后可逐项修改（改完立即生效）。' : '编辑模式下逐项修改，改完立即生效。'}
        </Text>
        <Space wrap>
          <Button
            icon={<ReloadOutlined />}
            loading={isFetching}
            onClick={() => {
              setExpandedKeys([])
              void refetch()
            }}
          >
            刷新
          </Button>
          {canManage && mode === 'edit' && (
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                createForm.resetFields()
                createForm.setFieldsValue({
                  parent: '__root__',
                  icon: 'link',
                  visible: true,
                  sort: CUSTOM_DEFAULT_SORT,
                  perms: [],
                })
                setCreateOpen(true)
              }}
            >
              新增自定义菜单
            </Button>
          )}
          {canManage &&
            (mode === 'view' ? (
              <Button type="primary" icon={<EditOutlined />} onClick={() => setMode('edit')}>
                编辑
              </Button>
            ) : (
              <Button type="primary" icon={<CheckOutlined />} onClick={() => setMode('view')}>
                完成
              </Button>
            ))}
        </Space>
      </div>

      <Card className="[&_.ant-table]:!m-0">
      <Table
        rowKey="key"
        columns={columns}
        dataSource={rows}
        loading={isLoading}
        pagination={false}
        size="small"
        scroll={{ x: 1050 }}
        expandable={{
          // 默认全部折叠；展开状态受控（避免在 effect 里 setState）
          expandedRowKeys: expandedKeys,
          onExpandedRowsChange: (keys) => setExpandedKeys(keys.map(String)),
          indentSize: 18,
        }}
      />
      </Card>

      {/* 行编辑：改完立即提交，无需全局保存 */}
      <Modal
        title={
          editRow?.isCustom ? `编辑自定义菜单：${editRow.label}` : `编辑菜单项：${editRow?.label ?? ''}`
        }
        open={!!editRow}
        onOk={applyRowEdit}
        onCancel={() => setEditRow(null)}
        confirmLoading={committing}
        okText="确定"
        cancelText="取消"
        width="min(620px, calc(100vw - 24px))"
      >
        <Form form={editForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="label" label="菜单名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="显示在导航里的名称" />
          </Form.Item>
          {editRow?.isCustom ? (
            <>
              <Form.Item
                name="path"
                label="跳转路径"
                rules={[{ required: true, message: '请输入路径' }]}
                extra="以 / 开头的站内路径，或 http(s):// 外部链接"
              >
                <Input placeholder="例如：/quality/dashboard" />
              </Form.Item>
              <Form.Item name="icon" label="图标">
                <Select options={ICON_OPTIONS} />
              </Form.Item>
            </>
          ) : (
            <Form.Item
              label="跳转路径（只读）"
              extra="对应代码里的页面路由，不可修改（改了会指向不存在的页面）"
            >
              <Input value={editRow?.path} disabled />
            </Form.Item>
          )}

          <Space size="large" align="start">
            <Form.Item name="visible" label="显示" valuePropName="checked">
              <Switch disabled={!!editRow && PROTECTED_MENU_KEYS.has(editRow.key)} />
            </Form.Item>
            <Form.Item name="sort" label="排列权重" extra={editRow?.isCustom ? undefined : '数字小排前面（-9999 ~ 9999）'}>
              <InputNumber min={-9999} max={9999} style={{ width: 130 }} />
            </Form.Item>
          </Space>

          <Form.Item
            name="perms"
            label="可见范围"
            extra="留空 = 不限制（名称 / 权限码都能搜）"
          >
            <Select
              mode="tags"
              placeholder="留空 = 不限制"
              options={buildPermOptions(editRow?.perms ?? [])}
              optionFilterProp="label"
              // 名称、权限码都能搜到
              filterOption={(input, option) =>
                String(option?.label ?? '').includes(input) ||
                String(option?.value ?? '').includes(input)
              }
            />
          </Form.Item>
          <Text className="text-[12px] text-[var(--color-steel)]">
            与代码默认一致（权重、权限都没改）时不会写入覆盖项，配置保持干净；改了即生效。
          </Text>
        </Form>
      </Modal>

      {/* 新建自定义菜单 */}
      <Modal
        title="新增自定义菜单项"
        open={createOpen}
        onOk={handleCreate}
        onCancel={() => setCreateOpen(false)}
        confirmLoading={committing}
        okText="创建"
        cancelText="取消"
        width="min(560px, calc(100vw - 24px))"
      >
        <Form form={createForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="parent" label="父级" rules={[{ required: true, message: '请选择父级' }]}>
            <Select options={parentOptions} showSearch optionFilterProp="label" />
          </Form.Item>
          <Form.Item name="title" label="菜单名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="例如：质量看板" />
          </Form.Item>
          <Form.Item
            name="path"
            label="跳转路径"
            rules={[{ required: true, message: '请输入路径名称' }]}
            extra={
              createParentPath
                ? `已选父级，只需填地址名：最终路径 = ${createParentPath}/<你填的名称>`
                : '以 / 开头的站内路径，或 http(s):// 外部链接'
            }
          >
            {createParentPath ? (
              <Input addonBefore={createParentPath} placeholder="例如：test" />
            ) : (
              <Input placeholder="例如：/quality/dashboard" />
            )}
          </Form.Item>
          <Space size="large" align="start" wrap>
            <Form.Item name="icon" label="图标" style={{ width: '100%', maxWidth: 160 }}>
              <Select options={ICON_OPTIONS} />
            </Form.Item>
            <Form.Item name="sort" label="排列权重" style={{ width: '100%', maxWidth: 150 }}>
              <InputNumber min={-9999} max={9999} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="visible" label="显示" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
          <Form.Item name="perms" label="可见范围" extra="留空 = 不限制（名称 / 权限码都能搜）">
            <Select
              mode="tags"
              placeholder="留空 = 不限制"
              options={buildPermOptions([])}
              optionFilterProp="label"
              filterOption={(input, option) =>
                String(option?.label ?? '').includes(input) ||
                String(option?.value ?? '').includes(input)
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

/** 父级下拉选项（层级缩进） */
function collectFlatOptions(nodes: MenuRow[]): Array<{ value: string; label: string }> {
  return nodes.flatMap((node) => [
    { value: node.key, label: `${'— '.repeat(node.level)}${node.label}` },
    ...(node.children ? collectFlatOptions(node.children) : []),
  ])
}
