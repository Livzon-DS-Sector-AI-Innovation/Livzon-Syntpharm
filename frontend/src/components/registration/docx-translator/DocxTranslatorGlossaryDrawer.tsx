'use client'

import { useEffect, useRef, useState } from 'react'
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query'
import { App, Drawer, Input, Switch, Table, Upload } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  fetchGlossaryTerms,
  glossaryExportUrl,
  importGlossaryFile,
} from '@/lib/api/client/docx-translator'
import { createGlossaryTerm, deleteGlossaryTerm, updateGlossaryTerm } from '@/actions/docx-translator'
import type { DocxGlossaryTerm, DocxGlossaryTermSource } from '@/types/docx-translator'
import ui from '../registration-ui.module.css'
import styles from './docx-translator.module.css'

const SOURCE_LABEL: Record<DocxGlossaryTermSource, string> = {
  builtin: '内置',
  import: '导入',
  manual: '手动',
}
const SOURCE_CLASS: Record<DocxGlossaryTermSource, string> = {
  builtin: styles.srcBuiltin,
  import: styles.srcImport,
  manual: styles.srcManual,
}

const PAGE_SIZE = 50

interface Draft {
  term_en: string
  term_zh: string
}

export function DocxTranslatorGlossaryDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [editId, setEditId] = useState<string | 'new' | null>(null)
  const [draft, setDraft] = useState<Draft>({ term_en: '', term_zh: '' })
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  const termsQuery = useInfiniteQuery({
    queryKey: ['docx-glossary', keyword],
    queryFn: ({ pageParam }) => fetchGlossaryTerms({ keyword, page: pageParam, pageSize: PAGE_SIZE }),
    initialPageParam: 1,
    getNextPageParam: (lastPage, allPages) => {
      const loaded = allPages.reduce((sum, page) => sum + page.items.length, 0)
      return loaded < lastPage.total ? allPages.length + 1 : undefined
    },
    enabled: open,
  })

  const items = termsQuery.data?.pages.flatMap(page => page.items) ?? []
  const total = termsQuery.data?.pages[0]?.total ?? 0
  const hasNextPage = Boolean(termsQuery.hasNextPage)
  const isFetchingNextPage = termsQuery.isFetchingNextPage
  const fetchNextPage = termsQuery.fetchNextPage

  // 滚动到底自动加载下一页：哨兵放在表格末尾，root 取抽屉滚动容器
  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const node = loadMoreRef.current
    if (!open || !node || !hasNextPage) return
    const scrollRoot = node.closest('.ant-drawer-body')
    const observer = new IntersectionObserver(
      entries => {
        if (entries[0]?.isIntersecting && !isFetchingNextPage) {
          void fetchNextPage()
        }
      },
      { root: scrollRoot instanceof HTMLElement ? scrollRoot : null, rootMargin: '120px' },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [open, hasNextPage, isFetchingNextPage, fetchNextPage])

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['docx-glossary'] })
  }

  const startEdit = (row: DocxGlossaryTerm) => {
    setConfirmId(null)
    setEditId(row.id)
    setDraft({ term_en: row.term_en, term_zh: row.term_zh })
  }

  const startCreate = () => {
    setConfirmId(null)
    setEditId('new')
    setDraft({ term_en: '', term_zh: '' })
  }

  const saveDraft = async () => {
    if (!draft.term_en.trim() || !draft.term_zh.trim()) {
      message.warning('英文与中文都不能为空')
      return
    }
    setSaving(true)
    try {
      if (editId === 'new') {
        await createGlossaryTerm({ ...draft, is_enabled: true })
        message.success('术语已新增')
      } else if (editId) {
        await updateGlossaryTerm(editId, draft)
        message.success('术语已保存')
      }
      setEditId(null)
      await refresh()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '保存术语失败')
    } finally {
      setSaving(false)
    }
  }

  const toggleEnabled = async (row: DocxGlossaryTerm, enabled: boolean) => {
    try {
      await updateGlossaryTerm(row.id, { is_enabled: enabled })
      await refresh()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '更新状态失败')
    }
  }

  const removeTerm = async (termId: string) => {
    try {
      await deleteGlossaryTerm(termId)
      message.success('术语已删除')
      setConfirmId(null)
      await refresh()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '删除术语失败')
    }
  }

  const handleImport = async (file: File) => {
    try {
      const result = await importGlossaryFile(file)
      message.success(`导入完成：新增 ${result.imported}、更新 ${result.updated}、跳过 ${result.skipped}`)
      await refresh()
    } catch (error) {
      message.error(error instanceof Error ? error.message : '导入失败')
    }
    return false
  }

  const columns: ColumnsType<DocxGlossaryTerm> = [
    {
      title: '英文',
      dataIndex: 'term_en',
      width: '36%',
      align: 'center',
      className: styles.termCell,
      render: (value: string, row) =>
        editId === row.id ? (
          <Input
            value={draft.term_en}
            onChange={event => setDraft(prev => ({ ...prev, term_en: event.target.value }))}
          />
        ) : (
          <span className={`${styles.termText} ${styles.termTextStrong}`} title={value}>
            {value}
          </span>
        ),
    },
    {
      title: '中文',
      dataIndex: 'term_zh',
      width: '26%',
      align: 'center',
      className: styles.termCell,
      render: (value: string, row) =>
        editId === row.id ? (
          <Input
            value={draft.term_zh}
            onChange={event => setDraft(prev => ({ ...prev, term_zh: event.target.value }))}
          />
        ) : (
          <span className={styles.termText} title={value}>
            {value}
          </span>
        ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: '10%',
      align: 'center',
      render: (value: DocxGlossaryTermSource) => (
        <span className={`${styles.srcTag} ${SOURCE_CLASS[value] ?? styles.srcManual}`}>
          {SOURCE_LABEL[value] ?? '手动'}
        </span>
      ),
    },
    {
      title: '启用',
      dataIndex: 'is_enabled',
      width: '8%',
      align: 'center',
      render: (value: boolean, row) => (
        <Switch
          size="small"
          checked={value}
          className={styles.gSwitch}
          onChange={checked => toggleEnabled(row, checked)}
        />
      ),
    },
    {
      title: '操作',
      key: 'ops',
      width: '20%',
      align: 'center',
      render: (_, row) => {
        if (confirmId === row.id) {
          return (
            <div className={styles.gOps}>
              <span className={styles.gConfirmInline}>
                确认删除「{row.term_en} / {row.term_zh}」？删除后新翻译不再套用
              </span>
              <button type="button" className={`${styles.gOp} ${styles.gOpRisk}`} onClick={() => removeTerm(row.id)}>
                确认删除
              </button>
              <button type="button" className={`${styles.gOp} ${styles.gOpDanger}`} onClick={() => setConfirmId(null)}>
                取消
              </button>
            </div>
          )
        }
        return (
          <div className={styles.gOps}>
            <button type="button" className={styles.gOp} onClick={() => startEdit(row)}>
              编辑
            </button>
            <button
              type="button"
              className={`${styles.gOp} ${styles.gOpDanger}`}
              onClick={() => {
                setEditId(null)
                setConfirmId(row.id)
              }}
            >
              删除
            </button>
          </div>
        )
      },
    },
  ]

  const dataSource: DocxGlossaryTerm[] =
    editId === 'new'
      ? [
          {
            id: 'new',
            term_en: '',
            term_zh: '',
            is_enabled: true,
            source: 'manual',
          },
          ...items,
        ]
      : items

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={880}
      title={
        <div>
          <div className={styles.drawerTitle}>术语表库</div>
          <div className={styles.drawerSub}>
            翻译时按语言方向自动套用 · 共 {total} 条
          </div>
        </div>
      }
      rootClassName={styles.glossaryDrawer}
      className={ui.tokenScope}
      styles={{ body: { padding: 0 } }}
    >
      <div className={styles.drawerRoot}>
        <div className={styles.drawerToolbar}>
          <Input.Search
            className={styles.gSearch}
            allowClear
            placeholder="搜索英文或中文术语"
            onChange={event => {
              // 实时过滤（中英文都可搜）；回车走 onSearch 立即生效
              setKeyword(event.target.value.trim())
            }}
            onSearch={value => {
              setKeyword(value.trim())
            }}
          />
          <a className={ui.btn} href={glossaryExportUrl()} download="术语表.xlsx">
            导出
          </a>
          <Upload accept=".xlsx" showUploadList={false} beforeUpload={handleImport}>
            <button type="button" className={ui.btn}>
              导入
            </button>
          </Upload>
          <button type="button" className={`${ui.btn} ${ui.btnPrimary}`} onClick={startCreate}>
            新增术语
          </button>
        </div>

        {editId === 'new' && (
          <div className={styles.drawerEditBar}>
            <Input
              className={styles.gSearch}
              placeholder="英文术语"
              value={draft.term_en}
              onChange={event => setDraft(prev => ({ ...prev, term_en: event.target.value }))}
            />
            <Input
              className={styles.gSearch}
              placeholder="中文术语"
              value={draft.term_zh}
              onChange={event => setDraft(prev => ({ ...prev, term_zh: event.target.value }))}
            />
            <button type="button" className={styles.gOp} disabled={saving} onClick={saveDraft}>
              保存
            </button>
            <button type="button" className={`${styles.gOp} ${styles.gOpDanger}`} onClick={() => setEditId(null)}>
              取消
            </button>
          </div>
        )}

        {editId && editId !== 'new' && (
          <div className={styles.drawerEditBar}>
            <span className={styles.gConfirm}>正在行内编辑，改完点「保存」</span>
            <button type="button" className={styles.gOp} disabled={saving} onClick={saveDraft}>
              保存
            </button>
            <button type="button" className={`${styles.gOp} ${styles.gOpDanger}`} onClick={() => setEditId(null)}>
              取消
            </button>
          </div>
        )}

        <div className={styles.glossaryTableWrap}>
          <Table
            className={`${styles.gTable} ${styles.glossaryTable}`}
            rowKey="id"
            tableLayout="fixed"
            columns={columns}
            dataSource={dataSource}
            loading={termsQuery.isLoading}
            pagination={false}
            locale={{
              emptyText: (
                <div className={styles.emptyHint}>
                  还没有术语。点击「导入」上传 xlsx（列名须为「英文」「中文」），或「新增术语」手工录入。
                </div>
              ),
            }}
          />
        </div>

        <div className={styles.gFooter}>
          <span>
            已显示 {items.length} 条 / 共 {total} 条
          </span>
          <span className={styles.gFooterHint}>
            {isFetchingNextPage ? '加载中…' : hasNextPage ? '下滑加载更多' : '已全部加载'}
          </span>
        </div>
        {hasNextPage && <div ref={loadMoreRef} className={styles.gLoadMore} />}
      </div>
    </Drawer>
  )
}

export default DocxTranslatorGlossaryDrawer
