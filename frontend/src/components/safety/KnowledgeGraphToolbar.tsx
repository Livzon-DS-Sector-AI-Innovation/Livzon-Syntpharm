'use client'

import { useState, useCallback, useRef } from 'react'
import { Button, Input, Select, Space, Tooltip, App } from 'antd'
import {
  SearchOutlined,
  ReloadOutlined,
  ExpandOutlined,
  ExportOutlined,
} from '@ant-design/icons'
import { Panel } from '@xyflow/react'
import type { GraphNode } from '@/types/safety'
import { searchGraphNodes } from '@/actions/safety/knowledge-graph'
import { useKnowledgeGraphStore } from '@/stores/safety/knowledgeGraphStore'
import { NODE_TYPE_OPTIONS, RELATION_TYPE_OPTIONS } from './GraphConstants'

interface ToolbarProps {
  onRefresh: () => void
  loading: boolean
  onFitView: () => void
}

export default function KnowledgeGraphToolbar({
  onRefresh,
  loading,
  onFitView,
}: ToolbarProps) {
  const { message } = App.useApp()
  const messageRef = useRef(message)
  messageRef.current = message
  const nodeTypeFilter = useKnowledgeGraphStore(s => s.nodeTypeFilter)
  const relationTypeFilter = useKnowledgeGraphStore(s => s.relationTypeFilter)
  const [searching, setSearching] = useState(false)

  // 搜索
  const handleSearch = useCallback(
    async (value: string) => {
      useKnowledgeGraphStore.setState({ searchQuery: value })
      if (!value.trim()) {
        useKnowledgeGraphStore.setState({ searchResults: [] })
        return
      }
      setSearching(true)
      try {
        const state = useKnowledgeGraphStore.getState()
        const results = await searchGraphNodes(value, state.nodeTypeFilter || undefined)
        useKnowledgeGraphStore.setState({ searchResults: results })
        if (results.length === 0) {
          messageRef.current.info('未找到匹配节点')
        } else {
          messageRef.current.success(`找到 ${results.length} 个节点`)
        }
      } catch {
        messageRef.current.error('搜索失败')
      } finally {
        setSearching(false)
      }
    },
    [],  // 零依赖
  )

  // 导出图片
  const handleExport = useCallback(() => {
    const svgElement = document.querySelector('.react-flow__renderer svg')
    if (!svgElement) {
      messageRef.current.warning('未找到画布元素')
      return
    }
    const serializer = new XMLSerializer()
    const svgStr = serializer.serializeToString(svgElement)
    const blob = new Blob([svgStr], { type: 'image/svg+xml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `知识图谱_${new Date().toISOString().slice(0, 10)}.svg`
    a.click()
    URL.revokeObjectURL(url)
    messageRef.current.success('导出成功')
  }, [])  // 零依赖

  return (
    <Panel position="top-left" style={{ margin: 12 }}>
      <div
        style={{
          background: 'white',
          borderRadius: 10,
          padding: '8px 12px',
          boxShadow: '0 1px 6px rgba(0,0,0,0.08)',
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          flexWrap: 'wrap',
        }}
      >
        {/* 搜索 */}
        <Input.Search
          placeholder="搜索节点..."
          allowClear
          size="small"
          style={{ width: 200 }}
          loading={searching}
          onSearch={handleSearch}
          onClear={() => useKnowledgeGraphStore.setState({ searchResults: [] })}
        />

        <div style={{ width: 1, height: 20, background: 'var(--color-hairline, #e5e3df)' }} />

        {/* 节点类型筛选 */}
        <Select
          size="small"
          placeholder="节点类型"
          allowClear
          style={{ minWidth: 110 }}
          value={nodeTypeFilter}
          onChange={(v) => useKnowledgeGraphStore.setState({ nodeTypeFilter: v })}
          options={NODE_TYPE_OPTIONS}
        />

        {/* 关系类型筛选 */}
        <Select
          size="small"
          placeholder="关系类型"
          allowClear
          style={{ minWidth: 100 }}
          value={relationTypeFilter}
          onChange={(v) => useKnowledgeGraphStore.setState({ relationTypeFilter: v })}
          options={RELATION_TYPE_OPTIONS}
        />

        <div style={{ width: 1, height: 20, background: 'var(--color-hairline, #e5e3df)' }} />

        {/* 操作按钮 */}
        <Space size={4}>
          <Tooltip title="刷新">
            <Button size="small" icon={<ReloadOutlined />} loading={loading} onClick={onRefresh} />
          </Tooltip>
          <Tooltip title="适应画布">
            <Button size="small" icon={<ExpandOutlined />} onClick={onFitView} />
          </Tooltip>
          <Tooltip title="导出 SVG">
            <Button size="small" icon={<ExportOutlined />} onClick={handleExport} />
          </Tooltip>
        </Space>
      </div>
    </Panel>
  )
}
