'use client'

/**
 * 申报进度查询（审评进度）
 * 视觉按 review-progress-redesign.html 原型实现：
 * - 页头 + 4 张 KPI 卡（数字滚动入场）
 * - 审评节点导轨（10 节点单行 + 流动虚线 + 轮回点亮动画）
 * - 六列表格：药品名称 / 类型 / 受理日期 / 审评进度（十分段条 + x/10）/ 当前节点 / 操作
 * 数据全部来自真实接口：/registration/drugs、/drugs/nodes、/drugs/{id}/prediction
 */

import { useState, useCallback, useMemo, useEffect, useRef } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Modal, App, Form, Input, Select, DatePicker, Popconfirm, Drawer, Empty, Spin, Switch,
} from 'antd'
import type { Dayjs } from 'dayjs'
import {
  Drug,
  fetchDrugs, fetchReviewNodes, fetchDrugPrediction, fetchProjectsByDrug,
} from '@/lib/api/client/registration'
import type { ReviewNodeConfig } from '@/types/registration'
import { createDrug, updateDrug, deleteDrug } from '@/actions/registration'
import { ReviewFlowGuide } from './ReviewFlowGuide'
import { projectStatusMeta } from './projectStatus'
import ui from './registration-ui.module.css'
import styles from './review-progress.module.css'
import {
  IconRefresh, IconPlus, IconFlask, IconBulb, IconClock, IconShieldCheck,
  IconTrash, IconCheck, IconList,
} from './RegistrationIcons'

type DrugType = '仿制药' | '创新药' | '原料药'

const PAGE_SIZE = 10
const TOTAL_NODES = 10

interface RowProgress {
  current: number | null
  approved: boolean
  label: string | null
}

/** 列表行进度：优先用后端 stage（含自动定位与逾期），无 stage 时本地兜底 */
function computeRowProgress(drug: Drug, reviewNodes: ReviewNodeConfig[]): RowProgress {
  const stage = drug.stage
  if (stage) {
    return {
      approved: stage.approved,
      current: stage.approved ? null : (stage.current_node_index ?? null),
      label: stage.approved ? '已获批' : (stage.current_node_name ?? null),
    }
  }
  const records = drug.nodes ?? []
  const lastIndex = reviewNodes.length
  const approved = records.some(n => n.node_index === lastIndex && n.actual_date)
  const current = reviewNodes.find(n => {
    const rec = records.find(x => x.node_index === n.index)
    return !rec?.skipped && !rec?.actual_date
  })
  return {
    approved,
    current: approved ? null : (current?.index ?? null),
    label: approved ? '已获批' : (current?.name ?? null),
  }
}

/** 当前节点标签配色映射：发补递交=橙、CDE 发补审评=蓝、开展核查=青、已获批=绿、其他=紫 */
function nodeTagClass(name: string | null | undefined, approved: boolean): string {
  if (approved) return ui.tagOk
  if (!name) return ui.tagBrand
  if (name.includes('发补递交')) return ui.tagWarn
  if (name.includes('发补审评')) return ui.tagInfo
  if (name.includes('开展核查')) return ui.tagTeal
  if (name.includes('获批')) return ui.tagOk
  return ui.tagBrand
}

/** KPI 数字滚动入场：0 → 目标值，900ms 三次缓出；减弱动效时直接显示终值 */
function CountUp({ value, delay = 0 }: { value: number; delay?: number }) {
  const [display, setDisplay] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches ? value : 0,
  )

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      // 初始值已是目标值，无需动画
      return
    }
    let raf = 0
    const startTimer = window.setTimeout(() => {
      const dur = 900
      const t0 = performance.now()
      const tick = (t: number) => {
        const p = Math.min((t - t0) / dur, 1)
        const e = 1 - Math.pow(1 - p, 3)
        setDisplay(Math.round(value * e))
        if (p < 1) raf = requestAnimationFrame(tick)
      }
      raf = requestAnimationFrame(tick)
    }, delay)
    // 兜底：动画结束后写回真实值，防止 rAF 被挂起时数字停在中间值
    const fallback = window.setTimeout(() => setDisplay(value), delay + 900 + 300)
    return () => {
      clearTimeout(startTimer)
      clearTimeout(fallback)
      cancelAnimationFrame(raf)
    }
  }, [value, delay])

  return <>{display}</>
}

export function ReviewPageClient() {
  const { message } = App.useApp()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('全部')
  const [yearFilter, setYearFilter] = useState<string>('全部')
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [expandedNode, setExpandedNode] = useState<number | null>(null)
  // 从概览页「?drug=xxx」进入时只定位一次，避免轮询刷新反复弹抽屉
  const focusedHandledRef = useRef<string | null>(null)
  const [addModalOpen, setAddModalOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [page, setPage] = useState(1)
  const [acceptanceNo, setAcceptanceNo] = useState('')
  const [acceptanceSaving, setAcceptanceSaving] = useState(false)
  const [form] = Form.useForm()

  const queryClient = useQueryClient()

  const { data: drugs = [], isLoading: drugsLoading } = useQuery({
    queryKey: ['registration-drugs'],
    queryFn: fetchDrugs,
  })

  const { data: reviewNodes = [], isLoading: nodesLoading } = useQuery({
    queryKey: ['registration-review-nodes'],
    queryFn: fetchReviewNodes,
  })

  const { data: prediction, isLoading: predictionLoading } = useQuery({
    queryKey: ['registration-drug-prediction', selectedDrug?.id],
    queryFn: () => fetchDrugPrediction(selectedDrug!.id),
    enabled: !!selectedDrug && drawerOpen,
  })

  const { data: drugProjects = [] } = useQuery({
    queryKey: ['registration-drug-projects', selectedDrug?.id],
    queryFn: () => fetchProjectsByDrug(selectedDrug!.id),
    enabled: !!selectedDrug && drawerOpen,
  })

  const loading = drugsLoading || nodesLoading

  const refreshData = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['registration-drugs'] })
    queryClient.invalidateQueries({ queryKey: ['registration-review-nodes'] })
    queryClient.invalidateQueries({ queryKey: ['registration-drug-prediction'] })
    queryClient.invalidateQueries({ queryKey: ['registration-ledger-summary'] })
    // 受理号登记 / 节点推进都会回写关联项目状态，抽屉内「关联注册项目」需即时刷新
    queryClient.invalidateQueries({ queryKey: ['registration-drug-projects'] })
    queryClient.invalidateQueries({ queryKey: ['registration-projects'] })
    queryClient.invalidateQueries({ queryKey: ['registration-projects-kpi'] })
  }, [queryClient])

  const filtered = useMemo(() => drugs.filter(d => {
    if (search && !d.name.includes(search)) return false
    if (typeFilter !== '全部' && d.type !== typeFilter) return false
    if (yearFilter !== '全部' && !d.acceptance_date.startsWith(yearFilter)) return false
    return true
  }), [drugs, search, typeFilter, yearFilter])

  const safePage = Math.min(page, Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)))
  const pagedDrugs = useMemo(
    () => filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [filtered, safePage],
  )
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))

  // KPI 卡：全局口径（不随搜索/筛选变化）
  const stats = useMemo(() => ({
    total: drugs.length,
    innovative: drugs.filter(d => d.type === '创新药').length,
    inProgress: drugs.filter(d => {
      const stage = d.stage
      if (stage) return stage.current_node_index != null && !stage.approved
      const nodes = (d.nodes || []).filter(n => !n.skipped)
      return nodes.some(n => n.actual_date) && nodes.some(n => !n.actual_date)
    }).length,
    approved: drugs.filter(d => {
      const stage = d.stage
      if (stage) return stage.approved
      const nodes = (d.nodes || []).filter(n => !n.skipped)
      const last = nodes.find(n => n.node_index === reviewNodes.length)
      return !!last?.actual_date
    }).length,
  }), [drugs, reviewNodes.length])

  const handleAdd = async (values: { name: string; type: DrugType; acceptance_date: Dayjs }) => {
    setSubmitting(true)
    try {
      await createDrug({
        name: values.name,
        type: values.type,
        acceptance_date: values.acceptance_date.format('YYYY-MM-DD'),
      })
      message.success('添加成功')
      setAddModalOpen(false)
      form.resetFields()
      refreshData()
    } catch {
      message.error('添加失败')
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteDrug(id)
      message.success('删除成功')
      if (selectedDrug?.id === id) { setSelectedDrug(null); setDrawerOpen(false) }
      refreshData()
    } catch {
      message.error('删除失败')
    }
  }

  const handleUpdateNode = async (drugId: string, nodeIndex: number, payload: { actual_date?: string | null; skipped?: boolean }) => {
    try {
      const result = await updateDrug(drugId, {
        nodes: [{ node_index: nodeIndex, ...payload }],
      })
      if (result && 'success' in result && result.success === false) {
        message.error(result.message || '更新失败')
        return
      }
      message.success('节点更新成功')
      refreshData()
    } catch {
      message.error('更新失败')
    }
  }

  const openDetail = (drug: Drug) => {
    setSelectedDrug(drug)
    setAcceptanceNo(drug.acceptance_number ?? '')
    setExpandedNode(null)
    setDrawerOpen(true)
  }

  // 概览页点击品种行 → /registration/review?drug=<id>：自动打开该品种详情
  useEffect(() => {
    if (typeof window === 'undefined') return
    const focusedId = new URLSearchParams(window.location.search).get('drug')
    if (!focusedId || !drugs.length) return
    if (focusedHandledRef.current === focusedId) return
    const target = drugs.find(d => d.id === focusedId)
    if (!target) return
    focusedHandledRef.current = focusedId
    // setState 挪入微任务，避免在 effect 体内同步触发级联渲染
    queueMicrotask(() => {
      setSelectedDrug(target)
      setAcceptanceNo(target.acceptance_number ?? '')
      setDrawerOpen(true)
    })
  }, [drugs])

  const handleSaveAcceptanceNo = async () => {
    if (!selectedDrug || acceptanceSaving) return
    setAcceptanceSaving(true)
    try {
      const result = await updateDrug(selectedDrug.id, { acceptance_number: acceptanceNo.trim() || null })
      if (result && 'success' in result && result.success === false) {
        message.error(result.message || '保存失败')
        return
      }
      message.success('受理号已登记，关联注册项目状态将自动同步')
      refreshData()
    } catch {
      message.error('保存失败')
    } finally {
      setAcceptanceSaving(false)
    }
  }

  const statCards = [
    { key: 'total', label: '药品总数', value: stats.total, sub: '在册申报品种', icon: IconFlask, accent: 'var(--brand-600)', accentBg: 'var(--brand-50)' },
    { key: 'innovative', label: '创新药', value: stats.innovative, sub: '创新药申报数量', icon: IconBulb, accent: 'var(--info-600)', accentBg: 'var(--info-50)' },
    { key: 'inProgress', label: '审评中', value: stats.inProgress, sub: '已有审评节点推进、尚未获批（含发补）', icon: IconClock, accent: 'var(--warn-600)', accentBg: 'var(--warn-50)' },
    { key: 'approved', label: '已获批', value: stats.approved, sub: '已获批准的品种', icon: IconShieldCheck, accent: 'var(--ok-600)', accentBg: 'var(--ok-50)' },
  ]

  // 抽屉时间轴：展开的节点 = 用户点选的，否则默认当前进行中节点
  const expandedIndex = expandedNode ?? prediction?.current_node_index ?? null
  const completedWithOverdue = (prediction?.completed_nodes ?? 0)
    + (prediction?.nodes?.filter(n => n.status === 'overdue').length ?? 0)
  const summaryPercent = prediction?.total_nodes
    ? Math.round((completedWithOverdue / prediction.total_nodes) * 100)
    : 0

  return (
    <div className={styles.reviewPage}>
      {/* 页头 */}
      <div className={styles.pageHead}>
        <div>
          <div className={styles.pageTitle}>
            <div className={styles.titleIco}>{IconClock}</div>
            <h1>申报进度查询</h1>
          </div>
          <div className={styles.pageSub}>审评节点进度跟踪与查询</div>
        </div>
        <div className={styles.headActions}>
          <button type="button" className={styles.btn} onClick={refreshData} disabled={loading}>
            {IconRefresh}
            刷新
          </button>
          <button type="button" className={styles.btnPrimary} onClick={() => setAddModalOpen(true)}>
            {IconPlus}
            添加药品
          </button>
        </div>
      </div>

      {/* ① KPI 条 */}
      <div className={styles.kpiRow} aria-label="进度概览">
        {statCards.map((card, i) => (
          <div
            key={card.key}
            className={styles.kpi}
            tabIndex={0}
            style={{ '--accent': card.accent, '--accent-bg': card.accentBg } as React.CSSProperties}
          >
            <div className={styles.kpiTop}>
              <div className={styles.kpiChip}>{card.icon}</div>
              <div className={styles.kpiLabel}>{card.label}</div>
            </div>
            <div className={styles.kpiNum}>
              <CountUp value={card.value} delay={120 + i * 90} />
            </div>
            <div className={styles.kpiSub}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* ② 审评节点导轨 */}
      <ReviewFlowGuide />

      {/* ③ 进度表格面板 */}
      <div className={styles.panel}>
        <div className={styles.panelHead}>
          <div className={styles.panelIco}>{IconList}</div>
          <div className={styles.panelTitle}>审评进度</div>
          <span className={styles.countPill}>{filtered.length}</span>
          <div className={styles.toolbar}>
            <div className={styles.search}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                <circle cx="11" cy="11" r="7" />
                <path d="m21 21-4.3-4.3" />
              </svg>
              <input
                type="text"
                placeholder="药品名称"
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
            </div>
            <select className={styles.select} value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
              <option value="全部">全部类型</option>
              <option value="原料药">原料药</option>
              <option value="创新药">创新药</option>
              <option value="仿制药">仿制药</option>
            </select>
            <select className={styles.select} value={yearFilter} onChange={e => setYearFilter(e.target.value)}>
              <option value="全部">全部年份</option>
              <option value="2025">2025</option>
              <option value="2026">2026</option>
              <option value="2027">2027</option>
            </select>
          </div>
        </div>

        <div className={styles.tableWrap}>
          {loading ? (
            <div className={styles.emptyRow}><Spin /></div>
          ) : pagedDrugs.length === 0 ? (
            <div className={styles.emptyRow}>暂无数据</div>
          ) : (
            <table className={styles.table}>
              <thead>
                <tr>
                  <th className={styles.th}>药品名称</th>
                  <th className={styles.th}>类型</th>
                  <th className={styles.th}>受理日期</th>
                  <th className={styles.th}>审评进度</th>
                  <th className={styles.th}>当前节点</th>
                  <th className={styles.th}>操作</th>
                </tr>
              </thead>
              <tbody>
                {pagedDrugs.map(record => {
                  const p = computeRowProgress(record, reviewNodes)
                  const current = p.approved ? TOTAL_NODES : (p.current ?? 0)
                  return (
                    <tr key={record.id} className={styles.row} tabIndex={0} onClick={() => openDetail(record)}>
                      <td className={styles.td}>
                        <div className={styles.drug}>
                          <div className={styles.drugIco}>{IconFlask}</div>
                          <div>
                            <div className={styles.drugName}>{record.name}</div>
                            <div className={styles.drugSub}>
                              {record.acceptance_number ? `受理号 ${record.acceptance_number}` : '未登记受理号'}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className={styles.td}><span className={ui.tagBrand}>{record.type}</span></td>
                      <td className={styles.td}>{record.acceptance_date}</td>
                      <td className={styles.td}>
                        <div className={styles.prog}>
                          <div className={styles.steps}>
                            {Array.from({ length: TOTAL_NODES }, (_, idx) => {
                              const i = idx + 1
                              const cls = p.approved || i < current
                                ? styles.segmentDone
                                : i === current
                                  ? styles.segmentCur
                                  : styles.segment
                              return (
                                <i
                                  key={i}
                                  className={cls}
                                  style={{ animationDelay: `${0.5 + idx * 0.05}s` }}
                                />
                              )
                            })}
                          </div>
                          <span className={styles.pct}>{current}/{TOTAL_NODES}</span>
                        </div>
                      </td>
                      <td className={styles.td}>
                        {p.label
                          ? <span className={nodeTagClass(p.label, p.approved)}>{p.label}</span>
                          : <span className={ui.tagPlain}>未开始</span>}
                      </td>
                      <td className={styles.td}>
                        <button type="button" className={styles.link} onClick={e => { e.stopPropagation(); openDetail(record) }}>
                          详情 ›
                        </button>
                        <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="确定" cancelText="取消">
                          <button type="button" className={styles.opDel} title="删除" onClick={e => e.stopPropagation()}>
                            {IconTrash}
                          </button>
                        </Popconfirm>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        <div className={styles.panelFoot}>
          <span>共 {filtered.length} 条</span>
          <div className={styles.pager}>
            <button type="button" className={styles.pg} disabled={safePage <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>‹</button>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map(p => (
              <button
                key={p}
                type="button"
                className={`${styles.pg} ${p === safePage ? styles.on : ''}`}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            ))}
            <button type="button" className={styles.pg} disabled={safePage >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>›</button>
          </div>
        </div>
      </div>

      {/* 详情抽屉：540px，摘要卡 + 节点时间轴 */}
      <Drawer
        size={540}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setSelectedDrug(null) }}
        title={
          selectedDrug && (
            <div>
              <div className={styles.drawerName}>
                {selectedDrug.name}
                <span className={ui.tagBrand}>{selectedDrug.type}</span>
              </div>
              <div className={styles.drawerSub}>受理日期：{selectedDrug.acceptance_date}</div>
            </div>
          )
        }
        styles={{ body: { padding: 0 } }}
      >
        <div className={`${ui.tokenScope} ${styles.drawerBody}`}>
          {selectedDrug && (
            <Spin spinning={predictionLoading}>
              {prediction && (
                <>
                  <div className={styles.summary}>
                    <div className={styles.summaryTop}>
                      <span className={styles.summaryLabel}>整体进度</span>
                      <span className={styles.summaryNum}>
                        {completedWithOverdue}/{prediction.total_nodes} · {summaryPercent}%
                      </span>
                    </div>
                    <div className={styles.summaryBar}>
                      <i className={styles.summaryBarFill} style={{ width: `${summaryPercent}%` }} />
                    </div>
                    <div className={styles.summaryDates}>
                      <div>
                        <div className={styles.dLabel}>受理日期</div>
                        <div className={styles.dVal}>{selectedDrug.acceptance_date}</div>
                      </div>
                      {prediction.estimated_approval_date && (
                        <div>
                          <div className={styles.dLabel}>预计获批</div>
                          <div className={styles.dValKey}>{prediction.estimated_approval_date}</div>
                        </div>
                      )}
                    </div>
                  </div>

                  <div className={styles.acceptanceRow}>
                    <span className={styles.acceptanceLabel}>受理号</span>
                    <Input
                      size="small"
                      placeholder="登记受理号，如 CXHS2600001"
                      value={acceptanceNo}
                      onChange={e => setAcceptanceNo(e.target.value)}
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className={styles.acceptanceSave}
                      disabled={acceptanceSaving || acceptanceNo.trim() === (selectedDrug.acceptance_number ?? '')}
                      onClick={() => void handleSaveAcceptanceNo()}
                    >
                      登记
                    </button>
                  </div>

                  <div className={styles.tlTitle}>
                    关联注册项目
                    <span className={styles.tlCount}>共 {drugProjects.length} 个</span>
                  </div>
                  {drugProjects.length > 0 ? (
                    <div className={styles.projList}>
                      {drugProjects.map(project => {
                        const cfg = projectStatusMeta(project.status)
                        return (
                          <Link
                            key={project.id}
                            href={`/registration/projects?project=${project.id}`}
                            className={styles.projItem}
                          >
                            <span className={styles.projName}>
                              {project.market} · {project.registration_type || '注册'}
                            </span>
                            <span className={cfg.tagClass}>{cfg.label}</span>
                            <span className={styles.projMeta}>
                              {project.owner || '未指定负责人'}
                              {project.expected_completion_at ? ` · 预计 ${project.expected_completion_at}` : ''}
                            </span>
                            <span className={styles.projLink}>查看 ›</span>
                          </Link>
                        )
                      })}
                    </div>
                  ) : (
                    <div className={styles.projEmpty}>
                      <div className={styles.projEmptyText}>该品种暂未关联注册项目</div>
                      <Link href="/registration/projects" className={styles.projEmptyLink}>
                        去注册项目页创建 ›
                      </Link>
                    </div>
                  )}

                  <div className={styles.tlTitle}>
                    审评节点
                    <span className={styles.tlCount}>共 {prediction.total_nodes} 个</span>
                  </div>
                  {prediction.nodes.map(node => {
                    const expanded = expandedIndex === node.node_index
                    const stateClass =
                      node.status === 'in_progress' ? styles.tlItemCurrent
                      : node.status === 'completed' || node.status === 'overdue' ? styles.tlItemDone
                      : ''
                    return (
                      <div
                        key={node.node_index}
                        className={`${styles.tlItem} ${stateClass} ${expanded ? styles.tlItemExpanded : ''}`}
                        onClick={() => setExpandedNode(expanded ? -1 : node.node_index)}
                      >
                        <div className={styles.tlDot}>
                          {node.status === 'completed' || node.status === 'overdue' ? IconCheck
                            : node.status === 'skipped' ? '–'
                            : node.node_index}
                        </div>
                        <div className={styles.tlBody}>
                          <div className={styles.tlRow}>
                            <span className={node.status === 'skipped' ? styles.tlNameSkipped : styles.tlName}>
                              {node.node_name}
                            </span>
                            {node.status === 'in_progress' && (
                              <span className={ui.tagBrand}>进行中</span>
                            )}
                            <span className={styles.tlManage}>标记 ›</span>
                          </div>
                          <div className={styles.tlMeta}>
                            {node.status === 'skipped'
                              ? '该节点不发生（已跳过）'
                              : node.status === 'overdue'
                                ? `预计 ${node.estimated_date ?? '-'}（按预测已通过，实际日期未填）`
                                : node.actual_date
                                  ? `实际：${node.actual_date}`
                                  : `预计：${node.estimated_date ?? '-'}`}
                          </div>
                          <div className={styles.tlControls} onClick={e => e.stopPropagation()}>
                            {node.status !== 'skipped' && (
                              <>
                                <span>标记完成日期</span>
                                <DatePicker
                                  size="small"
                                  placeholder="选择日期"
                                  onChange={(date: Dayjs | null) =>
                                    handleUpdateNode(selectedDrug.id, node.node_index, {
                                      actual_date: date ? date.format('YYYY-MM-DD') : null,
                                    })
                                  }
                                />
                                {node.actual_date && (
                                  <button
                                    type="button"
                                    className={styles.undoLink}
                                    onClick={() => handleUpdateNode(selectedDrug.id, node.node_index, { actual_date: null })}
                                  >
                                    撤销完成
                                  </button>
                                )}
                              </>
                            )}
                            <span>跳过此节点</span>
                            <Switch
                              size="small"
                              checked={node.status === 'skipped'}
                              onChange={checked =>
                                handleUpdateNode(selectedDrug.id, node.node_index, { skipped: checked })
                              }
                            />
                          </div>
                        </div>
                      </div>
                    )
                  })}
                </>
              )}
              {!prediction && !predictionLoading && (
                <Empty description="预测数据加载失败" />
              )}
            </Spin>
          )}
        </div>
      </Drawer>

      {/* 添加药品弹窗 */}
      <Modal
        title="添加药品"
        open={addModalOpen}
        onCancel={() => { setAddModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
        confirmLoading={submitting}
      >
        <Form form={form} layout="vertical" onFinish={handleAdd}>
          <Form.Item name="name" label="药品名称" rules={[{ required: true, message: '请输入药品名称' }]}>
            <Input placeholder="请输入药品名称" />
          </Form.Item>
          <Form.Item name="type" label="药品类型" rules={[{ required: true, message: '请选择类型' }]}>
            <Select
              placeholder="请选择类型"
              options={[
                { label: '创新药', value: '创新药' },
                { label: '仿制药', value: '仿制药' },
                { label: '原料药', value: '原料药' },
              ]}
            />
          </Form.Item>
          <Form.Item name="acceptance_date" label="受理日期" rules={[{ required: true, message: '请选择日期' }]}>
            <DatePicker className="w-full" placeholder="请选择受理日期" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
