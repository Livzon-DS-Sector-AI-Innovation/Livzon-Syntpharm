
import { StatsDashboard } from '@/components/equipment'
import {
  fetchEquipmentStatistics,
  fetchWorkOrderStatistics,
  fetchStockWarnings,
  fetchOverdueMaintenancePlans,
  fetchCalibrationPlans,
  fetchWorkOrders,
} from '@/actions/equipment'
import type {

  EquipmentStatus,
  WorkOrderStatus,
  WorkOrderPriority,
  WorkOrderType,
  EquipmentStatistics,
  WorkOrderStatistics,
  StockWarning,
  MaintenancePlan,
  CalibrationPlan,
  WorkOrder,
} from '@/types/equipment'
import { unwrapResponse } from '@/lib/api/server/base'

export const dynamic = 'force-dynamic'

// 默认空数据
const defaultEquipmentStats: EquipmentStatistics = {
  total: 0,
  by_status: { '在用': 0, '备用': 0, '维修中': 0, '停用': 0, '报废': 0 } as Record<EquipmentStatus, number>,
  by_category: {} as Record<string, number>,
  by_location: {} as Record<string, number>,
}

const defaultWorkOrderStats: WorkOrderStatistics = {
  total: 0,
  by_status: { '待处理': 0, '执行中': 0, '待验收': 0, '已完成': 0, '已关闭': 0 } as Record<WorkOrderStatus, number>,
  by_type: { '故障维修': 0, '计划维护': 0, '巡检': 0, '校准': 0, '异常处理': 0, '日常维护': 0 } as Record<WorkOrderType, number>,
  by_priority: { '紧急': 0, '高': 0, '中': 0, '低': 0 } as Record<WorkOrderPriority, number>,
}

export default async function StatsPage() {
  let equipmentStats: EquipmentStatistics = defaultEquipmentStats
  let workOrderStats: WorkOrderStatistics = defaultWorkOrderStats
  let stockWarnings: StockWarning[] = []
  let overduePlans: MaintenancePlan[] = []
  let calibrationPlans: CalibrationPlan[] = []
  let recentWorkOrders: WorkOrder[] = []

  try {
    const results = await Promise.allSettled([
      fetchEquipmentStatistics(),
      fetchWorkOrderStatistics(),
      fetchStockWarnings(),
      fetchOverdueMaintenancePlans(),
      fetchCalibrationPlans({ status: '启用', page_size: 100 }),
      fetchWorkOrders({ page: 1, page_size: 10 }),
    ])

    // 依次解构，每个接口错误不影响其他
    const [eqResult, woResult, swResult, overdueResult, calResult, ordersResult] = results

    if (eqResult.status === 'fulfilled') {
      equipmentStats = unwrapResponse<EquipmentStatistics>(eqResult.value) ?? defaultEquipmentStats
    } else {
      console.warn('设备统计加载失败:', eqResult.reason)
    }

    if (woResult.status === 'fulfilled') {
      workOrderStats = unwrapResponse<WorkOrderStatistics>(woResult.value) ?? defaultWorkOrderStats
    } else {
      console.warn('工单统计加载失败:', woResult.reason)
    }

    if (swResult.status === 'fulfilled') {
      const data = unwrapResponse(swResult.value)
      stockWarnings = Array.isArray(data) ? data : []
    } else {
      console.warn('库存预警加载失败:', swResult.reason)
    }

    if (overdueResult.status === 'fulfilled') {
      const data = unwrapResponse(overdueResult.value)
      overduePlans = Array.isArray(data) ? data : []
    } else {
      console.warn('逾期维护计划加载失败:', overdueResult.reason)
    }

    if (calResult.status === 'fulfilled') {
      const data = unwrapResponse(calResult.value) as Record<string, unknown>
      calibrationPlans = Array.isArray(data?.items) ? data.items as CalibrationPlan[] : (Array.isArray(data) ? data as CalibrationPlan[] : [])
    } else {
      console.warn('校准计划加载失败:', calResult.reason)
    }

    if (ordersResult.status === 'fulfilled') {
      const data = unwrapResponse(ordersResult.value) as Record<string, unknown>
      recentWorkOrders = Array.isArray(data?.items) ? data.items as WorkOrder[] : (Array.isArray(data) ? data as WorkOrder[] : [])
    } else {
      console.warn('近期工单加载失败:', ordersResult.reason)
    }
  } catch (error) {
    console.warn('设备仪表盘数据加载异常:', error)
  }

  return (
    <>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">设备仪表盘</h1>
      <StatsDashboard
      initialData={{
        equipmentStats,
        workOrderStats,
        stockWarnings,
        overduePlans,
        calibrationPlans,
        recentWorkOrders,
      }}
      />
    </>
  )
}
