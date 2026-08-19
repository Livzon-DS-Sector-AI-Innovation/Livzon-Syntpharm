'use client'

import { useState } from 'react'
import { App, Button, Space, Popconfirm, Empty, Tooltip } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, InfoCircleOutlined } from '@ant-design/icons'
import { EquipmentCategory } from '@/types/equipment'
import { useEquipmentStore } from '@/stores/equipment'
import { CategoryEditor } from './CategoryEditor'
import { deleteCategory } from '@/actions/equipment'

interface CategoryTreeProps {
  categories: EquipmentCategory[]
  onRefresh?: () => void
}

// ==================== 自定义树节点 ====================

interface TreeNodeData {
  id: string
  name: string
  children?: TreeNodeData[]
}

function Chevron({ expanded }: { expanded: boolean }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 20,
        height: 20,
        flexShrink: 0,
        transition: 'transform 0.15s ease',
        transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
      }}
    >
      <svg
        width="10"
        height="10"
        viewBox="0 0 10 10"
        fill="none"
        style={{ display: 'block' }}
      >
        <path
          d="M3.5 2L6.5 5L3.5 8"
          stroke="#a4a097"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </span>
  )
}

function TreeNode({
  node,
  level,
  selectedId,
  onSelect,
  onEdit,
  onDelete,
  onRefresh,
}: {
  node: TreeNodeData
  level: number
  selectedId: string | null
  onSelect: (id: string) => void
  onEdit: (node: TreeNodeData) => void
  onDelete: (node: TreeNodeData) => void
  onRefresh?: () => void
}) {
  const [expanded, setExpanded] = useState(true)
  const [hovered, setHovered] = useState(false)
  const hasChildren = node.children && node.children.length > 0
  const isSelected = selectedId === node.id

  return (
    <div>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'flex-end' }}>
        <Space>
          <CategoryEditor 
            mode="create" 
            trigger={<Button type="primary" size="small" icon={<PlusOutlined />}>新建分类</Button>}
            onSuccess={onRefresh || (() => {})}
          />
          <Tooltip title="分类用于设备类型管理和统计分析。例如：生产设备、辅助设备。">
            <InfoCircleOutlined style={{ color: '#94a3b8', cursor: 'help' }} />
          </Tooltip>
        </Space>
      </div>
      {/* 节点行 */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => onSelect(isSelected ? '' : node.id)}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onKeyDown={(e) => { if (e.key === 'Enter') onSelect(node.id) }}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 4,
          padding: '5px 8px 5px 4px',
          paddingLeft: 4 + level * 20,
          marginBottom: 1,
          borderRadius: 6,
          cursor: 'pointer',
          background: isSelected ? '#f6f5f4' : 'transparent',
          borderLeft: isSelected ? '2px solid #5645d4' : '2px solid transparent',
          transition: 'background 0.12s ease, border-color 0.12s ease',
          fontSize: 14,
          lineHeight: '20px',
          color: isSelected ? '#1a1a1a' : '#37352f',
          fontWeight: isSelected ? 500 : 400,
          userSelect: 'none' as const,
        }}
      >
        {/* 展开/折叠箭头 */}
        {hasChildren ? (
          <span
            role="button"
            tabIndex={-1}
            onClick={(e) => {
              e.stopPropagation()
              setExpanded(!expanded)
            }}
            style={{ display: 'inline-flex' }}
          >
            <Chevron expanded={expanded} />
          </span>
        ) : (
          <span style={{ width: 20, flexShrink: 0 }} />
        )}

        {/* 节点名称 */}
        <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {node.name}
        </span>

        {/* 操作按钮 — hover 时显示 */}
        <Space
          size={2}
          style={{
            opacity: hovered ? 1 : 0,
            transition: 'opacity 0.12s ease',
            flexShrink: 0,
          }}
        >
          <Button
            type="text"
            size="small"
            icon={<EditOutlined style={{ fontSize: 11 }} />}
            onClick={(e) => {
              e.stopPropagation()
              onEdit(node)
            }}
            style={{ color: '#787671', width: 24, height: 24, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
          />
          <Popconfirm
            title="确定删除此分类？"
            onConfirm={() => onDelete(node)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              icon={<DeleteOutlined style={{ fontSize: 11 }} />}
              onClick={(e) => e.stopPropagation()}
              style={{ color: '#e03131', width: 24, height: 24, padding: 0, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
            />
          </Popconfirm>
        </Space>
      </div>

      {/* 子节点 */}
      {hasChildren && expanded && (
        <div>
          {node.children!.map((child) => (
            <TreeNode
              key={child.id}
              node={child}
              level={level + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              onEdit={onEdit}
              onDelete={onDelete}
              onRefresh={onRefresh}
            />
          ))}
        </div>
      )}
    </div>
  )
}

// ==================== 分类树主组件 ====================

export function CategoryTree({ categories, onRefresh }: CategoryTreeProps) {
  const { message } = App.useApp()
  const {
    selectedCategory,
    setSelectedCategory,
    openCategoryDrawer,
  } = useEquipmentStore()

  const handleDelete = async (node: TreeNodeData) => {
    try {
      await deleteCategory(node.id)
      message.success('删除分类成功')
      onRefresh?.()
    } catch (error: any) {
      message.error(error?.message || '删除分类失败')
    }
  }

  const handleEdit = (node: TreeNodeData) => {
    // 从 categories 中找到完整对象传给 drawer
    function find(items: EquipmentCategory[] | undefined): EquipmentCategory | undefined {
      if (!items) return undefined
      for (const item of items) {
        if (item.id === node.id) return item
        if (item.children?.length) {
          const found = find(item.children)
          if (found) return found
        }
      }
      return undefined
    }
    const full = find(categories)
    if (full) openCategoryDrawer(full)
  }

  if (!categories.length) {
    return (
      <div>
        <div style={{ marginBottom: 12 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            block
            onClick={() => openCategoryDrawer()}
          >
            新增分类
          </Button>
        </div>
        <Empty
          description={
            <div style={{ textAlign: 'center' }}>
              <p style={{ margin: '0 0 8px 0', fontSize: 14 }}>暂无设备分类</p>
              <p style={{ margin: 0, fontSize: 12, color: '#94a3b8' }}>
                分类用于设备类型管理和统计分析。<br />
                请先创建分类体系，以便对设备进行标准化管理。
              </p>
            </div>
          }
          styles={{ description: { color: '#787671' } }}
        />
      </div>
    )
  }

  return (
    <div>
      <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'flex-end' }}>
        <Space>
          <CategoryEditor 
            mode="create" 
            trigger={<Button type="primary" size="small" icon={<PlusOutlined />}>新建分类</Button>}
            onSuccess={onRefresh || (() => {})}
          />
          <Tooltip title="分类用于设备类型管理和统计分析。例如：生产设备、辅助设备。">
            <InfoCircleOutlined style={{ color: '#94a3b8', cursor: 'help' }} />
          </Tooltip>
        </Space>
      </div>
      <div style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={() => openCategoryDrawer()}
        >
          新增分类
        </Button>
      </div>

      {/* 自定义树 */}
      <div style={{ marginLeft: -4 }}>
        {categories.map((cat) => (
          <TreeNode
            key={cat.id}
            node={cat}
            level={0}
            selectedId={selectedCategory}
            onSelect={(id) => setSelectedCategory(id || null)}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onRefresh={onRefresh}
          />
        ))}
      </div>
    </div>
  )
}
