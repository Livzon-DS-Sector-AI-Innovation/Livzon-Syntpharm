import { EquipmentPage } from './EquipmentPage'
import { fetchCategoryTree, fetchLocationTree, fetchEquipments, fetchEquipmentStatistics, fetchDepartments } from '@/lib/api/server/equipment'
import { parseEquipmentUrlRecord, toEquipmentListQuery, toEquipmentStatsQuery } from '@/lib/api/equipment-query'
import type { DepartmentOption } from '@/types/equipment/generated-bridge'
import { EquipmentCategory, Location, Equipment, EquipmentStatistics } from '@/types/equipment/generated-bridge'
import { unwrapResponse } from '@/lib/api/server/base'

// 强制动态渲染：不在构建时预渲染，每次请求都实时从后端获取数据
export const dynamic = 'force-dynamic'

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}

export default async function EquipmentPageWrapper({ searchParams }: PageProps) {
  let categories: EquipmentCategory[] = []
  let locations: Location[] = []
  let equipments: Equipment[] = []
  let total = 0
  // null = 首屏统计取数失败，客户端不喂 initialData，直接按当前筛选重新请求
  let statistics: EquipmentStatistics | null = null
  let departments: DepartmentOption[] = []

  // 服务端首屏按 URL 的完整查询状态（筛选 + 排序 + 分页）取数，
  // 与客户端 hydration 后的 queryKey 同源，否则首屏数据会被二次请求覆盖并产生闪变
  const { state: urlState } = parseEquipmentUrlRecord(await searchParams)
  const listQuery = toEquipmentListQuery(urlState)
  const statsQuery = toEquipmentStatsQuery(urlState)

  // 每个 API 独立 try/catch，避免一个失败拖垮全部数据
  try {
    categories = await fetchCategoryTree()
  } catch (error) {
    console.warn('加载分类树失败:', error)
  }
  try {
    locations = await fetchLocationTree()
  } catch (error) {
    console.warn('加载位置树失败:', error)
  }
  try {
    const result = await fetchEquipments(listQuery)
    const data = unwrapResponse(result)
    equipments = Array.isArray(data) ? data : ((data as Record<string, unknown>)?.items as Equipment[]) ?? []
    total = (data as Record<string, unknown>)?.total as number ?? equipments.length
  } catch (error) {
    console.warn('加载设备列表失败:', error)
  }
  try {
    const statsResult = await fetchEquipmentStatistics(statsQuery)
    statistics = unwrapResponse<EquipmentStatistics>(statsResult)
  } catch (error) {
    console.warn('加载设备统计失败:', error)
  }
  try {
    departments = await fetchDepartments()
  } catch (error) {
    console.warn('加载部门列表失败:', error)
  }

  return (
    <EquipmentPage
      initialCategories={categories}
      initialLocations={locations}
      initialEquipments={equipments}
      initialTotal={total}
      initialStatistics={statistics}
      initialDepartments={departments}
    />
  )
}
