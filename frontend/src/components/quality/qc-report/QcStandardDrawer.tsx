'use client'

import { useEffect, useMemo, useState } from 'react'
import { fetchQcItems, rejudgeQcProduct, updateQcItem } from '@/lib/api/client/qc-report'
import type { QcItem, QcItemUpdatePayload } from '@/types/qc-report'

interface Props {
  open: boolean
  productId: string
  productName: string
  onClose: () => void
  onRejudged: () => void
}

type Layer = 'legal' | 'internal' | 'sigma'

const LAYERS: { key: Layer; label: string; dot: string; field: keyof QcItem }[] = [
  { key: 'legal', label: '法定标准', dot: '#D64545', field: 'legal_text' },
  { key: 'internal', label: '内控标准', dot: '#D97A0B', field: 'internal_text' },
  { key: 'sigma', label: '3σ 趋势限', dot: '#C9A227', field: 'sigma_text' },
]

/** 数值区间统一成「下限 ~ 上限」，比较符后补空格；文字保持原样。 */
function renderStandard(text: string | null) {
  if (!text) return null
  const normalized = text
    .replace(/[～~]/g, ' ~ ')
    .replace(/^([≤≥<>])\s*/, '$1 ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!/\d/.test(normalized)) {
    return <span className="qc-std-text">{normalized}</span>
  }

  return (
    <span className="qc-std-num">
      {normalized.split(/( ~ )/).map((part, index) =>
        part === ' ~ ' ? (
          <span key={index} className="qc-std-tilde">
            ~
          </span>
        ) : (
          <span key={index}>{part}</span>
        ),
      )}
    </span>
  )
}

export function QcStandardDrawer({
  open,
  productId,
  productName,
  onClose,
  onRejudged,
}: Props) {
  const [items, setItems] = useState<QcItem[]>([])
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [editing, setEditing] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rejudged, setRejudged] = useState<number | null>(null)

  useEffect(() => {
    if (!open) return
    let active = true
    fetchQcItems(productId)
      .then((data) => {
        if (!active) return
        setItems(data)
        setDraft({})
      })
      .catch((err: unknown) => {
        if (!active) return
        setError(err instanceof Error ? err.message : '标准加载失败')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [open, productId])

  const changed = useMemo(() => {
    const map: Record<string, Partial<Record<Layer, string | null>>> = {}
    Object.entries(draft).forEach(([key, value]) => {
      const [itemId, layer] = key.split('::') as [string, Layer]
      const item = items.find((entry) => entry.id === itemId)
      if (!item) return
      const field = LAYERS.find((entry) => entry.key === layer)?.field
      if (!field) return
      if (((item[field] as string | null) ?? '') !== value) {
        map[itemId] = { ...map[itemId], [layer]: value }
      }
    })
    return map
  }, [draft, items])

  const changedCount = Object.keys(changed).length

  function valueOf(item: QcItem, layer: Layer): string {
    const key = `${item.id}::${layer}`
    if (key in draft) return draft[key]
    const field = LAYERS.find((entry) => entry.key === layer)!.field
    return ((item[field] as string | null) ?? '') || ''
  }

  function commitCell(item: QcItem, layer: Layer, value: string) {
    setDraft((prev) => ({ ...prev, [`${item.id}::${layer}`]: value.trim() }))
    setEditing(null)
  }

  function close() {
    if (changedCount > 0 && !window.confirm(`还有 ${changedCount} 项标准没保存，确定关闭？`)) return
    setItems([])
    setDraft({})
    setEditing(null)
    setError(null)
    setRejudged(null)
    setLoading(true)
    onClose()
  }

  async function save() {
    if (changedCount === 0 || saving) return
    setSaving(true)
    setError(null)
    try {
      for (const [itemId, layers] of Object.entries(changed)) {
        const payload: QcItemUpdatePayload = {}
        if ('legal' in layers) payload.legal_text = layers.legal ?? ''
        if ('internal' in layers) payload.internal_text = layers.internal ?? ''
        if ('sigma' in layers) payload.sigma_text = layers.sigma ?? ''
        await updateQcItem(itemId, payload)
      }
      const result = await rejudgeQcProduct(productId)
      setRejudged(result.changed_batch_count)
      const fresh = await fetchQcItems(productId)
      setItems(fresh)
      setDraft({})
      onRejudged()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (!open) return null

  function renderCell(item: QcItem, layer: Layer) {
    const key = `${item.id}::${layer}`
    const value = valueOf(item, layer)
    if (editing === key) {
      return (
        <input
          autoFocus
          defaultValue={value}
          onBlur={(event) => commitCell(item, layer, event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') commitCell(item, layer, event.currentTarget.value)
            if (event.key === 'Escape') setEditing(null)
          }}
          className="qc-std-input"
        />
      )
    }

    // 该层没设、但法定有值 → 视为沿用法定；法定本身为空 → 仅记录项
    if (!value) {
      const legal = valueOf(item, 'legal')
      const text =
        layer !== 'legal' && legal ? (
          <span className="qc-std-empty">同法定标准一致</span>
        ) : (
          <span className="qc-std-dash">—</span>
        )
      return (
        <button type="button" onClick={() => setEditing(key)} className="qc-std-cell">
          {text}
        </button>
      )
    }

    return (
      <button
        type="button"
        onClick={() => setEditing(key)}
        className="qc-std-cell"
        title={value}
      >
        {renderStandard(value)}
      </button>
    )
  }

  return (
    <div className="fixed inset-0 z-[70]">
      <button type="button" aria-label="关闭" onClick={close} className="qc-std-mask" />

      <aside className="qc-std-panel" role="dialog" aria-label="检验标准">
        <header className="qc-std-head">
          <div>
            <h2 className="qc-std-title">检验标准 · {productName}</h2>
            <p className="qc-std-sub">
              共 <b>{items.length || '—'}</b> 个检验项目
            </p>
          </div>
          <button type="button" onClick={close} className="qc-std-close" aria-label="关闭">
            ✕
          </button>
        </header>

        <div className="qc-std-body">
          {loading ? (
            <p className="px-6 py-12 text-center text-[12.5px] text-[#9CA3AF]">正在加载标准…</p>
          ) : items.length === 0 ? (
            <p className="px-6 py-12 text-center text-[12.5px] text-[#9CA3AF]">该品种还没有检验项目</p>
          ) : (
            <table className="qc-std-table">
              <colgroup>
                <col style={{ width: 170 }} />
                <col />
                <col style={{ width: 150 }} />
                <col style={{ width: 150 }} />
              </colgroup>
              <thead>
                <tr>
                  <th>检验项目</th>
                  {LAYERS.map((layer) => (
                    <th key={layer.key}>
                      <span className="qc-std-dot" style={{ backgroundColor: layer.dot }} />
                      {layer.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
                  <tr
                    key={item.id}
                    className="qc-std-row"
                    style={{ animationDelay: `${Math.min(index * 20, 320)}ms` }}
                  >
                    <td>
                      <span className="qc-std-item" title={item.standard_item_name ?? undefined}>
                        {item.item_name.replace(/\n/g, '')}
                      </span>
                      {(item.sub_label || item.unit) && (
                        <span className="qc-std-item-sub">
                          {item.sub_label ?? `单位 ${item.unit}`}
                        </span>
                      )}
                    </td>
                    {LAYERS.map((layer) => (
                      <td key={layer.key}>{renderCell(item, layer.key)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <footer className="qc-std-foot">
          <div className="min-w-0">
            <span className="qc-std-warn">
              <svg viewBox="0 0 16 16" className="h-3.5 w-3.5 shrink-0" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M8 2.6 14 13H2L8 2.6Z" strokeLinejoin="round" />
                <path d="M8 6.4v3M8 11.2v.6" strokeLinecap="round" />
              </svg>
              保存后将按新标准重新判定全部在库批次历史数据
            </span>
            {error && <p className="mt-1 text-[11.5px] text-[#D64545]">{error}</p>}
            {rejudged !== null && (
              <p className="mt-1 text-[11.5px] text-[#1E8E5A]">
                已重新判定，<b className="qc-num">{rejudged}</b> 个批次的等级有变化
              </p>
            )}
            {changedCount > 0 && (
              <p className="mt-1 text-[11.5px] text-[#4F46C9]">已修改 {changedCount} 项</p>
            )}
          </div>

          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={close}
              className="qc-btn"
              style={{ height: 36 }}
            >
              取消
            </button>
            <button
              type="button"
              onClick={() => void save()}
              disabled={changedCount === 0 || saving}
              className="qc-btn qc-std-save"
              style={{ height: 36 }}
            >
              {saving ? '重新判定中…' : '保存并重新判定'}
            </button>
          </div>
        </footer>
      </aside>
    </div>
  )
}
