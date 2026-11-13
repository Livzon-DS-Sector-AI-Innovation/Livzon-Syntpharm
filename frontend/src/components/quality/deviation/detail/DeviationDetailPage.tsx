'use client'

import { useCallback, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Alert, App, Breadcrumb, Button, FloatButton, Popconfirm } from 'antd'
import { ArrowLeftOutlined, DeleteOutlined, ReloadOutlined, VerticalAlignTopOutlined } from '@ant-design/icons'
import { deleteDeviationLedger } from '@/actions/quality'
import type {
  DeviationInvestigationPrefill,
  DeviationLedgerDetail,
  DeviationLedgerOption,
} from '@/types/quality'
import { DEVIATION_LEDGER_PATH } from '../constants'
import { DetailSummaryBar } from './DetailSummaryBar'
import { DetailSectionNav } from './DetailSectionNav'
import { getScrollElement, useActiveSection } from './detailScroll'
import { SCROLLSPY_SECTION_KEYS } from './detailSections'
import { FlowPanel } from './FlowPanel'
import { BasicInfoCard } from './BasicInfoCard'
import { AiAnalysisCard } from './AiAnalysisCard'
import { InvestigationCard, type InvestigationCardHandle } from './InvestigationCard'
import { CrossDeptReviewCard } from './CrossDeptReviewCard'
import { ReviewCard } from './ReviewCard'
import { FinalCodeCard } from './FinalCodeCard'
import { ReviewTimelineCard } from './ReviewTimelineCard'

interface DeviationDetailPageProps {
  initialLedger: DeviationLedgerDetail
  departmentOptions: DeviationLedgerOption[]
  /** 部门候选取失败时提示，不影响详情查看 */
  optionsError?: boolean
}

/**
 * 偏差详情整页：摘要条 → 分区导航 → 左栏（2/3）环节板块 + 右栏（1/3）审核流程。
 * 窄屏自动退化为单列，流程区跟在主体之后；右下角提供回到顶部。
 */
export function DeviationDetailPage({
  initialLedger,
  departmentOptions,
  optionsError = false,
}: DeviationDetailPageProps) {
  const router = useRouter()
  const { message } = App.useApp()
  // 页面根节点：用于定位真正的滚动容器（AppShell 的 <main>）
  const pageRef = useRef<HTMLDivElement>(null)
  const [ledger, setLedger] = useState(initialLedger)
  const [deleting, setDeleting] = useState(false)
  // AI 分析 → 调查表单的一次性填充载荷：由 AI 卡片写入、调查卡片消费后清空
  const [investigationPrefill, setInvestigationPrefill] = useState<DeviationInvestigationPrefill | null>(null)
  // 调查卡片的命令式入口：AI 卡片发出「一键填写」时展开表单（依赖稳定化，避免子组件重复渲染）
  const investigationCardRef = useRef<InvestigationCardHandle>(null)

  const handleFillInvestigation = useCallback((prefill: DeviationInvestigationPrefill) => {
    // 先下发载荷再展开表单：同一批渲染里表单挂载即可按 nonce 消费
    setInvestigationPrefill(prefill)
    investigationCardRef.current?.openSubmitForm()
  }, [])

  const handlePrefillApplied = useCallback(
    (filled: number) => {
      setInvestigationPrefill(null)
      if (filled > 0) {
        message.success(`已把 AI 分析带入 ${filled} 项空白内容，请核对后提交`)
      } else {
        message.info('调查表单已有内容，AI 分析未覆盖任何字段')
      }
    },
    [message],
  )
  // 当前滚动到的板块：驱动分区导航高亮
  const activeSection = useActiveSection(pageRef, SCROLLSPY_SECTION_KEYS)

  const handleDelete = async () => {
    setDeleting(true)
    const result = await deleteDeviationLedger(ledger.id)
    setDeleting(false)
    if (result.code === 200) {
      message.success('偏差已删除')
      router.push(DEVIATION_LEDGER_PATH)
      router.refresh()
    } else {
      message.error(result.message)
    }
  }

  return (
    <div ref={pageRef} className="flex flex-col gap-4">
      <Breadcrumb
        items={[
          { title: <Link href="/quality">质量管理</Link> },
          { title: <Link href="/quality/deviation">偏差管理</Link> },
          { title: <Link href={DEVIATION_LEDGER_PATH}>偏差台账</Link> },
          { title: '偏差详情' },
        ]}
      />
      {/* 顶部只放页面级操作：编号与标题统一由下方摘要条承载，避免同一信息在一屏内出现两次 */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Link href={DEVIATION_LEDGER_PATH}>
          <Button icon={<ArrowLeftOutlined />}>返回台账</Button>
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <Popconfirm
            title="删除该偏差？"
            description="删除后不再出现在台账中（软删除，数据仍可追溯）。"
            okText="删除"
            okButtonProps={{ danger: true }}
            cancelText="取消"
            onConfirm={handleDelete}
          >
            <Button danger icon={<DeleteOutlined />} loading={deleting}>
              删除
            </Button>
          </Popconfirm>
          <Button icon={<ReloadOutlined />} onClick={() => router.refresh()}>
            刷新
          </Button>
        </div>
      </div>

      <DetailSummaryBar ledger={ledger} />

      <DetailSectionNav ledger={ledger} activeId={activeSection} />

      {optionsError && (
        <Alert
          type="warning"
          showIcon
          title="部门候选加载失败"
          description="详情仍可查看；如需编辑基础信息或切换部门，请刷新页面重试。调查人下拉改为展开时远端加载，不受影响。"
        />
      )}

      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-3">
        <div className="flex min-w-0 flex-col gap-4 lg:col-span-2">
          <BasicInfoCard ledger={ledger} departmentOptions={departmentOptions} onUpdated={setLedger} />
          <AiAnalysisCard
            ledger={ledger}
            onUpdated={setLedger}
            onFillInvestigation={handleFillInvestigation}
          />
          <InvestigationCard
            ref={investigationCardRef}
            ledger={ledger}
            onUpdated={setLedger}
            prefill={investigationPrefill}
            onPrefillApplied={handlePrefillApplied}
          />
          <CrossDeptReviewCard ledger={ledger} onUpdated={setLedger} />
          <ReviewCard ledger={ledger} onUpdated={setLedger} />
          <FinalCodeCard ledger={ledger} onUpdated={setLedger} />
          <ReviewTimelineCard opinions={ledger.review_opinions ?? []} />
        </div>

        <aside className="min-w-0 lg:col-span-1">
          <div className="flex flex-col gap-4">
            <FlowPanel ledger={ledger} />
          </div>
        </aside>
      </div>

      <FloatButton.BackTop
        type="primary"
        icon={<VerticalAlignTopOutlined />}
        tooltip="回到顶部"
        aria-label="回到顶部"
        visibilityHeight={280}
        duration={420}
        target={() => getScrollElement(pageRef.current)}
        style={{ right: 24, bottom: 24 }}
      />
    </div>
  )
}