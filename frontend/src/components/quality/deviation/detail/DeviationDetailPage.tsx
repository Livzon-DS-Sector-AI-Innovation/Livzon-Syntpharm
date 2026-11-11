'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Alert, Breadcrumb, Button } from 'antd'
import { ArrowLeftOutlined, ReloadOutlined } from '@ant-design/icons'
import type { DeviationLedgerDetail, DeviationLedgerOption } from '@/types/quality'
import { DEVIATION_LEDGER_PATH } from '../constants'
import { DetailSummaryBar } from './DetailSummaryBar'
import { FlowPanel } from './FlowPanel'
import { BasicInfoCard } from './BasicInfoCard'
import { AiAnalysisCard } from './AiAnalysisCard'
import { InvestigationCard } from './InvestigationCard'
import { ReportCard } from './ReportCard'
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
 * 偏差详情整页：左栏（16/24）承载各环节操作卡，右栏（8/24）粘性流程区。
 * 窄屏自动退化为单列，流程区跟在主体之后。
 */
export function DeviationDetailPage({
  initialLedger,
  departmentOptions,
  optionsError = false,
}: DeviationDetailPageProps) {
  const router = useRouter()
  const [ledger, setLedger] = useState(initialLedger)

  return (
    <div className="flex flex-col gap-4">
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
        <Button icon={<ReloadOutlined />} onClick={() => router.refresh()}>
          刷新
        </Button>
      </div>

      <DetailSummaryBar ledger={ledger} />

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
          <AiAnalysisCard ledger={ledger} onUpdated={setLedger} />
          <InvestigationCard ledger={ledger} onUpdated={setLedger} />
          <ReportCard ledger={ledger} onUpdated={setLedger} />
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
    </div>
  )
}