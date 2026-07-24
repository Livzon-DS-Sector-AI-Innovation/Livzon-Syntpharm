'use client'

import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'

import { useState, useEffect, useCallback } from 'react'
import { Button, Space, App, Tabs, DatePicker, Select, Card, message } from 'antd'
import { PlusOutlined, ReloadOutlined, ImportOutlined } from '@ant-design/icons'
import { AlertRuleTable, AlertConfigDrawer, AlertRecordTable } from '@/components/energy'
import { AlertRule, AlertRecord } from '@/types/energy'
import { deleteAlertRule, syncBitableDailyDataAction } from '@/actions/energy'
import { fetchAlertRecords as fetchAlertRecordsAPI, fetchAlertRules as fetchAlertRulesAPI } from '@/lib/api/client/energy'
import { useEnergyStore } from '@/stores/energy'

export default function AlertsPage() {
  const { message } = App.useApp()
  const { alertConfigDrawerOpen, openAlertConfigDrawer } = useEnergyStore()
  
  // 预警规则状态
  const [rules, setRules] = useState<AlertRule[]>([])
  const [rulesLoading, setRulesLoading] = useState(false)
  const [rulesTotal, setRulesTotal] = useState(0)
  const [rulesPage, setRulesPage] = useState(1)
  const [rulesPageSize, setRulesPageSize] = useState(10)

  // 预警记录状态
  const [records, setRecords] = useState<AlertRecord[]>([])
  const [recordsLoading, setRecordsLoading] = useState(false)
  const [recordsTotal, setRecordsTotal] = useState(0)
  const [recordsPage, setRecordsPage] = useState(1)
  const [recordsPageSize, setRecordsPageSize] = useState(10)

  // 筛选状态
  const [filterDate, setFilterDate] = useState<Dayjs | null>(null)
  const [filterEnergyType, setFilterEnergyType] = useState<string | undefined>(undefined)

  // 获取预警规则
  const fetchRules = useCallback(async () => {
    setRulesLoading(true)
    try {
      const result = await fetchAlertRulesAPI({ page: rulesPage, page_size: rulesPageSize })
      setRules(result.items)
      setRulesTotal(result.total)
    } catch (error) {
      message.error('获取预警规则失败')
    } finally {
      setRulesLoading(false)
    }
  }, [rulesPage, rulesPageSize])

  // 获取预警记录（支持筛选）
  const fetchRecords = useCallback(async () => {
    setRecordsLoading(true)
    try {
      const params: any = { page: recordsPage, page_size: recordsPageSize }
      if (filterDate) {
        params.start_time = filterDate.startOf('day').toISOString()
        params.end_time = filterDate.endOf('day').toISOString()
      }
      if (filterEnergyType) {
        params.energy_type = filterEnergyType
      }
      const result = await fetchAlertRecordsAPI(params)
      setRecords(result.items)
      setRecordsTotal(result.total)
    } catch (error) {
      message.error('获取预警记录失败')
    } finally {
      setRecordsLoading(false)
    }
  }, [recordsPage, recordsPageSize, filterDate, filterEnergyType])

  useEffect(() => {
    fetchRules()
    fetchRecords()
  }, [fetchRules, fetchRecords])

  const handleRulesPageChange = (p: number, ps: number) => {
    setRulesPage(p)
    setRulesPageSize(ps)
  }

  const handleRecordsPageChange = (p: number, ps: number) => {
    setRecordsPage(p)
    setRecordsPageSize(ps)
  }

  const handleEditRule = (record: AlertRule) => {
    openAlertConfigDrawer('edit', record.id)
  }

  const handleDeleteRule = async (id: string) => {
    try {
      await deleteAlertRule(id)
      message.success('删除成功')
      fetchRules()
    } catch (error) {
      message.error('删除失败')
    }
  }

  const handleProcessRecord = (record: AlertRecord) => {
    message.info('处理功能待实现')
  }

  const [syncLoading, setSyncLoading] = useState(false)

  const handleSyncData = async () => {
    setSyncLoading(true)
    try {
      const result = await syncBitableDailyDataAction()
      const alertCount = result.auto_check_alerts || 0
      if (alertCount > 0) {
        message.success(`数据导入成功！新增 ${result.total_created} 条，更新 ${result.total_updated} 条，自动生成 ${alertCount} 条预警记录`)
      } else {
        message.success(`数据导入成功！新增 ${result.total_created} 条，更新 ${result.total_updated} 条，无新增预警`)
      }
      fetchRecords()
    } catch (error) {
      message.error('数据导入失败')
    } finally {
      setSyncLoading(false)
    }
  }

  const handleFilterDateChange = (date: Dayjs | null) => {
    setFilterDate(date)
    setRecordsPage(1)
  }

  const handleFilterEnergyTypeChange = (value: string | undefined) => {
    setFilterEnergyType(value)
    setRecordsPage(1)
  }

  const tabItems = [
    {
      key: 'records',
      label: '预警记录',
      children: (
        <Card
          styles={{
            body: { padding: '20px 24px' }
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <Space size="middle">
              <Button 
                type="primary" 
                icon={<ImportOutlined />}
                onClick={handleSyncData}
                loading={syncLoading}
                size="large"
              >
                导入数据
              </Button>
            </Space>
            <Space size="middle">
              <DatePicker
                value={filterDate}
                onChange={handleFilterDateChange}
                placeholder="选择日期"
                allowClear
                style={{ width: 160 }}
              />
              <Select
                value={filterEnergyType}
                onChange={handleFilterEnergyTypeChange}
                placeholder="能源类型"
                allowClear
                style={{ width: 140 }}
                options={[
                  { label: '电力', value: 'electricity' },
                  { label: '水', value: 'water' },
                  { label: '蒸汽', value: 'steam' },
                  { label: '天然气', value: 'natural_gas' },
                ]}
              />
              <Button icon={<ReloadOutlined />} onClick={() => fetchRecords()}>
                刷新
              </Button>
            </Space>
          </div>
          <AlertRecordTable
            data={records}
            loading={recordsLoading}
            total={recordsTotal}
            page={recordsPage}
            pageSize={recordsPageSize}
            onPageChange={handleRecordsPageChange}
            onRefresh={() => fetchRecords()}
            onProcess={handleProcessRecord}
          />
        </Card>
      ),
    },
    {
      key: 'rules',
      label: '预警规则',
      children: (
        <Card
          styles={{
            body: { padding: '20px 24px' }
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 20 }}>
            <Space size="middle">
              <Button icon={<ReloadOutlined />} onClick={() => fetchRules()}>
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => openAlertConfigDrawer('create')}>
                新建规则
              </Button>
            </Space>
          </div>
          <AlertRuleTable
            data={rules}
            loading={rulesLoading}
            total={rulesTotal}
            page={rulesPage}
            pageSize={rulesPageSize}
            onPageChange={handleRulesPageChange}
            onRefresh={() => fetchRules()}
            onEdit={handleEditRule}
            onDelete={handleDeleteRule}
          />
        </Card>
      ),
    },
  ]

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ marginBottom: 24 }}>
        <h1 style={{ 
          fontSize: 24, 
          fontWeight: 600, 
          color: '#1a1a1a', 
          margin: 0,
          marginBottom: 8
        }}>
          预警管理
        </h1>
        <p style={{ 
          fontSize: 14, 
          color: '#8c8c8c', 
          margin: 0 
        }}>
          管理能源预警记录和规则配置
        </p>
      </div>

      <Tabs 
        defaultActiveKey="records" 
        items={tabItems}
        size="large"
        style={{
          background: '#fff',
          padding: '16px 24px',
          borderRadius: 8,
          boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px 0 rgba(0, 0, 0, 0.02)'
        }}
      />
      
      <AlertConfigDrawer onRefresh={() => fetchRules()} />
    </div>
  )
}
