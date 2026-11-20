'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { App, Alert, InputNumber, Progress, Segmented, Upload } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { UploadFile } from 'antd'
import { ApiError } from '@/lib/api/client'
import {
  fetchTranslationJobState,
  fetchTranslationJobStates,
  fetchTranslationTasks,
  fetchSubmitTranslationJob,
} from '@/lib/api/client/docx-translator'
import { usePollingJob } from '@/hooks/usePollingJob'
import type {
  DocxTranslationFileResult,
  DocxTranslationJobState,
  DocxTranslationMode,
} from '@/types/docx-translator'
import { RegistrationPageHeader } from '../RegistrationPageHeader'
import { IconBook, IconTitleDoc, IconUpload } from '../RegistrationIcons'
import ui from '../registration-ui.module.css'
import styles from './docx-translator.module.css'
import { DocxTranslatorResultTable } from './DocxTranslatorResultTable'
import { DocxTranslatorGlossaryDrawer } from './DocxTranslatorGlossaryDrawer'
import dynamic from 'next/dynamic'

// 相对时间（刚刚/x 分钟前）依赖当前时刻，SSR 与 CSR 结果必然不同，
// 关闭服务端渲染避免 hydration 不匹配告警。
const DocxTranslatorHistory = dynamic(() => import('./DocxTranslatorHistory'), {
  ssr: false,
  loading: () => <div className={styles.historyPane} />,
})

interface ResultRow extends DocxTranslationFileResult {
  /** 该行结果所属任务：单文件重试会新建任务，下载必须用它自己的 job_id */
  job_id: string
}

const MODE_OPTIONS: { label: string; value: DocxTranslationMode }[] = [
  { label: '双语对照', value: 'bilingual' },
  { label: '译文替换', value: 'replace' },
  { label: '同时输出两种', value: 'both' },
]

const MODE_NOTES: Record<DocxTranslationMode, string> = {
  bilingual: '双语对照：每段原文后紧跟一段蓝色译文，审校核对用',
  replace: '译文替换：原文直接替换为译文，生成纯目标语言成品文件',
  both: '同时输出：对照版 + 成品版各生成一份',
}

const MAX_FILE_MB = 50
const MAX_FILES = 10
const ACCEPT = '.docx,.doc,.wps'
const RESUME_KEY = 'docx-translator:job'
const JOBS_KEY = 'docx-translator:jobs'
const DISMISSED_KEY = 'docx-translator:dismissed'

/** 已提交任务的原件：File 不能持久化，只在当前页面会话内有效 */
const sourceFilesByJob = new Map<string, Map<string, File>>()

/** 用户手动清除过的任务：即使服务端仍把它算作 running，刷新也不再恢复 */
function readDismissed(): Set<string> {
  try {
    const raw = window.sessionStorage.getItem(DISMISSED_KEY)
    return new Set<string>(raw ? (JSON.parse(raw) as string[]) : [])
  } catch {
    return new Set<string>()
  }
}

function addDismissed(ids: string[]): void {
  if (!ids.length) return
  try {
    const merged = Array.from(new Set([...readDismissed(), ...ids])).slice(-100)
    window.sessionStorage.setItem(DISMISSED_KEY, JSON.stringify(merged))
  } catch {
    // 会话存储不可用时忽略：下次刷新可能恢复，不影响主流程
  }
}

const MAX_FINISHED_CARDS = 5

/** 运行中/未知状态全部保留；已结束只留最近 5 个，避免卡片无限堆积 */
function capFinishedCards(jobs: TrackedJob[], finishedIds: Set<string>): TrackedJob[] {
  const alive = jobs.filter(job => !finishedIds.has(job.jobId))
  const finished = jobs
    .filter(job => finishedIds.has(job.jobId))
    .sort((a, b) => b.startedAt - a.startedAt)
    .slice(0, MAX_FINISHED_CARDS)
  // 最新提交的任务排最上面，最多保留 20 张卡
  return [...alive, ...finished].sort((a, b) => b.startedAt - a.startedAt).slice(0, 20)
}

interface TrackedJob {
  jobId: string
  startedAt: number
  filenames: string[]
  sourceCount: number
  sourceLang: string
  targetLang: string
  mode: DocxTranslationMode
}

/** 记住当前任务，刷新后可恢复进度轮询（sessionStorage：仅本标签页、关页即清） */
function rememberJob(jobId: string, startedAt: number): void {
  try {
    window.sessionStorage.setItem(RESUME_KEY, JSON.stringify({ jobId, startedAt }))
  } catch {
    // 隐私模式等场景下不可写：忽略，不影响翻译本身
  }
}

function forgetJob(): void {
  try {
    window.sessionStorage.removeItem(RESUME_KEY)
  } catch {
    // 同上
  }
}

function formatSize(bytes: number): string {
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
  if (bytes >= 1024) return `${Math.round(bytes / 1024)} KB`
  return `${bytes} B`
}

function formatElapsed(seconds: number): string {
  const mm = String(Math.floor(seconds / 60)).padStart(2, '0')
  const ss = String(seconds % 60).padStart(2, '0')
  return `${mm}:${ss}`
}

/** 读取 sessionStorage 里记录的任务（纯读取，不取数）。 */
function readStoredJobs(): TrackedJob[] {
  try {
    const rawArr = window.sessionStorage.getItem(JOBS_KEY)
    const rawOne = window.sessionStorage.getItem(RESUME_KEY)
    if (rawArr) return JSON.parse(rawArr) as TrackedJob[]
    if (!rawOne) return []
    const one = JSON.parse(rawOne) as { jobId?: string; startedAt?: number }
    if (!one.jobId) return []
    return [
      {
        jobId: one.jobId,
        startedAt: one.startedAt ?? Date.now(),
        filenames: [],
        sourceCount: 0,
        sourceLang: 'en',
        targetLang: 'zh',
        mode: 'bilingual',
      },
    ]
  } catch {
    return []
  }
}

export function DocxTranslatorPageClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [sourceLang, setSourceLang] = useState<'en' | 'zh'>('en')
  const [mode, setMode] = useState<DocxTranslationMode>('bilingual')
  const [batchSize, setBatchSize] = useState(30)
  const [advOpen, setAdvOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  // 任务状态页签同时跟踪多个任务：新提交不再覆盖旧任务。
  // 初始值取自 sessionStorage（纯读取）；服务端「我的进行中任务」由 React Query 取回后
  // 在 useMemo 里合并，避免用 useEffect 取数 + setState。
  const [trackedState, setTracked] = useState<TrackedJob[]>(() => readStoredJobs())
  // 已提交任务的原件：左栏清空后仍可「重试此文件」；File 不可持久化，刷新后重试引导去历史页
  const [now, setNow] = useState(() => Date.now())
  const [startedAt, setStartedAt] = useState<number | null>(null)
  const [elapsed, setElapsed] = useState(0)
  // 多任务结果累积：单文件重试会新建任务，旧结果必须先落到这里再与当前任务合并
  const [carriedRows, setCarriedRows] = useState<ResultRow[]>([])
  const [glossaryOpen, setGlossaryOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'live' | 'history'>('live')

  const targetLang = sourceLang === 'en' ? 'zh' : 'en'

  // 历史徽标：条数随任务归档同步（完成后 invalidate）
  const taskBadgeQuery = useQuery({
    queryKey: ['docx-tasks', 'badge'],
    queryFn: () => fetchTranslationTasks({ page: 1, pageSize: 1 }),
    staleTime: 10_000,
  })
  const taskTotal = taskBadgeQuery.data?.total ?? 0

  // 刷新恢复：服务端「我的进行中任务」（取数走 React Query，不在 effect 里取数）
  const runningTasksQuery = useQuery({
    queryKey: ['docx-tasks', 'my-running'],
    queryFn: () => fetchTranslationTasks({ page: 1, pageSize: 20, status: 'running', mine: true }),
    staleTime: 5_000,
  })
  const serverRunning = useMemo<TrackedJob[]>(() => {
    const page = runningTasksQuery.data
    if (!page) return []
    return page.items.map(task => ({
      jobId: task.job_ref,
      startedAt: task.created_at ? Date.parse(task.created_at) : Date.now(),
      filenames: [task.first_source_filename],
      sourceCount: task.source_count,
      sourceLang: task.source_lang,
      targetLang: task.target_lang,
      mode: task.mode as DocxTranslationMode,
    }))
  }, [runningTasksQuery.data])

  // 本地快照 + 服务端运行中任务合并（用户手动清除过的不再恢复）
  const tracked = useMemo<TrackedJob[]>(() => {
    const dismissed = readDismissed()
    const merged = new Map(trackedState.map(item => [item.jobId, item]))
    serverRunning.forEach(item => {
      if (!merged.has(item.jobId)) merged.set(item.jobId, item)
    })
    return Array.from(merged.values())
      .filter(item => !dismissed.has(item.jobId))
      .sort((a, b) => b.startedAt - a.startedAt)
      .slice(0, 20)
  }, [trackedState, serverRunning])

  // 多任务：一次请求拿回所有任务的进度（2 秒一轮，全部结束自动停）
  const trackedIds = tracked.map(item => item.jobId)
  const statesQuery = useQuery({
    queryKey: ['docx-jobs', trackedIds.join(',')],
    queryFn: () => fetchTranslationJobStates(trackedIds),
    enabled: trackedIds.length > 0,
    refetchInterval: query =>
      query.state.data?.some(item => item.status === 'running') ? 2000 : false,
  })
  const stateMap = useMemo(
    () => new Map((statesQuery.data ?? []).map(item => [item.job_id, item])),
    [statesQuery.data],
  )
  // 只有真的还有任务在跑时才每秒刷新；全部结束必须停表
  const anyRunning = (statesQuery.data ?? []).some(item => item.status === 'running')

  useEffect(() => {
    if (!anyRunning) return
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [anyRunning])

  // 任一任务结束时刷新历史列表与徽标（多任务下不再依赖单任务 phase）
  const statusSignature = (statesQuery.data ?? []).map(item => `${item.job_id}:${item.status}`).join(',')
  useEffect(() => {
    if (!statusSignature.includes(':done') && !statusSignature.includes(':failed')) return
    void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
  }, [statusSignature, queryClient])

  // 已结束任务只留最近 5 个；后端重启后查不到的任务不再展示（只在顶部提示）
  const finishedIds = useMemo(
    () => new Set((statesQuery.data ?? []).filter(item => item.status !== 'running').map(item => item.job_id)),
    [statesQuery.data],
  )
  // 后端重启后查不到状态的任务：保留卡片并标记「已中断」，不再让它凭空消失
  const missingIds = useMemo(() => {
    if (!statesQuery.isSuccess || statesQuery.data === undefined) return new Set<string>()
    const returned = new Set(statesQuery.data.map(item => item.job_id))
    return new Set(
      tracked
        .filter(job => !returned.has(job.jobId) && Date.now() - job.startedAt > 15_000)
        .map(job => job.jobId),
    )
  }, [statesQuery.isSuccess, statesQuery.data, tracked])

  // 失败/部分失败的任务自动归档：历史里已有记录，任务状态不再占位
  const archivedFailedIds = useMemo(() => {
    const ids = new Set<string>()
    tracked.forEach(job => {
      const state = stateMap.get(job.jobId)
      if (!state) return
      const hasFailedFile = state.files.some(item => !item.success)
      if (state.status === 'failed' || (state.status === 'done' && hasFailedFile)) {
        ids.add(job.jobId)
      }
    })
    return ids
  }, [tracked, stateMap])
  const visibleJobs = useMemo(
    () =>
      capFinishedCards(
        tracked.filter(job => !archivedFailedIds.has(job.jobId)),
        finishedIds,
      ),
    [tracked, finishedIds, archivedFailedIds],
  )

  const trackJob = useCallback(
    (nextJobId: string, names: string[], started: number) => {
      setTracked(prev => {
        const rest = prev.filter(item => item.jobId !== nextJobId)
        const next: TrackedJob = {
          jobId: nextJobId,
          startedAt: started,
          filenames: names,
          sourceCount: names.length,
          sourceLang,
          targetLang,
          mode,
        }
        return [...rest, next].slice(-20)
      })
    },
    [sourceLang, targetLang, mode],
  )

  const fetchJob = useCallback(async (id: string) => {
    const state = await fetchTranslationJobState(id)
    return {
      job_id: state.job_id,
      status: state.status,
      result: state,
      // 生成类型里 error 是可选字段，JobState 要求 string | null，这里统一收敛
      error: state.error ?? null,
    }
  }, [])

  const activeJobId = jobId ?? tracked[0]?.jobId ?? null
  const activeStartedAt = startedAt ?? tracked[0]?.startedAt ?? null

  const { phase, result, errorMessage } = usePollingJob<DocxTranslationJobState>({
    jobId: activeJobId,
    startedAt: activeStartedAt,
    queryKey: ['docx-translator-job', jobId],
    fetchJob,
    pollIntervalMs: 1500,
    timeoutMs: 3_600_000,
  })

  useEffect(() => {
    if (phase !== 'done' && phase !== 'failed') return
    // 任务已结束：历史可查，刷新不再恢复该任务
    forgetJob()
    void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
    // 详情抽屉若仍打开，立即补上最后一个文件，不用等下一次轮询
    void queryClient.invalidateQueries({ queryKey: ['docx-task-detail'] })
  }, [phase, queryClient])

  // 变更即持久化，刷新后可恢复所有任务卡片
  useEffect(() => {
    try {
      window.sessionStorage.setItem(JOBS_KEY, JSON.stringify(tracked))
    } catch {
      // 隐私模式等场景不可写：忽略
    }
  }, [tracked])

  useEffect(() => {
    if (phase !== 'running' || startedAt === null) return
    const timer = setInterval(() => setElapsed(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(timer)
  }, [phase, startedAt])

  // 结果直接从「查询状态 + 已累积结果」派生，不在 effect 里写 state（避免级联渲染）
  const displayRows = useMemo<ResultRow[]>(() => {
    const merged = new Map(carriedRows.map(item => [item.filename, item]))
    if (phase === 'done' && jobId && result?.files?.length) {
      result.files.forEach(item => merged.set(item.filename, { ...item, job_id: jobId }))
    }
    return Array.from(merged.values())
  }, [carriedRows, phase, result, jobId])

  const runningState = phase === 'running' ? result : null
  const totalFiles = runningState?.files_total || fileList.length
  const doneFiles = runningState?.files_done || 0
  const percent = totalFiles ? Math.round((doneFiles / totalFiles) * 100) : 0

  const failedCount = displayRows.filter(item => !item.success).length
  const successFiles = displayRows.filter(item => item.success)

  const resetJob = () => {
    forgetJob()
    setJobId(null)
    setStartedAt(null)
    setCarriedRows([])
    setElapsed(0)
  }

  const handleRemove = (uid: string) => setFileList(prev => prev.filter(item => item.uid !== uid))

  const handleSubmit = async () => {
    const originFiles: File[] = fileList.flatMap(item => (item.originFileObj ? [item.originFileObj] : []))
    if (!originFiles.length) {
      message.warning('请先上传 Word 文档')
      return
    }
    if (originFiles.length > MAX_FILES) {
      message.warning(`单次最多处理 ${MAX_FILES} 个文件`)
      return
    }
    const oversize = originFiles.find(item => item.size > MAX_FILE_MB * 1024 * 1024)
    if (oversize) {
      message.warning(`文件超过 ${MAX_FILE_MB}MB：${oversize.name}`)
      return
    }

    setSubmitting(true)
    try {
      const accepted = await fetchSubmitTranslationJob({
        files: originFiles,
        sourceLang,
        targetLang,
        mode,
        batchSize,
      })
      const now = Date.now()
      setCarriedRows([])
      setElapsed(0)
      setStartedAt(now)
      setActiveTab('live')
      sourceFilesByJob.set(accepted.job_id, new Map(originFiles.map(file => [file.name, file])))
      rememberJob(accepted.job_id, now)
      trackJob(accepted.job_id, originFiles.map(file => file.name), now)
      void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
      // 提交成功才清空左栏：失败时保留，方便用户直接重试
      setFileList([])
      message.success('翻译已提交，左栏已清空，可在右侧查看进度')
    } catch (error) {
      const text = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '提交失败'
      message.error(text)
    } finally {
      setSubmitting(false)
    }
  }

  const handleRetryFile = async (jobId: string, fileName: string) => {
    const target = sourceFilesByJob.get(jobId)?.get(fileName)
    if (!target) {
      message.warning('原始文件已不在本页（刷新后失效），请到「历史翻译」用「再次翻译」')
      return
    }
    setSubmitting(true)
    // 先保留已完成的结果，新任务完成后再按文件名覆盖失败那一行
    setCarriedRows(displayRows)
    try {
      const accepted = await fetchSubmitTranslationJob({
        files: [target],
        sourceLang,
        targetLang,
        mode,
        batchSize,
      })
      setElapsed(0)
      setStartedAt(Date.now())
      const now = Date.now()
      setStartedAt(now)
      sourceFilesByJob.set(accepted.job_id, new Map([[fileName, target]]))
      rememberJob(accepted.job_id, now)
      trackJob(accepted.job_id, [fileName], now)
      void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
      message.success(`已重新提交：${fileName}`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '重新提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  /** 下载即归档：任务卡移除 + 记入已清除名单，历史仍可查 */
  const archivateJob = (targetJobId: string) => {
    addDismissed([targetJobId])
    sourceFilesByJob.delete(targetJobId)
    setTracked(prev => prev.filter(item => item.jobId !== targetJobId))
    message.success('已下载，任务已归档到「历史翻译」')
    // 最后一张卡移除后复位单任务视图，避免残留旧结果表占位
    if (tracked.filter(item => item.jobId !== targetJobId).length === 0) {
      resetJob()
    }
  }

  const renderTaskList = () => {
    const runningCount = visibleJobs.filter(
      job => (stateMap.get(job.jobId)?.status ?? 'running') === 'running',
    ).length
    const endedCount = tracked.filter(
      job => finishedIds.has(job.jobId) || missingIds.has(job.jobId),
    ).length
    return (
      <>
        {missingIds.size > 0 && (
          <div className={styles.taskNotice}>
            有 {missingIds.size} 个任务状态已丢失（服务重启），卡片保留供查看，结果请到「历史翻译」
          </div>
        )}
        <div className={styles.taskToolbar}>
          <span>
            共 {visibleJobs.length} 个任务（进行中 {runningCount}）
            {archivedFailedIds.size > 0 ? ` · 已归档失败 ${archivedFailedIds.size}` : ''}
          </span>
          <button
            type="button"
            className={styles.taskLink}
            disabled={endedCount === 0}
            onClick={() => {
              const removable = new Set<string>([...finishedIds, ...missingIds])
              addDismissed(Array.from(removable))
              const clearAll = removable.size >= tracked.length
              setTracked(prev => {
                prev.forEach(job => {
                  if (removable.has(job.jobId)) sourceFilesByJob.delete(job.jobId)
                })
                return prev.filter(job => !removable.has(job.jobId))
              })
              // 自动刷新历史列表与条数徽标，无需手动 F5
              void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
              void queryClient.invalidateQueries({ queryKey: ['docx-task-detail'] })
              if (clearAll) resetJob()
            }}
          >
            清除已结束{endedCount > 0 ? `（${endedCount}）` : ''}
          </button>
        </div>
        <div className={styles.taskList}>
          {visibleJobs.map(job => {
        const state = stateMap.get(job.jobId)
        // 查不到状态 = 服务重启或进程内任务被清理，保留卡片并明确提示
        const interrupted = !state
        const expired = false
        const status = state?.status ?? 'failed'
        const done = state?.files_done ?? 0
        const total = state?.files_total || job.sourceCount || 0
        const percent = total ? Math.round((done / total) * 100) : 0
        // 运行中走本地秒表；结束/失败用后端冻结的耗时，避免继续跳动
        const seconds =
          status === 'running' && !expired
            ? Math.max(0, Math.floor((now - job.startedAt) / 1000))
            : (state?.elapsed_seconds ?? null)
        const name = job.filenames[0] || '历史任务'
        const more = job.filenames.length > 1 ? ` +${job.filenames.length - 1}` : ''
        const rows = (state?.files ?? []).map(item => ({ ...item, job_id: job.jobId }))
        const successCount = rows.filter(item => item.success).length
        const failCount = rows.filter(item => !item.success).length
        // 只要有一个文件失败（或任务级失败），状态必须是「失败」，不能显示「已完成」
        const hasFailure = status === 'failed' || failCount > 0
        const statusClass =
          expired || interrupted || hasFailure
            ? styles.pillRisk
            : status === 'done'
              ? styles.pillOk
              : styles.pillInfo
        const statusText = interrupted
          ? '已中断'
          : expired
            ? '已过期'
          : hasFailure
            ? successCount > 0
              ? '部分失败'
              : '失败'
            : status === 'done'
              ? '已完成'
              : '翻译中'

        return (
          <div key={job.jobId} className={styles.taskCard}>
            <div className={styles.taskCardHead}>
              <span className={styles.taskName} title={`${name}${more}`}>
                {name}
                {more}
              </span>
              <span className={`${styles.pill} ${statusClass}`}>{statusText}</span>
            </div>
            <div className={styles.taskMeta}>
              <span className={styles.numCell}>{seconds === null ? '—' : formatElapsed(seconds)}</span>
              <span>
                {done} / {total} 个文件
                {state?.batch_total ? ` · 第 ${state.batch_done}/${state.batch_total} 批` : ''}
              </span>
            </div>

            {status === 'running' && !expired && (
              <div className={styles.taskBody}>
                <Progress percent={percent} showInfo={false} strokeLinecap="round" />
                <div className={styles.taskLine}>
                  正在翻译：<b>{state?.current_file || '准备中'}</b>
                </div>
              </div>
            )}

            {(expired || interrupted) && (
              <div className={styles.taskBody}>
                {interrupted
                  ? '服务重启导致任务中断，进度已丢失；结果请到「历史翻译」查看或重新提交。'
                  : '任务状态已过期（服务重启），结果请到「历史翻译」查看。'}
                <button
                  type="button"
                  className={styles.taskLink}
                  onClick={() => {
                    addDismissed([job.jobId])
                    sourceFilesByJob.delete(job.jobId)
                    setTracked(prev => prev.filter(item => item.jobId !== job.jobId))
                  }}
                >
                  移除这张卡
                </button>
              </div>
            )}

            {(status === 'done' || status === 'failed') && !expired && (
              <div className={styles.taskBody}>
                <div className={styles.taskLine}>
                  成功 {successCount} / 失败 {failCount}
                  {state?.error ? ` · ${state.error}` : ''}
                </div>
                {rows.length > 0 && (
                  <div className={styles.taskResultScroll}>
                    <DocxTranslatorResultTable
                      rows={rows}
                      onRetry={fileName => handleRetryFile(job.jobId, fileName)}
                      retrying={submitting}
                      onDownloaded={() => archivateJob(job.jobId)}
                    />
                  </div>
                )}
              </div>
            )}
          </div>
            )
          })}
        </div>
      </>
    )
  }

  const renderState = () => {
    if (!jobId) {
      return (
        <div className={styles.idle}>
          <span className={styles.idleHalo} aria-hidden />
          <div className={styles.idleIco}>
            {IconTitleDoc}
          </div>
          <div className={styles.idleTitle}>还没有翻译任务</div>
          <div className={styles.idleDesc}>
            在左侧上传文档、选好语言方向和输出模式
            <br />
            点击右上角「开始翻译」即可提交
          </div>
        </div>
      )
    }

    if (phase === 'unavailable') {
      return (
        <div className={styles.unavailable}>
          <div className={styles.idleIco}>
            {IconTitleDoc}
          </div>
          <div className={styles.idleTitle}>任务状态已过期，请重新提交</div>
          <div className={styles.idleDesc}>服务可能已重启，任务进度只保存在内存中。</div>
          <button type="button" className={ui.btnPrimary} style={{ marginTop: 16 }} onClick={resetJob}>
            重新提交
          </button>
        </div>
      )
    }

    if (phase === 'failed') {
      return (
        <div className={styles.unavailable}>
          <Alert type="error" showIcon message="翻译任务执行失败" description={errorMessage || '请重试或联系管理员'} />
          <button type="button" className={ui.btn} style={{ marginTop: 16 }} onClick={resetJob}>
            重新提交
          </button>
        </div>
      )
    }

    if (phase === 'running' || phase === 'timeout') {
      return (
        <div className={styles.running}>
          <div className={styles.runTop}>
            <span className={styles.runBadge}>
              <span className={styles.spinner} />
              翻译中
            </span>
            <span className={styles.runElapsed}>
              已用时 <b>{formatElapsed(elapsed)}</b>
            </span>
          </div>
          <div className={styles.runFile}>
            正在翻译：<b>{runningState?.current_file || '准备中'}</b>
          </div>
          <div className={styles.runBar}>
            <Progress percent={percent} showInfo={false} strokeLinecap="round" />
          </div>
          <div className={styles.runMeta}>
            <span>
              {doneFiles} / {totalFiles} 个文件
            </span>
            <span>{percent}%</span>
          </div>
          {doneFiles > 0 && (
            <div className={styles.runMoreHint}>
              已完成 {doneFiles} 个文件
              <button type="button" className={styles.runMoreLink} onClick={() => setActiveTab('history')}>
                前往历史翻译查看
              </button>
            </div>
          )}
          <div className={styles.runNote}>
            {IconBook}
            翻译在后台运行，可离开本页
          </div>
        </div>
      )
    }

    return (
      <div className={styles.done}>
        <div className={`${styles.doneSummary} ${failedCount ? styles.doneSummaryWarn : ''}`}>
          <div className={styles.doneIco}>{failedCount ? IconTitleDoc : IconUpload}</div>
          <div>
            <div className={styles.doneTitle}>
              {failedCount ? `翻译完成，${failedCount} 个文件失败` : '全部翻译完成'}
            </div>
            <div className={styles.doneSub}>
              成功 {successFiles.length} / 失败 {failedCount} · 已用时 {formatElapsed(elapsed)}
            </div>
          </div>
        </div>
        <DocxTranslatorResultTable
          rows={displayRows}
          onRetry={fileName => handleRetryFile(jobId ?? '', fileName)}
          retrying={submitting}
          onDownloaded={() => {
            if (!jobId) return
            archivateJob(jobId)
            resetJob()
          }}
        />
      </div>
    )
  }

  const stateNode = renderState()

  // 状态区语气：空态=紫蓝引导 / 运行=信息蓝 / 完成=成功绿 / 部分失败=警示橙 / 任务失败=风险红
  const paneTone: 'idle' | 'running' | 'done' | 'warn' | 'failed' =
    !jobId ? 'idle'
      : phase === 'running' || phase === 'timeout' ? 'running'
        : phase === 'failed' || phase === 'unavailable' ? 'failed'
          : failedCount > 0 ? 'warn' : 'done'

  return (
    <div className={`${ui.regUi} ${styles.page}`}>
      <RegistrationPageHeader
        icon={IconTitleDoc}
        title="文档翻译"
        sub="Word 文档中英互译，保留原文格式"
        actions={
          <span className={styles.headerActions}>
            <button type="button" className={ui.btn} onClick={() => setGlossaryOpen(true)}>
              {IconBook} 术语表
            </button>
            <button
              type="button"
              className={ui.btnPrimary}
              disabled={submitting}
              onClick={handleSubmit}
            >
              {submitting ? '提交中…' : '开始翻译'}
            </button>
          </span>
        }
      />

      <div className={styles.workbench}>
        <section className={styles.card}>
          <div className={styles.cardHead}>
            <span className={styles.cardIco}>{IconUpload}</span>
            <div className={styles.cardTitle}>上传与参数</div>
            <div className={styles.cardMeta}>
              单文件 ≤{MAX_FILE_MB}MB · 单次 ≤{MAX_FILES} 个
            </div>
          </div>
          <div className={styles.cardBody}>
            <div className={styles.upload}>
              <Upload.Dragger
                multiple
                accept={ACCEPT}
                fileList={fileList}
                showUploadList={false}
                beforeUpload={() => false}
                onChange={({ fileList: next }) => setFileList(next)}
              >
                <div className={styles.uploadInner}>
                  <div className={styles.uploadIco}>
                    {IconUpload}
                  </div>
                  <div className={styles.uploadTitle}>点击或拖拽上传 Word 文档</div>
                  <div className={styles.uploadHint}>支持 .docx / .doc，.doc 自动转换无需手动另存</div>
                </div>
              </Upload.Dragger>
            </div>

            {fileList.length > 0 && (
              <div className={styles.fileList}>
                {fileList.map(item => (
                  <div key={item.uid} className={styles.fileItem}>
                    <div className={styles.fileIco}>W</div>
                    <span className={styles.fileName}>{item.name}</span>
                    {/\.(doc|wps)$/i.test(item.name) && <span className={styles.fileDocTag}>.doc 将自动转换</span>}
                    <span className={styles.fileSize}>{formatSize(item.size || 0)}</span>
                    <button
                      type="button"
                      className={styles.fileDel}
                      aria-label={`移除 ${item.name}`}
                      onClick={() => handleRemove(item.uid)}
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className={styles.cfg}>
              <div className={styles.cfgLabel}>
                <span className={`${styles.cfgDot} ${styles.cfgDotInfo}`} aria-hidden />
                语言方向
              </div>
              <Segmented
                block
                className={styles.seg}
                value={sourceLang}
                onChange={value => setSourceLang(value as 'en' | 'zh')}
                options={[
                  { label: '英文 → 中文', value: 'en' },
                  { label: '中文 → 英文', value: 'zh' },
                ]}
              />
            </div>

            <div className={styles.cfg}>
              <div className={styles.cfgLabel}>
                <span className={`${styles.cfgDot} ${styles.cfgDotBrand}`} aria-hidden />
                输出模式
              </div>
              <Segmented
                block
                className={`${styles.seg} ${styles.segCompact}`}
                value={mode}
                onChange={value => setMode(value as DocxTranslationMode)}
                options={MODE_OPTIONS}
              />
              <div className={styles.modeNote}>{MODE_NOTES[mode]}</div>
            </div>

            <button type="button" className={styles.advToggle} onClick={() => setAdvOpen(prev => !prev)}>
              <span className={`${styles.advArrow} ${advOpen ? styles.advArrowOpen : ''}`}>▶</span> 高级参数
            </button>
            {advOpen && (
              <div className={styles.advBody}>
                <div className={styles.advRow}>
                  每批段落数
                  <InputNumber min={5} max={200} value={batchSize} onChange={value => setBatchSize(value || 30)} />
                  <span className={styles.advTip}>默认 30；批次小更稳但耗时更长</span>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.paneHead}>
            <div className={styles.paneTabs} role="tablist" aria-label="任务状态与历史翻译">
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'live'}
                className={activeTab === 'live' ? styles.paneTabOn : styles.paneTab}
                onClick={() => setActiveTab('live')}
              >
                任务状态
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={activeTab === 'history'}
                className={activeTab === 'history' ? styles.paneTabOn : styles.paneTab}
                onClick={() => setActiveTab('history')}
              >
                历史翻译
                {taskTotal > 0 && <span className={styles.tabCount}>{taskTotal}</span>}
              </button>
            </div>
          </div>
          {activeTab === 'live' ? (
            <div className={`${styles.statePane} ${styles[`statePane_${paneTone}`]}`}>
              {tracked.length > 0 ? renderTaskList() : stateNode}
            </div>
          ) : (
            <DocxTranslatorHistory
              active={activeTab === 'history'}
              onOpenLive={nextJobId => {
                const started = Date.now()
                setCarriedRows([])
                setElapsed(0)
                setStartedAt(started)
                trackJob(nextJobId, [], started)
                setActiveTab('live')
              }}
            />
          )}
        </section>
      </div>

      <DocxTranslatorGlossaryDrawer open={glossaryOpen} onClose={() => setGlossaryOpen(false)} />
    </div>
  )
}

export default DocxTranslatorPageClient
