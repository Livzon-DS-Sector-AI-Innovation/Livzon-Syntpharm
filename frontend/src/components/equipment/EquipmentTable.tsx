'use client'

import { useEffect, useState } from 'react'
import { App, Table, Space, Button } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { EditOutlined, DeleteOutlined, ToolOutlined, EyeOutlined } from '@ant-design/icons'
import { Equipment } from '@/types/equipment/generated-bridge'
import { EquipmentStatus } from '@/types/equipment/generated-bridge'
import { useEquipmentStore } from '@/stores/equipment'
import { deleteEquipment, batchDeleteEquipments } from '@/actions/equipment'
import { linkDanger, linkPrimary, linkWarning } from '@/components/equipment/shared/shared-styles'
import type { SorterResult, TablePaginationConfig } from 'antd/es/table/interface'
import {
  DEFAULT_EQUIPMENT_SORT_BY,
  DEFAULT_EQUIPMENT_SORT_ORDER,
  type EquipmentSortBy,
  type EquipmentSortOrder,
  type EquipmentUrlState,
} from '@/lib/api/equipment-query'
import { SORT_BY_LABEL, sortableColumnKey } from './sorting'
import { EquipmentDetailDrawer } from './EquipmentDetailDrawer'
import { StatusBadge } from './StatusBadge'

interface EquipmentTableProps {
  onRefreshStatistics?: () => void
  onRefresh?: () => void
  loading?: boolean
  page: number
  pageSize: number
  sortBy: EquipmentSortBy
  sortOrder: EquipmentSortOrder
  /** 排序与分页写回 URL（唯一来源） */
  onQueryChange: (patch: Partial<EquipmentUrlState>) => void
  /** 列配置：从父组件受控，避免工具栏里的按钮与表内 modal 状态分散 */
  visibleColumns: string[]
  onVisibleColumnsChange?: (cols: string[]) => void
  /** sticky 表头吸顶偏移 = sticky 工具栏实测高度（px），由父组件测量传入 */
  stickyTop?: number
}

/** 编号 / 日期 / 金额列共用等宽数字样式，靠数位对齐建立秩序而非加大行高 */
const monoCell = () => ({ className: 'equipment-cell-mono' })

export function EquipmentTable({
  loading = false, page, pageSize, sortBy, sortOrder, onQueryChange, onRefreshStatistics, onRefresh,
  visibleColumns, stickyTop = 0,
}: EquipmentTableProps) {
  const { message, modal } = App.useApp()
  const {
    equipments, total,
    openEquipmentDrawer, openRepairDrawer,
  } = useEquipmentStore()

  const [selectedRowKeys, setSelectedRowKeys] = useState<string[]>([])

  /**
   * 白名单内的列才拿到受控 sorter；其余列不渲染排序 affordance（D2/D7）。
   * R5：排序列被列配置隐藏时保留排序、不回落默认序——URL 是唯一真相，静默改序会让分享链接失效；
   * 此时表头没有指示器，当前排序由 FilterSummary 的排序标签承载。
   */
  const sorterProps = (key: string) => {
    const columnSortBy = sortableColumnKey(key)
    if (!columnSortBy) return {}
    return {
      sorter: true as const,
      sortOrder: columnSortBy === sortBy
        ? (sortOrder === 'asc' ? ('ascend' as const) : ('descend' as const))
        : null,
    }
  }

  const handleTableChange = (
    pagination: TablePaginationConfig,
    _filters: unknown,
    sorter: SorterResult<Equipment> | SorterResult<Equipment>[],
  ) => {
    const info = Array.isArray(sorter) ? sorter[0] : sorter
    const columnKey = String(info?.columnKey ?? info?.field ?? '')
    const nextSortBy = info?.order ? sortableColumnKey(columnKey) : undefined
    const nextSortOrder: EquipmentSortOrder | undefined =
      info?.order === 'ascend' ? 'asc' : info?.order === 'descend' ? 'desc' : undefined

    if (nextSortBy && nextSortOrder && (nextSortBy !== sortBy || nextSortOrder !== sortOrder)) {
      onQueryChange({ sort_by: nextSortBy, sort_order: nextSortOrder, page: 1 })
      return
    }
    // 第三次点击取消排序：回落默认序，与「恢复默认」同一语义
    if (!info?.order && (sortBy !== DEFAULT_EQUIPMENT_SORT_BY || sortOrder !== DEFAULT_EQUIPMENT_SORT_ORDER)) {
      onQueryChange({ sort_by: DEFAULT_EQUIPMENT_SORT_BY, sort_order: DEFAULT_EQUIPMENT_SORT_ORDER, page: 1 })
      return
    }
    onQueryChange({ page: pagination.current ?? page, page_size: pagination.pageSize ?? pageSize })
  }

  const [detailOpen, setDetailOpen] = useState(false)
  const [detailEquipment, setDetailEquipment] = useState<Equipment | null>(null)

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
          onRefresh?.()
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
          onRefresh?.()
          onRefreshStatistics?.()
        } catch (error: any) {
          message.error(error?.message || '删除设备失败')
        }
      },
    })
  }

  const columns: ColumnsType<Equipment> = [
    { title: SORT_BY_LABEL.asset_no, dataIndex: 'asset_no', key: 'asset_no', width: 140, fixed: 'start', onCell: monoCell, ...sorterProps('asset_no') },
    { title: '标签号', dataIndex: 'label_no', key: 'label_no', width: 120, onCell: monoCell, render: (v: string | null) => v || '-' },
    { title: '设备位号', dataIndex: 'equipment_tag', key: 'equipment_tag', width: 120, onCell: monoCell, render: (v: string | null) => v || '-' },
    { title: SORT_BY_LABEL.name, dataIndex: 'name', key: 'name', width: 180, fixed: 'start', ellipsis: true, ...sorterProps('name') },
    { title: '设备分类', dataIndex: 'equipment_class', key: 'equipment_class', width: 100, render: (v: string) => v ? `${v}类` : '-' },
    { title: '设备位置', dataIndex: 'location_text', key: 'location_text', width: 150, render: (v: string | null) => v || '-' },
    { title: SORT_BY_LABEL.department_name, dataIndex: 'department_name', key: 'department', width: 120,
      render: (v: string | null) => v || '-', ...sorterProps('department') },
    { title: '负责人', dataIndex: 'responsible_person_name', key: 'responsible', width: 100,
      render: (v: string | null) => v || '-' },
    { title: SORT_BY_LABEL.status, dataIndex: 'status', key: 'status', width: 100,
      render: (s: EquipmentStatus) => <StatusBadge status={s} />, ...sorterProps('status') },
    { title: '资产类别说明', dataIndex: 'category_description', key: 'category_description', width: 140, ellipsis: true, render: (v: string | null) => v || '-' },
    { title: '型号', dataIndex: 'model', key: 'model', width: 140, ellipsis: true },
    { title: '制造商', dataIndex: 'manufacturer', key: 'manufacturer', width: 140, ellipsis: true },
    { title: '供应商', dataIndex: 'supplier', key: 'supplier', width: 150, ellipsis: true },
    { title: SORT_BY_LABEL.commissioning_date, dataIndex: 'commissioning_date', key: 'commissioning_date', width: 120,
      onCell: monoCell, ...sorterProps('commissioning_date') },
    { title: SORT_BY_LABEL.current_cost, dataIndex: 'current_cost', key: 'current_cost', width: 120, align: 'right', onCell: monoCell,
      render: (v: number | null) => v ? `¥${v.toLocaleString()}` : '-', ...sorterProps('current_cost') },
    { title: SORT_BY_LABEL.book_value, dataIndex: 'book_value', key: 'book_value', width: 120, align: 'right', onCell: monoCell,
      render: (v: number | null) => v ? `¥${v.toLocaleString()}` : '-', ...sorterProps('book_value') },
    { title: '报废状态', dataIndex: 'scrap_status', key: 'scrap_status', width: 100, render: (v: string | null) => v || '-' },
    { title: '报废时间', dataIndex: 'scrap_time', key: 'scrap_time', width: 120, onCell: monoCell },
    {
      title: '数量',
      dataIndex: 'technical_params',
      key: 'quantity',
      width: 80,
      align: 'right',
      onCell: monoCell,
      render: (params: Record<string, unknown> | null) => {
        if (!params || typeof params !== 'object') return '-'
        const quantity = (params as Record<string, unknown>)['数量']
        return quantity ?? '-'
      }
    },
    { title: SORT_BY_LABEL.created_at, dataIndex: 'created_at', key: 'created_at', width: 160, onCell: monoCell,
      render: (v: string | null) => v ? dayjs(v).format('YYYY-MM-DD HH:mm') : '-', ...sorterProps('created_at') },
    { title: '操作', key: 'action', width: 240, fixed: 'end',
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

  // 换序/翻页时切换淡入相位：animation-name 变化即重启动画，无需重挂载表体（D9）
  const [fadePhase, setFadePhase] = useState(false)
  useEffect(() => {
    setFadePhase((prev) => !prev)
  }, [sortBy, sortOrder, page])

  return (
    <div className="equipment-ledger" data-fade={fadePhase ? 'b' : 'a'} style={{}}>
      {selectedRowKeys.length > 0 && (
        <div style={{
          marginBottom: 12,
          padding: '10px 16px',
          background: '#fffbeb',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          border: '1px solid #fde68a',
          borderLeft: '4px solid #f59e0b'
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
      <div>
        <Table
          rowSelection={rowSelection}
          columns={filteredColumns} dataSource={equipments} rowKey="id" size="small"
          loading={loading} 
          scroll={{ x: 'max-content' }}
          sticky={{ offsetHeader: stickyTop }}
          onChange={handleTableChange}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 条`,
          }}
        />
      </div>
      <EquipmentDetailDrawer
        open={detailOpen} equipment={detailEquipment}
        categoryName={detailEquipment?.category_names || ''}
        locationName={detailEquipment?.location_name || ''}
        onClose={() => { setDetailOpen(false); setDetailEquipment(null) }}
      />
    </div>
  )
}
