'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Drawer, Descriptions, Table, Tabs, Tag, Empty, Spin } from 'antd'
import { ToolOutlined, SearchOutlined, CalendarOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import type { Equipment, MaintenancePlan, WorkOrder } from '@/types/equipment/generated-bridge'
import type { InspectionTask } from '@/types/inspection'
import { fetchMaintenancePlansClient, fetchWorkOrdersClient } from '@/lib/api/client/equipment'
import { fetchInspectionHistory } from '@/lib/api/client/inspection'
import {monoFont, pillNeutral, pillSuccess, pillWarning, pillError, statusPill} from '@/components/equipment/shared-styles'
import type { EquipmentStatus } from '@/types/equipment/generated-bridge'

interface EquipmentDetailDrawerProps {
  open: boolean
  equipment: Equipment | null
  categoryName: string
  locationName: string
  onClose: () => void
}

const MAINTENANCE_STATUS_MAP: Record<string, { color: string; bg: string }> = {
  '启用': { color: '#1aae39', bg: '#d9f3e1' },
  '停用': { color: '#787671', bg: '#f0eeec' },
  '已完成': { color: '#0075de', bg: '#dcecfa' },
}

const WORK_ORDER_STATUS_MAP: Record<string, { color: string; bg: string }> = {
  '待处理': { color: '#dd5b00', bg: '#ffe8d4' },
  '执行中': { color: '#7b3ff2', bg: '#e6e0f5' },
  '待验收': { color: '#0075de', bg: '#dcecfa' },
  '已完成': { color: '#1aae39', bg: '#d9f3e1' },
  '已关闭': { color: '#787671', bg: '#f0eeec' },
}

const TASK_STATUS_MAP: Record<string, { color: string; bg: string }> = {
  '待执行': { color: '#0075de', bg: '#dcecfa' },
  '执行中': { color: '#dd5b00', bg: '#ffe8d4' },
  '已完成': { color: '#1aae39', bg: '#d9f3e1' },
  '已关闭': { color: '#787671', bg: '#f0eeec' },
}

function localStatusPill(color: string, bg: string): React.CSSProperties {
  return { display: 'inline-flex', alignItems: 'center', padding: '2px 10px', borderRadius: 4, fontSize: 12, fontWeight: 600, lineHeight: '20px', color, background: bg }
}

const EQUIP_STATUS_MAP: Record<EquipmentStatus, React.CSSProperties> = {
  '在用': statusPill('#1aae39', '#d9f3e1'),
  '备用': statusPill('#0075de', '#dcecfa'),
  '维修中': statusPill('#dd5b00', '#ffe8d4'),
  '停用': statusPill('#787671', '#f0eeec'),
  '报废': statusPill('#e03131', '#fde0ec'),
}



export function EquipmentDetailDrawer({ open, equipment, categoryName, locationName, onClose }: EquipmentDetailDrawerProps) {

  const [activeTab, setActiveTab] = useState<'plans' | 'history' | 'orders'>('plans')

  // 维护保养计划
  const { data: plans = [], isLoading: plansLoading } = useQuery({
    queryKey: ['equipment-maintenance-plans', equipment?.id],
    queryFn: async () => {
      if (!equipment) return []
      const result = await fetchMaintenancePlansClient({ equipment_id: equipment.id, page: 1, page_size: 50 })
      return result.items
    },
    enabled: open && !!equipment,
  })

  // 巡检记录
  const { data: history = [], isLoading: historyLoading } = useQuery({
    queryKey: ['equipment-inspection-history', equipment?.id],
    queryFn: async () => {
      if (!equipment) return []
      const result = await fetchInspectionHistory({ equipment_id: equipment.id, page: 1, page_size: 50 })
      return result.items
    },
    enabled: open && !!equipment,
  })

  // 维修工单
  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ['equipment-work-orders', equipment?.id],
    queryFn: async () => {
      if (!equipment) return []
      const result = await fetchWorkOrdersClient({ equipment_id: equipment.id, page: 1, page_size: 50 })
      return result.items
    },
    enabled: open && !!equipment,
  })

  // ── 维护保养计划列 ──
  const planColumns: ColumnsType<MaintenancePlan> = [
    { title: '计划名称', dataIndex: 'plan_name', key: 'plan_name', width: 150, ellipsis: true },
    {
      title: '类型', dataIndex: 'plan_type', key: 'plan_type', width: 100,
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: '周期', key: 'frequency', width: 100,
      render: (_: unknown, r: MaintenancePlan) => `${r.frequency}${r.frequency_unit}`,
    },
    { title: '上次维护', dataIndex: 'last_maintenance_date', key: 'last_maintenance_date', width: 110, render: (d: string | null) => d || '-' },
    { title: '下次维护', dataIndex: 'next_maintenance_date', key: 'next_maintenance_date', width: 110, render: (d: string | null) => d || '-' },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => {
        const m = MAINTENANCE_STATUS_MAP[s] || { color: '#787671', bg: '#f0eeec' }
        return <span style={localStatusPill(m.color, m.bg)}>{s}</span>
      },
    },
  ]

  // ── 巡检记录列 ──
  const historyColumns: ColumnsType<InspectionTask> = [
    {
      title: '任务编号', dataIndex: 'task_no', key: 'task_no', width: 170,
      render: (no: string) => <span style={monoFont}>{no}</span>,
    },
    { title: '巡检类型', dataIndex: 'plan_type', key: 'plan_type', width: 90 },
    { title: '计划日期', dataIndex: 'planned_date', key: 'planned_date', width: 100 },
    { title: '巡检人', dataIndex: 'assignee_name', key: 'assignee_name', width: 80, render: (n: string | undefined) => n || '-' },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => {
        const m = TASK_STATUS_MAP[s] || { color: '#787671', bg: '#f0eeec' }
        return <span style={localStatusPill(m.color, m.bg)}>{s}</span>
      },
    },
    {
      title: '结果', dataIndex: 'overall_result', key: 'overall_result', width: 75,
      render: (r: string | null) => {
        if (!r) return '-'
        return <span style={r === '正常' ? pillSuccess : pillError}>{r}</span>
      },
    },
  ]

  // ── 维修工单列 ──
  const orderColumns: ColumnsType<WorkOrder> = [
    {
      title: '工单编号', dataIndex: 'work_order_no', key: 'work_order_no', width: 170,
      render: (no: string) => <span style={monoFont}>{no}</span>,
    },
    {
      title: '类型', dataIndex: 'order_type', key: 'order_type', width: 90,
      render: (t: string) => <Tag>{t}</Tag>,
    },
    {
      title: '优先级', dataIndex: 'priority', key: 'priority', width: 70,
      render: (p: string) => {
        const cmap: Record<string, React.CSSProperties> = { '紧急': { color: '#e03131', fontWeight: 600 }, '高': { color: '#dd5b00', fontWeight: 600 } }
        return <span style={{ fontSize: 13, ...cmap[p] }}>{p}</span>
      },
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => {
        const m = WORK_ORDER_STATUS_MAP[s] || { color: '#787671', bg: '#f0eeec' }
        return <span style={localStatusPill(m.color, m.bg)}>{s}</span>
      },
    },
    { title: '报修人', dataIndex: 'reporter_name', key: 'reporter_name', width: 80, render: (n: string | undefined) => n || '-' },
    { title: '维修人', dataIndex: 'assignee_name', key: 'assignee_name', width: 80, render: (n: string | undefined) => n || '-' },
    { title: '报修时间', dataIndex: 'reported_at', key: 'reported_at', width: 100, render: (d: string) => d?.slice(0, 10) || '-' },
  ]

  const tabItems = [
    {
      key: 'plans' as const,
      label: <span><CalendarOutlined /> 维护保养计划</span>,
      children: (
        <Spin spinning={plansLoading}>
          {plans.length === 0 ? (
            <Empty description="暂无维护保养计划" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Table columns={planColumns} dataSource={plans} rowKey="id" size="small" pagination={false} scroll={{ x: 'max-content' }} />
          )}
        </Spin>
      ),
    },
    {
      key: 'history' as const,
      label: <span><SearchOutlined /> 巡检记录</span>,
      children: (
        <Spin spinning={historyLoading}>
          {history.length === 0 ? (
            <Empty description="暂无巡检记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Table columns={historyColumns} dataSource={history} rowKey="id" size="small" pagination={false} scroll={{ x: 'max-content' }} />
          )}
        </Spin>
      ),
    },
    {
      key: 'orders' as const,
      label: <span><ToolOutlined /> 维修工单</span>,
      children: (
        <Spin spinning={ordersLoading}>
          {orders.length === 0 ? (
            <Empty description="暂无维修工单" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          ) : (
            <Table columns={orderColumns} dataSource={orders} rowKey="id" size="small" pagination={false} scroll={{ x: 'max-content' }} />
          )}
        </Spin>
      ),
    },
  ]

  if (!equipment) return null

  return (
    <Drawer
      title="设备详情"
      size={860}
      open={open}
      onClose={onClose}
      destroyOnHidden
      styles={{
        header: { borderBottom: '1px solid #e5e3df', padding: '16px 24px' },
        body: { padding: '24px' },
      }}
    >
      {/* 基本信息 */}
      <div style={{ marginBottom: 24 }}>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a', margin: '0 0 16px 0' }}>基本信息</h3>
        <Descriptions bordered size="small" column={2} styles={{ label: { fontWeight: 500, color: '#5d5b54', width: 100 } }}>
          <Descriptions.Item label="资产编号">
            <span style={monoFont}>{equipment.asset_no}</span>
          </Descriptions.Item>
          <Descriptions.Item label="标签号">{equipment.label_no || '-'}</Descriptions.Item>
          <Descriptions.Item label="设备位号">{equipment.equipment_tag || '-'}</Descriptions.Item>
          <Descriptions.Item label="设备分类">{equipment.equipment_class ? `${equipment.equipment_class}类` : '-'}</Descriptions.Item>
          <Descriptions.Item label="设备名称">
            <span style={{ fontWeight: 600 }}>{equipment.name}</span>
          </Descriptions.Item>
          <Descriptions.Item label="设备位置">{equipment.location_text || locationName || '-'}</Descriptions.Item>
          <Descriptions.Item label="归属部门">{equipment.department_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="负责人">{equipment.responsible_person_name || '-'}</Descriptions.Item>
          <Descriptions.Item label="设备状态">
            <span style={EQUIP_STATUS_MAP[equipment.status as EquipmentStatus] || pillNeutral}>{equipment.status}</span>
          </Descriptions.Item>
          <Descriptions.Item label="资产类别说明">{equipment.category_description || '-'}</Descriptions.Item>
          <Descriptions.Item label="数量">
            {equipment.technical_params?.['数量'] != null ? String(equipment.technical_params['数量']) : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="设备型号">{equipment.model || '-'}</Descriptions.Item>
          <Descriptions.Item label="设备规格">{equipment.specification || '-'}</Descriptions.Item>
          <Descriptions.Item label="制造商">{equipment.manufacturer || '-'}</Descriptions.Item>
          <Descriptions.Item label="供应商">{equipment.supplier || '-'}</Descriptions.Item>
          <Descriptions.Item label="报废状态">{equipment.scrap_status || '-'}</Descriptions.Item>
          <Descriptions.Item label="报废时间">{equipment.scrap_time || '-'}</Descriptions.Item>
          <Descriptions.Item label="出厂日期">{equipment.production_date || '-'}</Descriptions.Item>
          <Descriptions.Item label="投用日期">{equipment.commissioning_date || '-'}</Descriptions.Item>
          <Descriptions.Item label="当前成本">{equipment.current_cost ? `¥${equipment.current_cost.toLocaleString()}` : '-'}</Descriptions.Item>
          <Descriptions.Item label="账面净值">{equipment.book_value ? `¥${equipment.book_value.toLocaleString()}` : '-'}</Descriptions.Item>
          <Descriptions.Item label=" "></Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{equipment.description || '-'}</Descriptions.Item>
        </Descriptions>
      </div>

      {/* 关联记录 */}
      <div>
        <h3 style={{ fontSize: 15, fontWeight: 600, color: '#1a1a1a', margin: '0 0 16px 0' }}>关联记录</h3>
        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as 'plans' | 'history' | 'orders')}
          items={tabItems}
        />
      </div>
    </Drawer>
  )
}
