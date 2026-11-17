'use client'

/**
 * 注册项目页（按 registration-project-redesign 原型实现）
 * - KPI：申报前（蓝）/ 已受理·审评中（紫）/ 临期未递交（橙）/ 已获批（绿）
 * - 表格列宽固定、两端钉死（首列左 / 末列右 / 中间居中）、申报前阶段 5 段分段横线
 * - 受理后状态（已受理/审评中/发补中/已获批/已撤回/已终止）带「· 同步」标，本页只读
 * - 维护抽屉：阶段轨点击推进（受理为界）、基本信息、进展时间线（只增不删）
 * 数据全部来自真实接口：/registration/projects（列表/KPI/阶段/进展记录）
 */

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, DatePicker, Drawer, Empty, Form, Input, Modal, Pagination, Popconfirm, Select, Spin, Table } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import type { Dayjs } from 'dayjs'

import {
  addProjectProgressLog,
  advanceProjectStage,
  createRegistrationProject,
  deleteRegistrationProject,
  fetchProjectKpiServer,
  fetchProjectLogsServer,
  fetchRegistrationProjectsServer,
} from '@/actions/registration'
import { searchPersonnel } from '@/lib/api/client/identity'
import type { PreStage, RegistrationProject } from '@/types/registration'
import { DataUnavailable } from '@/components/common/DataUnavailable'
import { RegistrationPageHeader } from './RegistrationPageHeader'
import { RegSvg } from './registration-icons'
import ui from './registration-ui.module.css'
import styles from './projects.module.css'
import {
  IconActivity,
  IconCheck,
  IconGrid,
  IconList,
  IconPlus,
  IconRefresh,
  IconTrash,
  IconWarn,
} from './registration-icons'

// ── 常量（与后端状态机一致） ──

const STAGES: { key: PreStage; label: string }[] = [
  { key: 'initiation', label: '立项' },
  { key: 'data_preparation', label: '资料准备' },
  { key: 'internal_review', label: '内部审核' },
  { key: 'submission', label: '递交' },
  { key: 'accepted', label: '已受理' },
]

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  preparing: '准备中',
  submitted: '已申报',
  accepted: '已受理',
  under_review: '审评中',
  supplementary: '发补中',
  approved: '已获批',
  withdrawn: '已撤回',
  terminated: '已终止',
}

/** 受理后状态：唯一维护入口为申报进度查询，本页只读并带「· 同步」标 */
const POST_ACCEPTANCE = new Set(['accepted', 'under_review', 'supplementary', 'approved', 'withdrawn', 'terminated'])

const TYPE_CARDS = [
  { value: '新注册', desc: '品种首次申请注册，从零递交整套资料', icon: <RegSvg size={15}><path d="M12 5v14M5 12h14" /></RegSvg> },
  { value: '再注册', desc: '证书到期前申请延续，沿用原资料基础', icon: <RegSvg size={15}><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" /></RegSvg> },
  { value: '变更', desc: '已获批内容发生变化，按变更等级申报', icon: <RegSvg size={15}><path d="M17 3a2.83 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z" /></RegSvg> },
  { value: '补充申请', desc: '审评过程中应要求补充资料或说明', icon: <RegSvg size={15}><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6M12 18v-6M9 15h6" /></RegSvg> },
]

const IconSync = (
  <RegSvg size={12}>
    <path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" />
  </RegSvg>
)
const IconInfo = (
  <RegSvg size={16}>
    <circle cx="12" cy="12" r="10" />
    <path d="M12 16v-4M12 8h.01" />
  </RegSvg>
)
const IconLock = (
  <RegSvg size={14}>
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </RegSvg>
)

const PAGE_SIZE = 10

function statusTagClass(status: string): string {
  switch (status) {
    case 'draft':
    case 'terminated':
      return ui.tagPlain
    case 'submitted':
      return ui.tagBrand
    case 'supplementary':
      return ui.tagWarn
    case 'approved':
      return ui.tagOk
    case 'withdrawn':
      return ui.tagRisk
    default:
      return ui.tagInfo
  }
}

/** 状态标签：受理后状态前带同步图标 + 「· 同步」后缀 */
function StatusTag({ status }: { status: string }) {
  const synced = POST_ACCEPTANCE.has(status)
  return (
    <span className={`${statusTagClass(status)} ${synced ? styles.syncTag : ''}`}>
      {synced && IconSync}
      {STATUS_LABELS[status] ?? status}
      {synced && ' · 同步'}
    </span>
  )
}

/** 系统记录内容渲染：「草稿 → 准备中」两侧加粗高亮 */
function SystemLogText({ content }: { content: string }) {
  const arrowIdx = content.indexOf(' → ')
  if (arrowIdx > 0) {
    const from = content.slice(0, arrowIdx)
    const to = content.slice(arrowIdx + 3)
    const prefixMatch = from.match(/^(状态变更|阶段推进|阶段回退)：(.*)$/)
    if (prefixMatch) {
      return (
        <>
          {prefixMatch[1]}：<b>{prefixMatch[2]}</b> → <b>{to}</b>
        </>
      )
    }
    return (
      <>
        状态变更：<b>{from}</b> → <b>{to}</b>
      </>
    )
  }
  const colonIdx = content.indexOf('：')
  if (colonIdx > 0) {
    return (
      <>
        {content.slice(0, colonIdx)}：<b>{content.slice(colonIdx + 1)}</b>
      </>
    )
  }
  return <>{content}</>
}

export function ProjectsPageClient() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('全部')
  const [statusFilter, setStatusFilter] = useState<string>('全部')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<RegistrationProject | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [createOpen, setCreateOpen] = useState(false)
  const [regType, setRegType] = useState<string>('新注册')
  const [submitting, setSubmitting] = useState(false)
  const [logText, setLogText] = useState('')
  const [logSaving, setLogSaving] = useState(false)
  const [advancing, setAdvancing] = useState(false)
  const [createForm] = Form.useForm()

  // 集合端点规范路径带尾斜杠，浏览器直连会被 trailingSlash 归一化打断 → 统一走 Server Action 服务端取数
  const projectsQuery = useQuery({
    queryKey: ['registration-projects', search, typeFilter, statusFilter],
    queryFn: () =>
      fetchRegistrationProjectsServer({
        search: search || undefined,
        registration_type: typeFilter === '全部' ? undefined : typeFilter,
        status: statusFilter === '全部' ? undefined : statusFilter,
      }),
  })
  const projects = useMemo(() => projectsQuery.data ?? [], [projectsQuery.data])

  const kpiQuery = useQuery({
    queryKey: ['registration-projects-kpi'],
    queryFn: fetchProjectKpiServer,
  })

  const logsQuery = useQuery({
    queryKey: ['registration-project-logs', selected?.id],
    queryFn: () => fetchProjectLogsServer(selected!.id),
    enabled: !!selected && drawerOpen,
  })
  const logs = useMemo(() => logsQuery.data ?? [], [logsQuery.data])

  const personnelQuery = useQuery({
    queryKey: ['identity-personnel-options'],
    queryFn: () => searchPersonnel('', 0, 100),
    enabled: createOpen,
  })

  const refreshAll = () => {
    void queryClient.invalidateQueries({ queryKey: ['registration-projects'] })
    void queryClient.invalidateQueries({ queryKey: ['registration-projects-kpi'] })
    void queryClient.invalidateQueries({ queryKey: ['registration-project-logs'] })
  }

  // ── 派生数据 ──

  const safePage = Math.min(page, Math.max(1, Math.ceil(projects.length / PAGE_SIZE)))
  const pagedProjects = useMemo(
    () => projects.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE),
    [projects, safePage],
  )

  const kpi = kpiQuery.data
  const statCards = [
    { key: 'pre', label: '申报前', value: kpi?.pre_submission, icon: IconList, accent: 'var(--info-600)', accentBg: 'var(--info-50)' },
    { key: 'reviewing', label: '已受理 · 审评中', value: kpi?.accepted_reviewing, icon: IconActivity, accent: 'var(--brand-600)', accentBg: 'var(--brand-50)' },
    { key: 'due', label: '临期未递交', value: kpi?.due_soon, icon: IconWarn, accent: 'var(--warn-600)', accentBg: 'var(--warn-50)' },
    { key: 'approved', label: '已获批', value: kpi?.approved, icon: IconCheck, accent: 'var(--ok-600)', accentBg: 'var(--ok-50)' },
  ]

  // ── 行为 ──

  const openDrawer = (project: RegistrationProject) => {
    setSelected(project)
    setLogText('')
    setDrawerOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteRegistrationProject(id)
      message.success('删除成功')
      if (selected?.id === id) setDrawerOpen(false)
      refreshAll()
    } catch {
      message.error('删除失败')
    }
  }

  const handleCreate = async () => {
    try {
      const values = await createForm.validateFields()
      setSubmitting(true)
      const result = await createRegistrationProject({
        name: values.name,
        product_name: values.product_name,
        registration_type: regType as '新注册' | '再注册' | '变更' | '补充申请',
        project_no: values.project_no?.trim() || null,
        market: values.market ?? null,
        owner: values.owner ?? null,
        planned_submission_date: values.planned_submission_date
          ? (values.planned_submission_date as Dayjs).format('YYYY-MM-DD')
          : null,
      })
      if (result.code !== 200) {
        message.error(result.message || '创建失败')
        return
      }
      message.success('项目已创建，初始状态：草稿')
      setCreateOpen(false)
      createForm.resetFields()
      refreshAll()
    } catch (error) {
      if (error instanceof Error) message.error(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleStageClick = async (stageKey: PreStage) => {
    if (!selected || advancing) return
    if (POST_ACCEPTANCE.has(selected.status)) {
      message.info('项目已受理，阶段与状态由申报进度查询维护，此处只读')
      return
    }
    if (stageKey === 'accepted') {
      message.info('「已受理」阶段由申报进度查询登记受理号后自动同步置达')
      return
    }
    if (stageKey === selected.pre_stage) return
    setAdvancing(true)
    try {
      const result = await advanceProjectStage(selected.id, stageKey)
      if (!result.success) {
        message.error(result.message)
        return
      }
      if (result.data) setSelected(result.data as RegistrationProject)
      message.success('阶段已更新')
      refreshAll()
    } finally {
      setAdvancing(false)
    }
  }

  const handleAddLog = async () => {
    const content = logText.trim()
    if (!selected || !content || logSaving) return
    setLogSaving(true)
    try {
      const result = await addProjectProgressLog(selected.id, content)
      if (!result.success) {
        message.error(result.message)
        return
      }
      message.success('记录已添加')
      setLogText('')
      refreshAll()
    } finally {
      setLogSaving(false)
    }
  }

  // ── 表格列 ──

  const renderStageCell = (p: RegistrationProject) => {
    const currentIdx = Math.max(0, STAGES.findIndex(s => s.key === p.pre_stage))
    const doneCount = currentIdx + 1
    return (
      <div>
        <div className={styles.stageName}>{STAGES[currentIdx].label}</div>
        <div className={styles.prog}>
          <div className={styles.steps}>
            {STAGES.map((s, i) => (
              <span key={s.key} className={i <= currentIdx ? styles.stepDone : styles.step} />
            ))}
          </div>
          <span className={styles.progNum}>{doneCount}/5</span>
        </div>
      </div>
    )
  }

  const renderDeadline = (p: RegistrationProject) => {
    if (POST_ACCEPTANCE.has(p.status)) {
      return (
        <div>
          <div className={styles.dateMain}>—</div>
          <div className={styles.dateSub}>
            <span className={statusTagClass(p.status)}>{STATUS_LABELS[p.status]}</span>
          </div>
        </div>
      )
    }
    if (!p.planned_submission_date) return <div className={styles.dateMain}>—</div>
    const days = dayjs(p.planned_submission_date).diff(dayjs().startOf('day'), 'day')
    const tag =
      days < 0 ? (
        <span className={ui.tagRisk}>逾期 {-days} 天</span>
      ) : days <= 30 ? (
        <span className={ui.tagWarn}>临期 {days} 天</span>
      ) : (
        <span className={ui.tagOk}>正常</span>
      )
    return (
      <div>
        <div className={styles.dateMain}>{p.planned_submission_date}</div>
        <div className={styles.dateSub}>{tag}</div>
      </div>
    )
  }

  const columns: ColumnsType<RegistrationProject> = [
    {
      title: '项目 / 品种',
      key: 'project',
      width: '24%',
      align: 'left',
      render: (_, p) => (
        <div>
          <div className={styles.pName}>{p.name || p.product_name}</div>
          <div className={styles.pMeta}>
            <b>{p.project_no || '—'}</b> · {p.product_name}
          </div>
        </div>
      ),
    },
    {
      title: '类型',
      dataIndex: 'registration_type',
      key: 'registration_type',
      width: '10%',
      align: 'center',
      render: v => (v ? <span className={ui.tagBrand}>{v}</span> : '—'),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: '11%',
      align: 'center',
      render: v => <StatusTag status={v} />,
    },
    {
      title: '申报前阶段',
      key: 'pre_stage',
      width: '18%',
      align: 'center',
      render: (_, p) => renderStageCell(p),
    },
    {
      title: '最新进展',
      key: 'latest_log',
      width: '24%',
      align: 'center',
      render: (_, p) =>
        p.latest_log ? (
          <div>
            <div className={styles.note}>{p.latest_log.content}</div>
            <div className={styles.noteMeta}>
              {dayjs(p.latest_log.created_at).format('YYYY-MM-DD')} ·{' '}
              {p.latest_log.created_by_name || (p.latest_log.log_type === 'system' ? '系统自动' : '—')}
            </div>
          </div>
        ) : (
          <div className={styles.noteEmpty}>暂无进展</div>
        ),
    },
    {
      title: '预计递交',
      key: 'planned_submission_date',
      width: '7%',
      align: 'center',
      render: (_, p) => renderDeadline(p),
    },
    {
      title: '操作',
      key: 'action',
      width: '6%',
      align: 'right',
      render: (_, p) => (
        <span onClick={e => e.stopPropagation()}>
          <button type="button" className={styles.opLink} onClick={() => openDrawer(p)}>
            详情
          </button>
          <Popconfirm title="确定删除该项目？" okText="确定" cancelText="取消" onConfirm={() => handleDelete(p.id)}>
            <button type="button" className={styles.opDel} title="删除">
              {IconTrash}
            </button>
          </Popconfirm>
        </span>
      ),
    },
  ]

  // ── 抽屉派生 ──

  const stageIdx = selected ? Math.max(0, STAGES.findIndex(s => s.key === selected.pre_stage)) : 0
  const locked = !!selected && POST_ACCEPTANCE.has(selected.status)

  return (
    <div className={ui.regUi}>
      <RegistrationPageHeader
        icon={IconGrid}
        title="注册项目"
        sub="申报前阶段的立项、资料准备与进展记录，受理后自动转入申报进度查询"
        actions={
          <>
            <button type="button" className={ui.btn} onClick={refreshAll} disabled={projectsQuery.isFetching}>
              {IconRefresh}
              刷新
            </button>
            <button type="button" className={ui.btnPrimary} onClick={() => setCreateOpen(true)}>
              {IconPlus}
              新建项目
            </button>
          </>
        }
      />

      {/* KPI 卡 */}
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
            <div className={ui.kpiNum}>{card.value ?? '—'}</div>
          </div>
        ))}
      </div>

      {/* 列表面板 */}
      <div className={ui.panel}>
        <div className={ui.toolbar}>
          <div className={ui.toolbarGroup}>
            <Input
              placeholder="搜索项目名称 / 编号 / 品种"
              prefix={<SearchOutlined />}
              value={search}
              onChange={e => {
                setSearch(e.target.value)
                setPage(1)
              }}
              style={{ width: 260 }}
              allowClear
            />
            <Select
              value={typeFilter}
              onChange={v => {
                setTypeFilter(v)
                setPage(1)
              }}
              style={{ width: 130 }}
              options={[{ label: '全部类型', value: '全部' }, ...TYPE_CARDS.map(t => ({ label: t.value, value: t.value }))]}
            />
            <Select
              value={statusFilter}
              onChange={v => {
                setStatusFilter(v)
                setPage(1)
              }}
              style={{ width: 130 }}
              options={[
                { label: '全部状态', value: '全部' },
                ...Object.entries(STATUS_LABELS).map(([value, label]) => ({ label, value })),
              ]}
            />
          </div>
          <div className={styles.toolbarHint}>点击任意行可维护进展</div>
        </div>
        <div className={`${ui.tableWrap} ${styles.tableStd}`}>
          <Table
            dataSource={pagedProjects}
            columns={columns}
            rowKey="id"
            loading={projectsQuery.isPending}
            pagination={false}
            tableLayout="fixed"
            size="middle"
            onRow={record => ({
              onClick: () => openDrawer(record),
              style: { cursor: 'pointer' },
            })}
            locale={{
              emptyText: projectsQuery.isError ? (
                <DataUnavailable compact onRetry={refreshAll} />
              ) : (
                <Empty description="暂无注册项目" />
              ),
            }}
          />
        </div>
        <div className={styles.tableFoot}>
          <span className={styles.totalText}>共 {projects.length} 条</span>
          <Pagination current={safePage} pageSize={PAGE_SIZE} total={projects.length} onChange={setPage} showSizeChanger={false} />
        </div>
      </div>

      {/* 维护抽屉 */}
      <Drawer
        size={580}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelected(null)
        }}
        title={
          selected && (
            <div>
              <div className={styles.drawerName}>
                {selected.name || selected.product_name}
                <span className={ui.tagBrand}>{selected.registration_type}</span>
                <StatusTag status={selected.status} />
              </div>
              <div className={styles.drawerSub}>
                {selected.project_no || '—'} · {selected.product_name} · 负责人 {selected.owner || '—'}
              </div>
            </div>
          )
        }
        styles={{ body: { padding: 0 } }}
      >
        <div className={`${ui.tokenScope} ${styles.drawerBody}`}>
          {selected && (
            <Spin spinning={advancing}>
              {/* 阶段轨 */}
              <div className={styles.secTitle}>
                申报前阶段 <span className={styles.secCnt}>{locked ? '已受理，只读展示' : '点击标记完成'}</span>
              </div>
              <div className={styles.stageRail}>
                {STAGES.map((s, i) => {
                  const done = i < stageIdx || (i === stageIdx && s.key === 'accepted')
                  const cur = i === stageIdx && s.key !== 'accepted'
                  const itemClass = done ? styles.srItemDone : cur ? styles.srItemCur : ''
                  const notClickable = locked || s.key === 'accepted'
                  return (
                    <button
                      key={s.key}
                      type="button"
                      className={`${styles.srItem} ${itemClass} ${notClickable ? styles.srItemLocked : ''}`}
                      onClick={() => void handleStageClick(s.key)}
                      title={s.key === 'accepted' ? '由申报进度查询登记受理号后自动同步置达' : undefined}
                    >
                      <div className={styles.srDot}>{done ? IconCheck : i + 1}</div>
                      <div className={styles.srLabel}>{s.label}</div>
                    </button>
                  )
                })}
              </div>

              {/* 蓝色提示卡 */}
              <div className={styles.linkHint}>
                {IconInfo}
                <div>
                  取得<b>受理号</b>后，审评节点、进度与预计获批在{' '}
                  <Link href="/registration/review">申报进度查询 ›</Link>{' '}
                  维护；状态（已受理、审评中、发补中、已获批…）会自动同步回本页，此处只读展示，不可修改。
                </div>
              </div>

              {/* 基本信息 */}
              <div className={styles.secTitle}>基本信息</div>
              <div className={styles.kvGrid}>
                <div className={styles.kv}>
                  <div className={styles.kvK}>编号</div>
                  <div className={styles.kvV}>{selected.project_no || '—'}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>品种</div>
                  <div className={styles.kvV}>{selected.product_name}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>类型</div>
                  <div className={styles.kvV}>{selected.registration_type || '—'}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>当前状态</div>
                  <div className={styles.kvV}>{STATUS_LABELS[selected.status] ?? selected.status}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>目标市场</div>
                  <div className={styles.kvV}>{selected.market || '—'}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>负责人</div>
                  <div className={styles.kvV}>{selected.owner || '—'}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>预计递交日期</div>
                  <div className={styles.kvV}>{selected.planned_submission_date || '—'}</div>
                </div>
                <div className={styles.kv}>
                  <div className={styles.kvK}>受理号</div>
                  <div className={selected.acceptance_number ? styles.kvV : styles.kvVMuted}>
                    {selected.acceptance_number || '—（受理后自动同步）'}
                  </div>
                </div>
              </div>
              {/* 进展记录 */}
              <div className={styles.secTitle}>
                进展记录 <span className={styles.secCnt}>{logs.length} 条</span>
              </div>
              <div className={styles.logLock}>
                {IconLock}
                全部历史记录留痕保存，不可删除或修改；状态变更由系统自动记录
              </div>
              <Spin spinning={logsQuery.isPending}>
                <div className={styles.logList}>
                  {logs.map((log, idx) => (
                    <div
                      key={log.id}
                      className={`${styles.logItem} ${log.log_type === 'system' ? styles.logItemSys : ''} ${idx === 0 ? styles.logItemFirst : ''}`}
                    >
                      <div className={styles.logDot} />
                      <div className={styles.logBody}>
                        <div className={styles.logText}>
                          {log.log_type === 'system' ? <SystemLogText content={log.content} /> : log.content}
                        </div>
                        <div className={styles.logMeta}>
                          {dayjs(log.created_at).format('YYYY-MM-DD')} ·{' '}
                          {log.created_by_name || (log.log_type === 'system' ? '系统自动' : '—')}
                        </div>
                      </div>
                    </div>
                  ))}
                  {logs.length === 0 && !logsQuery.isPending && <Empty description="暂无进展记录" />}
                </div>
              </Spin>

              {/* 进展输入 */}
              <div className={styles.editor}>
                <textarea
                  placeholder="添加进展说明…（例：3.2.S 已完成初稿，待 QA 审阅）"
                  value={logText}
                  onChange={e => setLogText(e.target.value)}
                />
                <div className={styles.editorBar}>
                  <span className={styles.editorTip}>记录后自动写入时间与当前登录人</span>
                  <button type="button" className={styles.btnSm} onClick={() => setLogText('')}>
                    取消
                  </button>
                  <button
                    type="button"
                    className={styles.btnSmPrimary}
                    disabled={!logText.trim() || logSaving}
                    onClick={() => void handleAddLog()}
                  >
                    添加记录
                  </button>
                </div>
              </div>
            </Spin>
          )}
        </div>
      </Drawer>

      {/* 新建项目弹窗 */}
      <Modal
        width={660}
        open={createOpen}
        onCancel={() => {
          setCreateOpen(false)
          createForm.resetFields()
        }}
        onOk={() => void handleCreate()}
        okText="创建项目"
        cancelText="取消"
        confirmLoading={submitting}
        title={
          <div>
            <div style={{ fontSize: 20, fontWeight: 600 }}>新建注册项目</div>
            <div className={styles.modalSub}>先选类型，表单字段会随类型自动调整</div>
          </div>
        }
        className={styles.modalRoot}
      >
        <div className={ui.tokenScope}>
          <Form form={createForm} layout="vertical" initialValues={{ market: '国内' }}>
            <Form.Item label="项目类型" required style={{ marginBottom: 18 }}>
              <div className={styles.typeGrid}>
                {TYPE_CARDS.map(t => (
                  <button
                    key={t.value}
                    type="button"
                    className={regType === t.value ? styles.typeCardSel : styles.typeCard}
                    onClick={() => setRegType(t.value)}
                  >
                    <div className={styles.tcTop}>
                      <div className={styles.tcIco}>{t.icon}</div>
                      <div className={styles.tcName}>{t.value}</div>
                    </div>
                    <div className={styles.tcDesc}>{t.desc}</div>
                  </button>
                ))}
              </div>
              <div className={styles.fieldHelp}>注册类型只支持以上 4 种；项目创建后初始状态为「草稿」</div>
            </Form.Item>

            <Form.Item
              name="name"
              label="项目名称"
              rules={[{ required: true, message: '请输入项目名称' }]}
              extra={<div className={styles.fieldHelp}>建议格式：品种名 + 类型 + 动作</div>}
            >
              <Input placeholder="例：恩替卡韦 US DMF 立项" />
            </Form.Item>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <Form.Item
                name="product_name"
                label="品种"
                rules={[{ required: true, message: '请输入品种名称' }]}
              >
                <Input placeholder="例：恩替卡韦" />
              </Form.Item>
              <Form.Item name="project_no" label="项目编号">
                <Input placeholder="留空则自动生成" />
              </Form.Item>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <Form.Item name="market" label="目标市场">
                <Select
                  options={['美国', '欧盟', '国内', 'WHO', '其他'].map(v => ({ label: v, value: v }))}
                />
              </Form.Item>
              <Form.Item name="owner" label="负责人" rules={[{ required: true, message: '请选择负责人' }]}>
                <Select
                  showSearch
                  placeholder="选择负责人"
                  optionFilterProp="label"
                  options={(personnelQuery.data?.items ?? []).map(p => ({ label: p.name, value: p.name }))}
                />
              </Form.Item>
            </div>

            <Form.Item
              name="planned_submission_date"
              label="预计递交日期"
              extra={<div className={styles.fieldHelp}>用于临期提醒，可在项目详情中随时调整</div>}
            >
              <DatePicker style={{ width: '100%' }} placeholder="选择日期" />
            </Form.Item>
          </Form>
        </div>
      </Modal>
    </div>
  )
}
