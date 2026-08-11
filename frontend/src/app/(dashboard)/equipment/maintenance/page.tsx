
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
import { unwrapResponse } from '@/lib/api/server/base'

export const dynamic = 'force-dynamic'

function extractArray<T>(data: unknown): T[] {
  if (Array.isArray(data)) return data as T[]
  const d = data as Record<string, unknown>
  return Array.isArray(d?.items) ? (d.items as T[]) : []
}

function extractTotal(data: unknown, fallback: number): number {
  if (typeof data === 'object' && data !== null) {
    return (data as Record<string, unknown>)?.total as number ?? fallback
  }
  return fallback
}

const defaultStatistics: WorkOrderStatistics = {
  total: 0,
  by_status: {} as Record<string, number>,
  by_type: {} as Record<string, number>,
  by_priority: {} as Record<string, number>,
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

    const [e0, e1, e2, e3, e4, e5, e6, e7, e8] = result.map(r => unwrapResponse(r))

    equipments = extractArray<Equipment>(e0)
    workOrders = extractArray<WorkOrder>(e1)
    workOrderTotal = extractTotal(e1, workOrders.length)
    workOrderStatistics = (e2 as WorkOrderStatistics) ?? defaultStatistics
    failureCodes = {
      symptoms: (Array.isArray(e3) ? e3 : []) as FailureCode[],
      causes: (Array.isArray(e4) ? e4 : []) as FailureCode[],
      actions: (Array.isArray(e5) ? e5 : []) as FailureCode[],
    }
    calibrationPlans = extractArray<CalibrationPlan>(e6)
    calibrationPlanTotal = extractTotal(e6, calibrationPlans.length)
    calibrationRecords = extractArray<CalibrationRecord>(e7)
    calibrationRecordTotal = extractTotal(e7, calibrationRecords.length)
    maintenancePlans = extractArray<MaintenancePlan>(e8)
    maintenancePlanTotal = extractTotal(e8, maintenancePlans.length)
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
