'use client'

import { useState } from 'react'
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Input, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import {
  fetchTranslationTaskDetail,
  fetchTranslationTasks,
  translationFileDownloadUrl,
} from '@/lib/api/client/docx-translator'
import { retranslateTranslationTask } from '@/actions/docx-translator'
import type {
  DocxTranslationTaskFile,
  DocxTranslationTaskRecord,
} from '@/types/docx-translator'
import { IconClock } from '../RegistrationIcons'
import styles from './docx-translator.module.css'

const PAGE_SIZE = 10

const MODE_LABEL: Record<string, string> = {
  bilingual: '双语对照',
  replace: '译文替换',
  both: '同时输出',
}
const LANG_SHORT: Record<string, string> = { en: '英', zh: '中' }

function formatSize(bytes: number): string {
  if (!bytes) return '—'
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} B`
}

function relativeTime(iso?: string | null): string {
  if (!iso) return '—'
  const value = dayjs(iso)
  const now = dayjs()
  const minutes = now.diff(value, 'minute')
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (value.isSame(now, 'day')) return `今天 ${value.format('HH:mm')}`
  if (value.isSame(now.subtract(1, 'day'), 'day')) return `昨天 ${value.format('HH:mm')}`
  return value.format('MM-DD HH:mm')
}

interface Props {
  active: boolean
  /** 再次翻译成功后切回任务状态并接管新任务 */
  onOpenLive: (jobId: string) => void
}

export function DocxTranslatorHistory({ active, onOpenLive }: Props) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState('')
  const [page, setPage] = useState(1)
  const [detailId, setDetailId] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  const tasksQuery = useQuery({
    queryKey: ['docx-tasks', keyword, page],
    queryFn: () => fetchTranslationTasks({ keyword, page, pageSize: PAGE_SIZE }),
    enabled: active && !detailId,
    placeholderData: keepPreviousData,
  })

  const detailQuery = useQuery({
    queryKey: ['docx-task-detail', detailId],
    queryFn: () => fetchTranslationTaskDetail(detailId as string),
    enabled: Boolean(detailId),
  })

  const rows = tasksQuery.data?.items ?? []
  const total = tasksQuery.data?.total ?? 0

  const handleRetranslate = async (record: DocxTranslationTaskRecord) => {
    if (!record.can_retranslate) {
      message.warning('该任务未保存原件，无法再次翻译，请重新上传文件')
      return
    }
    setBusyId(record.id)
    try {
      const accepted = await retranslateTranslationTask(record.id)
      message.success('已按原件重新提交翻译')
      await queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
      onOpenLive(accepted.job_id)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '再次翻译失败')
    } finally {
      setBusyId(null)
    }
  }

  const columns: ColumnsType<DocxTranslationTaskRecord> = [
    {
      title: '文档',
      dataIndex: 'first_source_filename',
      width: '30%',
      align: 'center',
      render: (value: string, record) => (
        <div className={styles.histDoc}>
          <div className={styles.histDocLine}>
            <span className={styles.cellEllipsis} title={value}>
              {value}
            </span>
            {record.source_count > 1 && <span className={styles.histMore}>+{record.source_count - 1}</span>}
          </div>
          <div className={styles.histSub}>
            共 {record.source_count} 个文件 · {formatSize(record.total_file_size)}
          </div>
        </div>
      ),
    },
    {
      title: '翻译参数',
      key: 'params',
      width: '16%',
      align: 'center',
      render: (_, record) => (
        <span className={styles.histParam}>
          {`${LANG_SHORT[record.source_lang] ?? record.source_lang} → ${LANG_SHORT[record.target_lang] ?? record.target_lang}`}
          {' · '}
          {MODE_LABEL[record.mode] ?? record.mode}
        </span>
      ),
    },
    {
      title: '结果',
      key: 'result',
      width: '15%',
      align: 'center',
      render: (_, record) =>
        record.fail_count > 0 ? (
          <span className={`${styles.pill} ${styles.pillWarn}`}>
            {record.success_count} 成功 · {record.fail_count} 失败
          </span>
        ) : (
          <span className={`${styles.pill} ${styles.pillOk}`}>全部成功</span>
        ),
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      width: '12%',
      align: 'center',
      render: (value: string | null) => (
        <span className={styles.histUser} title={value ?? ''}>
          {value || '—'}
        </span>
      ),
    },
    {
      title: '时间',
      key: 'time',
      width: '14%',
      align: 'center',
      render: (_, record) => (
        <span className={styles.histTime} title={record.created_at ?? ''}>
          {relativeTime(record.created_at)}
        </span>
      ),
    },
    {
      title: '操作',
      key: 'ops',
      width: '13%',
      align: 'center',
      render: (_, record) => (
        <div className={styles.histOps}>
          <button type="button" className={styles.histLink} onClick={event => {
            event.stopPropagation()
            setDetailId(record.id)
          }}>
            详情
          </button>
          <button
            type="button"
            className={styles.histLinkMuted}
            disabled={busyId === record.id}
            onClick={event => {
              event.stopPropagation()
              void handleRetranslate(record)
            }}
          >
            {busyId === record.id ? '提交中…' : '再次翻译'}
          </button>
        </div>
      ),
    },
  ]

  if (detailId) {
    const detail = detailQuery.data
    const detailColumns: ColumnsType<DocxTranslationTaskFile> = [
      {
        title: '文件',
        dataIndex: 'source_filename',
        width: '20%',
        align: 'center',
        render: (value: string) => (
          <span className={styles.cellEllipsis} title={value}>
            {value}
          </span>
        ),
      },
      {
        title: '段落成功率',
        dataIndex: 'success_rate',
        width: '20%',
        align: 'center',
        render: (value: number, file) =>
          file.success ? (
            <span className={`${styles.rateValue} ${styles.numCell}`}>{value.toFixed(1)}%</span>
          ) : (
            <span className={styles.rateNone}>—</span>
          ),
      },
      {
        title: '状态',
        dataIndex: 'success',
        width: '20%',
        align: 'center',
        render: (success: boolean) =>
          success ? (
            <span className={`${styles.pill} ${styles.pillOk}`}>成功</span>
          ) : (
            <span className={`${styles.pill} ${styles.pillRisk}`}>失败</span>
          ),
      },
      {
        title: '说明',
        dataIndex: 'error',
        width: '20%',
        align: 'center',
        render: (error: string | null, file) =>
          file.success ? (
            <span className={styles.histTime}>{file.output_filename}</span>
          ) : (
            <span className={styles.failText}>{error || '翻译失败'}</span>
          ),
      },
      {
        title: '下载',
        key: 'download',
        width: '20%',
        align: 'center',
        render: (_, file) =>
          file.success ? (
            <a className={styles.dlBtn} href={translationFileDownloadUrl(file.id)} download={file.output_filename}>
              下载
            </a>
          ) : (
            <span className={styles.histTime}>—</span>
          ),
      },
    ]

    return (
      <div className={styles.historyPane}>
        <div className={styles.histDetailHead}>
          <button type="button" className={styles.histLink} onClick={() => setDetailId(null)}>
            ‹ 返回历史
          </button>
          <span className={styles.histDetailTitle}>{detail?.task.first_source_filename ?? '任务详情'}</span>
          <span className={styles.histTime}>
            {relativeTime(detail?.task.created_at)}
            {detail ? ` · 成功 ${detail.task.success_count} / 失败 ${detail.task.fail_count}` : ''}
          </span>
        </div>
        <Table
          className={`${styles.gTable} ${styles.historyTable}`}
          rowKey="id"
          columns={detailColumns}
          dataSource={detail?.files ?? []}
          loading={detailQuery.isLoading}
          pagination={false}
          tableLayout="fixed"
          locale={{ emptyText: <div className={styles.emptyHint}>该任务没有可展示的文件记录</div> }}
        />
      </div>
    )
  }

  const showEmpty = !tasksQuery.isLoading && total === 0

  return (
    <div className={styles.historyPane}>
      <div className={styles.historyBar}>
        <span>最近 30 天内的翻译记录 ｜ 点击任意一行可查看逐文件结果</span>
      </div>
      <div className={styles.historyToolbar}>
        <Input.Search
          className={styles.gSearch}
          allowClear
          placeholder="搜索文件名"
          onSearch={value => {
            setKeyword(value.trim())
            setPage(1)
          }}
        />
      </div>
      {showEmpty ? (
        <div className={styles.histEmpty}>
          <div className={styles.histEmptyIco}>{IconClock}</div>
          <div className={styles.histEmptyTitle}>还没有历史记录</div>
          <div className={styles.histEmptyDesc}>完成一次翻译后，任务会自动归档到这里</div>
        </div>
      ) : (
        <Table
          className={`${styles.gTable} ${styles.historyTable} ${styles.historyClickable}`}
          rowKey="id"
          columns={columns}
          dataSource={rows}
          loading={tasksQuery.isLoading || tasksQuery.isFetching}
          tableLayout="fixed"
          pagination={{
            current: page,
            pageSize: PAGE_SIZE,
            total,
            showSizeChanger: false,
            onChange: next => setPage(next),
          }}
          onRow={record => ({ onClick: () => setDetailId(record.id) })}
        />
      )}
    </div>
  )
}

export default DocxTranslatorHistory
