import { SupplierManagementClient } from '@/components/procurement'
import { fetchSuppliers } from '@/lib/api/server/procurement'

export const dynamic = 'force-dynamic'

const DEFAULT_PAGE_SIZE = 20

function getColumnsFromData(data: unknown) {
  // `columns` moved from meta to data: it is column metadata, not pagination.
  const columns = (data as { columns?: unknown } | null | undefined)?.columns
  if (!Array.isArray(columns)) return []
  return columns.filter((column): column is string => typeof column === 'string')
}

export default async function SupplierManagementPage() {
  let initialLoadFailed = false
  let response
  try {
    response = await fetchSuppliers({
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
    })
  } catch {
    initialLoadFailed = true
    response = {
      code: 200,
      message: 'success',
      data: [],
      meta: {
        page: 1,
        page_size: DEFAULT_PAGE_SIZE,
        total: 0,
        columns: [],
      },
    }
  }

  const initialTotal = Number(response.meta?.total ?? response.data.length)

  return (
    <SupplierManagementClient
      initialRecords={response.data}
      initialTotal={Number.isFinite(initialTotal) ? initialTotal : response.data.length}
      initialColumns={getColumnsFromData(response.data)}
      initialLoadFailed={initialLoadFailed}
    />
  )
}
