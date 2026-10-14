'use client'

import { useMemo, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  App,
  Button,
  Card,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd'
import { DeleteOutlined, ReloadOutlined, SearchOutlined } from '@ant-design/icons'
import {
  clearLogs,
  deleteRedisKeys,
  fetchApiRoutes,
  fetchDbTableColumns,
  fetchDbTables,
  fetchHealth,
  fetchLogs,
  fetchRedisKeys,
  fetchRedisOverview,
  fetchResources,
  fetchScheduledTasks,
  fetchSystemInfo,
  setApiSwitch,
  toggleScheduledTask,
} from '@/actions/system-ops'
import type {
  ApiRouteItem,
  ComponentHealth,
  DbColumnItem,
  DbTableItem,
  LogItem,
  ScheduledTaskItem,
} from '@/types/system-ops'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'

const { Text } = Typography

function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (days > 0) return `${days} 天 ${hours} 小时`
  if (hours > 0) return `${hours} 小时 ${minutes} 分`
  if (minutes > 0) return `${minutes} 分`
  return `${seconds} 秒`
}

// ── Tab 1：服务健康 + 系统信息 ────────────────────────────────────

function HealthTab() {
  const queryClient = useQueryClient()
  const { data: health = [], isLoading } = useQuery({
    queryKey: ['ops-health'],
    queryFn: fetchHealth,
    refetchInterval: 30000,
  })
  const { data: info } = useQuery({
    queryKey: ['ops-info'],
    queryFn: fetchSystemInfo,
  })

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Text className="text-[13px] text-[var(--color-steel)]">
          每 30 秒自动刷新；redis 为共享实例（本机与 UAT 共用）
        </Text>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => queryClient.invalidateQueries({ queryKey: ['ops-health'] })}
        >
          刷新
        </Button>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
        {health.map((item: ComponentHealth) => (
          <Card key={item.name} size="small">
            <div className="flex items-center justify-between">
              <span className="font-medium text-[var(--color-charcoal)]">{item.name}</span>
              <Tag color={item.status === 'ok' ? 'success' : item.status === 'disabled' ? 'default' : 'error'}>
                {item.status === 'ok' ? '正常' : item.status === 'disabled' ? '未启用' : '异常'}
              </Tag>
            </div>
            <div className="mt-2 text-[12px] text-[var(--color-steel)]">
              {[
                item.latency_ms != null ? `${item.latency_ms} ms` : null,
                item.uptime_seconds != null ? `运行时长 ${formatUptime(item.uptime_seconds)}` : null,
                item.detail,
              ]
                .filter(Boolean)
                .join(' · ') || '-'}
            </div>
          </Card>
        ))}
        {isLoading && health.length === 0 && <Card size="small" loading />}
      </div>

      {info && (
        <Card size="small" title="系统信息">
          <Descriptions column={2} size="small" bordered>
            <Descriptions.Item label="应用">{info.app_name}</Descriptions.Item>
            <Descriptions.Item label="环境">
              <Tag color={info.app_env === 'production' ? 'red' : info.app_env === 'development' ? 'blue' : 'orange'}>
                {info.app_env}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="版本">{info.version}</Descriptions.Item>
            <Descriptions.Item label="Python">{info.python_version}</Descriptions.Item>
            <Descriptions.Item label="启动时间">{info.started_at?.replace('T', ' ').slice(0, 19)}</Descriptions.Item>
            <Descriptions.Item label="运行时长">{formatUptime(info.uptime_seconds)}</Descriptions.Item>
            <Descriptions.Item label="关键依赖" span={2}>
              {info.dependencies.map((d) => (
                <Tag key={d.name} className="mb-1">
                  {d.name} {d.version}
                </Tag>
              ))}
            </Descriptions.Item>
          </Descriptions>
        </Card>
      )}
    </div>
  )
}

// ── Tab 2：资源监控 ───────────────────────────────────────────────

function ResourcesTab() {
  const { data } = useQuery({
    queryKey: ['ops-resources'],
    queryFn: fetchResources,
    refetchInterval: 30000,
  })

  if (!data) return <Card loading />

  const { disk, memory, load } = data
  return (
    <div className="space-y-4">
      <Card size="small" title={`磁盘（${disk.path}）`}>
        <Progress
          percent={disk.percent}
          status={disk.percent >= 85 ? 'exception' : 'normal'}
          format={(p) => `${p}%`}
        />
        <div className="mt-1 text-[13px] text-[var(--color-steel)]">
          总 {disk.total_gb} GB · 已用 {disk.used_gb} GB · 剩余{' '}
          <span className={disk.percent >= 85 ? 'font-semibold text-red-600' : ''}>{disk.free_gb} GB</span>
          {disk.percent >= 85 && ' · 磁盘紧张，建议 docker system prune'}
        </div>
      </Card>

      <Card size="small" title="内存">
        <Progress percent={memory.percent} status={memory.percent >= 90 ? 'exception' : 'normal'} />
        <div className="mt-1 text-[13px] text-[var(--color-steel)]">
          总 {memory.total_gb} GB · 已用 {memory.used_gb} GB · 可用 {memory.available_gb} GB
        </div>
      </Card>

      <Card size="small" title="系统负载">
        <Descriptions column={4} size="small">
          <Descriptions.Item label="1 分钟">{load.load1.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="5 分钟">{load.load5.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="15 分钟">{load.load15.toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="CPU 核数">{load.cpu_count}</Descriptions.Item>
        </Descriptions>
      </Card>
    </div>
  )
}

// ── Tab 3：缓存管理 ───────────────────────────────────────────────

function RedisTab() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [prefix, setPrefix] = useState('')
  const [queryPrefix, setQueryPrefix] = useState('')

  const { data: overview } = useQuery({
    queryKey: ['ops-redis'],
    queryFn: fetchRedisOverview,
  })

  const { data: keysData, isLoading } = useQuery({
    queryKey: ['ops-redis-keys', queryPrefix],
    queryFn: () => fetchRedisKeys(queryPrefix),
  })

  const handleDelete = async () => {
    if (queryPrefix.length < 2) {
      message.warning('前缀至少 2 个字符，禁止全库清理')
      return
    }
    try {
      const result = await deleteRedisKeys(queryPrefix)
      message.success(`已清理 ${result.deleted} 个 key（${result.pattern}）`)
      queryClient.invalidateQueries({ queryKey: ['ops-redis'] })
      queryClient.invalidateQueries({ queryKey: ['ops-redis-keys'] })
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    }
  }

  const columns = [
    { title: 'Key', dataIndex: 'key', ellipsis: true },
  ]

  return (
    <div className="space-y-4">
      {overview && (
        <Card size="small" title="Redis 概览">
          <Descriptions column={4} size="small">
            <Descriptions.Item label="Key 总数">{overview.dbsize}</Descriptions.Item>
            <Descriptions.Item label="内存占用">{overview.used_memory_human}</Descriptions.Item>
            <Descriptions.Item label="连接数">{overview.connected_clients}</Descriptions.Item>
            <Descriptions.Item label="版本">{overview.version}</Descriptions.Item>
            <Descriptions.Item label="命中">{overview.keyspace_hits}</Descriptions.Item>
            <Descriptions.Item label="未命中">{overview.keyspace_misses}</Descriptions.Item>
            <Descriptions.Item label="运行天数">{overview.uptime_in_days}</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <Card size="small" title="按前缀查询 / 清理">
        <Space className="mb-3">
          <Input
            placeholder="key 前缀（留空 = 全部，至少 2 字符才能清理）"
            value={prefix}
            onChange={(e) => setPrefix(e.target.value)}
            onPressEnter={() => setQueryPrefix(prefix)}
            style={{ width: 360 }}
            prefix={<SearchOutlined />}
          />
          <Button type="primary" onClick={() => setQueryPrefix(prefix)}>
            查询
          </Button>
          <Popconfirm
            title={`确认清理 ${queryPrefix || '(全部)'}* ？`}
            description="删除后不可恢复"
            onConfirm={handleDelete}
          >
            <Button danger icon={<DeleteOutlined />} disabled={queryPrefix.length < 2}>
              清理该前缀
            </Button>
          </Popconfirm>
        </Space>

        <Table
          columns={columns}
          dataSource={(keysData?.keys ?? []).map((k) => ({ key: k }))}
          rowKey="key"
          size="small"
          loading={isLoading}
          pagination={{ pageSize: 15 }}
          locale={{
            emptyText: queryPrefix ? `无匹配 key（${queryPrefix}*）` : '暂无 key',
          }}
          footer={() =>
            keysData ? (
              <Text className="text-[12px] text-[var(--color-steel)]">
                共 {keysData.total_scanned} 个{keysData.truncated ? '（已截断，仅显示前 200）' : ''}
              </Text>
            ) : null
          }
        />
      </Card>
    </div>
  )
}

// ── Tab 4：任务清单 ───────────────────────────────────────────────

const kindLabel: Record<string, { label: string; color: string }> = {
  task: { label: '调度任务', color: 'blue' },
  generator: { label: '动态生成器', color: 'purple' },
  worker: { label: '后台进程', color: 'green' },
  loop: { label: '轮询循环', color: 'orange' },
}

function TasksTab() {
  const queryClient = useQueryClient()
  const { message } = App.useApp()
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.opsManage)
  const [keyword, setKeyword] = useState('')
  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['ops-tasks'],
    queryFn: fetchScheduledTasks,
  })

  const handleToggle = async (name: string, enabled: boolean) => {
    try {
      await toggleScheduledTask(name, enabled)
      message.success(enabled ? '已启用' : '已禁用')
      queryClient.invalidateQueries({ queryKey: ['ops-tasks'] })
    } catch (e) {
      message.error(e instanceof Error ? e.message : '切换失败')
    }
  }

  const columns = [
    { title: '任务名', dataIndex: 'name', width: 240 },
    {
      title: '类型',
      dataIndex: 'kind',
      width: 110,
      render: (v: string) => {
        const meta = kindLabel[v] ?? { label: v, color: 'default' }
        return <Tag color={meta.color}>{meta.label}</Tag>
      },
    },
    { title: '调度', dataIndex: 'schedule', width: 160, render: (v: string) => v || '-' },
    { title: '模块', dataIndex: 'module', width: 120, render: (v: string) => v || '-' },
    { title: '说明', dataIndex: 'description', ellipsis: true },
    ...(canManage
      ? [
          {
            title: '启用',
            key: 'enabled',
            width: 70,
            render: (_: unknown, task: ScheduledTaskItem) => {
              const togglable = task.kind === 'task' || task.kind === 'generator'
              if (!togglable) return null
              return (
                <Switch
                  size="small"
                  checked={task.enabled}
                  onChange={(checked) => handleToggle(task.name, checked)}
                />
              )
            },
          },
        ]
      : []),
  ]

  // 列表搜索：任务名 / 类型 / 调度 / 模块 / 说明（任务来自代码注册，前端过滤即可）
  const query = keyword.trim().toLowerCase()
  const visibleTasks = query
    ? tasks.filter((task) =>
        [
          task.name,
          kindLabel[task.kind]?.label ?? task.kind,
          task.schedule,
          task.module,
          task.description,
        ].some((value) => (value ?? '').toLowerCase().includes(query)),
      )
    : tasks

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Text className="text-[13px] text-[var(--color-steel)]">
          任务来自代码注册（调度引擎 / 后台进程 / 轮询循环）。执行历史需等执行记录表落地。
        </Text>
        <Space>
          <Input.Search
            allowClear
            placeholder="搜索任务名、模块、说明"
            style={{ width: 260 }}
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
          />
          <Button
            icon={<ReloadOutlined />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['ops-tasks'] })}
          >
            刷新
          </Button>
        </Space>
      </div>
      <Table
        columns={columns}
        dataSource={visibleTasks}
        rowKey="name"
        size="small"
        loading={isLoading}
        pagination={{ pageSize: 20 }}
      />
    </div>
  )
}

// ── Tab 5：API 管理（启停开关）───────────────────────────────────

function ApiTab() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()

  // 权限：无「系统运维管理」权限时隐藏接口启停入口（只读信息仍可查看）
  const { can, loading: permissionLoading } = usePermission()
  const canManage = !permissionLoading && can(PERM.opsManage)
  const [keyword, setKeyword] = useState('')
  const [methodFilter, setMethodFilter] = useState<string | undefined>(undefined)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [disableTarget, setDisableTarget] = useState<ApiRouteItem | null>(null)
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)

  const { data: routes = [], isLoading } = useQuery({
    queryKey: ['ops-api-routes'],
    queryFn: fetchApiRoutes,
  })

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return routes.filter((r) => {
      if (kw && !r.route.toLowerCase().includes(kw) && !r.summary.toLowerCase().includes(kw)) {
        return false
      }
      if (methodFilter && r.method !== methodFilter) return false
      if (statusFilter === 'disabled' && !r.disabled) return false
      if (statusFilter === 'protected' && !r.protected) return false
      if (statusFilter === 'normal' && (r.disabled || r.protected)) return false
      return true
    })
  }, [routes, keyword, methodFilter, statusFilter])

  const handleDisable = async () => {
    if (!disableTarget) return
    try {
      setSaving(true)
      await setApiSwitch(disableTarget.method, disableTarget.route, false, reason || null)
      message.success(`已禁用 ${disableTarget.method} ${disableTarget.route}`)
      setDisableTarget(null)
      setReason('')
      queryClient.invalidateQueries({ queryKey: ['ops-api-routes'] })
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    } finally {
      setSaving(false)
    }
  }

  const handleEnable = async (record: ApiRouteItem) => {
    try {
      await setApiSwitch(record.method, record.route, true, null)
      message.success(`已启用 ${record.method} ${record.route}`)
      queryClient.invalidateQueries({ queryKey: ['ops-api-routes'] })
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    }
  }

  const columns = [
    {
      title: '方法',
      dataIndex: 'method',
      width: 90,
      render: (v: string) => <Tag color="geekblue">{v}</Tag>,
    },
    { title: '路径', dataIndex: 'route', width: 380, ellipsis: true },
    { title: '说明', dataIndex: 'summary', ellipsis: true },
    {
      title: '状态',
      key: 'status',
      width: 110,
      render: (_: unknown, r: ApiRouteItem) => {
        if (r.disabled) return <Tag color="error">已禁用</Tag>
        if (r.protected) return <Tag color="gold">保护名单</Tag>
        return <Tag color="success">启用</Tag>
      },
    },
    // 操作列：无运维管理权限时整列不出现
    ...(canManage
      ? [
          {
            title: '操作',
            key: 'actions',
            width: 130,
            fixed: 'right' as const,
            render: (_: unknown, r: ApiRouteItem) => {
              if (r.protected) return <Text type="secondary">不可禁用</Text>
              if (r.disabled) {
                return (
                  <Popconfirm title="确认重新启用该接口？" onConfirm={() => handleEnable(r)}>
                    <Button size="small" type="primary">
                      启用
                    </Button>
                  </Popconfirm>
                )
              }
              return (
                <Button size="small" danger onClick={() => setDisableTarget(r)}>
                  禁用
                </Button>
              )
            },
          },
        ]
      : []),
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Input.Search
          allowClear
          placeholder="搜索路径或说明"
          style={{ width: 320 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <Select
          allowClear
          placeholder="方法"
          style={{ width: 120 }}
          value={methodFilter}
          onChange={setMethodFilter}
          options={['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((m) => ({ value: m, label: m }))}
        />
        <Select
          style={{ width: 140 }}
          value={statusFilter}
          onChange={setStatusFilter}
          options={[
            { value: 'all', label: '全部状态' },
            { value: 'disabled', label: '已禁用' },
            { value: 'normal', label: '正常启用' },
            { value: 'protected', label: '保护名单' },
          ]}
        />
        <Button
          icon={<ReloadOutlined />}
          onClick={() => queryClient.invalidateQueries({ queryKey: ['ops-api-routes'] })}
        >
          刷新
        </Button>
        <Text className="text-[12px] text-[var(--color-steel)]">
          共 {routes.length} 条，筛选后 {filtered.length} 条；禁用后立即 403，无需重启
        </Text>
      </div>

      <Table
        columns={columns}
        dataSource={filtered}
        rowKey={(r) => `${r.method} ${r.route}`}
        size="small"
        loading={isLoading}
        scroll={{ x: 1000 }}
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      <Modal
        title={`禁用接口：${disableTarget?.method} ${disableTarget?.route}`}
        open={!!disableTarget}
        onOk={handleDisable}
        onCancel={() => {
          setDisableTarget(null)
          setReason('')
        }}
        confirmLoading={saving}
        okText="确认禁用"
        okButtonProps={{ danger: true }}
        cancelText="取消"
      >
        <div className="mt-3 space-y-2">
          <Text type="secondary" className="text-[13px]">
            禁用后该接口对所有调用方立即返回 403；填写原因便于排查（记入审计日志）。
          </Text>
          <Input.TextArea
            rows={3}
            placeholder="禁用原因（可选），例如：接口异常，临时下线排查"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  )
}

// ── Tab 6：日志管理 ──────────────────────────────────────────────

const levelColor: Record<string, string> = {
  DEBUG: 'default',
  INFO: 'blue',
  WARNING: 'orange',
  ERROR: 'red',
  CRITICAL: 'magenta',
}

function LogsTab() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [levels, setLevels] = useState<string[]>([])
  const [keyword, setKeyword] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(false)

  const levelParam = levels.join(',')

  const { data, isLoading } = useQuery({
    queryKey: ['ops-logs', levelParam, keyword],
    queryFn: () => fetchLogs(levelParam, keyword),
    refetchInterval: autoRefresh ? 5000 : false,
  })

  const handleClear = async () => {
    try {
      const result = await clearLogs()
      message.success(`已清空 ${result.cleared} 条缓冲日志`)
      queryClient.invalidateQueries({ queryKey: ['ops-logs'] })
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    }
  }

  const columns = [
    { title: '时间', dataIndex: 'timestamp', width: 170 },
    {
      title: '级别',
      dataIndex: 'level',
      width: 100,
      render: (v: string) => <Tag color={levelColor[v] ?? 'default'}>{v}</Tag>,
    },
    { title: '来源', dataIndex: 'logger', width: 280, ellipsis: true },
    { title: '消息', dataIndex: 'message', ellipsis: true },
    {
      title: '请求ID',
      dataIndex: 'request_id',
      width: 100,
      render: (v: string) => (v && v !== '-' ? v.slice(0, 8) : '-'),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="rounded-md bg-[var(--color-mist)] px-3 py-2 text-[12px] text-[var(--color-steel)]">
        当前展示的是内存缓冲（最近约 2000 条，服务重启后清空）。完整历史：生产环境按模块落盘到
        <Text code className="mx-1">logs/*.log</Text>（10MB×轮转）；本地开发可查看后端容器的 stdout 日志
        （<Text code>docker logs local-backend</Text>）。
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Select
          mode="multiple"
          allowClear
          placeholder="级别（默认全部）"
          style={{ minWidth: 260 }}
          value={levels}
          onChange={setLevels}
          options={['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map((lv) => ({ value: lv, label: lv }))}
        />
        <Input.Search
          allowClear
          placeholder="搜索消息 / 来源"
          style={{ width: 300 }}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
        <Space size={6}>
          <span className="text-[13px] text-[var(--color-steel)]">自动刷新</span>
          <Switch checked={autoRefresh} onChange={setAutoRefresh} size="small" />
        </Space>
        <Button
          icon={<ReloadOutlined />}
          onClick={() => queryClient.invalidateQueries({ queryKey: ['ops-logs'] })}
        >
          刷新
        </Button>
        <Popconfirm title="确认清空内存日志缓冲？" onConfirm={handleClear}>
          <Button danger icon={<DeleteOutlined />}>
            清空缓冲
          </Button>
        </Popconfirm>
      </div>

      <Text className="text-[12px] text-[var(--color-steel)]">
        内存环形缓冲：最多 2000 条、重启清空（不落盘，避免磁盘压力）。当前 {data?.buffer_size ?? 0} 条、
        筛选后 {data?.total ?? 0} 条；更早的日志可用 <code>docker logs local-backend</code> 查看。
      </Text>

      <Table
        columns={columns}
        dataSource={data?.items ?? []}
        rowKey={(r: LogItem) => String(r.seq)}
        size="small"
        loading={isLoading}
        scroll={{ x: 1100 }}
        pagination={{ pageSize: 25, showSizeChanger: true }}
      />
    </div>
  )
}

// ── Tab 7：数据库（只读：概览 + 表清单 + 字段详情） ────────────────

/** 字节 → 人类可读 */
function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB', 'TB']
  let value = bytes / 1024
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[index]}`
}

/** postgres 类型 → 易读简写（character varying(255) → varchar(255)） */
const TYPE_ALIAS: Record<string, string> = {
  'character varying': 'varchar',
  character: 'char',
  'timestamp with time zone': 'timestamptz',
  'timestamp without time zone': 'timestamp',
  'double precision': 'float8',
  integer: 'int',
  boolean: 'bool',
}

function shortType(dataType: string): string {
  const matched = Object.keys(TYPE_ALIAS).find((key) => dataType.startsWith(key))
  return matched ? dataType.replace(matched, TYPE_ALIAS[matched]) : dataType
}

function DbTab() {
  const [keyword, setKeyword] = useState('')
  const [detail, setDetail] = useState<DbTableItem | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['ops-db-tables'],
    queryFn: fetchDbTables,
  })

  // 字段按需加载：点开某张表才去查它的列（避免首屏背 4000+ 列）
  const { data: columns, isFetching: columnsLoading } = useQuery({
    queryKey: ['ops-db-columns', detail?.schema, detail?.table],
    queryFn: () => fetchDbTableColumns(detail?.schema ?? '', detail?.table ?? ''),
    enabled: !!detail,
  })

  const items = (data?.items ?? []).filter((item) => {
    if (!keyword) return true
    const kw = keyword.toLowerCase()
    return item.table.toLowerCase().includes(kw) || item.schema.toLowerCase().includes(kw)
  })

  const overview = data?.overview

  return (
    <div className="space-y-4">
      {overview && (
        <Card size="small">
          <Descriptions column={3} size="small">
            <Descriptions.Item label="数据库">{overview.database}</Descriptions.Item>
            <Descriptions.Item label="版本">{overview.version}</Descriptions.Item>
            <Descriptions.Item label="迁移版本">
              {overview.migration_version ?? '—'}
            </Descriptions.Item>
            <Descriptions.Item label="库大小">{formatBytes(overview.size_bytes)}</Descriptions.Item>
            <Descriptions.Item label="表数量">{overview.table_count}</Descriptions.Item>
            <Descriptions.Item label="连接数">
              {overview.connections} / {overview.max_connections}
            </Descriptions.Item>
            <Descriptions.Item label="缓存命中率">{overview.cache_hit_percent}%</Descriptions.Item>
          </Descriptions>
        </Card>
      )}

      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <Text className="text-[13px] text-[var(--color-steel)]">
          只读视图：仅展示表结构与体积，不含任何数据内容；行数为统计估算值（ANALYZE 后准确）。
        </Text>
        <Input.Search
          allowClear
          placeholder="搜索表名 / schema"
          style={{ width: 240 }}
          onSearch={(value) => setKeyword(value)}
        />
      </div>

      <Table
        rowKey={(row: DbTableItem) => `${row.schema}.${row.table}`}
        loading={isLoading}
        dataSource={items}
        size="small"
        scroll={{ x: 900 }}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        columns={[
          {
            title: '表名',
            key: 'table',
            width: 280,
            render: (_: unknown, row: DbTableItem) => (
              <div>
                <div className="font-medium text-[var(--color-charcoal)]">{row.table}</div>
                <Text className="text-[12px] text-[var(--color-steel)]">{row.schema}</Text>
              </div>
            ),
          },
          {
            title: '估算行数',
            dataIndex: 'est_rows',
            width: 110,
            align: 'right' as const,
            render: (value: number) => value.toLocaleString('zh-CN'),
          },
          {
            title: '占用',
            dataIndex: 'total_bytes',
            width: 100,
            align: 'right' as const,
            render: (value: number) => formatBytes(value),
          },
          { title: '列数', dataIndex: 'column_count', width: 80, align: 'right' as const },
          {
            title: '最后分析',
            dataIndex: 'last_analyze',
            width: 170,
            render: (value: string | null) =>
              value ? value.replace('T', ' ').slice(0, 19) : <Text type="secondary">从未</Text>,
          },
          {
            title: '操作',
            key: 'actions',
            width: 90,
            fixed: 'right' as const,
            render: (_: unknown, row: DbTableItem) => (
              <Button size="small" onClick={() => setDetail(row)}>
                详情
              </Button>
            ),
          },
        ]}
      />

      <Drawer
        title={detail ? `${detail.schema}.${detail.table}` : '表字段'}
        width={880}
        open={!!detail}
        onClose={() => setDetail(null)}
      >
        {detail && (
          <div className="space-y-3">
            <Space size="large" wrap>
              <Text className="text-[13px] text-[var(--color-steel)]">
                估算行数 {detail.est_rows.toLocaleString('zh-CN')}
              </Text>
              <Text className="text-[13px] text-[var(--color-steel)]">
                占用 {formatBytes(detail.total_bytes)}
              </Text>
              <Text className="text-[13px] text-[var(--color-steel)]">
                字段 {columns?.items.length ?? detail.column_count} 个
              </Text>
            </Space>
            <Table
              rowKey={(row: DbColumnItem) => String(row.ordinal)}
              loading={columnsLoading}
              dataSource={columns?.items ?? []}
              size="small"
              pagination={false}
              columns={[
                { title: '#', dataIndex: 'ordinal', width: 50 },
                { title: '字段名', dataIndex: 'name', width: 200 },
                {
                  title: '类型',
                  dataIndex: 'data_type',
                  width: 170,
                  render: (value: string) => <Text code>{shortType(value)}</Text>,
                },
                {
                  title: '可空',
                  dataIndex: 'nullable',
                  width: 70,
                  render: (value: boolean) => (value ? '是' : '否'),
                },
                {
                  title: '默认值',
                  dataIndex: 'default',
                  width: 130,
                  render: (value: string | null) => value ?? '-',
                },
                {
                  title: '注释',
                  dataIndex: 'comment',
                  render: (value: string | null) => value ?? '-',
                },
              ]}
            />
          </div>
        )}
      </Drawer>
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────

export default function SystemOpsClient() {
  return (
    <div className="mx-auto max-w-[1320px] px-6 py-6">
      <div className="mb-5">
        <h1 className="m-0 text-[24px] font-semibold text-[var(--color-charcoal)]">系统运维</h1>
        <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">
          服务健康、资源监控、缓存管理、后台任务清单与数据库结构。
        </p>
      </div>
      <Tabs
        defaultActiveKey="health"
        items={[
          { key: 'health', label: '服务健康', children: <HealthTab /> },
          { key: 'resources', label: '资源监控', children: <ResourcesTab /> },
          { key: 'redis', label: '缓存管理', children: <RedisTab /> },
          { key: 'tasks', label: '任务清单', children: <TasksTab /> },
          { key: 'api', label: 'API 管理', children: <ApiTab /> },
          { key: 'logs', label: '日志管理', children: <LogsTab /> },
          { key: 'db', label: '数据库', children: <DbTab /> },
        ]}
      />
    </div>
  )
}
