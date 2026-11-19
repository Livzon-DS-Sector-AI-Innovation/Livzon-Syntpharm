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
import {
  IconCheck,
  IconClock,
  IconDownload,
  IconFile,
  IconTitleDoc,
} from '../RegistrationIcons'
import styles from './docx-translator.module.css'

const PAGE_SIZE = 10

const MODE_LABEL: Record<string, string> = {
  bilingual: '双语对照',
  replace: '译文替换',
  both: '同时输出',
}
const LANG_SHORT: Record<string, string> = { en: '英', zh: '中' }

/** 任务结局：驱动整行语气（边条、图标块、摘要卡底色） */
type TaskOutcome = 'running' | 'ok' | 'partial' | 'fail'

function outcomeOf(record: DocxTranslationTaskRecord): TaskOutcome {
  if (record.status === 'running') return 'running'
  if (record.fail_count > 0) return 'partial'
  if (record.status === 'failed') return 'fail'
  return 'ok'
}

const ROW_CLASS: Record<TaskOutcome, string> = {
  running: styles.rowRunning,
  ok: styles.rowOk,
  partial: styles.rowPartial,
  fail: styles.rowFail,
}

const DOC_ICO_CLASS: Record<TaskOutcome, string> = {
  running: styles.docIcoInfo,
  ok: styles.docIcoOk,
  partial: styles.docIcoWarn,
  fail: styles.docIcoRisk,
}

const SUMMARY_CLASS: Record<TaskOutcome, string> = {
  running: styles.detailSummaryRunning,
  ok: styles.detailSummaryOk,
  partial: styles.detailSummaryWarn,
  fail: styles.detailSummaryRisk,
}

const PILL_CLASS: Record<TaskOutcome, string> = {
  running: `${styles.pill} ${styles.pillInfo}`,
  ok: `${styles.pill} ${styles.pillOk}`,
  partial: `${styles.pill} ${styles.pillWarn}`,
  fail: `${styles.pill} ${styles.pillRisk}`,
}

const OUTCOME_LABEL: Record<TaskOutcome, string> = {
  running: '翻译中',
  ok: '全部成功',
  partial: '部分失败',
  fail: '任务失败',
}

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

function absoluteTime(iso?: string | null): string {
  if (!iso) return '—'
  return dayjs(iso).format('MM-DD HH:mm')
}

/** 成功率分档：≥95 绿 / 80–95 橙 / <80 红 */
function rateTone(rate: number): 'ok' | 'warn' | 'risk' {
  if (rate >= 95) return 'ok'
  if (rate >= 80) return 'warn'
  return 'risk'
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
    // 完成瞬间可能正好轮询停止：回到页签或重新挂载时强制取一次最新数据
    refetchOnMount: 'always',
    staleTime: 0,
    // 有进行中的任务时定时刷新，完成后自然停止
    refetchInterval: query =>
      query.state.data?.items.some(item => item.status === 'running') ? 5000 : false,
  })

  const detailQuery = useQuery({
    queryKey: ['docx-task-detail', detailId],
    queryFn: () => fetchTranslationTaskDetail(detailId as string),
    enabled: Boolean(detailId),
    refetchInterval: query => (query.state.data?.task.status === 'running' ? 5000 : false),
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
      align: 'left',
      render: (value: string, record) => {
        const outcome = outcomeOf(record)
        return (
          <div className={styles.docCell}>
            <span className={`${styles.docIco} ${DOC_ICO_CLASS[outcome]}`}>{IconFile}</span>
            <div className={styles.docText}>
              <div className={styles.docLine}>
                <span className={styles.docName} title={value}>
                  {value}
                </span>
                {record.source_count > 1 && (
                  <span className={styles.histMore}>+{record.source_count - 1}</span>
                )}
              </div>
              <div className={styles.histSub}>
                共 {record.source_count} 个文件 · {formatSize(record.total_file_size)}
              </div>
            </div>
          </div>
        )
      },
    },
    {
      title: '翻译参数',
      key: 'params',
      width: '16%',
      align: 'center',
      render: (_, record) => (
        <span className={styles.paramChips}>
          <span className={styles.chipLang}>
            {`${LANG_SHORT[record.source_lang] ?? record.source_lang} → ${LANG_SHORT[record.target_lang] ?? record.target_lang}`}
          </span>
          <span className={styles.chipMode}>{MODE_LABEL[record.mode] ?? record.mode}</span>
        </span>
      ),
    },
    {
      title: '结果',
      key: 'result',
      width: '15%',
      align: 'center',
      render: (_, record) => {
        // 任务行在提交时即创建（running），计数要等收尾才回写，
        // 所以运行中必须按 status 判断，不能用 fail_count 推断“全部成功”
        if (record.status === 'running') {
          const done = record.success_count + record.fail_count
          return (
            <span className={`${styles.pill} ${styles.pillInfo}`}>
              <span className={styles.miniSpin} />
              {record.source_count > 0 ? `翻译中 ${done}/${record.source_count}` : '翻译中'}
            </span>
          )
        }
        if (record.fail_count > 0) {
          return (
            <span className={styles.resultSplit}>
              <span className={styles.resultOkChip}>{record.success_count} 成功</span>
              <span className={styles.resultFailChip}>{record.fail_count} 失败</span>
            </span>
          )
        }
        if (record.status === 'failed') {
          return <span className={`${styles.pill} ${styles.pillRisk}`}>任务失败</span>
        }
        return (
          <span className={`${styles.pill} ${styles.pillOk}`}>
            {IconCheck}
            全部成功
          </span>
        )
      },
    },
    {
      title: '创建人',
      dataIndex: 'created_by_name',
      width: '12%',
      align: 'center',
      render: (value: string | null) => (
        <span className={styles.userCell}>
          <span className={styles.userAvatar}>{value ? value.slice(0, 1).toUpperCase() : '—'}</span>
          <span className={styles.histUser} title={value ?? ''}>
            {value || '—'}
          </span>
        </span>
      ),
    },
    {
      title: '时间',
      key: 'time',
      width: '14%',
      align: 'center',
      render: (_, record) => (
        <span className={styles.timeCell} title={record.created_at ?? ''}>
          <span className={styles.timeMain}>{relativeTime(record.created_at)}</span>
          <span className={styles.timeSub}>{absoluteTime(record.created_at)}</span>
        </span>
      ),
    },
    {
      title: '操作',
      key: 'ops',
      width: '13%',
      align: 'right',
      render: (_, record) => (
        <div className={styles.opsRight}>
          <button type="button" className={styles.opLike} onClick={event => {
            event.stopPropagation()
            setDetailId(record.id)
          }}>
            详情
          </button>
          {record.status !== 'running' && (
            <button
              type="button"
              className={styles.opMuted}
              disabled={busyId === record.id}
              onClick={event => {
                event.stopPropagation()
                void handleRetranslate(record)
              }}
            >
              {busyId === record.id ? '提交中…' : '再次翻译'}
            </button>
          )}
        </div>
      ),
    },
  ]

  if (detailId) {
    const detail = detailQuery.data
    const task = detail?.task
    const outcome: TaskOutcome = task ? outcomeOf(task) : 'running'
    const files = detail?.files ?? []
    const percent = task && task.source_count > 0
      ? Math.min(100, Math.round((files.length / task.source_count) * 100))
      : 0

    const detailColumns: ColumnsType<DocxTranslationTaskFile> = [
      {
        title: '文件',
        dataIndex: 'source_filename',
        width: '30%',
        align: 'left',
        render: (value: string) => (
          <div className={styles.docCell}>
            <span className={`${styles.docIco} ${styles.docIcoSm}`}>{IconFile}</span>
            <span className={styles.docName} title={value}>
              {value}
            </span>
          </div>
        ),
      },
      {
        title: '段落成功率',
        dataIndex: 'success_rate',
        width: '20%',
        align: 'center',
        render: (value: number, file) => {
          if (!file.success) return <span className={styles.rateNone}>—</span>
          const tone = rateTone(value)
          return (
            <span className={styles.rateWrap}>
              <span className={`${styles.rateValue} ${styles[`rate${tone === 'ok' ? 'Ok' : tone === 'warn' ? 'Warn' : 'Risk'}`]}`}>
                {value.toFixed(1)}%
              </span>
              <span className={styles.rateBar}>
                <i
                  className={`${styles.rateBarFill} ${styles[`rateBar${tone === 'ok' ? 'Ok' : tone === 'warn' ? 'Warn' : 'Risk'}`]}`}
                  style={{ width: `${Math.max(2, Math.min(100, value))}%` }}
                />
              </span>
            </span>
          )
        },
      },
      {
        title: '状态',
        dataIndex: 'success',
        width: '14%',
        align: 'center',
        render: (success: boolean) =>
          success ? (
            <span className={`${styles.pill} ${styles.pillOk}`}>{IconCheck}成功</span>
          ) : (
            <span className={`${styles.pill} ${styles.pillRisk}`}>失败</span>
          ),
      },
      {
        title: '说明',
        dataIndex: 'error',
        width: '22%',
        align: 'left',
        render: (error: string | null, file) =>
          file.success ? (
            <span className={styles.fileOut} title={file.output_filename}>
              {file.output_filename}
            </span>
          ) : (
            <span className={styles.failText}>{error || '翻译失败'}</span>
          ),
      },
      {
        title: '下载',
        key: 'download',
        width: '14%',
        align: 'right',
        render: (_, file) =>
          file.success ? (
            <a
              className={styles.dlBtn}
              href={translationFileDownloadUrl(file.id)}
              download={file.output_filename}
            >
              {IconDownload}
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
          <button type="button" className={styles.opLike} onClick={() => setDetailId(null)}>
            ‹ 返回历史
          </button>
          <span className={styles.histDetailTitle} title={task?.first_source_filename ?? ''}>
            {task?.first_source_filename ?? '任务详情'}
          </span>
          <span className={styles.histDetailMeta}>
            {task
              ? task.status === 'running'
                ? `翻译中 ${files.length}/${task.source_count} · ${relativeTime(task.created_at)}`
                : `成功 ${task.success_count} / 失败 ${task.fail_count} · ${relativeTime(task.created_at)}`
              : ''}
          </span>
        </div>

        {task && (
          <div className={`${styles.detailSummary} ${SUMMARY_CLASS[outcome]}`}>
            <div className={styles.summaryTop}>
              <span className={PILL_CLASS[outcome]}>
                {outcome === 'running' && <span className={styles.miniSpin} />}
                {OUTCOME_LABEL[outcome]}
              </span>
              <span className={styles.summaryNum}>
                {task.status === 'running'
                  ? `${files.length}/${task.source_count} 个文件`
                  : `成功 ${task.success_count} · 失败 ${task.fail_count}`}
              </span>
            </div>
            <div className={styles.summaryBar}>
              <i className={styles.summaryFill} style={{ width: `${percent}%` }} />
            </div>
            <div className={styles.summaryGrid}>
              <div className={styles.summaryField}>
                <span className={styles.summaryLabel}>
                  <i className={styles.summaryDot} aria-hidden />
                  语言方向
                </span>
                <span className={styles.summaryValue}>
                  {`${LANG_SHORT[task.source_lang] ?? task.source_lang} → ${LANG_SHORT[task.target_lang] ?? task.target_lang}`}
                </span>
              </div>
              <div className={styles.summaryField}>
                <span className={styles.summaryLabel}>
                  <i className={styles.summaryDot} aria-hidden />
                  输出模式
                </span>
                <span className={styles.summaryValue}>{MODE_LABEL[task.mode] ?? task.mode}</span>
              </div>
              <div className={styles.summaryField}>
                <span className={styles.summaryLabel}>
                  <i className={styles.summaryDot} aria-hidden />
                  创建人
                </span>
                <span className={styles.summaryValue}>{task.created_by_name || '—'}</span>
              </div>
              <div className={styles.summaryField}>
                <span className={styles.summaryLabel}>
                  <i className={styles.summaryDot} aria-hidden />
                  创建时间
                </span>
                <span className={styles.summaryValue}>
                  {task.created_at ? dayjs(task.created_at).format('YYYY-MM-DD HH:mm') : '—'}
                </span>
              </div>
            </div>
          </div>
        )}

        <Table
          className={`${styles.gTable} ${styles.historyTable}`}
          rowKey="id"
          columns={detailColumns}
          dataSource={files}
          loading={detailQuery.isLoading}
          pagination={false}
          tableLayout="fixed"
          rowClassName={record => (record.success ? styles.rowOk : styles.failRow)}
          locale={{
            emptyText: (
              <div className={styles.histEmpty}>
                <div className={styles.histEmptyIco}>{IconTitleDoc}</div>
                <div className={styles.histEmptyTitle}>该任务没有可展示的文件记录</div>
                <div className={styles.histEmptyDesc}>任务可能仍在解析，稍后刷新即可</div>
              </div>
            ),
          }}
        />
      </div>
    )
  }

  const showEmpty = !tasksQuery.isLoading && total === 0

  return (
    <div className={styles.historyPane}>
      <div className={styles.historyBar}>
        <span className={styles.barIco}>{IconClock}</span>
        <span className={styles.barText}>最近 30 天内的翻译记录 ｜ 点击任意一行可查看逐文件结果</span>
        {total > 0 && <span className={styles.barCount}>共 {total} 条</span>}
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
          rowClassName={record => ROW_CLASS[outcomeOf(record)]}
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
