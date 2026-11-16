'use client'

/**
 * 注册概览（注册管理首页）
 * 视觉按 registration-home-redesign.html 原型实现；数据全部来自真实接口：
 * - KPI：GET /registration/ledger/summary
 * - 审评中品种 / 需要关注：GET /registration/drugs + /drugs/{id}/prediction + /drugs/nodes
 */

import Link from 'next/link'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Spin } from 'antd'
import { fetchLedgerSummary } from '@/lib/api/client/registration-ledger'
import { fetchDrugs, fetchReviewNodes, fetchDrugPrediction } from '@/lib/api/client/registration'
import type { Drug, DrugPrediction, NodePrediction, ReviewNodeConfig } from '@/types/registration'
import type { LedgerSummary } from '@/types/registration-ledger'
import { RegistrationPageHeader } from './RegistrationPageHeader'
import ui from './registration-ui.module.css'
import styles from './registration-home.module.css'
import {
  IconTitleDoc, IconRefresh, IconPlus, IconShieldCheck, IconGlobe, IconLink,
  IconCert, IconList, IconWarn, IconCheckCircle, IconGrid, IconFile, IconBulb,
  IconBook, IconActivity, IconSliders, IconEdit, IconCheckSquare, IconMessage, IconFlask,
} from './registration-icons'

/* ---------- 业务功能区配置（分组语义：紫=台账与进度 / 蓝=申报资料 / 绿=AI 与合规） ---------- */
interface BizItem {
  key: string
  name: string
  desc: string
  icon: React.ReactNode
  href: string
}
interface BizGroup {
  key: string
  title: string
  icon: React.ReactNode
  accentVar: string
  accentBgVar: string
  items: BizItem[]
}

const BIZ_GROUPS: BizGroup[] = [
  {
    key: 'ledger-progress',
    title: '台账与进度',
    icon: IconGrid,
    accentVar: 'var(--brand-600)',
    accentBgVar: 'var(--brand-50)',
    items: [
      { key: 'ledger', name: '注册台账', desc: '6 类注册台账维护，Excel 导入导出', icon: IconBook, href: '/registration/ledger' },
      { key: 'review', name: '审评进度', desc: '节点进度跟踪与预测', icon: IconActivity, href: '/registration/review' },
      { key: 'projects', name: '注册项目', desc: '项目全周期状态管理', icon: IconSliders, href: '/registration/projects' },
    ],
  },
  {
    key: 'dossier',
    title: '申报资料',
    icon: IconFile,
    accentVar: 'var(--info-600)',
    accentBgVar: 'var(--info-50)',
    items: [
      { key: 'dossier-writer', name: '申报资料撰写', desc: 'CTD 章节素材与 AI 填充', icon: IconEdit, href: '/registration/dossier-writer' },
      { key: 'authorization-letter', name: '授权书', desc: '按品种快速生成授权信', icon: IconCheckSquare, href: '/registration/authorization-letter' },
      { key: 'supplementary-reply', name: '发补回复', desc: '基于通知函生成回复草稿', icon: IconMessage, href: '/registration/supplementary-reply' },
    ],
  },
  {
    key: 'ai-compliance',
    title: 'AI 与合规',
    icon: IconBulb,
    accentVar: 'var(--ok-600)',
    accentBgVar: 'var(--ok-50)',
    items: [
      { key: 'validation-audit', name: '验证文件审核', desc: 'AI 合规性检查', icon: IconShieldCheck, href: '/registration/validation-audit' },
      { key: 'reference-standard', name: '对照物质说明表', desc: '对照物质 COA 与说明表', icon: IconFlask, href: '/registration/reference-standard' },
      { key: 'regulation', name: '法规跟踪', desc: '国内外法规动态跟踪', icon: IconGlobe, href: '/registration/regulation' },
    ],
  },
]

/* ---------- 提醒规则（真实数据驱动：节点停滞/逾期两档递进；预计获批 < 30 天 → 临期；证书三档见 computeCertAlerts） ---------- */
interface AlertItem {
  key: string
  severity: 'warn' | 'risk'
  severityLabel: string
  text: string
  suggestion: string
  href: string
}

function computeAlerts(
  items: { drug: Drug; prediction: DrugPrediction }[],
  reviewNodes: ReviewNodeConfig[],
): AlertItem[] {
  const alerts: AlertItem[] = []
  const today = new Date()
  for (const { drug, prediction } of items) {
    const current = prediction.nodes.find(n => n.node_index === prediction.current_node_index)
    const cfg = current ? reviewNodes.find(n => n.index === current.node_index) : null
    if (current && cfg && prediction.days_in_current_node !== null) {
      const overdueThreshold = Math.ceil(cfg.days * 1.5)
      if (prediction.days_in_current_node > overdueThreshold) {
        alerts.push({
          key: `${drug.id}-stall`,
          severity: 'risk',
          severityLabel: '逾期',
          text: `「${drug.name}」在「${current.node_name}」已停留 ${prediction.days_in_current_node} 天，超过常规周期（${cfg.days} 天）的 1.5 倍`,
          suggestion: '建议尽快核实审评状态并更新节点进度',
          href: '/registration/review',
        })
      } else if (prediction.days_in_current_node > cfg.days) {
        alerts.push({
          key: `${drug.id}-linger`,
          severity: 'warn',
          severityLabel: '停滞',
          text: `「${drug.name}」在「${current.node_name}」已停留 ${prediction.days_in_current_node} 天，超过常规周期（${cfg.days} 天）`,
          suggestion: '建议关注该节点进展，必要时与审评机构沟通',
          href: '/registration/review',
        })
      }
    }
    if (prediction.estimated_approval_date) {
      const eta = new Date(prediction.estimated_approval_date)
      const daysLeft = Math.ceil((eta.getTime() - today.getTime()) / 86400000)
      if (daysLeft >= 0 && daysLeft < 30) {
        alerts.push({
          key: `${drug.id}-eta`,
          severity: 'warn',
          severityLabel: '临期',
          text: `「${drug.name}」距预计获批仅剩 ${daysLeft} 天`,
          suggestion: '建议提前准备获批后登记与证书维护工作',
          href: '/registration/review',
        })
      }
    }
  }
  return alerts
}

/** 台账子表类型 → 中文标签（证书预警文案用）；certificate = 主证书表 */
const LEDGER_TYPE_LABELS: Record<string, string> = {
  domestic: '国内已获批',
  overseas: '国外已获批',
  copp: 'COPP证书',
  wc: 'WC证书',
  certificate: '注册证书',
}

/**
 * 再注册法定申请死线（天）：届满前 6 个月。
 * 依据：《药品注册管理办法》第82条（前6个月申请再注册）；
 * NMPA 2024年第38号通告（申报窗口为届满前12~6个月）。
 */
const REREG_DEADLINE_DAYS = 180

/**
 * 证书有效期预警三档（点击定位台账；主证书表无独立页面，统一跳台账首页）：
 * 已过期 → 红「已过期」；≤180 天 → 红「紧急」（逼近再注册死线）；≤365 天 → 橙「临期」（申报窗口期）
 */
function computeCertAlerts(summary: LedgerSummary | null): AlertItem[] {
  if (!summary) return []
  return summary.expiring_certificates.map(cert => {
    const typeLabel = LEDGER_TYPE_LABELS[cert.ledger_type] ?? cert.ledger_type
    const name = cert.certificate_name || cert.product_name
    const href =
      cert.ledger_type === 'certificate'
        ? '/registration/ledger'
        : `/registration/ledger?type=${cert.ledger_type}`
    if (cert.days_left < 0) {
      return {
        key: `cert-${cert.id}`,
        severity: 'risk' as const,
        severityLabel: '已过期',
        text: `「${name}」（${typeLabel}）已过期 ${-cert.days_left} 天`,
        suggestion: '证书已失效，请立即安排再注册或申报，避免影响业务',
        href,
      }
    }
    if (cert.days_left <= REREG_DEADLINE_DAYS) {
      return {
        key: `cert-${cert.id}`,
        severity: 'risk' as const,
        severityLabel: '紧急',
        text: `「${name}」（${typeLabel}）仅剩 ${cert.days_left} 天到期，已逼近再注册申请死线（届满前6个月）`,
        suggestion: '请立即启动再注册申报，为审查审批预留时间',
        href,
      }
    }
    return {
      key: `cert-${cert.id}`,
      severity: 'warn' as const,
      severityLabel: '临期',
      text: `「${name}」（${typeLabel}）${cert.days_left} 天后到期，已进入再注册申报窗口（届满前12~6个月）`,
      suggestion: '建议在届满前6个月前提交再注册申请',
      href,
    }
  })
}

/** "需要关注"卡片最多展示的条目数，超出以"还有 N 条"收口 */
const ALERT_DISPLAY_LIMIT = 5

/** 完整日期格式：YYYY-MM-DD（含年份） */
function fmtDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

interface DueTag {
  key: string
  className: string
  label: string
}

/** 三档变色共用判定：已逾期红 / ≤30 天橙 / 其余绿；无日期 → 灰"日期待估" */
function dueTagOf(key: string, dateStr: string | null, baseLabel: string): DueTag {
  if (!dateStr) {
    return { key, className: styles.tagBrand, label: `${baseLabel} · 日期待估` }
  }
  const d = new Date(dateStr)
  const daysLeft = Math.ceil((d.getTime() - Date.now()) / 86400000)
  if (daysLeft < 0) {
    return { key, className: styles.tagRisk, label: `${baseLabel} ${fmtDate(d)} · 已逾期 ${-daysLeft} 天` }
  }
  if (daysLeft <= 30) {
    return { key, className: styles.tagWarn, label: `${baseLabel} ${fmtDate(d)} · 剩 ${daysLeft} 天` }
  }
  return { key, className: styles.tagOk, label: `${baseLabel} ${fmtDate(d)}` }
}

/**
 * 审评中品种右侧标签：仅当前节点的预测完成时间（随节点推进自动变化、三档变色）；
 * 品种整体预计获批日期移至品种名下方展示。
 */
function nodeDueTag(current: NodePrediction | undefined): DueTag | null {
  if (!current) return null
  return dueTagOf(`node-${current.node_index}`, current.estimated_date, `${current.node_name} · 预计`)
}

function accentStyle(accent: string, accentBg: string): React.CSSProperties {
  return { '--accent': accent, '--accent-bg': accentBg } as React.CSSProperties
}

export default function RegistrationHomeClient() {
  const queryClient = useQueryClient()
  // 概览统计每次进入页面都取最新（品种/台账在其他页增删后，回来不能看到旧缓存）
  const fresh = { staleTime: 0, refetchOnMount: 'always' as const }
  const summaryQuery = useQuery({ queryKey: ['registration-ledger-summary'], queryFn: fetchLedgerSummary, ...fresh })
  const drugsQuery = useQuery({ queryKey: ['registration-drugs'], queryFn: fetchDrugs, ...fresh })
  const nodesQuery = useQuery({ queryKey: ['registration-review-nodes'], queryFn: fetchReviewNodes, ...fresh })

  const summary = summaryQuery.data ?? null
  const drugs = drugsQuery.data ?? []
  const reviewNodes = nodesQuery.data ?? []

  // 审评中口径：与申报进度查询页一致——除"全部节点已完成"外的品种都算审评中
  // （含新受理尚无节点、节点全部跳过的品种）
  const inProgressDrugs = drugs.filter(d => {
    const nodes = (d.nodes || []).filter(n => !n.skipped)
    return nodes.length === 0 || nodes.some(n => !n.actual_date)
  })

  // 审评中品种逐个拉预测（数量少，无瀑布问题）
  const predictionQueries = useQueries({
    queries: inProgressDrugs.map(d => ({
      queryKey: ['registration-drug-prediction', d.id],
      queryFn: () => fetchDrugPrediction(d.id),
    })),
  })

  const reviewing = inProgressDrugs
    .map((drug, i) => ({ drug, prediction: predictionQueries[i]?.data }))
    .filter((x): x is { drug: Drug; prediction: DrugPrediction } => !!x.prediction)

  // 证书有效期预警（更紧急）排在审评预警之前
  const alerts = [...computeCertAlerts(summary), ...computeAlerts(reviewing, reviewNodes)]
  const loading = summaryQuery.isFetching || drugsQuery.isFetching || nodesQuery.isFetching

  const handleRefresh = () => {
    void summaryQuery.refetch()
    void drugsQuery.refetch()
    void nodesQuery.refetch()
    void queryClient.invalidateQueries({ queryKey: ['registration-drug-prediction'] })
  }

  const kpis = [
    {
      key: 'domestic',
      label: '国内获批',
      icon: IconShieldCheck,
      accentVar: 'var(--brand-600)',
      accentBgVar: 'var(--brand-50)',
      href: '/registration/ledger?type=domestic',
      num: <>{summary?.domestic_count ?? 0}</>,
      sub: <>国内获批品种数量 · 今年新增 <b>{summary?.domestic_new_this_year ?? 0}</b></>,
    },
    {
      key: 'overseas',
      label: '国外获批',
      icon: IconGlobe,
      accentVar: 'var(--info-600)',
      accentBgVar: 'var(--info-50)',
      href: '/registration/ledger?type=overseas',
      num: <>{summary?.overseas_count ?? 0}</>,
      sub: <>覆盖 <b>{summary?.overseas_countries ?? 0}</b> 个国家/地区 · 今年新增 <b>{summary?.overseas_new_this_year ?? 0}</b></>,
    },
    {
      key: 'international',
      label: '国际关联审评',
      icon: IconLink,
      accentVar: 'var(--ok-600)',
      accentBgVar: 'var(--ok-50)',
      href: '/registration/ledger?type=international',
      num: <>{summary?.international_review_count ?? 0}</>,
      sub: '国际关联审评品种数',
    },
    {
      key: 'copp-wc',
      label: 'COPP / WC',
      icon: IconCert,
      accentVar: 'var(--warn-600)',
      accentBgVar: 'var(--warn-50)',
      href: '/registration/ledger?type=copp',
      num: <>{summary?.copp_count ?? 0}<small> / {summary?.wc_count ?? 0}</small></>,
      sub: `COPP ${summary?.copp_count ?? 0} 份 · WC ${summary?.wc_count ?? 0} 份证书 · 今年新增 ${(summary?.copp_new_this_year ?? 0) + (summary?.wc_new_this_year ?? 0)}`,
    },
  ]

  return (
    <div className={`${ui.regUi} ${styles.root}`}>
      <RegistrationPageHeader
        icon={IconTitleDoc}
        title="注册管理"
        sub="注册台账、审评进展与申报资料一览"
        actions={
          <>
            <button type="button" className={ui.btn} onClick={handleRefresh} disabled={loading}>
              {IconRefresh}
              刷新
            </button>
            <Link href="/registration/projects" className={ui.btnPrimary}>
              {IconPlus}
              新建注册项目
            </Link>
          </>
        }
      />

      {summaryQuery.isError && (
        <Alert
          type="warning"
          showIcon
          message="统计数据加载失败"
          description="注册台账汇总接口暂时不可用，下方功能不受影响。"
          action={<Button size="small" onClick={() => void summaryQuery.refetch()}>重试</Button>}
        />
      )}
      {drugsQuery.isError && (
        <Alert
          type="warning"
          showIcon
          message="审评品种加载失败"
          description="审评进度接口暂时不可用，请稍后重试。"
          action={<Button size="small" onClick={() => void drugsQuery.refetch()}>重试</Button>}
        />
      )}

      {/* ① KPI 条 */}
      <Spin spinning={summaryQuery.isPending}>
        <section className={styles.kpiRow}>
          {kpis.map(kpi => (
            <Link href={kpi.href} key={kpi.key} style={{ textDecoration: 'none' }}>
              <div className={styles.kpi} style={accentStyle(kpi.accentVar, kpi.accentBgVar)}>
                <div className={styles.kpiTop}>
                  <div className={styles.kpiChip}>{kpi.icon}</div>
                  <div className={styles.kpiLabel}>{kpi.label}</div>
                  <div className={styles.kpiLink}>明细 ›</div>
                </div>
                <div className={styles.kpiNum}>{kpi.num}</div>
                <div className={styles.kpiSub}>{kpi.sub}</div>
              </div>
            </Link>
          ))}
        </section>
      </Spin>

      {/* ② 工作区：审评中品种（7）+ 需要关注（5） */}
      <section className={styles.workRow}>
        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <div className={styles.panelIco} style={{ background: 'var(--brand-50)', color: 'var(--brand-600)' }}>
              {IconList}
            </div>
            <div className={styles.panelTitle}>审评中品种</div>
            <span className={styles.countPillBrand}>{inProgressDrugs.length}</span>
            <Link className={styles.panelMore} href="/registration/review">查看全部 ›</Link>
          </div>
          <Spin spinning={drugsQuery.isPending}>
            {reviewing.length === 0 ? (
              <div className={styles.emptyBody}>当前没有审评中的品种</div>
            ) : (
              // 最多展示 6 条（每行约 64px），超出卡片内部滚动
              <div style={{ maxHeight: 384, overflowY: 'auto' }}>
                {reviewing.map(({ drug, prediction }) => {
                  const current = prediction.nodes.find(n => n.node_index === prediction.current_node_index)
                  const nodeTag = nodeDueTag(current)
                  return (
                    <Link key={drug.id} href="/registration/review" className={styles.queueRow}>
                      <div>
                        <div className={styles.queueName}>{drug.name}</div>
                        <div className={styles.queueMeta}>
                          <span className={styles.tagBrand}>{drug.type}</span>
                          <span>预计获批：{prediction.estimated_approval_date ?? '日期待估'}</span>
                        </div>
                      </div>
                      <div className={styles.queueRight}>
                        {nodeTag && <span className={nodeTag.className}>{nodeTag.label}</span>}
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </Spin>
          <div className={styles.panelFoot}>
            <span>无审评任务时，可前往「审评进度」添加品种</span>
            <Link className={styles.panelMore} href="/registration/review">去添加 ›</Link>
          </div>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <div className={styles.panelIco} style={{ background: 'var(--warn-50)', color: 'var(--warn-600)' }}>
              {IconWarn}
            </div>
            <div className={styles.panelTitle}>需要关注</div>
            {alerts.length > 0 ? (
              <span className={styles.countPillWarn}>{alerts.length} 项待处理</span>
            ) : (
              <span className={styles.countPillOk}>0 项</span>
            )}
          </div>
          <Spin spinning={drugsQuery.isPending || predictionQueries.some(q => q.isPending)}>
            {alerts.length === 0 ? (
              <div className={styles.okState}>
                {IconCheckCircle}
                一切正常，暂无需要关注的事项
              </div>
            ) : (
              <>
                {alerts.slice(0, ALERT_DISPLAY_LIMIT).map(alert => (
                  <Link key={alert.key} href={alert.href} className={styles.alertRow}>
                    <span className={`${alert.severity === 'warn' ? styles.tagWarn : styles.tagRisk} ${styles.alertTag}`}>
                      {alert.severityLabel}
                    </span>
                    <div>
                      <div className={styles.alertText}>{alert.text}</div>
                      <div className={styles.alertSub}>{alert.suggestion}</div>
                    </div>
                    <span className={styles.alertAct}>去处理 ›</span>
                  </Link>
                ))}
                {alerts.length > ALERT_DISPLAY_LIMIT && (
                  <Link href="/registration/ledger" className={styles.alertRow}>
                    <div className={styles.alertText}>
                      还有 {alerts.length - ALERT_DISPLAY_LIMIT} 条预警，前往注册台账查看 ›
                    </div>
                  </Link>
                )}
              </>
            )}
          </Spin>
          <div className={styles.panelFoot}>
            <span>提醒基于审评节点停滞、获批临期与证书有效期规则自动生成</span>
          </div>
        </div>
      </section>

      {/* ③ 业务功能区 */}
      <div className={styles.bizHead}>
        <h2>业务功能</h2>
        <span>按工作流分组 · 共 {BIZ_GROUPS.reduce((n, g) => n + g.items.length, 0)} 项</span>
      </div>
      <section className={styles.bizGrid}>
        {BIZ_GROUPS.map(group => (
          <div
            key={group.key}
            className={styles.bizGroup}
            style={accentStyle(group.accentVar, group.accentBgVar)}
          >
            <div className={styles.bizGroupHead}>
              <div className={styles.kpiChip}>{group.icon}</div>
              <div className={styles.bizGroupTitle}>{group.title}</div>
              <div className={styles.bizGroupCount}>{group.items.length} 项</div>
            </div>
            {group.items.map(item => (
              <Link key={item.key} href={item.href} className={styles.bizItem}>
                <div className={styles.bizIco}>{item.icon}</div>
                <div>
                  <div className={styles.bizName}>{item.name}</div>
                  <div className={styles.bizDesc}>{item.desc}</div>
                </div>
                <span className={styles.bizArrow}>›</span>
              </Link>
            ))}
          </div>
        ))}
      </section>
    </div>
  )
}
