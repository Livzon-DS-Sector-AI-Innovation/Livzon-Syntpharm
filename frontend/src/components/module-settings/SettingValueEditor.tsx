'use client'

import { useState } from 'react'
import {
  App,
  Button,
  ColorPicker,
  Drawer,
  Input,
  InputNumber,
  Modal,
  Space,
  Switch,
  Tooltip,
  Typography,
} from 'antd'
import { CheckOutlined, CloseOutlined, EditOutlined, FormatPainterOutlined, KeyOutlined } from '@ant-design/icons'
import { updateModuleSetting } from '@/actions/module-settings'
import type { ModuleSetting } from '@/types/module-settings'
import { describeChange, formatFullTime, isBoolEnabled } from './runtimeSettingsMeta'

const { Text } = Typography
const { TextArea } = Input

interface SettingValueEditorProps {
  setting: ModuleSetting
  canManage: boolean
  onSaved: () => void
}

/** 颜色类配置（如 * _COLOR）：直接给取色器 + 色块，比让人手敲 #RRGGBB 靠谱 */
const DEFAULT_COLOR = '#FF3B30'

function isColorSetting(setting: ModuleSetting): boolean {
  return setting.value_type === 'string' && setting.key.endsWith('_COLOR')
}

/** 长文本类配置（Prompt / 指南）不适合行内输入，统一走抽屉 */
function prefersDrawer(setting: ModuleSetting): boolean {
  if (setting.value_type === 'json') return true
  const longText = (setting.value?.length ?? 0) > 60
  return longText || /PROMPT|GUIDE/.test(setting.key)
}

/**
 * 运行配置的值展示与就地编辑。
 *
 * - 布尔：开关直接切换，关闭类操作二次确认；
 * - 数字 / 短文本：行内输入，回车保存、Esc 取消；
 * - JSON / 长文本：抽屉内编辑，实时校验，非法内容禁止保存；
 * - 密钥：服务端只下发掩码，因此不提供「查看明文」，只能「重新设置」。
 */
export default function SettingValueEditor({ setting, canManage, onSaved }: SettingValueEditorProps) {
  const { message, modal } = App.useApp()
  const [saving, setSaving] = useState(false)
  const [inlineEditing, setInlineEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [secretOpen, setSecretOpen] = useState(false)
  const [secretDraft, setSecretDraft] = useState('')

  const isSecret = setting.is_secret === true
  const isBool = setting.value_type === 'bool'
  const enabled = isBoolEnabled(setting)

  const save = async (value: string) => {
    setSaving(true)
    try {
      await updateModuleSetting(setting.module, setting.key, { value })
      message.success('配置已保存')
      setInlineEditing(false)
      setDrawerOpen(false)
      setSecretOpen(false)
      setSecretDraft('')
      onSaved()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const toggleBool = (next: boolean) => {
    if (!canManage) return
    if (next) {
      void save('true')
      return
    }
    modal.confirm({
      title: `确认停用「${setting.label || setting.key}」？`,
      content: '停用后本模块的相关自动化或功能会立即停止，确认继续？',
      okText: '停用',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => save('false'),
    })
  }

  const startInlineEdit = () => {
    setDraft(setting.value ?? '')
    setInlineEditing(true)
  }

  const metaLine = (
    <Tooltip title={formatFullTime(setting.updated_at)}>
      <span className="text-[11px] text-[var(--color-stone)]">{describeChange(setting)}</span>
    </Tooltip>
  )

  // ── 密钥类：只展示掩码 + 重新设置 ──
  if (isSecret) {
    return (
      <div className="flex flex-col items-start gap-1 md:items-end">
        <Space size={6}>
          <KeyOutlined className="text-[var(--color-stone)]" />
          <Text code className="text-[12px]">
            {setting.has_value ? (setting.value_masked ?? '已配置') : '未配置'}
          </Text>
          {canManage && (
            <Button size="small" type="link" onClick={() => setSecretOpen(true)}>
              {setting.has_value ? '重新设置' : '设置'}
            </Button>
          )}
        </Space>
        {metaLine}
        <Modal
          title={`设置「${setting.label || setting.key}」`}
          open={secretOpen}
          onCancel={() => setSecretOpen(false)}
          onOk={() => {
            if (!secretDraft.trim()) {
              message.warning('请输入新的密钥值')
              return
            }
            void save(secretDraft)
          }}
          confirmLoading={saving}
          okText="保存"
          cancelText="取消"
          width="min(520px, calc(100vw - 24px))"
        >
          <Text type="secondary" className="text-[12px]">
            出于安全考虑，已保存的密钥不会回显。填写新值后保存会整体替换；留空离开不会改动原值。
          </Text>
          <Input.Password
            className="mt-3"
            value={secretDraft}
            onChange={(event) => setSecretDraft(event.target.value)}
            placeholder="粘贴新的密钥值"
            autoComplete="new-password"
          />
          {setting.value_hint && (
            <div className="mt-2 text-[12px] text-[var(--color-steel)]">{setting.value_hint}</div>
          )}
        </Modal>
      </div>
    )
  }

  // ── 布尔：开关直接切换 ──
  if (isBool) {
    return (
      <div className="flex flex-col items-start gap-1 md:items-end">
        <Switch
          checked={enabled}
          loading={saving}
          disabled={!canManage}
          checkedChildren="已启用"
          unCheckedChildren="已停用"
          onChange={toggleBool}
        />
        {metaLine}
      </div>
    )
  }

  // ── 颜色类（*_COLOR）：取色器直选，避免手敲 #RRGGBB ──
  if (isColorSetting(setting)) {
    const color = setting.value || DEFAULT_COLOR
    return (
      <div className="flex flex-col items-start gap-1 md:items-end">
        <Space size={6}>
          <span
            className="inline-block h-4 w-4 rounded align-middle"
            style={{ background: color, border: '1px solid #d9d9d9' }}
          />
          <Text code className="text-[12px]">
            {setting.value || '未设置'}
          </Text>
          {canManage && (
            <ColorPicker
              size="small"
              format="hex"
              disabledAlpha
              value={color}
              onChangeComplete={(picked) => void save(picked.toHexString().toUpperCase())}
            />
          )}
        </Space>
        {setting.value_hint && (
          <span className="text-[11px] text-[var(--color-steel)]">{setting.value_hint}</span>
        )}
        {metaLine}
      </div>
    )
  }

  // ── 数字 / 短文本：行内编辑 ──
  if (inlineEditing && !prefersDrawer(setting)) {
    return (
      <div className="flex flex-col items-start gap-1 md:items-end">
        <Space.Compact size="small">
          {setting.value_type === 'int' ? (
            <InputNumber
              size="small"
              autoFocus
              style={{ width: 160 }}
              value={draft === '' ? null : Number(draft)}
              onChange={(value) => setDraft(value === null || value === undefined ? '' : String(value))}
              onPressEnter={() => void save(draft)}
            />
          ) : (
            <Input
              size="small"
              autoFocus
              style={{ width: 220 }}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onPressEnter={() => void save(draft)}
              onKeyDown={(event) => {
                if (event.key === 'Escape') setInlineEditing(false)
              }}
            />
          )}
          <Button
            size="small"
            type="primary"
            icon={<CheckOutlined />}
            loading={saving}
            onClick={() => void save(draft)}
          />
          <Button size="small" icon={<CloseOutlined />} onClick={() => setInlineEditing(false)} />
        </Space.Compact>
        {setting.value_hint && (
          <span className="text-[11px] text-[var(--color-steel)]">{setting.value_hint}</span>
        )}
      </div>
    )
  }

  // ── 其余（数字 / 文本 / JSON / 长文本）：展示值 + 编辑入口 ──
  const display = (
    <Text code className="text-[12px] break-all">
      {setting.value?.trim() ? setting.value : <span className="text-[var(--color-steel)]">未设置</span>}
    </Text>
  )

  return (
    <div className="flex max-w-full flex-col items-start gap-1 md:items-end">
      <Space size={6} className="max-w-full justify-end">
        <div className="max-w-[420px] text-right">{display}</div>
        {canManage && (
          <Button
            size="small"
            type="link"
            icon={<EditOutlined />}
            onClick={() => {
              if (prefersDrawer(setting)) {
                setDraft(setting.value ?? '')
                setDrawerOpen(true)
              } else {
                startInlineEdit()
              }
            }}
          >
            编辑
          </Button>
        )}
      </Space>
      {metaLine}

      <Drawer
        title={`编辑「${setting.label || setting.key}」`}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        width="min(640px, 92vw)"
        extra={
          <Space>
            {setting.value_type === 'json' && (
              <Button
                icon={<FormatPainterOutlined />}
                onClick={() => {
                  try {
                    setDraft(JSON.stringify(JSON.parse(draft), null, 2))
                    message.success('已格式化')
                  } catch {
                    message.error('当前内容不是合法 JSON，无法格式化')
                  }
                }}
              >
                格式化
              </Button>
            )}
            <Button type="primary" loading={saving} onClick={() => void save(draft)}>
              保存
            </Button>
          </Space>
        }
      >
        <div className="mb-2 text-[12px] text-[var(--color-steel)]">
          <Text code className="text-[11px]">{setting.key}</Text>
          {setting.value_hint ? ` · ${setting.value_hint}` : ''}
        </div>
        <TextArea
          rows={setting.value_type === 'json' ? 16 : 8}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          className="font-mono text-[12px]"
        />
        {setting.value_type === 'json' && <JsonHint value={draft} />}
        {setting.description && (
          <div className="mt-3 text-[12px] text-[var(--color-steel)]">{setting.description}</div>
        )}
      </Drawer>
    </div>
  )
}

/** JSON 实时校验提示：合法时给字段数，非法时给行列号 */
function JsonHint({ value }: { value: string }) {
  if (!value.trim()) {
    return <div className="mt-2 text-[12px] text-[var(--color-warning)]">内容为空，保存会失败</div>
  }
  let sizeText: string | null = null
  let errorText: string | null = null
  try {
    const parsed: unknown = JSON.parse(value)
    sizeText = Array.isArray(parsed)
      ? `${parsed.length} 个元素`
      : `${Object.keys(parsed as object).length} 个字段`
  } catch (error) {
    errorText = describeJsonError(value, error)
  }

  if (errorText) {
    return <div className="mt-2 text-[12px] text-[var(--color-error)]">JSON 不合法：{errorText}</div>
  }
  return <div className="mt-2 text-[12px] text-[var(--color-success)]">JSON 合法，共 {sizeText}</div>
}

/** 把原生 JSON 报错换算成「第 X 行第 Y 列」，便于直接定位 */
function describeJsonError(value: string, error: unknown): string {
  const raw = error instanceof Error ? error.message : '格式不正确'
  const position = /position (\d+)/.exec(raw)
  if (!position) return raw
  const index = Math.min(Number(position[1]), value.length)
  const before = value.slice(0, index)
  const line = before.split('\n').length
  const column = index - before.lastIndexOf('\n')
  return `第 ${line} 行第 ${column} 列附近有语法错误`
}