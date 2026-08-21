'use client'

import { useCallback, useState, useEffect, useRef } from 'react'
import { App, Table, Space, Input, Select, Button } from 'antd'
import { EditOutlined, DeleteOutlined, SearchOutlined, ToolOutlined, PlusOutlined, EyeOutlined, ImportOutlined, SettingOutlined } from '@ant-design/icons'
import { Equipment } from '@/types/equipment/generated-bridge'
import { EquipmentStatus } from '@/types/equipment/generated-bridge'
import { useEquipmentStore } from '@/stores/equipment'
import { deleteEquipment, batchDeleteEquipments } from '@/actions/equipment'
import { statusPill, linkDanger, linkPrimary, linkWarning } from '@/components/equipment/shared-styles'
import { EquipmentDetailDrawer } from './EquipmentDetailDrawer'
import { EquipmentImportModal } from './EquipmentImportModal'
import { StatusBadge } from './StatusBadge'
import { ColumnConfigModal } from './ColumnConfigModal'

const statusConfig: Record<EquipmentStatus, { color: string; bg: string }> = {
  '在用':   { color: '#1aae39', bg: '#d9f3e1' },
  '备用':   { color: '#7b3ff2', bg: '#e6e0f5' },
  '维修中': { color: '#dd5b00', bg: '#ffe8d4' },
  '停用':   { color: '#787671', bg: '#f0eeec' },
  '报废':   { color: '#e03131', bg: '#fde0ec' },
}

const statusPillMap: Record<EquipmentStatus, React.CSSProperties> = Object.fromEntries(
  Object.entries(statusConfig).map(([k, v]) => [k, statusPill(v.color, v.bg)])
) as Record<EquipmentStatus, React.CSSProperties>

const statusOptions = Object.keys(statusConfig).map(value => ({ label: value, value }))

interface EquipmentTableProps {
  onRefreshStatistics?: () => void
  onRefresh?: () => void
  loading?: boolean
  onPageChange: (page: number, pageSize: number) => void
  /** 变化时重置分页到第一页 */
  resetKey: number
}


export function EquipmentTable({ loading = false, onPageChange, resetKey, onRefreshStatistics, onRefresh }: EquipmentTableProps) {
  const { message, modal } = App.useApp()
  const {
    equipments, total,
    statusFilter, keyword,
    departments, departmentFilter, setDepartmentFilter,
    setStatusFilter, setKeyword,
    openEquipmentDrawer, openRepairDrawer,
  } = useEquipmentStore()

  // 本地分页
  const [localPage, setLocalPage] = useState(1)
  const [localPageSize, setLocalPageSize] = useState(20)

  // resetKey 变化 → 重置到第一页
  useEffect(() => {
    setLocalPage(1)
  }, [resetKey])

  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailEquipment, setDetailEquipment] = useState<Equipment | null>(null)
  const [importOpen, setImportOpen] = useState(false)
  const [columnConfigOpen, setColumnConfigOpen] = useState(false)
  const [visibleColumns, setVisibleColumns] = useState<string[]>([])

  // 动态计算 scroll.y，使表头和筛选栏固定，仅表格数据行滚动
  const rootRef = useRef<HTMLDivElement>(null)
  const filterRef = useRef<HTMLDivElement>(null)
  const tableWrapRef = useRef<HTMLDivElement>(null)
  const [scrollY, setScrollY] = useState<number>(0)

  useEffect(() => {
    const tableWrap = tableWrapRef.current
    if (!tableWrap) return
    const observer = new ResizeObserver(() => {
      const h = tableWrap.clientHeight
      // 减去表头（small size 约 37px）和分页栏（约 56px）
      const y = h - 37 - 56
      setScrollY(y > 80 ? y : 80)
    })
    observer.observe(tableWrap)
    return () => observer.disconnect()
  }, [])
  // Load column config from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('equipment_visible_columns')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          setVisibleColumns(parsed)
          return
        }
      }
    } catch (e) {
      console.warn('Failed to load column config:', e)
    }
    // Default visible columns
    setVisibleColumns([
      'asset_no', 'name', 'location_text', 'department', 
      'responsible', 'status', 'commissioning_date'
    ])
  }, [])

  // 多选配置
  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys as string[]),
  }

  // 批量删除处理
  const handleBatchDelete = () => {
    modal.confirm({
      title: `确认删除 ${selectedRowKeys.length} 台设备？`,
      content: '此操作不可恢复，请谨慎操作',
      okText: '确认删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await batchDeleteEquipments(selectedRowKeys)
          message.success(`成功删除 ${selectedRowKeys.length} 台设备`)
          setSelectedRowKeys([])
          onPageChange(localPage, localPageSize)
          onRefreshStatistics?.()
        } catch (error) {
          message.error('批量删除失败')
        }
      },
    })
  }




  const handleDelete = (record: Equipment) => {
    modal.confirm({
      title: '确认删除', content: `确定要删除设备 "${record.name}" 吗？`,
      okText: '确认', cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteEquipment(record.id)
          message.success('删除设备成功')
          // 优先使用 onRefresh（包含最新筛选状态），否则回退到 onPageChange
          if (onRefresh) {
            onRefresh()
          } else {
            onPageChange(localPage, localPageSize)
          }
          onRefreshStatistics?.()
        } catch (error: any) {
          message.error(error?.message || '删除设备失败')
        }
      },
    })
  }

  const columns = [
    { title: '资产编号', dataIndex: 'asset_no', key: 'asset_no', width: 140, fixed: 'start' as const },
    { title: '标签号', dataIndex: 'label_no', key: 'label_no', width: 120, render: (v: string | null) => v || '-' },
    { title: '设备位号', dataIndex: 'equipment_tag', key: 'equipment_tag', width: 120, render: (v: string | null) => v || '-' },
    { title: '设备名称', dataIndex: 'name', key: 'name', width: 180, fixed: 'start' as const, ellipsis: true },
    { title: '设备分类', dataIndex: 'equipment_class', key: 'equipment_class', width: 100, render: (v: string) => v ? `${v}类` : '-' },
    { title: '设备位置', dataIndex: 'location_text', key: 'location_text', width: 150, render: (v: string | null) => v || '-' },
    { title: '归属部门', dataIndex: 'department_name', key: 'department', width: 120,
      render: (v: string | null) => v || '-' },
    { title: '负责人', dataIndex: 'responsible_person_name', key: 'responsible', width: 100,
      render: (v: string | null) => v || '-' },
    { title: '设备状态', dataIndex: 'status', key: 'status', width: 100,
      render: (s: EquipmentStatus) => <StatusBadge status={s} /> },
    { title: '资产类别说明', dataIndex: 'category_description', key: 'category_description', width: 140, ellipsis: true, render: (v: string | null) => v || '-' },
    { title: '型号', dataIndex: 'model', key: 'model', width: 140, ellipsis: true },
    { title: '制造商', dataIndex: 'manufacturer', key: 'manufacturer', width: 140, ellipsis: true },
    { title: '供应商', dataIndex: 'supplier', key: 'supplier', width: 150, ellipsis: true },
    { title: '投用日期', dataIndex: 'commissioning_date', key: 'commissioning_date', width: 120 },
    { title: '当前成本', dataIndex: 'current_cost', key: 'current_cost', width: 120, render: (v: number | null) => v ? `¥${v.toLocaleString()}` : '-' },
    { title: '账面净值', dataIndex: 'book_value', key: 'book_value', width: 120, render: (v: number | null) => v ? `¥${v.toLocaleString()}` : '-' },
    { title: '报废状态', dataIndex: 'scrap_status', key: 'scrap_status', width: 100, render: (v: string | null) => v || '-' },
    { title: '报废时间', dataIndex: 'scrap_time', key: 'scrap_time', width: 120 },
    { 
      title: '数量', 
      dataIndex: 'technical_params', 
      key: 'quantity', 
      width: 80, 
      render: (params: Record<string, unknown> | null) => {
        if (!params || typeof params !== 'object') return '-'
        const quantity = (params as Record<string, unknown>)['数量']
        return quantity ?? '-'
      } 
    },
    { title: '操作', key: 'action', width: 240, fixed: 'end' as const,
      render: (_: unknown, record: Equipment) => (
        <Space size={8}>
          <span role="button" onClick={() => { setDetailEquipment(record); setDetailOpen(true) }} style={linkPrimary}><EyeOutlined />详情</span>
          <span role="button" onClick={() => openRepairDrawer(record.id)} style={linkWarning}><ToolOutlined />报修</span>
          <span role="button" onClick={() => openEquipmentDrawer(record)} style={linkPrimary}><EditOutlined />编辑</span>
          <span role="button" onClick={() => handleDelete(record)} style={linkDanger}><DeleteOutlined />删除</span>
        </Space>
      ),
    },
  ]

  // Filter columns based on visibleColumns
  const filteredColumns = columns.filter(col => {
    // Always show action column
    if (col.key === 'action') return true
    // Show if in visibleColumns or if visibleColumns is empty (show all)
    return visibleColumns.length === 0 || visibleColumns.includes(col.key as string)
  })

  return (
    <div ref={rootRef} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div ref={filterRef} style={{ marginBottom: 12, display: 'flex', gap: 12, alignItems: 'center', flexShrink: 0 }}>
        <Select placeholder="设备状态" allowClear style={{ width: 120 }}
          value={statusFilter || undefined} onChange={(v) => setStatusFilter(v || '')} options={statusOptions} />
        <Select
          placeholder="归属部门"
          allowClear
          style={{ width: 140 }}
          value={departmentFilter || undefined}
          onChange={(v) => setDepartmentFilter(v || null)}
          options={departments.map(d => ({ label: d.name, value: d.id }))}
        />
        <Input placeholder="搜索设备编号或名称" prefix={<SearchOutlined style={{ color: '#a4a097' }} />}
          style={{ width: 240 }} value={keyword} onChange={(e) => setKeyword(e.target.value)} allowClear />
        <div style={{ flex: 1 }} />
        <Button icon={<SettingOutlined />} onClick={() => setColumnConfigOpen(true)}>列配置</Button>
        <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>导入</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => openEquipmentDrawer()}>新增设备</Button>
      </div>
      <div ref={tableWrapRef} style={{ flex: 1, minHeight: 0 }}>
        {/* 批量操作栏 */}
      {selectedRowKeys.length > 0 && (
        <div style={{ 
          marginBottom: 12, 
          padding: '8px 12px',
          background: '#f5f5f5',
          borderRadius: 6,
          display: 'flex', 
          alignItems: 'center',
          gap: 12,
          border: '1px solid #e0e0e0'
        }}>
          <span style={{ 
            fontSize: 14, 
            color: '#595959',
            fontWeight: 500 
          }}>
            已选择 <strong style={{ color: '#1a1a1a' }}>{selectedRowKeys.length}</strong> 项
          </span>
          <div style={{ flex: 1 }} />
          <Button size="small" onClick={() => setSelectedRowKeys([])}>
            取消选择
          </Button>
          <Button size="small" danger onClick={handleBatchDelete}>
            批量删除
          </Button>
        </div>
      )}

      <Table
        rowSelection={rowSelection}
          columns={filteredColumns} dataSource={equipments} rowKey="id" size="small"
          loading={loading} scroll={{ x: 'max-content', y: scrollY || undefined }}
          pagination={{
            current: localPage,
            pageSize: localPageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setLocalPage(p)
              if (ps !== localPageSize) setLocalPageSize(ps)
              onPageChange(p, ps)
            },
          }}
        />
      </div>
      <EquipmentDetailDrawer
        open={detailOpen} equipment={detailEquipment}
        categoryName={detailEquipment?.category_names || ''}
        locationName={detailEquipment?.location_name || ''}
        onClose={() => { setDetailOpen(false); setDetailEquipment(null) }}
      />
      <EquipmentImportModal
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onSuccess={() => { setImportOpen(false); onPageChange(1, localPageSize) }}
      />
      <ColumnConfigModal
        open={columnConfigOpen}
        onClose={() => setColumnConfigOpen(false)}
        onSave={(cols) => {
          setVisibleColumns(cols)
          // Force table re-render
          setLocalPage(p => p)
        }}
      />
    </div>
  )
}
