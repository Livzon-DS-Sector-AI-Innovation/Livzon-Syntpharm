
'use client'

import type { Dayjs } from 'dayjs'

import { useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {Button, Space, App, Tabs, DatePicker, Select, Card, Modal, Form, Input} from 'antd'
import type { FormInstance } from 'antd'
import { PlusOutlined, ReloadOutlined, ImportOutlined } from '@ant-design/icons'
import { AlertRuleTable, AlertConfigDrawer, AlertRecordTable } from '@/components/energy'
import { AlertRule, AlertRecord, RecordQueryParams, EnergyType } from '@/types/energy'
import { deleteAlertRule, deleteAlertRecord, syncBitableDailyDataAction, processAlertRecord } from '@/actions/energy'
import { fetchAlertRecords as fetchAlertRecordsAPI, fetchAlertRules as fetchAlertRulesAPI } from '@/lib/api/client/energy'
import { useEnergySyncJob } from '@/hooks/useEnergySyncJob'
import { useEnergyStore } from '@/stores/energy'

// 处理预警记录弹窗组件
const ProcessModal = ({
  processModalOpen,
  setProcessModalOpen,
  handleSubmitProcess,
  processing,
  processForm,
  processingRecord
}: {
  processModalOpen: boolean
  setProcessModalOpen: (open: boolean) => void
  handleSubmitProcess: () => void
  processing: boolean
  processForm: FormInstance
  processingRecord: AlertRecord | null
}) => (
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
          <div>预警日期：{processingRecord?.alert_time ? new Date(processingRecord.alert_time).toISOString().slice(0, 10) : '-'}</div>
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

export default function AlertsPage() {
  const { message, modal } = App.useApp()
  const { openAlertConfigDrawer } = useEnergyStore()
  
  // 预警规则状态
  const [rulesPage, setRulesPage] = useState(1)
  const [rulesPageSize, setRulesPageSize] = useState(10)

  // 预警记录状态
  const [recordsPage, setRecordsPage] = useState(1)
  const [recordsPageSize, setRecordsPageSize] = useState(10)

  // 筛选状态
  const [filterDate, setFilterDate] = useState<Dayjs | null>(null)
  const [filterEnergyType, setFilterEnergyType] = useState<string | undefined>(undefined)

  // 获取预警规则
  const { data: rulesData, isLoading: rulesLoading, refetch: refetchRules } = useQuery({
    queryKey: ['alert-rules', { rulesPage, rulesPageSize }],
    queryFn: async () => {
      const result = await fetchAlertRulesAPI({ page: rulesPage, page_size: rulesPageSize })
      return result
    },
  })

  const rules = rulesData?.items || []
  const rulesTotal = rulesData?.total || 0

  const fetchRules = (showSuccessMessage = false) => {
    const promise = refetchRules()
    if (showSuccessMessage) {
      message.success('刷新成功')
    }
    return promise
  }

  // 获取预警记录（支持筛选）
  const { data: recordsData, isLoading: recordsLoading, refetch: refetchRecords } = useQuery({
    queryKey: ['alert-records', { recordsPage, recordsPageSize, filterDate, filterEnergyType }],
    queryFn: async () => {
      const params: RecordQueryParams = { page: recordsPage, page_size: recordsPageSize }
      if (filterDate) {
        // alert_time 按「数据日的 00:00 UTC」存储，筛选窗口也必须按 UTC 日切，否则跨日漏记录
        params.start_time = new Date(Date.UTC(filterDate.year(), filterDate.month(), filterDate.date())).toISOString()
        params.end_time = new Date(
          Date.UTC(filterDate.year(), filterDate.month(), filterDate.date(), 23, 59, 59, 999),
        ).toISOString()
      }
      if (filterEnergyType) {
        params.energy_type = filterEnergyType as EnergyType
      }
      const result = await fetchAlertRecordsAPI(params)
      return result
    },
  })

  const records = recordsData?.items || []
  const recordsTotal = recordsData?.total || 0

  const fetchRecords = (showSuccessMessage = false) => {
    const promise = refetchRecords()
    if (showSuccessMessage) {
      message.success('刷新成功')
    }
    return promise
  }

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
    } catch (_error) {
      message.error('删除失败')
    }
  }

  const handleDeleteRecord = (record: AlertRecord) => {
    modal.confirm({
      title: '确认删除',
      content: '确定要删除这条预警记录吗？原始能耗数据不受影响；下次「导入数据」时若该日仍然超线，会重新生成一条预警。',
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: async () => {
        try {
          await deleteAlertRecord(record.id)
          message.success('删除成功')
          fetchRecords()
        } catch {
          message.error('删除失败')
        }
      },
    })
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
    } catch (error: unknown) {
      if (error && typeof error === 'object' && 'errorFields' in error) return // 表单验证错误
      message.error('处理失败：' + (error instanceof Error ? error.message : '未知错误'))
    } finally {
      setProcessing(false)
    }
  }

  const [recordsRefreshing, setRecordsRefreshing] = useState(false)
  const [rulesRefreshing, setRulesRefreshing] = useState(false)

  // 「导入数据」是异步任务：提交只拿到 job_id，计数必须轮询到 done 才存在（`D-48`）
  const [syncJobId, setSyncJobId] = useState<string | null>(null)
  const [syncStartedAt, setSyncStartedAt] = useState<number | null>(null)
  const syncNotifiedJob = useRef<string | null>(null)
  const { phase: syncPhase, result: syncResult, errorMessage: syncError } = useEnergySyncJob(syncJobId, syncStartedAt)
  const syncLoading = syncPhase === 'running'

  const handleSyncData = async () => {
    try {
      const job = await syncBitableDailyDataAction()
      setSyncJobId(job.job_id)
      setSyncStartedAt(Date.now())
    } catch (error: unknown) {
      message.error('导入任务提交失败：' + (error instanceof Error ? error.message : '未知错误'))
    }
  }

  useEffect(() => {
    if (!syncJobId || syncNotifiedJob.current === syncJobId) return
    if (syncPhase === 'idle' || syncPhase === 'running') return
    syncNotifiedJob.current = syncJobId
    if (syncPhase === 'done') {
      const created = syncResult?.total_created ?? 0
      const updated = syncResult?.total_updated ?? 0
      const alertCount = syncResult?.auto_check_alerts ?? 0
      message.success(
        alertCount > 0
          ? `数据导入成功！新增 ${created} 条，更新 ${updated} 条，自动生成 ${alertCount} 条预警记录`
          : `数据导入成功！新增 ${created} 条，更新 ${updated} 条，无新增预警`,
      )
      refetchRecords()
    } else if (syncPhase === 'failed') {
      message.error(`数据导入失败：${syncError || '后台任务执行出错'}`)
    } else if (syncPhase === 'unavailable') {
      message.warning('导入状态已不可查（后端重启或换实例），请稍后刷新列表确认')
      refetchRecords()
    } else {
      message.info('导入仍在后台进行，已超过 3 分钟未返回结果，请稍后刷新查看')
    }
  }, [syncPhase, syncJobId, syncResult, syncError, message, refetchRecords])

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
            onDelete={handleDeleteRecord}
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
          <ProcessModal
          processModalOpen={processModalOpen}
          setProcessModalOpen={setProcessModalOpen}
          handleSubmitProcess={handleSubmitProcess}
          processing={processing}
          processForm={processForm}
          processingRecord={processingRecord}
        />
</div>
  )
}
