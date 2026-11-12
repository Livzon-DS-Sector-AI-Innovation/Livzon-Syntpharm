import type { Metadata } from 'next'
import { DeviationLedgerTable } from '@/components/quality/deviation'
import {
  getDeviationDepartmentOptions,
  getDeviationLedger,
  getDeviationStatusOptions,
} from '@/lib/api/server/quality'
import type {
  DeviationLedgerFilters,
  DeviationLedgerListResult,
  DeviationLedgerOption,
} from '@/types/quality'

// 台账随数据变化，禁用静态预渲染
export const dynamic = 'force-dynamic'

export const metadata: Metadata = { title: '偏差台账' }

const DEFAULT_PAGE_SIZE = 20
const MAX_PAGE_SIZE = 100

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

function pickString(value: string | string[] | undefined): string | undefined {
  const raw = Array.isArray(value) ? value[0] : value
  const trimmed = raw?.trim()
  return trimmed ? trimmed : undefined
}

function pickPositiveInt(value: string | undefined, fallback: number, max?: number): number {
  const parsed = Number.parseInt(value ?? '', 10)
  if (!Number.isFinite(parsed) || parsed < 1) return fallback
  return max ? Math.min(parsed, max) : parsed
}

export default async function DeviationLedgerPage({ searchParams }: PageProps) {
  const params = await searchParams
  const filters: DeviationLedgerFilters = {
    reason_category: pickString(params.reason_category),
    status: pickString(params.status),
    department: pickString(params.department),
  }
  const page = pickPositiveInt(pickString(params.page), 1)
  const pageSize = pickPositiveInt(pickString(params.page_size), DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE)

  // 三个请求互不依赖，并行取；任一失败只降级该块，不整页 500
  const [listResult, departmentResult, statusResult] = await Promise.allSettled([
    getDeviationLedger({ ...filters, page, page_size: pageSize }),
    getDeviationDepartmentOptions(),
    getDeviationStatusOptions(),
  ])

  let list: DeviationLedgerListResult | null = null
  let loadError: string | null = null
  if (listResult.status === 'fulfilled') {
    list = listResult.value
  } else {
    console.error('偏差台账列表加载失败', listResult.reason)
    loadError = listResult.reason instanceof Error ? listResult.reason.message : '未知错误'
  }

  const departmentOptions: DeviationLedgerOption[] =
    departmentResult.status === 'fulfilled' ? departmentResult.value : []
  const statusOptions: DeviationLedgerOption[] =
    statusResult.status === 'fulfilled' ? statusResult.value : []

  return (
    <DeviationLedgerTable
      items={list?.items ?? []}
      total={list?.total ?? 0}
      page={list?.page ?? page}
      pageSize={list?.page_size ?? pageSize}
      filters={filters}
      departmentOptions={departmentOptions}
      statusOptions={statusOptions}
      loadError={loadError}
    />
  )
}