'use client'

import { useState, useEffect } from 'react'
import { Modal, Form, Input, Switch, Select, App, Card, Tag, Button, Space } from 'antd'
import { SettingOutlined } from '@ant-design/icons'
import {
  getSyncConfig,
  createSyncConfig,
  updateSyncConfig,
  deleteSyncConfig,
  pushToFeishu,
  pullFromFeishu,
  bidirectionalSync,
} from '@/actions/product-output'

interface ProductSyncConfigProps {
  productId: string
  onSynced?: () => void
}

interface SyncConfig {
  id: string
  product_id: string
  app_token: string
  table_id: string
  field_mapping: Record<string, string> | null
  auto_sync: boolean
  sync_direction: string
  last_sync_at: string | null
}

export default function ProductSyncConfig({ productId, onSynced }: ProductSyncConfigProps) {
  const { message } = App.useApp()
  const [configModalVisible, setConfigModalVisible] = useState(false)
  const [config, setConfig] = useState<SyncConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [form] = Form.useForm()

  const loadConfig = async () => {
    try {
      const res = await getSyncConfig(productId)
      if (res.code === 200 && res.data) {
        setConfig(res.data)
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadConfig()
  }, [productId])

  const handleOpenConfig = () => {
    if (config) {
      form.setFieldsValue({
        app_token: config.app_token,
        table_id: config.table_id,
        auto_sync: config.auto_sync,
        sync_direction: config.sync_direction,
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        sync_direction: 'pull',
        auto_sync: false,
      })
    }
    setConfigModalVisible(true)
  }

  const handleSaveConfig = async () => {
    const values = await form.validateFields()
    setLoading(true)
    try {
      if (config) {
        const res = await updateSyncConfig(config.id, values)
        if (res.code === 200) {
          message.success('配置已更新')
          await loadConfig()
        } else {
          message.error(res.message || '更新失败')
        }
      } else {
        const res = await createSyncConfig({
          product_id: productId,
          ...values,
        })
        if (res.code === 200) {
          message.success('配置已创建')
          await loadConfig()
        } else {
          message.error(res.message || '创建失败')
        }
      }
      setConfigModalVisible(false)
    } catch {
      message.error('保存配置失败')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteConfig = async () => {
    if (!config) return
    setLoading(true)
    try {
      const res = await deleteSyncConfig(config.id)
      if (res.code === 200) {
        message.success('配置已删除')
        setConfig(null)
      } else {
        message.error(res.message || '删除失败')
      }
    } catch {
      message.error('删除配置失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Space>
        <Button
          icon={<SettingOutlined />}
          onClick={handleOpenConfig}
        >
          同步配置
        </Button>
        {config && (
          <Button
            onClick={async () => {
              setSyncing(true)
              try {
                const res = await pullFromFeishu(productId)
                if (res.code === 200) {
                  message.success(res.data?.message || '拉取成功')
                  onSynced?.()
                  await loadConfig()
                } else {
                  message.error(res.message || '拉取失败')
                }
              } catch {
                message.error('拉取失败')
              } finally {
                setSyncing(false)
              }
            }}
            loading={syncing}
          >
            手动拉取
          </Button>
        )}
      </Space>

      <Modal
        title="飞书多维表格同步配置"
        open={configModalVisible}
        onOk={handleSaveConfig}
        onCancel={() => setConfigModalVisible(false)}
        confirmLoading={loading}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="app_token"
            label="飞书多维表格 App Token"
            rules={[{ required: true, message: '请输入 app_token' }]}
            extra="从飞书多维表格 URL 中获取，格式如：https://xxx.feishu.cn/base/xxxxx"
          >
            <Input placeholder="请输入 app_token" />
          </Form.Item>
          <Form.Item
            name="table_id"
            label="表格 ID"
            rules={[{ required: true, message: '请输入 table_id' }]}
            extra="从飞书多维表格 URL 中获取，?table= 后面的值"
          >
            <Input placeholder="请输入 table_id" />
          </Form.Item>
          <Form.Item
            name="sync_direction"
            label="同步方向"
          >
            <Select>
              <Select.Option value="push">仅推送（平台 → 飞书）</Select.Option>
              <Select.Option value="pull">仅拉取（飞书 → 平台）</Select.Option>
              <Select.Option value="bidirectional">双向同步</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="auto_sync"
            label="自动同步"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>

        {config && (
          <Card size="small" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Tag color="blue">当前配置</Tag>
              </div>
              <div>
                App Token: <code>{config.app_token}</code>
              </div>
              <div>
                Table ID: <code>{config.table_id}</code>
              </div>
              <div>
                同步方向: {config.sync_direction}
              </div>
              {config.last_sync_at && (
                <div>
                  最后同步: {new Date(config.last_sync_at).toLocaleString('zh-CN')}
                </div>
              )}
              <Button
                danger
                size="small"
                onClick={handleDeleteConfig}
                loading={loading}
              >
                删除配置
              </Button>
            </Space>
          </Card>
        )}
      </Modal>
    </>
  )
}
