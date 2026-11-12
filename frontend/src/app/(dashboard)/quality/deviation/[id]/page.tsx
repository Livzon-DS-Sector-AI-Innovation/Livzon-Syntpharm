import type { Metadata } from 'next'
import Link from 'next/link'
import { DEVIATION_LEDGER_PATH } from '@/components/quality/deviation/constants'
import { DeviationDetailPage } from '@/components/quality/deviation'
import {
  getDeviationDepartmentContactOptions,
  getDeviationLedgerDetail,
} from '@/lib/api/server/quality'
import type { DeviationLedgerOption } from '@/types/quality'

// 详情随流转状态变化，禁用静态预渲染
export const dynamic = 'force-dynamic'

export const metadata: Metadata = { title: '偏差详情' }

interface PageProps {
  params: Promise<{ id: string }>
}

export default async function DeviationDetailRoute({ params }: PageProps) {
  const { id } = await params

  // 详情为主，候选数据独立降级：候选失败不影响查看与审核
  const [detailResult, departmentResult] = await Promise.allSettled([
    getDeviationLedgerDetail(id),
    getDeviationDepartmentContactOptions(),
  ])

  if (detailResult.status === 'rejected') {
    const reason =
      detailResult.reason instanceof Error ? detailResult.reason.message : '未知错误，请稍后重试'
    console.error('偏差详情加载失败', detailResult.reason)
    return (
      <div className="flex flex-col gap-4">
        <div className="rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-8 text-center shadow-sm">
          <h1 className="text-[16px] font-semibold text-[var(--color-ink)]">偏差详情加载失败</h1>
          <p className="mt-2 text-[13px] text-[var(--color-slate)]">{reason}</p>
          <Link className="mt-4 inline-block text-[13px] text-[var(--color-primary)]" href={DEVIATION_LEDGER_PATH}>
            返回偏差台账
          </Link>
        </div>
      </div>
    )
  }

  // 部门候选同源于部门联系人配置；本单已填的部门即便未配置也要保留，避免编辑时丢值
  const configuredDepartments =
    departmentResult.status === 'fulfilled' ? departmentResult.value : []
  const currentDepartments = [
    detailResult.value.department,
    ...(detailResult.value.cross_dept_reviewers ?? []).map((reviewer) => reviewer.department),
  ].filter((name): name is string => Boolean(name && name.trim()))
  const departmentOptions: DeviationLedgerOption[] = [
    ...new Map(
      [...configuredDepartments, ...currentDepartments.map((name) => ({ value: name, label: name }))].map(
        (item) => [item.value, item],
      ),
    ).values(),
  ].sort((a, b) => a.label.localeCompare(b.label, 'zh-Hans-CN'))
  if (departmentResult.status === 'rejected') {
    console.error('偏差部门候选加载失败', departmentResult.reason)
  }

  return (
    <DeviationDetailPage
      initialLedger={detailResult.value}
      departmentOptions={departmentOptions}
      optionsError={departmentResult.status === 'rejected'}
    />
  )
}