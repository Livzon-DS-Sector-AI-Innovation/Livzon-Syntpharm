'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeftOutlined } from '@ant-design/icons'
import {
  Alert,
  App,
  AutoComplete,
  Button,
  Card,
  Col,
  Divider,
  InputNumber,
  Row,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  theme,
} from 'antd'
import { updateModuleSetting } from '@/actions/module-settings'
import { testReportGenModel } from '@/actions/research/report-gen'
import type { ModuleSetting } from '@/types/module-settings'
import type { LLMConfig } from '@/types/settings'
import {
  REPORT_GEN_MODEL_SLOTS,
  REPORT_GEN_TOOLS,
  modelLabel,
  parseDisabledTools,
  pickReportGenModels,
  type ReportGenModelSlot,
} from '@/types/research/report-gen'

const MODULE = 'research'

const MODEL_KEYS: Record<ReportGenModelSlot, string> = {
  main: 'REPORT_GEN_MODEL',
  structure: 'REPORT_GEN_STRUCTURE_MODEL',
  fallback: 'REPORT_GEN_FALLBACK_MODEL',
}

const DISABLED_TOOLS_KEY = 'REPORT_GEN_DISABLED_TOOLS'
const TOOL_MODE_KEY = 'REPORT_GEN_TOOL_MODE'

interface NumericField {
  key: string
  label: string
  unit: string
  min: number
  max: number
  hint: string
}

const NUMERIC_FIELDS: NumericField[] = [
  { key: 'REPORT_GEN_MAX_ROUNDS', label: '最大轮次', unit: '轮', min: 2, max: 60, hint: 'Agent 循环上限，超过即收成稿。' },
  {
    key: 'REPORT_GEN_JOB_TIMEOUT_SECONDS',
    label: '整任务超时',
    unit: '秒',
    min: 120,
    max: 10800,
    hint: '超时判失败；含解析、检索、渲染全过程。',
  },
  {
    key: 'REPORT_GEN_LLM_TIMEOUT_SECONDS',
    label: '单次调用超时',
    unit: '秒',
    min: 30,
    max: 900,
    hint: '单次模型请求上限，超时触发兜底档位。',
  },
  { key: 'REPORT_GEN_KB_TOP_K', label: '检索条数', unit: '条', min: 1, max: 30, hint: '每次知识库检索返回的最大片段数。' },
]

const TOOL_MODE_OPTIONS = [
  { value: 'auto', label: 'auto（先试 tools，不支持则降级 JSON）' },
  { value: 'tools', label: 'tools（只走 function calling）' },
  { value: 'json', label: 'json（只走 JSON 协议）' },
]

interface Props {
  settings: ModuleSetting[]
  llmConfigs: LLMConfig[]
  canManage: boolean
}

function initialModels(settings: ModuleSetting[]): Record<ReportGenModelSlot, string> {
  const { main, structure, fallback } = pickReportGenModels(settings)
  return { main, structure, fallback }
}

function initialNumbers(settings: ModuleSetting[]): Record<string, number> {
  const result: Record<string, number> = {}
  for (const field of NUMERIC_FIELDS) {
    const raw = settings.find((item) => item.key === field.key)?.value
    const parsed = Number(raw)
    result[field.key] = Number.isFinite(parsed) && raw !== '' ? parsed : field.min
  }
  return result
}

export default function ReportGenSettingsClient({ settings, llmConfigs, canManage }: Props) {
  const router = useRouter()
  const { message } = App.useApp()
  const { token } = theme.useToken()

  const existingKeys = useMemo(() => new Set(settings.map((item) => item.key)), [settings])
  const savedModels = useMemo(() => initialModels(settings), [settings])

  const [models, setModels] = useState<Record<ReportGenModelSlot, string>>(() => initialModels(settings))
  const [numbers, setNumbers] = useState<Record<string, number>>(() => initialNumbers(settings))
  const [toolMode, setToolMode] = useState(() => settings.find((item) => item.key === TOOL_MODE_KEY)?.value || 'auto')
  const [disabledTools, setDisabledTools] = useState<string[]>(() =>
    parseDisabledTools(settings.find((item) => item.key === DISABLED_TOOLS_KEY)?.value)
  )
  const [baseline, setBaseline] = useState(() =>
    JSON.stringify({
      models: initialModels(settings),
      numbers: initialNumbers(settings),
      toolMode: settings.find((item) => item.key === TOOL_MODE_KEY)?.value || 'auto',
      disabledTools: parseDisabledTools(settings.find((item) => item.key === DISABLED_TOOLS_KEY)?.value),
    })
  )
  const [saving, setSaving] = useState(false)
  const [testingSlot, setTestingSlot] = useState<ReportGenModelSlot | null>(null)

  const current = JSON.stringify({ models, numbers, toolMode, disabledTools })
  const dirty = current !== baseline
  const missingKeys = useMemo(
    () =>
      [...Object.values(MODEL_KEYS), DISABLED_TOOLS_KEY, TOOL_MODE_KEY, ...NUMERIC_FIELDS.map((f) => f.key)].filter(
        (key) => !existingKeys.has(key)
      ),
    [existingKeys]
  )

  const modelOptions = useMemo(
    () =>
      llmConfigs.map((config) => ({
        value: config.config_name,
        label: `${config.config_name} · ${config.model_name}`,
      })),
    [llmConfigs]
  )

  function collectChanges(): { key: string; value: string }[] {
    const changes: { key: string; value: string }[] = []
    for (const slot of REPORT_GEN_MODEL_SLOTS) {
      const key = MODEL_KEYS[slot.slot]
      const next = (models[slot.slot] ?? '').trim()
      if (next !== savedModels[slot.slot]) changes.push({ key, value: next })
    }
    for (const field of NUMERIC_FIELDS) {
      const saved = settings.find((item) => item.key === field.key)?.value ?? ''
      // 按数值比较：库里可能存 "2400" 或 "2400.0"，字符串直接比会永远判成已修改
      if (Number(saved) !== numbers[field.key]) changes.push({ key: field.key, value: String(numbers[field.key]) })
    }
    const savedMode = settings.find((item) => item.key === TOOL_MODE_KEY)?.value || 'auto'
    if (toolMode !== savedMode) changes.push({ key: TOOL_MODE_KEY, value: toolMode })
    const savedDisabled = settings.find((item) => item.key === DISABLED_TOOLS_KEY)?.value ?? ''
    const nextDisabled = disabledTools.join(',')
    if (parseDisabledTools(savedDisabled).join(',') !== nextDisabled) {
      changes.push({ key: DISABLED_TOOLS_KEY, value: nextDisabled })
    }
    return changes
  }

  function resetAll() {
    setModels(initialModels(settings))
    setNumbers(initialNumbers(settings))
    setToolMode(settings.find((item) => item.key === TOOL_MODE_KEY)?.value || 'auto')
    setDisabledTools(parseDisabledTools(settings.find((item) => item.key === DISABLED_TOOLS_KEY)?.value))
  }

  async function handleSave() {
    const changes = collectChanges()
    if (changes.length === 0) {
      message.info('没有需要保存的修改')
      return
    }
    const blocked = changes.filter((item) => !existingKeys.has(item.key))
    if (blocked.length > 0) {
      message.error(`配置键尚未初始化：${blocked.map((item) => item.key).join(', ')}`)
      return
    }
    setSaving(true)
    try {
      for (const change of changes) {
        const result = await updateModuleSetting(MODULE, change.key, { value: change.value })
        if (!result?.data) throw new Error(`保存 ${change.key} 失败`)
      }
      setBaseline(current)
      message.success('配置已保存，之后新建的任务生效')
      router.refresh()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  async function handleTest(slot: ReportGenModelSlot) {
    setTestingSlot(slot)
    try {
      const data = await testReportGenModel(slot)
      if (data?.ok) {
        message.success(`${data.model ?? '模型'} 连通正常 · ${data.latency_ms ?? '-'}ms`)
      } else if (data?.detail?.includes('未单独配置')) {
        // 留空档位没有独立端点可测，不算失败
        message.info(data.detail)
      } else {
        message.error(`连通失败：${data?.detail || '未知原因'}`)
      }
    } catch (error) {
      message.error(error instanceof Error ? error.message : '连通测试失败')
    } finally {
      setTestingSlot(null)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <Card size="small">
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <Typography.Title level={4} style={{ margin: 0 }}>
              报告生成配置
            </Typography.Title>
            <Space size={6} wrap style={{ marginTop: 8 }}>
              <Typography.Text type="secondary">当前：</Typography.Text>
              <Tag color="blue">正文生成 {modelLabel(savedModels.main)}</Tag>
              <Tag color="cyan">结构识别 {modelLabel(savedModels.structure)}</Tag>
              <Tag color={savedModels.fallback ? 'orange' : 'default'}>兜底 {modelLabel(savedModels.fallback)}</Tag>
            </Space>
            <div style={{ marginTop: 6 }}>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                保存后只影响之后新建的任务；已在跑或已结束的任务沿用创建时的模型快照。
              </Typography.Text>
            </div>
          </div>
          <Link href="/research/reports">
            <ArrowLeftOutlined /> 返回报告列表
          </Link>
        </div>
      </Card>

      {missingKeys.length > 0 && (
        <Alert
          type="warning"
          showIcon
          message="部分配置键未初始化"
          description={`缺少 ${missingKeys.join('、')}，需先执行 backend/scripts/seed/seed_module_settings.py 再回到本页保存。`}
        />
      )}

      <Card
        size="small"
        title="模型档位"
        extra={<Typography.Text type="secondary">留空 = 继承（结构档复用正文生成档）</Typography.Text>}
      >
        <Row gutter={[16, 16]}>
          {REPORT_GEN_MODEL_SLOTS.map((item) => (
            <Col xs={24} lg={8} key={item.slot}>
              <Card
                size="small"
                style={{ height: '100%', borderColor: token.colorBorderSecondary }}
                title={
                  <Space size={6}>
                    <span>{item.title}</span>
                    {item.slot === 'fallback' && <Tag color="orange">自动切换</Tag>}
                  </Space>
                }
                extra={
                  <Button
                    size="small"
                    loading={testingSlot === item.slot}
                    disabled={!canManage}
                    onClick={() => handleTest(item.slot)}
                  >
                    测试连通
                  </Button>
                }
              >
                <AutoComplete
                  style={{ width: '100%' }}
                  value={models[item.slot]}
                  options={modelOptions}
                  allowClear
                  placeholder={item.slot === 'structure' ? '留空 = 复用正文生成档' : '留空 = 全局默认'}
                  onChange={(value: string) => setModels((prev) => ({ ...prev, [item.slot]: value ?? '' }))}
                  filterOption={(input, option) => {
                    const text = `${option?.label ?? ''}${option?.value ?? ''}`.toLowerCase()
                    return text.includes(input.toLowerCase())
                  }}
                  disabled={!canManage}
                />
                <Typography.Paragraph type="secondary" style={{ fontSize: 12, margin: '8px 0 4px' }}>
                  {item.description}
                </Typography.Paragraph>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  当前生效：
                  {savedModels[item.slot]
                    ? savedModels[item.slot]
                    : item.slot === 'structure'
                      ? `复用正文生成档（${modelLabel(savedModels.main)}）`
                      : modelLabel(savedModels[item.slot])}
                </Typography.Text>
              </Card>
            </Col>
          ))}
        </Row>
        <Typography.Paragraph type="secondary" style={{ fontSize: 12, margin: '12px 0 0' }}>
          测试连通使用「已保存」的配置；未保存的下拉修改不会参与测试。结构识别模型改动后，需在模板侧重新解析才会重识别已有母本。
        </Typography.Paragraph>
      </Card>

      <Card size="small" title="运行参数">
        <Row gutter={[16, 12]}>
          {NUMERIC_FIELDS.map((field) => (
            <Col xs={24} md={12} key={field.key}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <Typography.Text>{field.label}</Typography.Text>
                <Space size={8}>
                  <InputNumber
                    min={field.min}
                    max={field.max}
                    value={numbers[field.key]}
                    disabled={!canManage}
                    onChange={(value) =>
                      setNumbers((prev) => ({ ...prev, [field.key]: typeof value === 'number' ? value : field.min }))
                    }
                  />
                  <Typography.Text type="secondary">{field.unit}</Typography.Text>
                </Space>
                <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                  {field.hint}
                </Typography.Text>
              </div>
            </Col>
          ))}
          <Col xs={24} md={12}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <Typography.Text>工具协议</Typography.Text>
              <Select
                value={toolMode}
                options={TOOL_MODE_OPTIONS}
                disabled={!canManage}
                onChange={(value) => setToolMode(value)}
              />
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                模型不支持 function calling 时建议保持 auto。
              </Typography.Text>
            </div>
          </Col>
        </Row>
      </Card>

      <Card
        size="small"
        title="Agent 工具"
        extra={<Typography.Text type="secondary">关闭后模型看不到该工具，也无法调用</Typography.Text>}
      >
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          {REPORT_GEN_TOOLS.map((tool, index) => (
            <div key={tool.name}>
              {index > 0 && <Divider style={{ margin: '10px 0' }} />}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16 }}>
                <div>
                  <Space size={8}>
                    <Typography.Text strong>{tool.label}</Typography.Text>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {tool.name}
                    </Typography.Text>
                    {tool.locked && <Tag>常开</Tag>}
                  </Space>
                  <div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {tool.description}
                    </Typography.Text>
                  </div>
                </div>
                <Switch
                  checked={!disabledTools.includes(tool.name)}
                  disabled={!canManage || tool.locked}
                  onChange={(checked) =>
                    setDisabledTools((prev) =>
                      checked ? prev.filter((name) => name !== tool.name) : [...prev, tool.name]
                    )
                  }
                />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div
        style={{
          position: 'sticky',
          bottom: 0,
          zIndex: 10,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 12,
          padding: '12px 16px',
          background: token.colorBgContainer,
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          boxShadow: token.boxShadowTertiary,
        }}
      >
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {canManage ? (dirty ? '有未保存的修改' : '配置与线上一致') : '当前账号只有查看权限'}
        </Typography.Text>
        <Space>
          <Button onClick={resetAll} disabled={!canManage || !dirty || saving}>
            重置
          </Button>
          <Button type="primary" loading={saving} disabled={!canManage || !dirty} onClick={handleSave}>
            保存配置
          </Button>
        </Space>
      </div>
    </div>
  )
}