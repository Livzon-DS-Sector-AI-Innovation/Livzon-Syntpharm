'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { App, Alert, InputNumber, Progress, Segmented, Upload } from 'antd'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { UploadFile } from 'antd'
import { ApiError } from '@/lib/api/client'
import {
  fetchTranslationJobState,
  fetchTranslationTasks,
  submitTranslationJob,
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

  const fetchJob = useCallback(async (id: string) => {
    const state = await fetchTranslationJobState(id)
    return {
      job_id: state.job_id,
      status: state.status,
      result: state,
      error: state.error,
    }
  }, [])

  const { phase, result, errorMessage } = usePollingJob<DocxTranslationJobState>({
    jobId,
    startedAt,
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

  // 刷新恢复：读回上次未结束的任务，继续轮询进度与计时
  useEffect(() => {
    let raw: string | null = null
    try {
      raw = window.sessionStorage.getItem(RESUME_KEY)
    } catch {
      raw = null
    }
    if (!raw) {
      // 本地无记录（换标签页/清缓存/首次加载）：向服务端接回我自己最新的进行中任务
      let cancelled = false
      void (async () => {
        try {
          const page = await fetchTranslationTasks({ page: 1, pageSize: 1, status: 'running', mine: true })
          const task = page.items[0]
          if (!task || cancelled) return
          const started = task.created_at ? Date.parse(task.created_at) : Date.now()
          window.setTimeout(() => {
            if (cancelled) return
            setJobId(task.job_ref)
            setStartedAt(started)
          }, 0)
        } catch {
          // 没有进行中任务或接口不可用时保持空闲态
        }
      })()
      return () => {
        cancelled = true
      }
    }
    let saved: { jobId?: string; startedAt?: number } = {}
    try {
      saved = JSON.parse(raw) as { jobId?: string; startedAt?: number }
    } catch {
      forgetJob()
      return
    }
    if (!saved.jobId || !saved.startedAt) {
      forgetJob()
      return
    }
    // 超过 1 小时视为过期（与轮询 timeout 一致）
    if (Date.now() - saved.startedAt > 3_600_000) {
      forgetJob()
      return
    }
    const job = saved.jobId
    const started = saved.startedAt
    // 放到宏任务里恢复，避免在 effect 同步 setState 触发级联渲染
    const timer = window.setTimeout(() => {
      setJobId(job)
      setStartedAt(started)
    }, 0)
    return () => window.clearTimeout(timer)
  }, [])

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
      const accepted = await submitTranslationJob({
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
      setJobId(accepted.job_id)
      setActiveTab('live')
      rememberJob(accepted.job_id, now)
      void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
      message.success('翻译已提交，可在右侧查看进度')
    } catch (error) {
      const text = error instanceof ApiError ? error.message : error instanceof Error ? error.message : '提交失败'
      message.error(text)
    } finally {
      setSubmitting(false)
    }
  }

  const handleRetryFile = async (fileName: string) => {
    const target = fileList.find(item => item.name === fileName)?.originFileObj
    if (!target) {
      message.warning('原始文件已不在列表中，请重新上传后翻译')
      return
    }
    setSubmitting(true)
    // 先保留已完成的结果，新任务完成后再按文件名覆盖失败那一行
    setCarriedRows(displayRows)
    try {
      const accepted = await submitTranslationJob({
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
      setJobId(accepted.job_id)
      rememberJob(accepted.job_id, now)
      void queryClient.invalidateQueries({ queryKey: ['docx-tasks'] })
      message.success(`已重新提交：${fileName}`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '重新提交失败')
    } finally {
      setSubmitting(false)
    }
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
          onRetry={handleRetryFile}
          retrying={submitting}
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
            <div className={`${styles.statePane} ${styles[`statePane_${paneTone}`]}`}>{stateNode}</div>
          ) : (
            <DocxTranslatorHistory
              active={activeTab === 'history'}
              onOpenLive={nextJobId => {
                setCarriedRows([])
                setElapsed(0)
                setStartedAt(Date.now())
                setJobId(nextJobId)
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
