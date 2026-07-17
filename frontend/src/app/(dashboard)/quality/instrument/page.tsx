'use client'

import { useRouter } from 'next/navigation'
import { useState, useCallback, useEffect } from 'react'
import { Card, Table, Button, Space, Tag, message, Empty, Spin, Modal, Select, Divider } from 'antd'
import {
  PlusOutlined,
  ReloadOutlined,
  MonitorOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  WarningOutlined,
  ExclamationCircleOutlined,
  SendOutlined,
  SettingOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import {
  getInstruments,
  getRecordsForReminder,
  sendCalibrationReminder,
  getReminderConfigs,
} from '@/actions/instrument'
import type { InstrumentListItem } from '@/types/instrument'
import './instrument-style.css'

interface ReminderConfig {
  id: string
  name: string
  feishu_app_id: string | null
  feishu_app_secret: string | null
  chat_id: string | null
  receive_id_type: string
  is_active: boolean
}

export default function InstrumentDashboardPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ total: 0, active: 0, warning: 0, overdue: 0 })
  const [warningDevices, setWarningDevices] = useState<InstrumentListItem[]>([])
  const [overdueDevices, setOverdueDevices] = useState<InstrumentListItem[]>([])
  const [isMobile, setIsMobile] = useState(false)

  const [remindModalVisible, setRemindModalVisible] = useState(false)
  const [remindLoading, setRemindLoading] = useState(false)
  const [remindDays, setRemindDays] = useState(30)
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null)
  const [upcomingRecords, setUpcomingRecords] = useState<Array<{
    id: string
    instrument_name: string | null
    instrument_no: string | null
    valid_until: string | null
    days_until_expiry: number | null
  }>>([])
  const [overdueRecords, setOverdueRecords] = useState<Array<{
    id: string
    instrument_name: string | null
    instrument_no: string | null
    valid_until: string | null
    days_until_expiry: number | null
  }>>([])
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [reminderConfigs, setReminderConfigs] = useState<ReminderConfig[]>([])

  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  const loadReminderConfigs = useCallback(async () => {
    try {
      const configs = await getReminderConfigs()
      const activeConfigs = configs.items?.filter((c) => c.is_active) || []
      setReminderConfigs(activeConfigs)
      if (activeConfigs.length > 0 && !selectedConfigId) {
        setSelectedConfigId(activeConfigs[0].id)
      }
    } catch {
      console.error('获取提醒配置失败')
    }
  }, [selectedConfigId])

  useEffect(() => {
    if (remindModalVisible) {
      loadReminderConfigs()
      setLoadingPreview(true)
      getRecordsForReminder(remindDays)
        .then((data) => {
          setOverdueRecords(data.overdue || [])
          setUpcomingRecords(data.upcoming || [])
        })
        .catch(() => message.error('获取到期记录失败'))
        .finally(() => setLoadingPreview(false))
    }
  }, [remindModalVisible, remindDays, loadReminderConfigs])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const response = await getInstruments({ page: 1, page_size: 100 })
      const items = response.items || []
      const now = dayjs()

      const total = items.length
      const active = items.filter((i: InstrumentListItem) => i.is_active).length

      const overdueCount = items.filter((i: InstrumentListItem) => {
        if (!i.valid_until) return false
        return dayjs(i.valid_until).isBefore(now)
      }).length

      const warningCount = items.filter((i: InstrumentListItem) => {
        if (!i.valid_until) return false
        const isOverdue = dayjs(i.valid_until).isBefore(now)
        if (isOverdue) return false
        const daysUntil = dayjs(i.valid_until).diff(now, 'day')
        return daysUntil >= 0 && daysUntil <= 30
      }).length

      setStats({ total, active, warning: warningCount, overdue: overdueCount })

      const warningList = items
        .filter((i: InstrumentListItem) => {
          if (!i.valid_until) return false
          const isOverdue = dayjs(i.valid_until).isBefore(now)
          if (isOverdue) return false
          const daysUntil = dayjs(i.valid_until).diff(now, 'day')
          return daysUntil >= 0 && daysUntil <= 30
        })
        .sort((a: InstrumentListItem, b: InstrumentListItem) => {
          const aDate = dayjs(a.valid_until).unix()
          const bDate = dayjs(b.valid_until).unix()
          return aDate - bDate
        })
        .slice(0, 10)
      setWarningDevices(warningList)

      const overdueList = items
        .filter((i: InstrumentListItem) => {
          if (!i.valid_until) return false
          return dayjs(i.valid_until).isBefore(now)
        })
        .sort((a: InstrumentListItem, b: InstrumentListItem) => {
          const aDate = dayjs(a.valid_until).unix()
          const bDate = dayjs(b.valid_until).unix()
          return aDate - bDate
        })
        .slice(0, 10)
      setOverdueDevices(overdueList)
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '加载数据失败，请检查后端服务'
      message.error(errorMsg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const getDaysColor = (days: number) => {
    if (days <= 7) return 'red'
    if (days <= 14) return 'orange'
    return 'green'
  }

  return (
    <div className="instrument-page">
      <div className="instrument-toolbar">
        <div>
          <h1 style={{ fontSize: isMobile ? '18px' : '24px', fontWeight: 700, margin: 0, color: 'var(--ins-text)' }}>
            仪器校准管理
          </h1>
          <p style={{ fontSize: isMobile ? '12px' : '14px', color: 'var(--ins-text-secondary)', margin: '4px 0 0 0' }}>
            仪器台账 · 校准记录 · 到期提醒
          </p>
        </div>
        <Space wrap size={8}>
          <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading} size={isMobile ? 'small' : 'middle'}>
            刷新
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => router.push('/quality/instrument/list/create')}
            size={isMobile ? 'small' : 'middle'}
          >
            新增仪器
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <div className="instrument-stats">
          <div className="instrument-stat-card stat-card-blue">
            <MonitorOutlined className="instrument-stat-icon" />
            <div className="instrument-stat-content">
              <div className="instrument-stat-num">{stats.total}</div>
              <div className="instrument-stat-label">仪器总数</div>
            </div>
          </div>
          <div className="instrument-stat-card stat-card-green">
            <CheckCircleOutlined className="instrument-stat-icon" />
            <div className="instrument-stat-content">
              <div className="instrument-stat-num">{stats.active}</div>
              <div className="instrument-stat-label">在用仪器</div>
            </div>
          </div>
          <div className="instrument-stat-card stat-card-orange">
            <ClockCircleOutlined className="instrument-stat-icon" />
            <div className="instrument-stat-content">
              <div className="instrument-stat-num">{stats.warning}</div>
              <div className="instrument-stat-label">即将到期</div>
            </div>
          </div>
          <div className="instrument-stat-card stat-card-red">
            <WarningOutlined className="instrument-stat-icon" />
            <div className="instrument-stat-content">
              <div className="instrument-stat-num">{stats.overdue}</div>
              <div className="instrument-stat-label">已超期</div>
            </div>
          </div>
        </div>

        <div className="alert-cards">
          <div className="alert-card">
            <div className="alert-card-header">
              <ClockCircleOutlined style={{ color: 'var(--ins-warning)' }} />
              <span>即将到期设备</span>
              {warningDevices.length > 0 && <Tag color="orange">{warningDevices.length}</Tag>}
            </div>
            <div className="alert-card-body">
              {warningDevices.length > 0 ? (
                isMobile ? (
                  <div className="alert-item-list">
                    {warningDevices.map((item) => (
                      <div key={item.id} className="alert-item">
                        <div className="alert-item-main">
                          <div className="alert-item-title">{item.instrument_name}</div>
                          <div className="alert-item-sub">{item.instrument_no}</div>
                        </div>
                        <div className="alert-item-right">
                          <div className="alert-item-date">{dayjs(item.valid_until).format('MM-DD')}</div>
                          <Tag color={getDaysColor(dayjs(item.valid_until).diff(dayjs(), 'day'))}>
                            {dayjs(item.valid_until).diff(dayjs(), 'day')}天
                          </Tag>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Table
                    columns={[
                      { title: '仪器编号', dataIndex: 'instrument_no', key: 'instrument_no', width: 120 },
                      { title: '仪器名称', dataIndex: 'instrument_name', key: 'instrument_name', width: 150, ellipsis: true },
                      { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 120, render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD') : '-') },
                      {
                        title: '剩余天数',
                        key: 'remaining_days',
                        width: 80,
                        render: (_: unknown, record: InstrumentListItem) => {
                          if (!record.valid_until) return '-'
                          const days = dayjs(record.valid_until).diff(dayjs(), 'day')
                          return <Tag color={days <= 7 ? 'red' : days <= 14 ? 'orange' : 'green'}>{days}天</Tag>
                        },
                      },
                    ]}
                    dataSource={warningDevices}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    scroll={{ y: 300 }}
                  />
                )
              ) : (
                <Empty description="暂无即将到期的设备" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </div>

          <div className="alert-card">
            <div className="alert-card-header">
              <WarningOutlined style={{ color: 'var(--ins-danger)' }} />
              <span>已超期设备</span>
              {overdueDevices.length > 0 && <Tag color="red">{overdueDevices.length}</Tag>}
            </div>
            <div className="alert-card-body">
              {overdueDevices.length > 0 ? (
                isMobile ? (
                  <div className="alert-item-list">
                    {overdueDevices.map((item) => (
                      <div key={item.id} className="alert-item">
                        <div className="alert-item-main">
                          <div className="alert-item-title">{item.instrument_name}</div>
                          <div className="alert-item-sub">{item.instrument_no}</div>
                        </div>
                        <div className="alert-item-right">
                          <div className="alert-item-date">{dayjs(item.valid_until).format('MM-DD')}</div>
                          <Tag color="red">{Math.abs(dayjs(item.valid_until).diff(dayjs(), 'day'))}天</Tag>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Table
                    columns={[
                      { title: '仪器编号', dataIndex: 'instrument_no', key: 'instrument_no', width: 120 },
                      { title: '仪器名称', dataIndex: 'instrument_name', key: 'instrument_name', width: 150, ellipsis: true },
                      { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 120, render: (date: string) => (date ? dayjs(date).format('YYYY-MM-DD') : '-') },
                      {
                        title: '超期天数',
                        key: 'overdue_days',
                        width: 80,
                        render: (_: unknown, record: InstrumentListItem) => {
                          if (!record.valid_until) return '-'
                          const days = Math.abs(dayjs(record.valid_until).diff(dayjs(), 'day'))
                          return <Tag color="red">{days}天</Tag>
                        },
                      },
                    ]}
                    dataSource={overdueDevices}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    scroll={{ y: 300 }}
                  />
                )
              ) : (
                <Empty description="暂无超期设备" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </div>
          </div>
        </div>

        <div className="quick-actions">
          <div className="quick-action-btn" onClick={() => router.push('/quality/instrument/list')}>
            <div className="action-icon">
              <MonitorOutlined />
            </div>
            <div className="action-label">仪器台账</div>
          </div>
          <div className="quick-action-btn" onClick={() => router.push('/quality/instrument/records')}>
            <div className="action-icon">
              <CheckCircleOutlined />
            </div>
            <div className="action-label">校准记录</div>
          </div>
          <div className="quick-action-btn" onClick={() => setRemindModalVisible(true)}>
            <div className="action-icon">
              <SendOutlined />
            </div>
            <div className="action-label">发送提醒</div>
          </div>
          <div className="quick-action-btn" onClick={() => router.push('/quality/instrument/settings')}>
            <div className="action-icon">
              <SettingOutlined />
            </div>
            <div className="action-label">提醒设置</div>
          </div>
        </div>
      </Spin>

      <Modal
        title={
          <Space>
            <SendOutlined />
            <span>发送校准到期提醒到飞书</span>
          </Space>
        }
        open={remindModalVisible}
        onCancel={() => {
          setRemindModalVisible(false)
          setUpcomingRecords([])
          setOverdueRecords([])
        }}
        footer={null}
        width={isMobile ? '100%' : 600}
      >
        {reminderConfigs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <ExclamationCircleOutlined style={{ fontSize: 48, color: '#faad14', marginBottom: 16 }} />
            <p style={{ marginBottom: 16 }}>暂无可用的提醒配置</p>
            <Button type="primary" onClick={() => router.push('/quality/instrument/settings')}>
              去设置飞书提醒
            </Button>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: 16 }}>
              <Space direction={isMobile ? 'vertical' : 'horizontal'} size={8} wrap>
                <span>使用配置：</span>
                <Select value={selectedConfigId} onChange={setSelectedConfigId} style={{ width: isMobile ? '100%' : 200 }}>
                  {reminderConfigs.map((config) => (
                    <Select.Option key={config.id} value={config.id}>
                      {config.name || (config.receive_id_type === 'chat_id' ? '群组' : '用户')}: {config.chat_id?.slice(0, 12)}...
                    </Select.Option>
                  ))}
                </Select>
                <Button type="link" onClick={() => router.push('/quality/instrument/settings')}>
                  修改配置
                </Button>
              </Space>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Space direction={isMobile ? 'vertical' : 'horizontal'} size={8} wrap>
                <span>提前提醒天数：</span>
                <Select
                  value={remindDays}
                  onChange={async (value) => {
                    setRemindDays(value)
                    setLoadingPreview(true)
                    try {
                      const data = await getRecordsForReminder(value)
                      setOverdueRecords(data.overdue || [])
                      setUpcomingRecords(data.upcoming || [])
                    } catch {
                      message.error('获取到期记录失败')
                    } finally {
                      setLoadingPreview(false)
                    }
                  }}
                  style={{ width: isMobile ? '100%' : 120 }}
                >
                  <Select.Option value={7}>7天内</Select.Option>
                  <Select.Option value={14}>14天内</Select.Option>
                  <Select.Option value={30}>30天内</Select.Option>
                  <Select.Option value={60}>60天内</Select.Option>
                  <Select.Option value={90}>90天内</Select.Option>
                </Select>
              </Space>
            </div>

            <Spin spinning={loadingPreview}>
              {overdueRecords.length > 0 && (
                <>
                  <Divider orientation={'left' as any} style={{ margin: '12px 0' }}>
                    <Tag color="red">⚠️ 已超期 {overdueRecords.length} 条</Tag>
                  </Divider>
                  {isMobile ? (
                    <div className="alert-item-list">
                      {overdueRecords.map((r, i) => (
                        <div key={i} className="alert-item">
                          <div className="alert-item-main">
                            <div className="alert-item-title">{r.instrument_name}</div>
                            <div className="alert-item-sub">{r.instrument_no}</div>
                          </div>
                          <div className="alert-item-right">
                            <div className="alert-item-date">{r.valid_until ? dayjs(r.valid_until).format('MM-DD') : '-'}</div>
                            <Tag color="red">{Math.abs(r.days_until_expiry!)}天</Tag>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Table
                      dataSource={overdueRecords.map((r, i) => ({ ...r, key: i }))}
                      columns={[
                        { title: '仪器编号', dataIndex: 'instrument_no', key: 'instrument_no', width: 100 },
                        { title: '仪器名称', dataIndex: 'instrument_name', key: 'instrument_name', width: 120, ellipsis: true },
                        { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 100, render: (val: string) => dayjs(val).format('YYYY-MM-DD') },
                        { title: '超期', dataIndex: 'days_until_expiry', key: 'days_until_expiry', width: 60, render: (val: number) => <Tag color="red">{Math.abs(val)}天</Tag> },
                      ]}
                      size="small"
                      pagination={false}
                      scroll={{ y: 150 }}
                    />
                  )}
                </>
              )}

              {upcomingRecords.length > 0 && (
                <>
                  <Divider orientation={'left' as any} style={{ margin: overdueRecords.length > 0 ? '12px 0' : 0 }}>
                    <Tag color="orange">📅 即将到期 {upcomingRecords.length} 条</Tag>
                  </Divider>
                  {isMobile ? (
                    <div className="alert-item-list">
                      {upcomingRecords.map((r, i) => (
                        <div key={i} className="alert-item">
                          <div className="alert-item-main">
                            <div className="alert-item-title">{r.instrument_name}</div>
                            <div className="alert-item-sub">{r.instrument_no}</div>
                          </div>
                          <div className="alert-item-right">
                            <div className="alert-item-date">{r.valid_until ? dayjs(r.valid_until).format('MM-DD') : '-'}</div>
                            <Tag color={r.days_until_expiry! <= 7 ? 'red' : r.days_until_expiry! <= 14 ? 'orange' : 'green'}>
                              {r.days_until_expiry}天
                            </Tag>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <Table
                      dataSource={upcomingRecords.map((r, i) => ({ ...r, key: i }))}
                      columns={[
                        { title: '仪器编号', dataIndex: 'instrument_no', key: 'instrument_no', width: 100 },
                        { title: '仪器名称', dataIndex: 'instrument_name', key: 'instrument_name', width: 120, ellipsis: true },
                        { title: '有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 100, render: (val: string) => dayjs(val).format('YYYY-MM-DD') },
                        { title: '剩余天数', dataIndex: 'days_until_expiry', key: 'days_until_expiry', width: 60, render: (val: number) => <Tag color={val <= 7 ? 'red' : val <= 14 ? 'orange' : 'green'}>{val}天</Tag> },
                      ]}
                      size="small"
                      pagination={false}
                      scroll={{ y: 150 }}
                    />
                  )}
                </>
              )}

              {upcomingRecords.length === 0 && overdueRecords.length === 0 && (
                <Empty description="暂无需要提醒的校准记录" image={Empty.PRESENTED_IMAGE_SIMPLE} />
              )}
            </Spin>

            <div style={{ marginTop: 20, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setRemindModalVisible(false)}>关闭</Button>
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  loading={remindLoading}
                  disabled={(upcomingRecords.length === 0 && overdueRecords.length === 0) || !selectedConfigId}
                  onClick={async () => {
                    const config = reminderConfigs.find((c) => c.id === selectedConfigId)
                    if (!config) {
                      message.error('请选择提醒配置')
                      return
                    }
                    setRemindLoading(true)
                    try {
                      const result = await sendCalibrationReminder(
                        config.chat_id!,
                        config.receive_id_type as 'chat_id' | 'open_id',
                        remindDays,
                        config.feishu_app_id || undefined,
                        config.feishu_app_secret || undefined
                      )
                      if (result.sent) {
                        message.success(`成功发送提醒，共 ${result.count} 条记录`)
                        setRemindModalVisible(false)
                      } else {
                        message.warning('没有需要提醒的记录')
                      }
                    } catch (err) {
                      message.error(err instanceof Error ? err.message : '发送失败')
                    } finally {
                      setRemindLoading(false)
                    }
                  }}
                >
                  发送飞书提醒
                </Button>
              </Space>
            </div>
          </>
        )}
      </Modal>
    </div>
  )
}
