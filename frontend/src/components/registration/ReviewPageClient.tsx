'use client'

/**
 * 申报进度查询（审评进度）
 * 视觉按 review-progress-redesign.html 原型实现：
 * - KPI 卡（芯片图标 + 32px 彩色数字）
 * - 表格「审评进度」列 = 6px 进度条 + n/m，替代原圆点
 * - 详情抽屉 540px：摘要卡 + 节点时间轴；节点操作默认收起，仅当前进行中节点默认展开
 * 数据全部来自真实接口：/registration/drugs、/drugs/nodes、/drugs/{id}/prediction
 */

import { useState, useCallback, useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Table, Space, Input, Select, Modal, App, Form, DatePicker,
  Popconfirm, Drawer, Empty, Spin, Switch, Pagination,
} from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { Dayjs } from 'dayjs'
import {
  Drug,
  fetchDrugs, fetchReviewNodes, fetchDrugPrediction, fetchProjectsByDrug,
} from '@/lib/api/client/registration'
import type { ReviewNodeConfig } from '@/types/registration'
import { createDrug, updateDrug, deleteDrug } from '@/actions/registration'
import { RegistrationPageHeader } from './RegistrationPageHeader'
import ui from './registration-ui.module.css'
import styles from './review-progress.module.css'
import {
  IconActivity, IconRefresh, IconPlus, IconFlask, IconBulb,
  IconClock, IconShieldCheck, IconTrash, IconCheck,
} from './registration-icons'

type DrugType = '仿制药' | '创新药' | '原料药'

const PAGE_SIZE = 10

/** 注册项目状态标签（与注册项目页保持一致） */
const PROJECT_STATUS: Record<string, { label: string; className: string }> = {
  draft: { label: '草稿', className: ui.tagPlain },
  preparing: { label: '准备中', className: ui.tagPlain },
  submitted: { label: '已申报', className: ui.tagInfo },
  accepted: { label: '已受理', className: ui.tagInfo },
  under_review: { label: '审评中', className: ui.tagWarn },
  supplementary: { label: '发补中', className: ui.tagWarn },
  approved: { label: '已获批', className: ui.tagOk },
  withdrawn: { label: '已撤回', className: ui.tagPlain },
  terminated: { label: '已终止', className: ui.tagRisk },
}

interface RowProgress {
  completed: number
  total: number
  percent: number
  currentNodeName: string | null
}

/** 列表行进度：有效节点 = 全部节点 - 已跳过；当前节点 = 首个未完成且未跳过的节点 */
function computeRowProgress(drug: Drug, reviewNodes: ReviewNodeConfig[]): RowProgress {
  const records = drug.nodes ?? []
  const skippedCount = records.filter(n => n.skipped).length
  const completed = records.filter(n => !n.skipped && n.actual_date).length
  const total = Math.max(reviewNodes.length - skippedCount, 0)
  const current = reviewNodes.find(n => {
    const rec = records.find(x => x.node_index === n.index)
    return !rec?.skipped && !rec?.actual_date
  })
  return {
    completed,
    total,
    percent: total ? Math.round((completed / total) * 100) : 0,
    currentNodeName: current?.name ?? null,
  }
}

export function ReviewPageClient() {
  const { message } = App.useApp()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('全部')
  const [yearFilter, setYearFilter] = useState<string>('全部')
  const [selectedDrug, setSelectedDrug] = useState<Drug | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [expandedNode, setExpandedNode] = useState<number | null>(null)
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

  // 该品种关联的注册项目（抽屉内展示，双向联动）
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
    // 品种增删会影响概览页 KPI 的"审评中"计数，同步失效
    queryClient.invalidateQueries({ queryKey: ['registration-ledger-summary'] })
  }, [queryClient])

  const filtered = useMemo(() => drugs.filter(d => {
    if (search && !d.name.includes(search)) return false
    if (typeFilter !== '全部' && d.type !== typeFilter) return false
    if (yearFilter !== '全部' && !d.acceptance_date.startsWith(yearFilter)) return false
    return true
  }), [drugs, search, typeFilter, yearFilter])

  // 筛选变化后回到第一页；当前页数据切片
  const safePage = Math.min(page, Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)))
  const pagedDrugs = useMemo(
    () => filtered.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [filtered, safePage],
  )

  const stats = useMemo(() => {
    const lastIndex = reviewNodes.length
    return {
      total: filtered.length,
      innovative: filtered.filter(d => d.type === '创新药').length,
      inProgress: filtered.filter(d => {
        const nodes = (d.nodes || []).filter(n => !n.skipped)
        return nodes.some(n => n.actual_date) && nodes.some(n => !n.actual_date)
      }).length,
      approved: filtered.filter(d => {
        const nodes = (d.nodes || []).filter(n => !n.skipped)
        const last = nodes.find(n => n.node_index === lastIndex)
        return !!last?.actual_date
      }).length,
    }
  }, [filtered, reviewNodes.length])

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

  const openDetail = (drug: Drug) => {
    setSelectedDrug(drug)
    setAcceptanceNo(drug.acceptance_number ?? '')
    setExpandedNode(null) // 重置为「当前进行中节点默认展开」
    setDrawerOpen(true)
  }

  /** 登记受理号：回写后触发后端同步，关联注册项目状态自动置「已受理」并留痕 */
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
      // 同步刷新注册项目页缓存（若已打开）
      queryClient.invalidateQueries({ queryKey: ['registration-projects'] })
    } catch {
      message.error('保存失败')
    } finally {
      setAcceptanceSaving(false)
    }
  }

  const statCards = [
    { key: 'total', label: '药品总数', value: stats.total, icon: IconFlask, accent: 'var(--brand-600)', accentBg: 'var(--brand-50)' },
    { key: 'innovative', label: '创新药', value: stats.innovative, icon: IconBulb, accent: 'var(--info-600)', accentBg: 'var(--info-50)' },
    { key: 'inProgress', label: '审评中', value: stats.inProgress, icon: IconClock, accent: 'var(--warn-600)', accentBg: 'var(--warn-50)' },
    { key: 'approved', label: '已获批', value: stats.approved, icon: IconShieldCheck, accent: 'var(--ok-600)', accentBg: 'var(--ok-50)' },
  ]

  // 列宽按原型固定百分比（tableLayout="fixed" 生效）；两端钉死：首列左、末列右、中间居中
  const columns = [
    {
      title: '药品名称',
      dataIndex: 'name',
      key: 'name',
      width: '14%',
      align: 'left' as const,
      render: (text: string) => <span className={styles.drugName}>{text}</span>,
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: '9%',
      align: 'center' as const,
      render: (type: DrugType) => <span className={ui.tagOk}>{type}</span>,
    },
    {
      title: '受理日期',
      dataIndex: 'acceptance_date',
      key: 'acceptance_date',
      width: '12%',
      align: 'center' as const,
    },
    {
      title: '审评进度',
      key: 'progress',
      width: '34%',
      align: 'center' as const,
      render: (_: unknown, record: Drug) => {
        // 分段短横线：每个节点一根；已完成或已跳过=实心紫，未到达=描边空心
        const records = record.nodes ?? []
        const skippedCount = records.filter(n => n.skipped).length
        const completed = records.filter(n => !n.skipped && n.actual_date).length
        const total = Math.max(reviewNodes.length - skippedCount, 0)
        return (
          <div className={styles.progressCell}>
            <div className={styles.segments}>
              {reviewNodes.map(n => {
                const rec = records.find(x => x.node_index === n.index)
                const filled = !!rec?.actual_date || !!rec?.skipped
                return <i key={n.index} className={filled ? styles.segFilled : styles.seg} />
              })}
            </div>
            <span className={styles.segNum}>{completed}/{total}</span>
          </div>
        )
      },
    },
    {
      title: '当前节点',
      key: 'currentNode',
      width: '21%',
      align: 'center' as const,
      render: (_: unknown, record: Drug) => {
        const p = computeRowProgress(record, reviewNodes)
        return p.currentNodeName
          ? <span className={ui.tagInfo}>{p.currentNodeName}</span>
          : <span className={ui.tagOk}>已完成</span>
      },
    },
    {
      title: '操作',
      key: 'action',
      width: '10%',
      align: 'right' as const,
      render: (_: unknown, record: Drug) => (
        <Space size={0} onClick={e => e.stopPropagation()}>
          <button type="button" className={styles.opLink} onClick={() => openDetail(record)}>
            详情
          </button>
          <Popconfirm title="确定删除？" onConfirm={() => handleDelete(record.id)} okText="确定" cancelText="取消">
            <button type="button" className={styles.opDel} title="删除">{IconTrash}</button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 抽屉时间轴：展开的节点 = 用户点选的，否则默认当前进行中节点
  const expandedIndex = expandedNode ?? prediction?.current_node_index ?? null
  const summaryPercent = prediction?.total_nodes
    ? Math.round((prediction.completed_nodes / prediction.total_nodes) * 100)
    : 0

  return (
    <div className={ui.regUi}>
      <RegistrationPageHeader
        icon={IconActivity}
        title="申报进度查询"
        sub="审评节点进度跟踪与预测"
        actions={
          <>
            <button type="button" className={ui.btn} onClick={refreshData} disabled={loading}>
              {IconRefresh}
              刷新
            </button>
            <button type="button" className={ui.btnPrimary} onClick={() => setAddModalOpen(true)}>
              {IconPlus}
              添加药品
            </button>
          </>
        }
      />

      {/* 指标条：与原型一致的芯片 KPI 卡 */}
      <div className={ui.kpiRow}>
        {statCards.map(card => (
          <div
            key={card.key}
            className={ui.kpi}
            style={{ '--accent': card.accent, '--accent-bg': card.accentBg } as React.CSSProperties}
          >
            <div className={ui.kpiTop}>
              <div className={ui.kpiChip}>{card.icon}</div>
              <div className={ui.kpiLabel}>{card.label}</div>
            </div>
            <div className={ui.kpiNum}>{card.value}</div>
          </div>
        ))}
      </div>

      {/* 列表面板 */}
      <div className={ui.panel}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGroup}>
            <Input
              placeholder="搜索药品名称"
              prefix={<SearchOutlined />}
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ width: 240 }}
              allowClear
            />
            <Select value={typeFilter} onChange={setTypeFilter} style={{ width: 120 }}
              options={[
                { label: '全部类型', value: '全部' },
                { label: '创新药', value: '创新药' },
                { label: '仿制药', value: '仿制药' },
                { label: '原料药', value: '原料药' },
              ]}
            />
            <Select value={yearFilter} onChange={setYearFilter} style={{ width: 120 }}
              options={[
                { label: '全部年份', value: '全部' },
                { label: '2025', value: '2025' },
                { label: '2026', value: '2026' },
                { label: '2027', value: '2027' },
              ]}
            />
          </div>
          <div className={styles.toolbarHint}>点击任意行可打开进度详情</div>
        </div>
        <div className={`${ui.tableWrap} ${styles.tableLg}`}>
          <Table
            dataSource={pagedDrugs}
            columns={columns}
            rowKey="id"
            loading={loading}
            pagination={false}
            tableLayout="fixed"
            size="middle"
            onRow={record => ({
              onClick: () => openDetail(record),
              style: { cursor: 'pointer' },
            })}
          />
        </div>
        {/* 底部栏：左侧总数，右侧分页（当前页紫底白字） */}
        <div className={styles.tableFoot}>
          <span className={styles.totalText}>共 {filtered.length} 条</span>
          <Pagination
            current={safePage}
            pageSize={PAGE_SIZE}
            total={filtered.length}
            onChange={setPage}
            size="small"
            showSizeChanger={false}
          />
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
                <span className={ui.tagOk}>{selectedDrug.type}</span>
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
                  {/* 摘要卡 */}
                  <div className={styles.summary}>
                    <div className={styles.summaryTop}>
                      <span className={styles.summaryLabel}>整体进度</span>
                      <span className={styles.summaryNum}>
                        {prediction.completed_nodes}/{prediction.total_nodes} · {summaryPercent}%
                      </span>
                    </div>
                    <div className={styles.summaryBar}>
                      <i className={styles.barFill} style={{ width: `${summaryPercent}%` }} />
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

                  {/* 受理号登记：登记后自动同步关联注册项目状态为「已受理」 */}
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

                  {/* 关联注册项目 */}
                  {drugProjects.length > 0 && (
                    <>
                      <div className={styles.tlTitle}>
                        关联注册项目
                        <span className={styles.tlCount}>共 {drugProjects.length} 个</span>
                      </div>
                      <div className={styles.projList}>
                        {drugProjects.map(project => {
                          const cfg = PROJECT_STATUS[project.status] || { label: project.status, className: ui.tagPlain }
                          return (
                            <a key={project.id} href="/registration/projects" className={styles.projItem}>
                              <span className={styles.projName}>
                                {project.market} · {project.registration_type || '注册'}
                              </span>
                              <span className={cfg.className}>{cfg.label}</span>
                              <span className={styles.projMeta}>
                                {project.owner || '未指定负责人'}
                                {project.expected_completion_at ? ` · 预计 ${project.expected_completion_at}` : ''}
                              </span>
                              <span className={styles.projLink}>查看 ›</span>
                            </a>
                          )
                        })}
                      </div>
                    </>
                  )}

                  {/* 节点时间轴 */}
                  <div className={styles.tlTitle}>
                    审评节点
                    <span className={styles.tlCount}>共 {prediction.total_nodes} 个</span>
                  </div>
                  {prediction.nodes.map(node => {
                    const expanded = expandedIndex === node.node_index
                    const stateClass =
                      node.status === 'in_progress' ? styles.tlItemCurrent
                      : node.status === 'completed' ? styles.tlItemDone
                      : ''
                    return (
                      <div
                        key={node.node_index}
                        className={`${styles.tlItem} ${stateClass} ${expanded ? styles.tlItemExpanded : ''}`}
                        onClick={() => setExpandedNode(expanded ? -1 : node.node_index)}
                      >
                        <div className={styles.tlDot}>
                          {node.status === 'completed' ? IconCheck
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
                              : node.actual_date
                                ? `实际：${node.actual_date}`
                                : `预计：${node.estimated_date ?? '-'}`}
                          </div>
                          {/* 节点操作区：默认收起，仅当前进行中节点默认展开 */}
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
