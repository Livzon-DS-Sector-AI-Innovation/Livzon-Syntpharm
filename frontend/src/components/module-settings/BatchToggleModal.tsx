'use client'

import { useState } from 'react'
import { Alert, App, Button, Empty, Modal, Switch, Tag, Typography } from 'antd'
import { batchUpdateModuleSettings } from '@/actions/module-settings'
import type { ModuleSetting, ModuleSettingBatchResult } from '@/types/module-settings'
import { isBoolEnabled, settingGroup, settingTitle } from './runtimeSettingsMeta'

const { Text } = Typography

interface BatchToggleModalProps {
  settings: ModuleSetting[]
  onClose: () => void
  onSaved: () => void
}

/**
 * 批量启停布尔配置：一次请求提交所有改动项，失败项逐条返回原因。
 *
 * 只提交被改动的项，避免把没碰的配置也写一遍 updated_by。
 * 组件由父级按需挂载（`{open && <BatchToggleModal/>}`），
 * 因此草稿用 useState 初始化即可，不需要在 effect 里同步 props。
 */
export default function BatchToggleModal({ settings, onClose, onSaved }: BatchToggleModalProps) {
  const { message } = App.useApp()
  const [draft, setDraft] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {}
    for (const setting of settings) initial[setting.key] = isBoolEnabled(setting)
    return initial
  })
  const [saving, setSaving] = useState(false)
  const [result, setResult] = useState<ModuleSettingBatchResult | null>(null)

  const changed = settings.filter(
    (setting) => (draft[setting.key] ?? isBoolEnabled(setting)) !== isBoolEnabled(setting),
  )

  const submit = async () => {
    if (changed.length === 0) {
      message.info('没有需要保存的改动')
      return
    }
    setSaving(true)
    try {
      const response = await batchUpdateModuleSettings({
        items: changed.map((setting) => ({
          module: setting.module,
          key: setting.key,
          value: draft[setting.key] ? 'true' : 'false',
        })),
      })
      setResult(response.data)
      onSaved()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '批量保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal
      title="批量启停配置项"
      open
      onCancel={onClose}
      destroyOnHidden
      footer={
        result
          ? [
              <Button key="close" type="primary" onClick={onClose}>
                知道了
              </Button>,
            ]
          : [
              <Button key="cancel" onClick={onClose}>
                取消
              </Button>,
              <Button
                key="ok"
                type="primary"
                loading={saving}
                disabled={changed.length === 0}
                onClick={() => void submit()}
              >
                {changed.length > 0 ? `保存 ${changed.length} 项改动` : '保存'}
              </Button>,
            ]
      }
      width="min(720px, calc(100vw - 24px))"
    >
      {result ? (
        <BatchOutcome result={result} />
      ) : settings.length === 0 ? (
        <Empty description="本模块没有开关类配置" />
      ) : (
        <>
          <Text type="secondary" className="text-[12px]">
            只提交被改动的项；保存后逐条返回结果，失败项不会影响其他配置。
          </Text>
          <div className="mt-3 max-h-[50vh] overflow-auto">
            {settings.map((setting) => {
              const value = draft[setting.key] ?? isBoolEnabled(setting)
              const dirty = value !== isBoolEnabled(setting)
              return (
                <div
                  key={setting.key}
                  className="flex items-center justify-between gap-3 border-b border-[var(--color-hairline-soft)] py-2 last:border-b-0"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-[13px] text-[var(--color-charcoal)]">
                        {settingTitle(setting)}
                      </span>
                      <Tag className="!mr-0">{settingGroup(setting)}</Tag>
                      {dirty && (
                        <Tag color="gold" className="!mr-0">
                          待保存
                        </Tag>
                      )}
                    </div>
                    <div className="truncate font-mono text-[11px] text-[var(--color-steel)]">{setting.key}</div>
                  </div>
                  <Switch
                    checked={value}
                    onChange={(next) => setDraft((prev) => ({ ...prev, [setting.key]: next }))}
                  />
                </div>
              )
            })}
          </div>
        </>
      )}
    </Modal>
  )
}

/** 批量结果：成功数 + 失败项逐条原因 */
function BatchOutcome({ result }: { result: ModuleSettingBatchResult }) {
  return (
    <>
      <Alert
        type={result.failed.length ? 'warning' : 'success'}
        showIcon
        title={
          result.failed.length
            ? `成功 ${result.succeeded.length} 项，失败 ${result.failed.length} 项`
            : `成功 ${result.succeeded.length} 项`
        }
        className="mb-3"
      />
      {result.failed.length > 0 && (
        <ul className="max-h-[300px] space-y-1 overflow-auto text-[13px]">
          {result.failed.map((item) => (
            <li key={`${item.module}:${item.key}`}>
              <Text code>{item.label || item.key}</Text>：{item.reason}
            </li>
          ))}
        </ul>
      )}
    </>
  )
}