
'use client'

import type { Dayjs } from 'dayjs'

import { useState, useEffect, useCallback } from 'react'
import {Button, Space, App, Tabs, DatePicker, Select, Card, Modal, Form, Input} from 'antd'
import { PlusOutlined, ReloadOutlined, ImportOutlined } from '@ant-design/icons'
import { AlertRuleTable, AlertConfigDrawer, AlertRecordTable } from '@/components/energy'
import { AlertRule, AlertRecord } from '@/types/energy'
import { deleteAlertRule, syncBitableDailyDataAction, processAlertRecord } from '@/actions/energy'
import { fetchAlertRecords as fetchAlertRecordsAPI, fetchAlertRules as fetchAlertRulesAPI } from '@/lib/api/client/energy'
import { useEnergyStore } from '@/stores/energy'

export default function AlertsPage() {
  const { message } = App.useApp()
  const { _alertConfigDrawerOpen, openAlertConfigDrawer } = useEnergyStore()
  
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
  const fetchRules = useCallback(async (showSuccessMessage = false) => {
    setRulesLoading(true)
    try {
      const result = await fetchAlertRulesAPI({ page: rulesPage, page_size: rulesPageSize })
      setRules(result.items)
      setRulesTotal(result.total)
      if (showSuccessMessage) {
        message.success('刷新成功')
      }
    } catch (_error) {
      message.error('获取预警规则失败')
    } finally {
      setRulesLoading(false)
    }
  }, [rulesPage, rulesPageSize])

  // 获取预警记录（支持筛选）
  const fetchRecords = useCallback(async (showSuccessMessage = false) => {
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
      if (showSuccessMessage) {
        message.success('刷新成功')
      }
    } catch (_error) {
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

  const [processModalOpen, setProcessModalOpen] = useState(false)
  const [processingRecord, setProcessingRecord] = useState<AlertRecord | null>(null)
  const [processForm] = Form.useForm()
  const [processing, setProcessing] = useState(false)

  const handleProcessRecord = (record: AlertRecord) => {
    setProcessingRecord(record)
    processForm.resetFields()
    setProcessModalOpen(true)
  }

  const handleSubmitProcess = async () => {
    if (!processingRecord) return
    
    try {
      const values = await processForm.validateFields()
      setProcessing(true)
      
      await processAlertRecord(processingRecord.id, {
        status: values.status || 'processed',
        process_note: values.process_note,
      })
      
      message.success('处理成功')
      setProcessModalOpen(false)
      fetchRecords()
    } catch (error: any) {
      if (error?.errorFields) return // 表单验证错误
      message.error('处理失败：' + (error?.message || '未知错误'))
    } finally {
      setProcessing(false)
    }
  }

  const [syncLoading, setSyncLoading] = useState(false)
  const [recordsRefreshing, setRecordsRefreshing] = useState(false)
  const [rulesRefreshing, setRulesRefreshing] = useState(false)

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
              <Button 
                icon={<ReloadOutlined />} 
                onClick={() => {
                  setRecordsRefreshing(true)
                  fetchRecords(true).finally(() => setRecordsRefreshing(false))
                }}
                loading={recordsRefreshing}
              >
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
              <Button 
                icon={<ReloadOutlined />} 
                onClick={() => {
                  setRulesRefreshing(true)
                  fetchRules(true).finally(() => setRulesRefreshing(false))
                }}
                loading={rulesRefreshing}
              >
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


  // 处理预警记录弹窗
  const ProcessModal = () => (
    <Modal
      title="处理预警记录"
      open={processModalOpen}
      onCancel={() => setProcessModalOpen(false)}
      onOk={handleSubmitProcess}
      confirmLoading={processing}
      okText="确认处理"
      cancelText="取消"
    >
      <Form form={processForm} layout="vertical">
        <Form.Item
          label="预警信息"
        >
          <div style={{ padding: '12px', background: '#f5f5f5', borderRadius: 4 }}>
            <div>能源类型：{processingRecord?.energy_type}</div>
            <div>预警等级：{processingRecord?.alert_level}</div>
            <div>触发值：{processingRecord?.trigger_value} {processingRecord?.unit}</div>
            <div>阈值：{processingRecord?.threshold_value} {processingRecord?.unit}</div>
            <div>预警时间：{processingRecord?.alert_time ? new Date(processingRecord.alert_time).toLocaleString('zh-CN') : '-'}</div>
          </div>
        </Form.Item>
        
        <Form.Item
          name="status"
          label="处理状态"
          initialValue="processed"
          rules={[{ required: true, message: '请选择处理状态' }]}
        >
          <Select
            options={[
              { label: '已处理', value: 'processed' },
              { label: '已忽略', value: 'ignored' },
            ]}
          />
        </Form.Item>
        
        <Form.Item
          name="process_note"
          label="处理备注"
        >
          <Input.TextArea
            rows={4}
            placeholder="请输入处理说明..."
          />
        </Form.Item>
      </Form>
    </Modal>
  )

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
          <ProcessModal />
</div>
  )
}
