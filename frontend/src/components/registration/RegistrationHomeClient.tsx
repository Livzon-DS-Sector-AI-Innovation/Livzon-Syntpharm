'use client'

/**
 * 注册概览（注册管理首页）
 * 严格按 registration-home-redesign.html 实现：
 * - 一屏固定：页头 + 三张 KPI + 左「审评中品种」/ 右上「申报资料撰写」/ 右下「AI 辅助」
 * - 数据全部来自接口：台账汇总 + 品种列表 + 逐品种规则推算（节点/预计完成/预计获批同源）
 * - 节点只由日期规则推算，本页不提供任何人工维护入口
 */

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { fetchLedgerSummary } from '@/lib/api/client/registration-ledger'
import { fetchDrugs, fetchDrugPrediction } from '@/lib/api/client/registration'
import type { Drug, DrugPrediction, NodePrediction } from '@/types/registration'
import type { LedgerSummary } from '@/types/registration-ledger'
import styles from './registration-home.module.css'
import {
  IconCert, IconGlobe, IconList, IconPlus, IconRefresh, IconShieldCheck, IconTitleDoc,
} from './RegistrationIcons'

/* ---------- 渠道：后端暂无字段，先按「受理号 + 品种类型」临时归口 ---------- */
type ChannelKey = '国家局' | 'CEP' | 'US DMF'

interface ChannelMeta {
  key: ChannelKey
  badge: string
  tagLabel: string
  color: string
  tagClass: string
}

const CHANNELS: Record<ChannelKey, ChannelMeta> = {
  国家局: { key: '国家局', badge: '国', tagLabel: '国家局审评', color: 'var(--brand-600)', tagClass: styles.tagBrand },
  CEP: { key: 'CEP', badge: 'CEP', tagLabel: 'CEP 审评', color: 'var(--info-600)', tagClass: styles.tagInfo },
  'US DMF': { key: 'US DMF', badge: 'US', tagLabel: 'US DMF', color: 'var(--teal-600)', tagClass: styles.tagTeal },
}

function channelOf(drug: Drug): ChannelMeta {
  const no = drug.acceptance_number ?? ''
  if (/^cep/i.test(no)) return CHANNELS.CEP
  if (/dmf/i.test(no)) return CHANNELS['US DMF']
  // 临时映射（待后端增加 channel 字段后替换）
  if (drug.type === '创新药') return CHANNELS.CEP
  return CHANNELS.国家局
}

/* ---------- 节点 → 语义色（配置驱动，与申报进度查询页同一套） ---------- */
function nodeTagClass(nodeName: string): string {
  if (/发补递交|缺陷信回复/.test(nodeName)) return styles.tagWarn
  if (/开展核查|完整性初审/.test(nodeName)) return styles.tagTeal
  if (/技术审评/.test(nodeName)) return styles.tagInfo
  return styles.tagBrand
}

/* ---------- KPI 数字滚动：rAF 缓出 + 超时兜底 + 减弱动效直出 ---------- */
function CountUp({ value, delay = 0 }: { value: number; delay?: number }) {
  const [text, setText] = useState(0)
  const rafRef = useRef<number | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduce || !Number.isFinite(value)) {
      // 用 rAF 异步写回终值：在 effect 体内同步 setState 会触发级联渲染，故延后一帧
      rafRef.current = requestAnimationFrame(() => setText(value))
      return () => {
        if (rafRef.current) cancelAnimationFrame(rafRef.current)
      }
    }
    const duration = 900
    const startAt = performance.now() + delay
    const tick = (now: number) => {
      const p = Math.min((now - startAt) / duration, 1)
      if (p < 0) {
        rafRef.current = requestAnimationFrame(tick)
        return
      }
      const eased = 1 - Math.pow(1 - p, 3)
      setText(Math.round(value * eased))
      if (p < 1) rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
    // 兜底：帧异常时强制写回终值，避免数字卡 0
    timerRef.current = setTimeout(() => setText(value), delay + duration + 300)
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [value, delay])

  return <>{text}</>
}

/* ---------- 单行推算：节点名 / 节点预计完成 / 项目预计获批（同一条结果） ---------- */
interface QueueItem {
  drug: Drug
  channel: ChannelMeta
  prediction: DrugPrediction
  nodeName: string
  nodeDue: string | null
  approveDate: string | null
  overdue: boolean
}

function toQueueItem(drug: Drug, channel: ChannelMeta, prediction: DrugPrediction): QueueItem {
  // 节点定位以接口 stage（后端日期规则引擎）为准，日期取同一条预测链里对应节点的结果
  const stage = drug.stage
  const currentIndex = stage?.current_node_index ?? prediction.current_node_index
  const current: NodePrediction | undefined =
    prediction.nodes.find(n => n.node_index === currentIndex)
    ?? prediction.nodes.find(n => n.node_index === prediction.current_node_index)

  return {
    drug,
    channel,
    prediction,
    nodeName: stage?.current_node_name ?? current?.node_name ?? '等待节点推算',
    nodeDue: current?.estimated_date ?? null,
    approveDate: prediction.estimated_approval_date ?? null,
    overdue: (stage?.overdue_indexes?.length ?? 0) > 0,
  }
}

/* ---------- AI 辅助卡（按设计稿 4 项） ---------- */
interface AiItem {
  key: string
  name: string
  desc: string
  href: string
  accent: string
  accentBg: string
  icon: React.ReactNode
}

const AI_ITEMS: AiItem[] = [
  {
    key: 'docx-translator',
    name: '文档翻译',
    desc: '中英互译保格式',
    href: '/registration/docx-translator',
    accent: 'var(--info-600)',
    accentBg: 'var(--info-50)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="M3 5h12M9 3v2c1.6 4.5 4.3 8.5 8 11M5 9c0 2.1.9 4.5 2.5 6.5M13 21l4-9 4 9m-7.5-2h5" />
      </svg>
    ),
  },
  {
    key: 'authorization-letter',
    name: '授权书',
    desc: '快速生成授权信',
    href: '/registration/authorization-letter',
    accent: 'var(--brand-600)',
    accentBg: 'var(--brand-50)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="m12 15 2 2 4-4" />
        <rect x="3" y="3" width="18" height="18" rx="2" />
      </svg>
    ),
  },
  {
    key: 'reference-standard',
    name: '标准物质说明书',
    desc: 'COA 与说明书',
    href: '/registration/reference-standard',
    accent: 'var(--teal-600)',
    accentBg: 'var(--teal-50)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="M10 2v7.31L4.16 19.16A2 2 0 0 0 5.93 22h12.14a2 2 0 0 0 1.77-2.84L14 9.31V2" />
        <path d="M8.5 2h7M7 16h10" />
      </svg>
    ),
  },
  {
    key: 'regulation',
    name: '法规跟踪',
    desc: '法规动态跟踪',
    href: '/registration/regulation',
    accent: 'var(--violet-600)',
    accentBg: 'var(--violet-50)',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20M2 12h20" />
      </svg>
    ),
  },
]

function accentStyle(accent: string, accentBg: string): React.CSSProperties {
  return { '--accent': accent, '--accent-bg': accentBg } as React.CSSProperties
}

interface RegistrationHomeClientProps {
  /** 外部申报资料撰写系统地址；为空时卡片保持系统内页面入口 */
  dossierWriterUrl?: string
}

export default function RegistrationHomeClient({ dossierWriterUrl }: RegistrationHomeClientProps) {
  const queryClient = useQueryClient()
  const fresh = { staleTime: 0, refetchOnMount: 'always' as const }
  const summaryQuery = useQuery({ queryKey: ['registration-ledger-summary'], queryFn: fetchLedgerSummary, ...fresh })
  const drugsQuery = useQuery({ queryKey: ['registration-drugs'], queryFn: fetchDrugs, ...fresh })

  const summary: LedgerSummary | null = summaryQuery.data ?? null
  const drugs = drugsQuery.data ?? []

  // 审评中口径：以后端 stage 为准（已获批品种不计入列表，直接计入 KPI）
  const inProgressDrugs = drugs.filter(d => {
    if (d.stage) return !d.stage.approved
    const nodes = (d.nodes || []).filter(n => !n.skipped)
    return nodes.length === 0 || nodes.some(n => !n.actual_date)
  })

  const predictionQueries = useQueries({
    queries: inProgressDrugs.map(d => ({
      queryKey: ['registration-drug-prediction', d.id],
      queryFn: () => fetchDrugPrediction(d.id),
    })),
  })

  const queue: QueueItem[] = inProgressDrugs
    .map((drug, i) => {
      const prediction = predictionQueries[i]?.data
      return prediction ? toQueueItem(drug, channelOf(drug), prediction) : null
    })
    .filter((x): x is QueueItem => x !== null)
    // 逾期置顶，其余按当前节点预计完成日期升序
    .sort((a, b) => {
      if (a.overdue !== b.overdue) return a.overdue ? -1 : 1
      const da = a.nodeDue ? dayjs(a.nodeDue).valueOf() : Number.MAX_SAFE_INTEGER
      const db = b.nodeDue ? dayjs(b.nodeDue).valueOf() : Number.MAX_SAFE_INTEGER
      return da - db
    })

  const loading = summaryQuery.isFetching || drugsQuery.isFetching

  const handleRefresh = () => {
    void summaryQuery.refetch()
    void drugsQuery.refetch()
    void queryClient.invalidateQueries({ queryKey: ['registration-drug-prediction'] })
  }

  // 申报资料撰写卡片内容。配置了外部系统地址时，文案改为「外部系统 + 新窗口」，
  // 避免仍暗示可以在系统内编辑；未配置时保持原有文案与内部页面入口。
  const externalDocUrl = (dossierWriterUrl ?? '').trim()
  const docCardBody = (
    <>
      <div>
        <div className={styles.docEyebrow}>申报资料</div>
        <div className={styles.docTitle}>申报资料撰写</div>
        <div className={styles.docDesc}>
          {externalDocUrl
            ? '外部申报资料撰写系统，点击后在新窗口打开'
            : 'CTD 章节素材管理，AI 辅助填充，按品种组织申报文档'}
        </div>
        <div className={styles.docChips}>
          <span className={styles.docChip}>CTD 章节</span>
          <span className={styles.docChip}>AI 填充</span>
          <span className={styles.docChip}>按品种归档</span>
        </div>
        <div className={styles.docCta}>
          {externalDocUrl ? '前往外部系统' : '进入撰写'}{' '}
          <span className={styles.arr}>{externalDocUrl ? '↗' : '›'}</span>
        </div>
      </div>
      <svg className={styles.docArt} viewBox="0 0 205 150" fill="none" aria-hidden>
        <ellipse cx="72" cy="82" rx="64" ry="56" fill="#E9EAFC" opacity=".55" />
        <g className={styles.docFloat}>
          <rect x="26" y="32" width="76" height="96" rx="10" fill="#fff" stroke="#D9DBF7" />
          <rect x="38" y="46" width="38" height="6" rx="3" fill="#E9EAFC" />
          <rect x="38" y="60" width="52" height="5" rx="2.5" fill="#EFF0FD" />
          <rect x="38" y="72" width="45" height="5" rx="2.5" fill="#EFF0FD" />
          <rect x="38" y="84" width="52" height="5" rx="2.5" fill="#EFF0FD" />
          <rect x="38" y="104" width="30" height="14" rx="7" fill="#4F46C9" />
          <text x="53" y="114.5" textAnchor="middle" fontSize="8" fontWeight="700" fill="#fff">AI</text>
        </g>
        <path d="M94 14l1.8 4.2 4.2 1.8-4.2 1.8L94 26l-1.8-4.2-4.2-1.8 4.2-1.8z" fill="#C9CDF2" />
        <path className={styles.flow} d="M102 58 C 132 58, 140 40, 164 40" stroke="#A5A0EE" strokeWidth="1.6" />
        <path className={styles.flow} d="M102 76 C 132 76, 140 70, 164 70" stroke="#A5A0EE" strokeWidth="1.6" />
        <path className={styles.flow} d="M102 94 C 132 94, 140 100, 164 100" stroke="#A5A0EE" strokeWidth="1.6" />
        <path className={styles.flow} d="M102 112 C 132 112, 140 130, 164 130" stroke="#A5A0EE" strokeWidth="1.6" />
        <g className={styles.nodePulse}>
          <circle cx="178" cy="40" r="12" fill="#fff" stroke="#C9CDF2" />
          <text x="178" y="43.5" textAnchor="middle" fontSize="9" fontWeight="700" fill="#4F46C9">M2</text>
          <circle cx="178" cy="70" r="12" fill="#4F46C9" />
          <text x="178" y="73.5" textAnchor="middle" fontSize="9" fontWeight="700" fill="#fff">M3</text>
          <circle cx="178" cy="100" r="12" fill="#fff" stroke="#C9CDF2" />
          <text x="178" y="103.5" textAnchor="middle" fontSize="9" fontWeight="700" fill="#4F46C9">M4</text>
          <circle cx="178" cy="130" r="12" fill="#fff" stroke="#C9CDF2" />
          <text x="178" y="133.5" textAnchor="middle" fontSize="9" fontWeight="700" fill="#4F46C9">M5</text>
        </g>
      </svg>
    </>
  )

  return (
    <div className={styles.root}>
      {/* ===== 页头 ===== */}
      <header className={styles.pageHead}>
        <div>
          <div className={styles.pageTitle}>
            <span className={styles.titleIco}>{IconTitleDoc}</span>
            <h1>注册管理</h1>
          </div>
          <div className={styles.pageSub}>注册台账、审评进展与申报资料一览</div>
        </div>
        <div className={styles.headActions}>
          <button type="button" className={styles.btn} onClick={handleRefresh} disabled={loading}>
            {IconRefresh}
            刷新
          </button>
          <Link href="/registration/projects" className={styles.btnPrimary}>
            {IconPlus}
            新建注册项目
          </Link>
        </div>
      </header>

      {/* ===== ① KPI 三卡 ===== */}
      <section className={styles.kpiRow} aria-label="关键指标">
        <Link
          href="/registration/ledger?type=domestic"
          className={styles.kpi}
          style={accentStyle('var(--ok-600)', 'var(--ok-50)')}
        >
          <div className={styles.kpiTop}>
            <span className={styles.kpiChip}>{IconShieldCheck}</span>
            <span className={styles.kpiLabel}>国内获批</span>
            <span className={styles.kpiLink}>明细 ›</span>
          </div>
          <div className={styles.kpiNum}><CountUp value={summary?.domestic_count ?? 0} delay={120} /></div>
          <div className={styles.kpiSub}>国内获批品种数量</div>
        </Link>

        <Link
          href="/registration/ledger?type=overseas"
          className={styles.kpi}
          style={accentStyle('var(--info-600)', 'var(--info-50)')}
        >
          <div className={styles.kpiTop}>
            <span className={styles.kpiChip}>{IconGlobe}</span>
            <span className={styles.kpiLabel}>国外获批</span>
            <span className={styles.kpiLink}>明细 ›</span>
          </div>
          <div className={styles.kpiNum}><CountUp value={summary?.overseas_count ?? 0} delay={210} /></div>
          <div className={styles.kpiSub}>覆盖 <b>{summary?.overseas_countries ?? 0}</b> 个国家/地区</div>
        </Link>

        <Link
          href="/registration/ledger?type=copp"
          className={styles.kpi}
          style={accentStyle('var(--warn-600)', 'var(--warn-50)')}
        >
          <div className={styles.kpiTop}>
            <span className={styles.kpiChip}>{IconCert}</span>
            <span className={styles.kpiLabel}>COPP / WC</span>
            <span className={styles.kpiLink}>明细 ›</span>
          </div>
          <div className={styles.kpiNum}>
            <CountUp value={summary?.copp_count ?? 0} delay={300} />
            <small> / {summary?.wc_count ?? 0}</small>
          </div>
          <div className={styles.kpiSub}>
            COPP {summary?.copp_count ?? 0} 份 · WC {summary?.wc_count ?? 0} 份证书
          </div>
        </Link>
      </section>

      {/* ===== ② 工作区 ===== */}
      <section className={styles.workRow}>
        {/* 审评中品种 */}
        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <span className={styles.panelIco}>{IconList}</span>
            <div className={styles.panelTitle}>审评中品种</div>
            <span className={styles.countPill}>{queue.length}</span>
            <Link className={styles.panelMore} href="/registration/review">查看全部 ›</Link>
          </div>

          <div className={styles.queueList}>
            {queue.length === 0 ? (
              <div className={styles.emptyBody}>
                {loading ? '正在加载审评品种…' : '当前没有审评中的品种'}
              </div>
            ) : (
              queue.map(item => (
                <Link
                  key={item.drug.id}
                  href={`/registration/review?drug=${item.drug.id}`}
                  className={styles.queueRow}
                  style={{ '--q-color': item.channel.color } as React.CSSProperties}
                >
                  <span className={styles.qBadge} aria-hidden>{item.channel.badge}</span>
                  <div className={styles.queueBody}>
                    <div className={styles.queueName}>{item.drug.name}</div>
                    <div className={styles.queueMeta}>
                      <span className={item.channel.tagClass}>{item.channel.tagLabel}</span>
                      <span className={item.overdue ? styles.tagRisk : nodeTagClass(item.nodeName)}>
                        {item.nodeName}
                      </span>
                      <span className={styles.qDueDate}>
                        预计完成 {item.nodeDue ?? '待估'}
                      </span>
                    </div>
                  </div>
                  <div className={styles.queueRight}>
                    <span className={styles.qDate}>
                      预计项目获批
                      <b className={styles.approve}>{item.approveDate ?? '待估'}</b>
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>

          <div className={styles.panelFoot}>
            <span>节点与日期由系统按自然日期自动推测，无需人工维护</span>
            <Link className={styles.panelMore} href="/registration/review">去添加 ›</Link>
          </div>
        </div>

        <div className={styles.sideCol}>
          {/* 申报资料撰写卡：配置了外部系统地址时新标签页打开，否则进系统内页面 */}
          {externalDocUrl ? (
            <a
              href={externalDocUrl}
              target="_blank"
              rel="noopener noreferrer"
              className={styles.docCard}
              aria-label="在新标签页打开外部申报资料撰写系统"
            >
              {docCardBody}
            </a>
          ) : (
            <Link href="/registration/dossier-writer" className={styles.docCard} aria-label="进入申报资料撰写">
              {docCardBody}
            </Link>
          )}

          {/* AI 辅助 */}
          <div className={styles.bizAi}>
            <div className={styles.bizAiHead}>
              <span className={styles.kpiChip}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                  <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />
                  <path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9z" />
                </svg>
              </span>
              <div className={styles.bizAiTitle}>AI 辅助</div>
              <div className={styles.bizAiCount}>{AI_ITEMS.length} 项</div>
            </div>
            <div className={styles.bizAiGrid}>
              {AI_ITEMS.map(item => (
                <Link
                  key={item.key}
                  href={item.href}
                  className={styles.aiItem}
                  style={accentStyle(item.accent, item.accentBg)}
                >
                  <span className={styles.aiIco}>{item.icon}</span>
                  <span className={styles.aiBody}>
                    <span className={styles.bizName}>{item.name}</span>
                    <span className={styles.bizDesc}>{item.desc}</span>
                  </span>
                  <span className={styles.bizArrow}>›</span>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
