'use client'

import type { ReactNode } from 'react'
import { Button, Input, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, SearchOutlined } from '@ant-design/icons'

interface LedgerTableShellProps<T extends { id: string }> {
  title: string
  total: number
  department: string
  keywordPlaceholder: string
  departmentPlaceholder: string
  onKeywordChange: (value: string) => void
  onDepartmentChange: (value: string) => void
  columns: ColumnsType<T>
  records: T[]
  loading: boolean
  page: number
  pageSize: number
  onPageChange: (page: number, pageSize: number) => void
  scrollX?: number
  onCreate: () => void
  children?: ReactNode
}

/** Shared chrome for the 入职/离职 ledger tables. */
export default function LedgerTableShell<T extends { id: string }>({
  title,
  total,
  department,
  keywordPlaceholder,
  departmentPlaceholder,
  onKeywordChange,
  onDepartmentChange,
  columns,
  records,
  loading,
  page,
  pageSize,
  onPageChange,
  scrollX = 1150,
  onCreate,
  children,
}: LedgerTableShellProps<T>) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="m-0 text-[22px] font-semibold text-[var(--color-charcoal)]">{title}</h1>
          <div className="mt-1 text-[12.5px] text-[var(--color-stone)]">共 {total} 条</div>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={onCreate}>
          新建
        </Button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <Input.Search
          placeholder={keywordPlaceholder}
          allowClear
          onSearch={onKeywordChange}
          onChange={(event) => {
            if (!event.target.value) onKeywordChange('')
          }}
          className="w-72"
        />
        <Input
          placeholder={departmentPlaceholder}
          allowClear
          prefix={<SearchOutlined />}
          value={department}
          onChange={(event) => onDepartmentChange(event.target.value)}
          className="w-56"
        />
      </div>

      <div className="overflow-hidden rounded-[10px] border border-[var(--color-hairline)] bg-white">
        <Table<T>
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={loading}
          size="middle"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (count) => `共 ${count} 条`,
            onChange: onPageChange,
          }}
          scroll={{ x: scrollX }}
        />
      </div>

      {children}
    </div>
  )
}
