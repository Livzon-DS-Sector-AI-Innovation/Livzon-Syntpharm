'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button, Space, App } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import { AlertRuleTable } from './AlertRuleTable'
import { AlertConfigDrawer } from './AlertConfigDrawer'
import { AlertRule } from '@/types/energy'
import { getAlertRules, deleteAlertRule } from '@/actions/energy'
import { useEnergyStore } from '@/stores/energy'

export function AlertsPageClient() {
  const { message } = App.useApp()
  const { alertConfigDrawerOpen, openAlertConfigDrawer } = useEnergyStore()
  const [data, setData] = useState<AlertRule[]>([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)

  const fetchData = useCallback(async (p = page, ps = pageSize) => {
    setLoading(true)
    try {
      const result = await getAlertRules({ page: p, page_size: ps })
      setData(result.items)
      setTotal(result.total)
    } catch (_error) {
      message.error('获取预警规则失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handlePageChange = (p: number, ps: number) => {
    setPage(p)
    setPageSize(ps)
  }

  const handleEdit = (record: AlertRule) => {
    openAlertConfigDrawer('edit', record.id)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteAlertRule(id)
      message.success('删除成功')
      fetchData()
    } catch (error) {
      message.error('删除失败')
    }
  }

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', lineHeight: 1.3, margin: 0 }}>
          预警管理
        </h1>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => fetchData()}>刷新</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openAlertConfigDrawer('create')}>新建规则</Button>
        </Space>
      </div>

      <AlertRuleTable
        data={data}
        loading={loading}
        total={total}
        page={page}
        pageSize={pageSize}
        onPageChange={handlePageChange}
        onRefresh={() => fetchData()}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
      <AlertConfigDrawer onRefresh={() => fetchData()} />
    </div>
  )
}
