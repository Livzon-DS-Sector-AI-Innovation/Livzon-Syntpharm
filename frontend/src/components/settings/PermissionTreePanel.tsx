'use client'

import { useMemo, useState } from 'react'
import type { Key } from 'react'
import { Button, Input, Tooltip, Tree, Typography } from 'antd'
import type { DataNode } from 'antd/es/tree'
import type { PermissionTreeNode } from '@/types/permission'
import PermissionApiBindingPopover from './PermissionApiBindingPopover'

const { Text } = Typography

const PERM_PREFIX = 'perm:'

interface PermissionTreePanelProps {
  tree: PermissionTreeNode[]
  value?: string[]
  onChange?: (codes: string[]) => void
  disabled?: boolean
}

/** 收集树中可勾选的权限码（跳过置灰节点）。 */
function collectCodes(nodes: PermissionTreeNode[]): string[] {
  const codes: string[] = []
  for (const node of nodes) {
    if (node.type === 'permission' && node.code && !node.disabled) codes.push(node.code)
    if (node.children?.length) codes.push(...collectCodes(node.children))
  }
  return codes
}

function collectKeys(nodes: PermissionTreeNode[]): string[] {
  const keys: string[] = []
  for (const node of nodes) {
    keys.push(node.key)
    if (node.children?.length) keys.push(...collectKeys(node.children))
  }
  return keys
}

/** 关键字过滤：自身命中保留整棵子树，子节点命中则保留父链。 */
function filterTree(nodes: PermissionTreeNode[], keyword: string): PermissionTreeNode[] {
  const result: PermissionTreeNode[] = []
  for (const node of nodes) {
    const children = node.children?.length ? filterTree(node.children, keyword) : []
    // 中文名、中文说明与权限码都参与匹配；权限码界面上不展示，但仍支持凭码搜到对应项
    const selfHit =
      node.title.toLowerCase().includes(keyword) ||
      (node.code ?? '').toLowerCase().includes(keyword) ||
      (node.description ?? '').toLowerCase().includes(keyword)
    if (selfHit) {
      result.push(node)
    } else if (children.length) {
      result.push({ ...node, children })
    }
  }
  return result
}

function NodeTitle({ node }: { node: PermissionTreeNode }) {
  if (node.type !== 'permission') {
    return (
      <Tooltip title={node.description ?? undefined}>
        <span className={node.disabled ? 'text-[var(--color-muted)]' : 'font-medium'}>
          {node.title}
          {node.disabled && (
            <Text className="ml-2 text-[12px] text-[var(--color-muted)]">待接入</Text>
          )}
        </span>
      </Tooltip>
    )
  }
  // 权限叶子双行：中文名 + 中文说明，界面上不出现英文权限码（点接口数才在浮层里看到）
  return (
    <div className="flex flex-col justify-center py-[2px]">
      <div className="flex items-center">
        <span className="text-[13px] font-medium text-[var(--color-ink)]">{node.title}</span>
        <PermissionApiBindingPopover code={node.code ?? ''} count={node.binding_count ?? 0} />
      </div>
      <div className="max-w-[560px]">
        <span
          className="block truncate text-[12px] text-[var(--color-steel)]"
          title={node.description ?? undefined}
        >
          {node.description}
        </span>
      </div>
    </div>
  )
}

function toTreeData(nodes: PermissionTreeNode[]): DataNode[] {
  return nodes.map((node) => ({
    key: node.key,
    disabled: node.disabled,
    title: <NodeTitle node={node} />,
    children: node.children?.length ? toTreeData(node.children) : undefined,
  }))
}

/**
 * 权限目录树选择面板（模块 → 资源 → 权限码），遵循 antd Form 的 value / onChange 协议。
 * 提交时只取叶子权限码；父节点仅作分组。
 */
export default function PermissionTreePanel({
  tree,
  value = [],
  onChange,
  disabled = false,
}: PermissionTreePanelProps) {
  const [keyword, setKeyword] = useState('')
  const [manualExpanded, setManualExpanded] = useState<string[]>(['module:platform'])

  const filteredTree = useMemo(
    () => (keyword ? filterTree(tree, keyword) : tree),
    [tree, keyword],
  )
  const treeData = useMemo(() => toTreeData(filteredTree), [filteredTree])
  const allCodes = useMemo(() => collectCodes(tree), [tree])
  // 搜索时自动展开命中路径（派生值，避免在 effect 里 setState）
  const expandedKeys = keyword ? collectKeys(filteredTree) : manualExpanded

  const checkedKeys = value.map((code) => `${PERM_PREFIX}${code}`)

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <div className="w-full sm:w-[220px]">
          <Input.Search
            allowClear
            placeholder="搜索模块 / 功能 / 说明"
            style={{ width: '100%' }}
            onChange={(event) => setKeyword(event.target.value.trim().toLowerCase())}
          />
        </div>
        <Button size="small" disabled={disabled} onClick={() => onChange?.(allCodes)}>
          全选
        </Button>
        <Button size="small" disabled={disabled} onClick={() => onChange?.([])}>
          清空
        </Button>
        <Text className="text-[12px] text-[var(--color-steel)]">
          已选 {value.length} / {allCodes.length} 项
        </Text>
      </div>

      <div className="rounded-md border border-[var(--color-hairline)] p-2">
        <Tree
          checkable
          disabled={disabled}
          treeData={treeData}
          checkedKeys={checkedKeys}
          expandedKeys={expandedKeys}
          onExpand={(keys) => setManualExpanded(keys as string[])}
          onCheck={(checked) => {
            const keys: Key[] = Array.isArray(checked) ? checked : checked.checked
            const codes = keys
              .filter((key) => typeof key === 'string' && key.startsWith(PERM_PREFIX))
              .map((key) => String(key).slice(PERM_PREFIX.length))
            onChange?.(codes)
          }}
          height={360}
        />
      </div>
    </div>
  )
}
