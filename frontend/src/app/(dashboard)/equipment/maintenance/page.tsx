
import { MaintenancePage } from '@/components/equipment'
import {
  fetchEquipments, fetchWorkOrders, fetchWorkOrderStatistics, fetchFailureCodes,
  fetchCalibrationPlans, fetchCalibrationRecords,
  fetchMaintenancePlans,
} from '@/actions/equipment'
import {

  Equipment, FailureCode, WorkOrder, WorkOrderStatistics, CalibrationPlan, CalibrationRecord,
  MaintenancePlan,
} from '@/types/equipment'

export const dynamic = 'force-dynamic'

const defaultStatistics: WorkOrderStatistics = {
  total: 0,
  by_status: {} as any,
  by_type: {} as any,
  by_priority: {} as any,
}

export default async function MaintenancePageWrapper() {
  let equipments: Equipment[] = []
  let workOrders: WorkOrder[] = []
  let workOrderTotal = 0
  let workOrderStatistics = defaultStatistics
  let failureCodes: Record<'symptoms' | 'causes' | 'actions', FailureCode[]> = {
    symptoms: [],
    causes: [],
    actions: [],
  }
  let calibrationPlans: CalibrationPlan[] = []
  let calibrationPlanTotal = 0
  let calibrationRecords: CalibrationRecord[] = []
  let calibrationRecordTotal = 0
  let maintenancePlans: MaintenancePlan[] = []
  let maintenancePlanTotal = 0

  try {
    const result = await Promise.all([
      fetchEquipments({ page: 1, page_size: 200 }),
      fetchWorkOrders({ page: 1, page_size: 20 }),
      fetchWorkOrderStatistics(),
      fetchFailureCodes('symptoms'),
      fetchFailureCodes('causes'),
      fetchFailureCodes('actions'),
      fetchCalibrationPlans({ page: 1, page_size: 20 }),
      fetchCalibrationRecords({ page: 1, page_size: 20 }),
      fetchMaintenancePlans({ page: 1, page_size: 20 }),
    ])

    equipments = Array.isArray(result[0]?.data) ? result[0].data : (result[0]?.data?.items ?? result[0]?.items ?? [])
    workOrders = result[1]?.data?.items ?? result[1]?.items ?? (Array.isArray(result[1]?.data) ? result[1].data : [])
    workOrderTotal = result[1]?.data?.total ?? result[1]?.total ?? workOrders.length
    workOrderStatistics = result[2]?.data ?? result[2]
    failureCodes = {
      symptoms: result[3]?.data ?? result[3] ?? [],
      causes: result[4]?.data ?? result[4] ?? [],
      actions: result[5]?.data ?? result[5] ?? [],
    }
    calibrationPlans = result[6]?.data?.items ?? result[6]?.items ?? (Array.isArray(result[6]?.data) ? result[6].data : [])
    calibrationPlanTotal = result[6]?.data?.total ?? result[6]?.total ?? calibrationPlans.length
    calibrationRecords = result[7]?.data?.items ?? result[7]?.items ?? (Array.isArray(result[7]?.data) ? result[7].data : [])
    calibrationRecordTotal = result[7]?.data?.total ?? result[7]?.total ?? calibrationRecords.length
    maintenancePlans = result[8]?.data?.items ?? result[8]?.items ?? (Array.isArray(result[8]?.data) ? result[8].data : [])
    maintenancePlanTotal = result[8]?.data?.total ?? result[8]?.total ?? maintenancePlans.length
  } catch (error) {
    console.warn('维护模块数据加载失败，使用空数据:', error)
  }

  return (
    <MaintenancePage
      initialEquipments={equipments}
      initialWorkOrders={workOrders}
      initialWorkOrderTotal={workOrderTotal}
      initialWorkOrderStatistics={workOrderStatistics}
      initialFailureCodes={failureCodes}
      initialCalibrationPlans={calibrationPlans}
      initialCalibrationPlanTotal={calibrationPlanTotal}
      initialCalibrationRecords={calibrationRecords}
      initialCalibrationRecordTotal={calibrationRecordTotal}
      initialMaintenancePlans={maintenancePlans}
      initialMaintenancePlanTotal={maintenancePlanTotal}
    />
  )
}
