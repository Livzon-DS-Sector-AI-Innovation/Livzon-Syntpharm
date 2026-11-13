'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Alert, App, Breadcrumb, Button, Popconfirm } from 'antd'
import { ArrowLeftOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { deleteDeviationLedger } from '@/actions/quality'
import type { DeviationLedgerDetail, DeviationLedgerOption } from '@/types/quality'
import { DEVIATION_LEDGER_PATH } from '../constants'
import { DetailSummaryBar } from './DetailSummaryBar'
import { FlowPanel } from './FlowPanel'
import { BasicInfoCard } from './BasicInfoCard'
import { AiAnalysisCard } from './AiAnalysisCard'
import { InvestigationCard } from './InvestigationCard'
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
 * 偏差详情整页：左栏（16/24）承载各环节操作卡，右栏（8/24）粘性流程区。
 * 窄屏自动退化为单列，流程区跟在主体之后。
 */
export function DeviationDetailPage({
  initialLedger,
  departmentOptions,
  optionsError = false,
}: DeviationDetailPageProps) {
  const router = useRouter()
  const { message } = App.useApp()
  const [ledger, setLedger] = useState(initialLedger)
  const [deleting, setDeleting] = useState(false)

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
    </div>
  )
}