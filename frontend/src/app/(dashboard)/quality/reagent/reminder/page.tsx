'use client'

import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Card,
  Form,
  Input,
  InputNumber,
  Switch,
  Button,
  Space,
  message,
  Table,
  Tag,
  Divider,
  Typography,
  Row,
  Col,
  Alert,
  Spin,
} from 'antd'
import {
  BellOutlined,
  SendOutlined,
  SaveOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  EyeOutlined,
  RobotOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons'
import { saveReagentReminderConfig, triggerReagentReminderCheck, setReagentItemReminder } from '@/actions/quality-reagent'

const { Title: _Title, Text } = Typography


interface LowStockItem {
  reagent_name: string
  count: number
  statuses: string
  units: string
  latest_arrival?: string
  is_enabled: boolean
}

const API_BASE = '/api/v1'

export default function ReagentReminderPage() {
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)
  const [checking, setChecking] = useState(false)
  const [settingItem, setSettingItem] = useState<string | null>(null)
  const [isMobile, setIsMobile] = useState(false)
  const queryClient = useQueryClient()

  // 检测移动端
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 767px)')
    const update = () => setIsMobile(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])

  // 加载配置
  const { data: configData, isLoading: loading } = useQuery({
    queryKey: ['reagent-reminder-config'],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/quality/reagent-reminder/config`)
      const data = await response.json()
      if (data.code === 200 && data.data) return data.data
      return null
    },
  })

  useEffect(() => {
    if (configData) {
      form.setFieldsValue({
        feishu_app_id: configData.feishu_app_id,
        feishu_app_secret: configData.feishu_app_secret,
        feishu_chat_id: configData.feishu_chat_id,
        low_stock_threshold: configData.low_stock_threshold,
        is_enabled: configData.is_enabled,
      })
    }
  }, [configData, form])

  // 加载库存不足列表
  const { data: lowStockList = [], isLoading: lowStockLoading, refetch: refetchLowStock } = useQuery({
    queryKey: ['reagent-reminder-low-stock'],
    queryFn: async () => {
      const threshold = form.getFieldValue('low_stock_threshold') || 2
      const response = await fetch(`${API_BASE}/quality/reagent-reminder/low-stock?threshold=${threshold}`)
      const data = await response.json()
      if (data.code === 200) return data.data.items || []
      return []
    },
  })

  // 保存配置
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      const data = await saveReagentReminderConfig(values)
      if (data.code === 200) {
        queryClient.invalidateQueries({ queryKey: ['reagent-reminder-config'] })
        message.success('保存成功')
      } else {
        message.error(data.message || '保存失败')
      }
    } catch (_error) {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleCheck = async () => {
    setChecking(true)
    try {
      await handleSave()
      const data = await triggerReagentReminderCheck()
      if (data.code === 200) {
        message.success(data.message || '检查完成')
        refetchLowStock()
      } else {
        message.error(data.message || '检查失败')
      }
    } catch (_error) {
      message.error('检查失败')
    } finally {
      setChecking(false)
    }
  }

  const handleSetItemReminder = async (reagentName: string, isEnabled: boolean) => {
    setSettingItem(reagentName)
    try {
      const data = await setReagentItemReminder(reagentName, isEnabled)
      if (data.code === 200) {
        message.success(isEnabled ? '已开启提醒' : '已关闭提醒')
        queryClient.invalidateQueries({ queryKey: ['low-stock-reagents'] })
      } else {
        message.error(data.message || '设置失败')
      }
    } catch (_error) {
      message.error('设置失败')
    } finally {
      setSettingItem(null)
    }
  }



  const columns = [
    { title: '试剂名称', dataIndex: 'reagent_name', key: 'reagent_name', ellipsis: true },
    { title: '数量', dataIndex: 'count', key: 'count', width: 80 },
    { title: '状态', dataIndex: 'statuses', key: 'statuses', render: (v: string) => <Tag color="orange">{v}</Tag> },
    { title: '单位', dataIndex: 'units', key: 'units', width: 80 },
    {
      title: '提醒开关',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 100,
      render: (isEnabled: boolean, record: LowStockItem) => (
        <Switch
          checked={isEnabled !== false}
          loading={settingItem === record.reagent_name}
          onChange={(checked) => handleSetItemReminder(record.reagent_name, checked)}
          checkedChildren="开"
          unCheckedChildren="关"
        />
      )
    },
  ]

  return (
    <div className="reminder-page">
      {/* 页面标题 */}
      <div className="reminder-header">
        <BellOutlined className="reminder-icon" />
        <div>
          <h1>试剂库存提醒</h1>
          <p>飞书机器人自动提醒配置</p>
        </div>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[16, 16]}>
          {/* 配置区 */}
          <Col xs={24} lg={12}>
            <Card className="reminder-card" styles={{ body: { padding: isMobile ? 16 : 20 } }}>
              <div className="card-title-area">
                <SettingOutlined className="card-icon" />
                <span>提醒配置</span>
              </div>

              <Alert
                type="info"
                icon={<ClockCircleOutlined />}
                message="自动提醒：每天早上 8:30 自动检查库存并发送飞书提醒"
                className="reminder-alert"
              />

              <Form form={form} layout="vertical">
                <Divider>飞书机器人配置</Divider>

                <Form.Item name="feishu_app_id" label="App ID" rules={[{ required: true }]}>
                  <Input placeholder="请输入飞书应用的 App ID" />
                </Form.Item>

                <Form.Item name="feishu_app_secret" label="App Secret" rules={[{ required: true }]}>
                  <Input.Password placeholder="请输入飞书应用的 App Secret" />
                </Form.Item>

                <Form.Item
                  name="feishu_chat_id"
                  label="群 ID"
                  rules={[{ required: true }]}
                  extra={<Text type="secondary" style={{ fontSize: 12 }}>在飞书群设置中获取群机器人，将机器人加入群后获取群 ID</Text>}
                >
                  <Input placeholder="请输入飞书群 ID" />
                </Form.Item>

                <Divider>提醒规则</Divider>

                <Form.Item
                  name="low_stock_threshold"
                  label="库存不足阈值"
                  extra={<Text type="secondary" style={{ fontSize: 12 }}>当相同名称的试剂数量低于此值时，将发送提醒</Text>}
                >
                  <InputNumber min={1} max={100} style={{ width: '100%' }} />
                </Form.Item>

                <Form.Item name="is_enabled" label="启用提醒" valuePropName="checked">
                  <Switch checkedChildren="开启" unCheckedChildren="关闭" />
                </Form.Item>

                <Divider />

                <Space style={{ width: '100%', justifyContent: 'flex-end', flexWrap: 'wrap', gap: 8 }}>
                  <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
                    保存配置
                  </Button>
                  <Button icon={<SendOutlined />} onClick={handleCheck} loading={checking}>
                    手动发送提醒
                  </Button>
                </Space>
              </Form>
            </Card>
          </Col>

          {/* 预览区 */}
          <Col xs={24} lg={12}>
            <Card
              className="reminder-card"
              styles={{ body: { padding: isMobile ? 16 : 20 } }}
              title={
                <div className="card-title-area">
                  <EyeOutlined className="card-icon" />
                  <span>库存不足预览</span>
                  {lowStockList.length > 0 && <Tag color="orange">{lowStockList.length}</Tag>}
                </div>
              }
              extra={<Button size="small" icon={<SyncOutlined spin={lowStockLoading} />} onClick={() => refetchLowStock()}>刷新</Button>}
            >
              <Table
                columns={columns}
                dataSource={lowStockList}
                rowKey="reagent_name"
                loading={lowStockLoading}
                pagination={false}
                size="small"
                scroll={{ x: isMobile ? 400 : undefined }}
              />
              {lowStockList.length === 0 && !lowStockLoading && (
                <div className="empty-reminder">
                  <RobotOutlined style={{ fontSize: 40, color: '#10b981' }} />
                  <Text type="secondary">所有试剂库存充足，暂无提醒项</Text>
                </div>
              )}
              <div className="reminder-tip">
                <InfoCircleOutlined style={{ color: '#6b7280' }} />
                <span>关闭单个试剂的提醒开关后，该试剂将不会收到库存不足提醒</span>
              </div>
            </Card>
          </Col>
        </Row>
      </Spin>

      {/* 页面样式 */}
      <style jsx global>{`
        .reminder-page {
          padding: 12px;
          min-height: 100%;
        }

        @media (min-width: 768px) {
          .reminder-page {
            padding: 24px;
          }
        }

        .reminder-header {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
        }

        @media (min-width: 768px) {
          .reminder-header {
            margin-bottom: 24px;
          }
        }

        .reminder-icon {
          font-size: 28px;
          color: #f59e0b;
        }

        @media (min-width: 768px) {
          .reminder-icon {
            font-size: 36px;
          }
        }

        .reminder-header h1 {
          font-size: 20px;
          font-weight: 700;
          margin: 0;
          color: #1f2937;
        }

        @media (min-width: 768px) {
          .reminder-header h1 {
            font-size: 24px;
          }
        }

        .reminder-header p {
          font-size: 13px;
          color: #6b7280;
          margin: 2px 0 0 0;
        }

        .reminder-card {
          border-radius: 12px;
          border: 1px solid #e5e7eb;
        }

        .card-title-area {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 15px;
          font-weight: 600;
        }

        @media (min-width: 768px) {
          .card-title-area {
            font-size: 16px;
          }
        }

        .card-icon {
          color: #5645d4;
        }

        .reminder-alert {
          margin-bottom: 16px;
          border-radius: 8px;
        }

        .empty-reminder {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 24px;
        }

        .reminder-tip {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          margin-top: 12px;
          padding: 8px 10px;
          background: #f9fafb;
          border-radius: 6px;
          font-size: 12px;
          color: #6b7280;
        }

        @media (min-width: 768px) {
          .reminder-tip {
            font-size: 13px;
          }
        }
      `}</style>
    </div>
  )
}