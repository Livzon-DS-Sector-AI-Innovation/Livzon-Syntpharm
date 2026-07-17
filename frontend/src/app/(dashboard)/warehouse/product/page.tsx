import { redirect } from 'next/navigation'

import { FeishuDomainMonitorClient } from '@/components/warehouse'
import {
  fetchWarehouseFeishuDomainRecords,
  fetchWarehouseFeishuTablesByParams,
} from '@/lib/api/server/warehouse'
import type { WarehouseFeishuRawRecordData, WarehouseFeishuTable } from '@/types/warehouse'

export const dynamic = 'force-dynamic'

interface PageProps {
  searchParams: Promise<{
    table_id?: string
    keyword?: string
    field?: string
    field_operator?: string
    field_value?: string
    page?: string
    page_size?: string
  }>
}

function toNumber(value: string | undefined, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

export default async function ProductPage({ searchParams }: PageProps) {
  const params = await searchParams
  const page = toNumber(params.page, 1)
  const pageSize = toNumber(params.page_size, 50)
  let data: WarehouseFeishuRawRecordData | null = null
  let tables: WarehouseFeishuTable[] = []
  let loadError: string | null = null

  try {
    tables = await fetchWarehouseFeishuTablesByParams({
      business_domain: 'hardware',
      enabled: true,
    })
  } catch (error) {
    loadError = error instanceof Error ? error.message : '五金飞书数据加载失败'
    console.warn('五金飞书表目录加载失败:', error)
  }

  if (!loadError && !params.table_id && tables[0]?.id) {
    redirect(`/warehouse/product?table_id=${tables[0].id}`)
  }

  if (!loadError) {
    try {
      data = await fetchWarehouseFeishuDomainRecords('hardware', {
        table_id: params.table_id,
        keyword: params.keyword,
        field: params.field,
        field_operator: params.field_operator,
        field_value: params.field_value,
        page,
        page_size: pageSize,
      })
    } catch (error) {
      loadError = error instanceof Error ? error.message : '五金飞书数据加载失败'
      console.warn('五金飞书数据加载失败:', error)
    }
  }

  return (
    <FeishuDomainMonitorClient
      key={[
        params.table_id,
        params.keyword,
        params.field,
        params.field_operator,
        params.field_value,
      ].join(':')}
      businessDomain="hardware"
      title="五金"
      description="展示五金多维表格中已启用数据表的本地同步快照"
      tables={tables}
      data={data}
      error={loadError}
      selectedTableId={params.table_id}
      keyword={params.keyword}
      field={params.field}
      fieldOperator={params.field_operator}
      fieldValue={params.field_value}
      page={page}
      pageSize={pageSize}
    />
  )
}
