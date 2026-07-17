'use client'

import { useMemo, useState } from 'react'
import {
  Alert,
  App,
  Button,
  Card,
  Form,
  Input,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ApiOutlined,
  CheckCircleOutlined,
  SaveOutlined,
  SyncOutlined,
} from '@ant-design/icons'

import {
  refreshWarehouseFeishuTables,
  restartWarehouseFeishuWs,
  saveWarehouseFeishuConfig,
  setWarehouseFeishuTableEnabled,
  setWarehouseFeishuTablesEnabled,
  syncWarehouseFeishuTable,
  testWarehouseFeishuConfig,
} from '@/actions/warehouse'
import type {
  WarehouseFeishuBusinessDomain,
  WarehouseFeishuConfig,
  WarehouseFeishuConfigUpsert,
  WarehouseFeishuConnectivityResult,
  WarehouseFeishuTable,
} from '@/types/warehouse'

const { Text } = Typography
const { TextArea } = Input

interface FeishuConfigClientProps {
  initialConfig: WarehouseFeishuConfig
  initialTables: WarehouseFeishuTable[]
}

const domains: Array<{
  key: WarehouseFeishuBusinessDomain
  label: string
  tokenField: keyof WarehouseFeishuConfigUpsert
}> = [
  {
    key: 'finished_product',
    label: '成品',
    tokenField: 'finished_product_app_token',
  },
  {
    key: 'materials_packaging',
    label: '原辅料及包材',
    tokenField: 'materials_packaging_app_token',
  },
  {
    key: 'hardware',
    label: '五金',
    tokenField: 'hardware_app_token',
  },
]

function cleanText(value?: string | null) {
  const cleaned = value?.trim()
  return cleaned || undefined
}

function extractBitableAppToken(value?: string | null) {
  const text = cleanText(value)
  if (!text) return undefined

  const baseMatch = text.match(/\/base\/([^/?#\s]+)/)
  if (baseMatch?.[1]) return baseMatch[1]

  const labelMatch = text.match(
    /(?:app[_\s-]?token|多维表格\s*app[_\s-]?token)\s*[:：]\s*([A-Za-z0-9_-]+)/i,
  )
  if (labelMatch?.[1]) return labelMatch[1]

  const tokenMatch = text.match(/\b([A-Za-z0-9_-]{10,})\b/)
  return tokenMatch?.[1] || text
}

function formatDate(value?: string | null) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'

  const shanghaiTime = new Date(date.getTime() + 8 * 60 * 60 * 1000)
  const year = shanghaiTime.getUTCFullYear()
  const month = shanghaiTime.getUTCMonth() + 1
  const day = shanghaiTime.getUTCDate()
  const hours = String(shanghaiTime.getUTCHours()).padStart(2, '0')
  const minutes = String(shanghaiTime.getUTCMinutes()).padStart(2, '0')
  const seconds = String(shanghaiTime.getUTCSeconds()).padStart(2, '0')

  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`
}

export function FeishuConfigClient({
  initialConfig,
  initialTables,
}: FeishuConfigClientProps) {
  const { message } = App.useApp()
  const [form] = Form.useForm<WarehouseFeishuConfigUpsert>()
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const [tableBusyId, setTableBusyId] = useState<string | null>(null)
  const [batchBusyDomain, setBatchBusyDomain] =
    useState<WarehouseFeishuBusinessDomain | null>(null)
  const [selectedTableIdsByDomain, setSelectedTableIdsByDomain] = useState<
    Partial<Record<WarehouseFeishuBusinessDomain, string[]>>
  >({})
  const [tables, setTables] = useState<WarehouseFeishuTable[]>(initialTables)
  const [testResult, setTestResult] =
    useState<WarehouseFeishuConnectivityResult | null>(null)

  const initialValues = useMemo<WarehouseFeishuConfigUpsert>(
    () => ({
      config_name: initialConfig.config_name || '仓储飞书配置',
      app_id: initialConfig.app_id || '',
      app_secret: '',
      finished_product_app_token:
        initialConfig.finished_product_app_token || undefined,
      materials_packaging_app_token:
        initialConfig.materials_packaging_app_token ||
        initialConfig.bitable_app_token ||
        undefined,
      hardware_app_token: initialConfig.hardware_app_token || undefined,
      is_active: initialConfig.is_active ?? true,
      remark: initialConfig.remark || '',
    }),
    [initialConfig],
  )

  const normalizePayload = (
    values: WarehouseFeishuConfigUpsert,
  ): WarehouseFeishuConfigUpsert => ({
    ...values,
    config_name: cleanText(values.config_name) || '仓储飞书配置',
    app_id: cleanText(values.app_id) || '',
    app_secret: cleanText(values.app_secret),
    finished_product_app_token: extractBitableAppToken(
      values.finished_product_app_token,
    ),
    materials_packaging_app_token: extractBitableAppToken(
      values.materials_packaging_app_token,
    ),
    hardware_app_token: extractBitableAppToken(values.hardware_app_token),
    remark: cleanText(values.remark),
  })

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)
      const response = await saveWarehouseFeishuConfig(normalizePayload(values))
      const refreshResponse = await refreshWarehouseFeishuTables()
      setTables(refreshResponse.data)
      setSelectedTableIdsByDomain({})
      form.setFieldValue('app_secret', '')
      message.success(response.message || '保存成功')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleRefreshTables = async () => {
    try {
      setRefreshing(true)
      const response = await refreshWarehouseFeishuTables()
      setTables(response.data)
      setSelectedTableIdsByDomain({})
      message.success(`已发现 ${response.data.length} 张数据表`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '刷新表目录失败')
    } finally {
      setRefreshing(false)
    }
  }

  const handleRestartWs = async () => {
    try {
      setRestarting(true)
      const response = await restartWarehouseFeishuWs()
      if (response.data.connected) {
        message.success('仓储飞书长连接已启动')
      } else {
        message.warning(response.data.last_error || '长连接未启动')
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '重启长连接失败')
    } finally {
      setRestarting(false)
    }
  }

  const handleTest = async () => {
    try {
      const values = await form.validateFields()
      setTesting(true)
      const response = await testWarehouseFeishuConfig(normalizePayload(values))
      setTestResult(response.data)
      const refreshResponse = await refreshWarehouseFeishuTables()
      setTables(refreshResponse.data)
      setSelectedTableIdsByDomain({})
      if (response.data.ok) {
        message.success('连通性测试通过')
      } else {
        message.error('连通性测试未通过')
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '连通性测试失败')
    } finally {
      setTesting(false)
    }
  }

  const handleToggle = async (table: WarehouseFeishuTable, checked: boolean) => {
    if (!table.id) return
    try {
      setTableBusyId(table.id)
      const response = await setWarehouseFeishuTableEnabled(table.id, checked)
      setTables((current) =>
        current.map((item) => (item.id === table.id ? response.data : item)),
      )
      message.success(checked ? '已启用并同步数据表' : '已停用数据表')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '更新启用状态失败')
    } finally {
      setTableBusyId(null)
    }
  }

  const handleBatchToggle = async (
    domain: WarehouseFeishuBusinessDomain,
    checked: boolean,
  ) => {
    const selectedTableIds = selectedTableIdsByDomain[domain] || []
    if (selectedTableIds.length === 0) {
      message.warning('请先选择数据表')
      return
    }

    try {
      setBatchBusyDomain(domain)
      const response = await setWarehouseFeishuTablesEnabled(
        selectedTableIds,
        checked,
      )
      const updatedById = new Map(
        response.data.map((table) => [table.id, table] as const),
      )
      setTables((current) =>
        current.map((item) => updatedById.get(item.id) || item),
      )
      setSelectedTableIdsByDomain((current) => ({
        ...current,
        [domain]: [],
      }))
      message.success(
        checked
          ? `已批量启用 ${response.data.length} 张数据表，状态为待同步`
          : `已批量停用 ${response.data.length} 张数据表`,
      )
    } catch (error) {
      message.error(error instanceof Error ? error.message : '批量更新失败')
    } finally {
      setBatchBusyDomain(null)
    }
  }

  const handleSync = async (table: WarehouseFeishuTable) => {
    if (!table.id) return
    try {
      setTableBusyId(table.id)
      const response = await syncWarehouseFeishuTable(table.id)
      setTables((current) =>
        current.map((item) =>
          item.id === table.id ? response.data.table : item,
        ),
      )
      message.success(`已同步 ${response.data.record_count} 条记录`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '同步失败')
    } finally {
      setTableBusyId(null)
    }
  }

  const columns: ColumnsType<WarehouseFeishuTable> = [
    {
      title: '数据表',
      dataIndex: 'name',
      key: 'name',
      render: (name, table) => (
        <div>
          <div className="font-medium text-[var(--color-charcoal)]">{name}</div>
          <Text type="secondary">{table.table_id}</Text>
        </div>
      ),
    },
    {
      title: '启用',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      width: 96,
      render: (enabled, table) => (
        <Switch
          checked={enabled}
          loading={tableBusyId === table.id}
          onChange={(checked) => handleToggle(table, checked)}
        />
      ),
    },
    {
      title: '字段/记录',
      key: 'counts',
      width: 120,
      render: (_, table) => `${table.field_count || 0}/${table.record_count || 0}`,
    },
    {
      title: '同步状态',
      dataIndex: 'sync_status',
      key: 'sync_status',
      width: 128,
      render: (status, table) => (
        <Space orientation="vertical" size={2}>
          <Tag color={status === 'failed' ? 'error' : 'default'}>
            {status || 'pending'}
          </Tag>
          {table.sync_error && <Text type="danger">{table.sync_error}</Text>}
        </Space>
      ),
    },
    {
      title: '最近同步',
      dataIndex: 'last_synced_at',
      key: 'last_synced_at',
      width: 180,
      render: formatDate,
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_, table) => (
        <Button
          size="small"
          icon={<SyncOutlined />}
          loading={tableBusyId === table.id}
          disabled={!table.is_enabled}
          onClick={() => handleSync(table)}
        >
          同步
        </Button>
      ),
    },
  ]

  return (
    <div className="max-w-[1180px]">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="mb-2 text-[22px] font-semibold text-[var(--color-charcoal)]">
            飞书配置
          </h1>
          <div className="flex items-center gap-2 text-[14px] text-[var(--color-steel)]">
            <ApiOutlined />
            <span>仓储管理</span>
            {initialConfig.app_secret_configured && <Tag color="success">密钥已配置</Tag>}
          </div>
        </div>
        <Space wrap>
          <Button icon={<SyncOutlined />} loading={testing} onClick={handleTest}>
            测试连通性
          </Button>
          <Button loading={refreshing} onClick={handleRefreshTables}>
            刷新表目录
          </Button>
          <Button loading={restarting} onClick={handleRestartWs}>
            重启长连接
          </Button>
          <Button
            type="primary"
            icon={<SaveOutlined />}
            loading={saving}
            onClick={handleSave}
          >
            保存配置
          </Button>
        </Space>
      </div>

      <Card className="rounded-[8px]">
        <Form
          form={form}
          layout="vertical"
          initialValues={initialValues}
          requiredMark={false}
        >
          <div className="grid grid-cols-1 gap-x-5 md:grid-cols-2">
            <Form.Item
              name="config_name"
              label="配置名称"
              rules={[{ required: true, message: '请输入配置名称' }]}
            >
              <Input maxLength={128} />
            </Form.Item>
            <Form.Item name="is_active" label="启用状态" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>
            <Form.Item
              name="app_id"
              label="App ID"
              rules={[{ required: true, message: '请输入 App ID' }]}
            >
              <Input maxLength={128} placeholder="cli_xxx" />
            </Form.Item>
            <Form.Item
              name="app_secret"
              label="App Secret"
              tooltip={
                initialConfig.app_secret_configured
                  ? '留空表示沿用已保存密钥'
                  : undefined
              }
              rules={[
                {
                  required: !initialConfig.app_secret_configured,
                  message: '请输入 App Secret',
                },
              ]}
            >
              <Input.Password
                maxLength={500}
                placeholder={
                  initialConfig.app_secret_configured
                    ? '留空沿用已保存密钥'
                    : '请输入 App Secret'
                }
              />
            </Form.Item>
            {domains.map((domain) => (
              <Form.Item
                key={domain.key}
                name={domain.tokenField}
                label={`${domain.label}多维表格 app_token`}
              >
                <Input maxLength={500} placeholder="可粘贴 base 链接或 app_token" />
              </Form.Item>
            ))}
          </div>
          <Form.Item name="remark" label="备注">
            <TextArea rows={3} maxLength={500} />
          </Form.Item>
        </Form>
      </Card>

      <div className="mt-5 grid grid-cols-1 gap-5">
        {domains.map((domain) => {
          const domainTables = tables.filter(
            (table) => table.business_domain === domain.key,
          )
          const selectedTableIds = selectedTableIdsByDomain[domain.key] || []
          const batchLoading = batchBusyDomain === domain.key
          return (
            <Card key={domain.key} className="rounded-[8px]">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <Text strong>{domain.label}数据表</Text>
                  <div className="mt-1 text-[13px] text-[var(--color-steel)]">
                    已发现 {domainTables.length} 张，启用{' '}
                    {domainTables.filter((table) => table.is_enabled).length} 张
                  </div>
                </div>
                <Space wrap>
                  <Tag>{domain.key}</Tag>
                  <Button
                    size="small"
                    disabled={selectedTableIds.length === 0}
                    loading={batchLoading}
                    onClick={() => handleBatchToggle(domain.key, true)}
                  >
                    批量启用
                  </Button>
                  <Button
                    size="small"
                    disabled={selectedTableIds.length === 0}
                    loading={batchLoading}
                    onClick={() => handleBatchToggle(domain.key, false)}
                  >
                    批量停用
                  </Button>
                </Space>
              </div>
              <Table
                columns={columns}
                dataSource={domainTables}
                rowKey={(table) => table.id || table.table_id}
                rowSelection={{
                  selectedRowKeys: selectedTableIds,
                  onChange: (selectedRowKeys) => {
                    setSelectedTableIdsByDomain((current) => ({
                      ...current,
                      [domain.key]: selectedRowKeys.map(String),
                    }))
                  },
                  getCheckboxProps: (table) => ({ disabled: !table.id }),
                }}
                size="small"
                pagination={{ pageSize: 6, showSizeChanger: false }}
              />
            </Card>
          )
        })}
      </div>

      {testResult && (
        <Card className="mt-5 rounded-[8px]">
          <div className="mb-4 flex items-center gap-2">
            <CheckCircleOutlined
              style={{ color: testResult.ok ? '#1aae39' : '#e03131' }}
            />
            <Text strong>{testResult.ok ? '测试通过' : '测试未通过'}</Text>
          </div>
          <Space orientation="vertical" size={10} className="w-full">
            {testResult.steps.map((step) => (
              <Alert
                key={`${step.name}-${step.message}`}
                type={
                  step.status === 'ok'
                    ? 'success'
                    : step.status === 'warning'
                      ? 'warning'
                      : 'error'
                }
                message={step.name}
                description={step.message}
                showIcon
              />
            ))}
          </Space>
        </Card>
      )}
    </div>
  )
}
