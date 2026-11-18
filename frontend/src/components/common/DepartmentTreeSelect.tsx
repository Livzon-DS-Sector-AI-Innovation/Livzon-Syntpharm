'use client'

import { useCallback, useMemo, useState } from 'react'
import { Input, Select, Spin, Tree } from 'antd'
import type { DataNode } from 'antd/es/tree'
import { useQuery } from '@tanstack/react-query'
import { fetchDirectoryDepartments, type DirectoryDepartmentNode } from '@/lib/api/client/hr'

/**
 * 统一部门选择器（#219）。
 *
 * 形态：下拉字段 = 顶部搜索框 + 下方**始终展开**的组织树（无折叠交互），
 * 公司 / 一级 / 二级任意节点都可选；输入关键词实时过滤，并展开命中路径；
 * 每行显示部门名 + 完整层级路径。
 *
 * 值恒为 `hr.departments.id`（部门主数据 UUID），飞书部门 ID 只作同步匹配键。
 * 表单里直接当受控组件用（value 是 UUID 字符串）。
 */

export interface PickedDepartment {
  /** hr.departments.id */
  id: string
  name: string
  /** 权限数据范围使用的部门编码 */
  code: string
}

export interface DepartmentTreeSelectProps {
  value?: string | null
  /** 已保存的部门名称快照：树未加载时用于回显，避免显示 UUID */
  label?: string | null
  allowClear?: boolean
  placeholder?: string
  disabled?: boolean
  /** 表单友好：只回写 UUID */
  onChange?: (departmentId: string | null) => void
  /** 需要名称/编码时使用（例如写入部门名称快照） */
  onSelect?: (department: PickedDepartment | null) => void
}

interface TreeRow {
  id: string
  name: string
  code: string
  pathNames: string[]
  children: TreeRow[]
}

function toRows(nodes: DirectoryDepartmentNode[]): TreeRow[] {
  return nodes.map((node) => ({
    id: node.id,
    name: node.name,
    code: node.code ?? '',
    pathNames: node.path_names ?? [node.name],
    children: toRows(node.children ?? []),
  }))
}

/** 过滤：命中节点保留，并保留其祖先，保证搜索结果的层级路径可见。 */
function filterRows(rows: TreeRow[], keyword: string): TreeRow[] {
  const lowered = keyword.trim().toLowerCase()
  if (!lowered) return rows
  const filtered: TreeRow[] = []
  for (const row of rows) {
    const children = filterRows(row.children, lowered)
    const hit = row.name.toLowerCase().includes(lowered) || row.code.toLowerCase().includes(lowered)
    if (hit || children.length > 0) {
      filtered.push({ ...row, children })
    }
  }
  return filtered
}

function toTreeData(rows: TreeRow[]): DataNode[] {
  return rows.map((row) => ({
    key: row.id,
    // 行内展示「部门名 + 完整层级路径」，让人一眼看出属于哪个上级。
    title: (
      <span style={{ display: 'inline-flex', alignItems: 'baseline', gap: 8, maxWidth: '100%' }}>
        <span>{row.name}</span>
        <span style={{ color: 'var(--ant-color-text-tertiary, #999)', fontSize: 12 }}>
          {row.pathNames.join(' / ')}
        </span>
      </span>
    ),
    children: toTreeData(row.children),
  }))
}

function collectKeys(rows: TreeRow[]): string[] {
  return rows.flatMap((row) => [row.id, ...collectKeys(row.children)])
}

function findRow(rows: TreeRow[], id: string): TreeRow | null {
  for (const row of rows) {
    if (row.id === id) return row
    const hit = findRow(row.children, id)
    if (hit) return hit
  }
  return null
}

export default function DepartmentTreeSelect({
  value,
  label,
  allowClear = false,
  placeholder = '选择部门（可搜索）',
  disabled,
  onChange,
  onSelect,
}: DepartmentTreeSelectProps) {
  const [open, setOpen] = useState(false)
  const [keyword, setKeyword] = useState('')

  // 部门树用 React Query 缓存：首次渲染即可回显已选部门名称，展开不重复请求。
  const { data: nodes = [], isLoading } = useQuery<DirectoryDepartmentNode[]>({
    queryKey: ['hr-directory-departments'],
    queryFn: fetchDirectoryDepartments,
    staleTime: 5 * 60 * 1000,
  })

  const rows = useMemo(() => toRows(nodes), [nodes])
  const visibleRows = useMemo(() => filterRows(rows, keyword), [rows, keyword])
  const treeData = useMemo(() => toTreeData(visibleRows), [visibleRows])
  // 全展开：搜索时命中路径必须可见，所以直接用全部 key 作为展开集合。
  const expandedKeys = useMemo(() => collectKeys(visibleRows), [visibleRows])

  const selectedRow = useMemo(() => (value ? findRow(rows, value) : null), [rows, value])
  const displayLabel = selectedRow?.name ?? label ?? null

  const handleSelect = useCallback(
    (keys: React.Key[]) => {
      const key = String(keys[0] ?? '')
      if (!key) return
      const row = findRow(rows, key)
      if (!row) return
      const picked: PickedDepartment = { id: row.id, name: row.name, code: row.code }
      onChange?.(row.id)
      onSelect?.(picked)
      setOpen(false)
      setKeyword('')
    },
    [onChange, onSelect, rows],
  )

  return (
    <Select
      open={open}
      disabled={disabled}
      allowClear={allowClear}
      placeholder={placeholder}
      style={{ width: '100%' }}
      value={value || undefined}
      labelRender={() => displayLabel ?? value ?? placeholder}
      onOpenChange={(next) => {
        setOpen(next)
        if (!next) setKeyword('')
      }}
      onClear={() => {
        onChange?.(null)
        onSelect?.(null)
      }}
      popupRender={() => (
        <div style={{ padding: 8, width: 360 }}>
          <Input
            allowClear
            autoFocus
            value={keyword}
            placeholder="搜索部门名称或编码"
            onChange={(event) => setKeyword(event.target.value)}
            style={{ marginBottom: 8 }}
          />
          {isLoading ? (
            <div style={{ padding: '12px 0', textAlign: 'center' }}>
              <Spin size="small" />
            </div>
          ) : visibleRows.length === 0 ? (
            <div style={{ padding: '12px 0', textAlign: 'center', color: '#999' }}>未找到匹配的部门</div>
          ) : (
            <div style={{ maxHeight: 320, overflow: 'auto' }}>
              <Tree
                key={`dept-tree-${keyword}`}
                blockNode
                selectable
                treeData={treeData}
                expandedKeys={expandedKeys}
                selectedKeys={value ? [value] : []}
                onSelect={handleSelect}
              />
            </div>
          )}
        </div>
      )}
    />
  )
}