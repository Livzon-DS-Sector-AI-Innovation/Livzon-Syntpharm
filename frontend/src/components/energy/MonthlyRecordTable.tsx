'use client'

import { useEffect, useState } from 'react'
import { App, Table, Button, Space, Select, DatePicker } from 'antd'
import {DeleteOutlined, ImportOutlined} from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { TableColumnsType } from 'antd'
import type { EnergyMonthlyRecord, EnergyType } from '@/types/energy'
import { deleteMonthlyRecordAction } from '@/actions/energy'
import { fetchMonthlyRecordsClient, fetchWorkshopsClient, fetchMonthlySummaryClient } from '@/lib/api/client/energy'
import { FeishuImportModal } from './FeishuImportModal'
import { BitableCrossImportModal } from './BitableCrossImportModal'
import dayjs from 'dayjs'

const { RangePicker } = DatePicker

const luxuryPill = (color: string, bg: string) =>
  ({
    display: 'inline-flex',
    alignItems: 'center',
    padding: '2px 12px',
    borderRadius: 9999,
    fontSize: 12,
    fontWeight: 500,
    lineHeight: '20px',
    color,
    background: bg,
  } as const)

const energyTypeConfig: Record<EnergyType, { label: string; pill: ReturnType<typeof luxuryPill> }> = {
  electricity: { label: '电', pill: luxuryPill('#0075de', '#dcecfa') },
  water: { label: '自来水', pill: luxuryPill('#1aae39', '#d9f3e1') },
  steam: { label: '蒸汽', pill: luxuryPill('#dd5b00', '#ffe8d4') },
  natural_gas: { label: '天然气', pill: luxuryPill('#8b5cf6', '#ede9fe') },
}

const tableStyles = `
.luxury-monthly-table .ant-table-thead > tr > th {
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #a4a097;
  background: #fafaf9;
  border-bottom: 1px solid #ede9e4;
  padding: 10px 16px;
  font-weight: 600;
}
.luxury-monthly-table .ant-table-thead > tr > th::before {
  display: none;
}
.luxury-monthly-table .ant-table-tbody > tr > td {
  border-bottom: 1px solid #ede9e4;
  border-inline-end: none;
  padding: 12px 16px;
  font-size: 14px;
  color: #37352f;
}
.luxury-monthly-table .ant-table-tbody > tr > td:last-child {
  border-inline-end: none;
}
.luxury-monthly-table .ant-table-tbody > tr:hover > td {
  background: #f6f3ff !important;
}
.luxury-monthly-table .ant-table-tbody > tr:hover > td:first-child {
  box-shadow: inset 2px 0 0 #5645d4;
}
.luxury-monthly-table .ant-table {
  border-inline-start: none !important;
  border-inline-end: none !important;
}
.luxury-monthly-table .ant-table-container {
  border-inline-start: none !important;
  border-inline-end: none !important;
}
`

const actionLink = {
  cursor: 'pointer' as const,
  color: '#e03131',
  fontSize: 13,
  fontWeight: 500,
  padding: '0 4px',
}

export function MonthlyRecordTable() {
  const { message, modal } = App.useApp()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [workshopFilter, setWorkshopFilter] = useState<string | undefined>()
  const [energyTypeFilter, setEnergyTypeFilter] = useState<EnergyType | undefined>()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [bitableImportModalOpen, setBitableImportModalOpen] = useState(false)

  // queryKey 用格式化后的日期字符串：dayjs 对象进 key 会随每次渲染重建，缓存永不命中
  const startDate = dateRange?.[0]?.format('YYYY-MM-DD')
  const endDate = dateRange?.[1]?.format('YYYY-MM-DD')

  const {
    data: recordsData,
    isFetching: recordsLoading,
    error: recordsError,
  } = useQuery({
    queryKey: [
      'energy-monthly-records',
      { workshopFilter, energyTypeFilter, startDate, endDate, page, pageSize },
    ],
    queryFn: () =>
      fetchMonthlyRecordsClient({
        workshop_id: workshopFilter,
        energy_type: energyTypeFilter,
        start_date: startDate,
        end_date: endDate,
        page,
        page_size: pageSize,
      }),
  })

  const { data: summary } = useQuery({
    queryKey: ['energy-monthly-summary', { workshopFilter, energyTypeFilter, startDate, endDate }],
    queryFn: () =>
      fetchMonthlySummaryClient({
        workshop_id: workshopFilter,
        energy_type: energyTypeFilter,
        start_date: startDate,
        end_date: endDate,
      }),
  })

  const { data: workshopsData } = useQuery({
    queryKey: ['energy-workshops'],
    // 后端 page_size 默认 100，真实车间表已接近该上限；不传会静默截断下拉选项
    queryFn: () => fetchWorkshopsClient({ page: 1, page_size: 500 }),
  })

  useEffect(() => {
    if (recordsError) message.error('加载月度记录失败')
  }, [recordsError, message])

  const records = recordsData?.items ?? []
  const total = recordsData?.total ?? 0
  const workshops = workshopsData ?? []

  // 月度记录与汇总同源，写入后一并失效。
  // React Query 的 queryKey 匹配按数组元素逐个比较、不做字符串前缀匹配，
  // 所以 ['energy-monthly'] 匹配不到 'energy-monthly-records'，必须逐个显式失效。
  const refreshMonthly = () => {
    queryClient.invalidateQueries({ queryKey: ['energy-monthly-records'] })
    queryClient.invalidateQueries({ queryKey: ['energy-monthly-summary'] })
  }

  const handleDelete = (record: EnergyMonthlyRecord) => {
    modal.confirm({
      title: '确认删除',
      content: `确定要删除这条记录吗？`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteMonthlyRecordAction(record.id)
          message.success('删除成功')
          refreshMonthly()
        } catch {
          message.error('删除失败')
        }
      },
    })
  }

  const columns: TableColumnsType<EnergyMonthlyRecord> = [
    {
      title: '车间',
      dataIndex: 'workshop_id',
      key: 'workshop_id',
      width: 150,
      render: (workshopId: string) => {
        const ws = workshops.find((w) => w.id === workshopId)
        return ws?.name || workshopId.slice(0, 8)
      },
    },
    {
      title: '能源类型',
      dataIndex: 'energy_type',
      key: 'energy_type',
      width: 100,
      render: (type: EnergyType) => {
        const config = energyTypeConfig[type]
        return <span style={config?.pill}>{config?.label || type}</span>
      },
    },
    {
      title: '日期范围',
      key: 'date_range',
      width: 200,
      render: (_, record) => {
        const start = record.record_date
        const end = record.date_range_end
        if (end && end !== start) {
          return `${start} ~ ${end}`
        }
        return start
      },
    },
    {
      title: '数值',
      dataIndex: 'value',
      key: 'value',
      width: 120,
      align: 'right',
      render: (value: number, record) => `${value.toLocaleString()} ${record.unit}`,
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      width: 80,
    },
    {
      title: '备注',
      dataIndex: 'remark',
      key: 'remark',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      width: 80,
      render: (_, record) => (
        <span style={actionLink} onClick={() => handleDelete(record)}>
          <DeleteOutlined /> 删除
        </span>
      ),
    },
  ]

  return (
    <>
      <style>{tableStyles}</style>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
        <Space wrap>
          <Select
            placeholder="按车间筛选"
            allowClear
            showSearch
            optionFilterProp="label"
            style={{ width: 180 }}
            value={workshopFilter}
            onChange={(val) => { setWorkshopFilter(val); setPage(1) }}
            options={workshops.map((w) => ({ value: w.id, label: w.name }))}
          />
          <Select
            placeholder="能源类型"
            allowClear
            style={{ width: 120 }}
            value={energyTypeFilter}
            onChange={(val) => { setEnergyTypeFilter(val); setPage(1) }}
            options={[
              { value: 'electricity', label: '电' },
              { value: 'water', label: '自来水' },
              { value: 'steam', label: '蒸汽' },
              { value: 'natural_gas', label: '天然气' },
            ]}
          />
          <RangePicker
            value={dateRange}
            onChange={(dates) => { setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null); setPage(1) }}
          />
        </Space>
        <Space>
          <Button icon={<ImportOutlined />} onClick={() => setBitableImportModalOpen(true)}>
            多维表格导入
          </Button>
          <Button icon={<ImportOutlined />} onClick={() => setImportModalOpen(true)}>
            表格导入
          </Button>
        </Space>
      </div>

      {/* 汇总显示 */}
      {summary && Object.keys(summary).length > 0 && (
        <div style={{ 
          marginBottom: 16, 
          padding: '12px 16px', 
          background: '#f8f9fa', 
          borderRadius: 8,
          display: 'flex',
          gap: 24,
          flexWrap: 'wrap',
          alignItems: 'center'
        }}>
          <span style={{ fontSize: 13, color: '#666', fontWeight: 500 }}>汇总：</span>
          {summary.electricity && (
            <span style={{ fontSize: 13, color: '#0075de' }}>
              电: {summary.electricity.total_value.toLocaleString()} {summary.electricity.unit}
            </span>
          )}
          {summary.water && (
            <span style={{ fontSize: 13, color: '#1aae39' }}>
              自来水: {summary.water.total_value.toLocaleString()} {summary.water.unit}
            </span>
          )}
          {summary.steam && (
            <span style={{ fontSize: 13, color: '#dd5b00' }}>
              蒸汽: {summary.steam.total_value.toLocaleString()} {summary.steam.unit}
            </span>
          )}
          {summary.natural_gas && (
            <span style={{ fontSize: 13, color: '#8b5cf6' }}>
              天然气: {summary.natural_gas.total_value.toLocaleString()} {summary.natural_gas.unit}
            </span>
          )}
        </div>
      )}
      <Table
        className="luxury-monthly-table"
        columns={columns}
        dataSource={records}
        rowKey="id"
        loading={recordsLoading}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          showTotal: (t) => `共 ${t} 条`,
          onChange: (p, ps) => { setPage(p); setPageSize(ps) },
        }}
      />
      <FeishuImportModal
        open={importModalOpen}
        onClose={() => setImportModalOpen(false)}
        onSuccess={() => {
          setImportModalOpen(false)
          refreshMonthly()
        }}
      />
      <BitableCrossImportModal
        open={bitableImportModalOpen}
        onClose={() => setBitableImportModalOpen(false)}
        onSuccess={() => refreshMonthly()}
      />
    </>
  )
}
