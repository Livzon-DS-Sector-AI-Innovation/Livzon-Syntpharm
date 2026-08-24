import { EquipmentPage } from '@/components/equipment'
import { fetchCategoryTree, fetchLocationTree, fetchEquipments, fetchEquipmentStatistics, fetchDepartments } from '@/actions/equipment'
import type { DepartmentOption } from '@/types/equipment/generated-bridge'
import { EquipmentCategory, Location, Equipment, EquipmentStatistics } from '@/types/equipment/generated-bridge'
import { unwrapResponse } from '@/lib/api/server/base'

// 强制动态渲染：不在构建时预渲染，每次请求都实时从后端获取数据
export const dynamic = 'force-dynamic'

// 默认空数据
const defaultStatistics: EquipmentStatistics = {
  total: 0,
  by_status: {
    '在用': 0,
    '备用': 0,
    '维修中': 0,
    '停用': 0,
    '报废': 0,
  },
  by_category: {},
  by_location: {},
}

export default async function EquipmentPageWrapper() {
  let categories: EquipmentCategory[] = []
  let locations: Location[] = []
  let equipments: Equipment[] = []
  let total = 0
  let statistics = defaultStatistics
  let departments: DepartmentOption[] = []

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
    const result = await fetchEquipments({ page: 1, page_size: 20 })
    const data = unwrapResponse(result)
    equipments = Array.isArray(data) ? data : ((data as Record<string, unknown>)?.items as Equipment[]) ?? []
    total = (data as Record<string, unknown>)?.total as number ?? equipments.length
  } catch (error) {
    console.warn('加载设备列表失败:', error)
  }
  try {
    const statsResult = await fetchEquipmentStatistics()
    statistics = unwrapResponse<EquipmentStatistics>(statsResult) ?? defaultStatistics
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
