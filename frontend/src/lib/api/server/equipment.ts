import { apiFetch, apiFetchRaw, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'

export async function createCategoryApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/categories`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateCategoryApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/categories/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteCategoryApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/categories/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createLocationApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/locations`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateLocationApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/locations/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteLocationApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/locations/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createEquipmentApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateEquipmentApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteEquipmentApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createFailureCodeApi(path: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/failure-codes/${path}`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateFailureCodeApi(path: string, id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/failure-codes/${path}/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteFailureCodeApi(path: string, id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/failure-codes/${path}/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createWorkOrderApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateWorkOrderApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function assignWorkOrderApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/assign`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function startWorkOrderApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/start`, {
    method: 'PUT',
    headers,
  })
}

export async function completeWorkOrderApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/complete`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function verifyWorkOrderApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/verify`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function closeWorkOrderApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/close`, {
    method: 'PUT',
    headers,
  })
}

export async function createCalibrationPlanApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/calibration/plans`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateCalibrationPlanApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/calibration/plans/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteCalibrationPlanApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/calibration/plans/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createCalibrationRecordApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/calibration/records`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function createSparePartApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateSparePartApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteSparePartApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function stockInboundApi(sparePartId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/${sparePartId}/stock/inbound`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function stockAdjustApi(sparePartId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/${sparePartId}/stock/adjust`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function createMaintenancePlanApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans/`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateMaintenancePlanApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteMaintenancePlanApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createInspectionTemplateApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateInspectionTemplateApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionTemplateApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createInspectionTemplateItemApi(templateId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/${templateId}/items`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateInspectionTemplateItemApi(itemId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/items/${itemId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionTemplateItemApi(itemId: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/items/${itemId}`, {
    method: 'DELETE',
    headers,
  })
}

export async function completeInspectionApi(workOrderId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-templates/complete/${workOrderId}`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function consumeMaterialsApi(workOrderId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${workOrderId}/materials`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function uploadWorkOrderImagesApi(workOrderId: string, formData: FormData, headers: Record<string, string>): Promise<unknown> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${workOrderId}/images`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as Record<string, unknown>).message || '上传失败')
  }
  const json = await res.json()
  return unwrapResponse(json)
}

export async function deleteWorkOrderImageApi(workOrderId: string, imageId: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${workOrderId}/images/${imageId}`, {
    method: 'DELETE',
    headers,
  })
}

export async function claimWorkOrderApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/claim`, {
    method: 'PUT',
    headers,
  })
}

export async function updateClaimTimeoutConfigApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/config/claim-timeout`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function downloadImportTemplateApi(headers?: Record<string, string>) {
  const res = await apiFetchRaw('/api/v1/equipment/equipments/import/template', {
    headers: headers || {},
  })
  const blob = await res.blob()
  const arrayBuffer = await blob.arrayBuffer()
  return Buffer.from(arrayBuffer).toString('base64')
}

export async function importEquipmentsApi(formData: FormData, headers: Record<string, string>): Promise<unknown> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/import`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as Record<string, unknown>).message || '导入失败')
  }
  const json = await res.json()
  return unwrapResponse(json)
}

export async function previewEquipmentImportApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/import/preview`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function batchImportEquipmentApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/import`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function createPersonnelRoleApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/roles`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updatePersonnelRoleApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/roles/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deletePersonnelRoleApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/roles/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function addPersonnelApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deletePersonnelApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function assignRolesApi(personnelId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/${personnelId}/roles`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function assignCategoriesApi(personnelId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/${personnelId}/categories`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function refreshFeishuApi(headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/refresh-feishu`, {
    method: 'POST',
    headers,
  })
}

export async function createInspectionRouteApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateInspectionRouteApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionRouteApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function setRouteLocationsApi(routeId: string, locations: unknown[], headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${routeId}/locations`, {
    method: 'POST',
    body: JSON.stringify({ locations }),
    headers,
  })
}

export async function createInspectionTaskApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function startInspectionTaskApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${id}/start`, {
    method: 'PUT',
    headers,
  })
}

export async function completeInspectionTaskApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${id}/complete`, {
    method: 'PUT',
    headers,
  })
}

export async function closeInspectionTaskApi(id: string, closureRemark?: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${id}/close`, {
    method: 'PUT',
    body: JSON.stringify({ closure_remark: closureRemark }),
    headers,
  })
}

export async function submitEquipmentCheckApi(taskId: string, equipmentId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${taskId}/equipments/${equipmentId}/check`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function uploadInspectionPhotoApi(taskId: string, equipmentId: string, formData: FormData, headers: Record<string, string>): Promise<unknown> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${taskId}/equipments/${equipmentId}/photos`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as Record<string, unknown>).message || '上传失败')
  }
  const json = await res.json()
  return unwrapResponse(json)
}

export async function deleteInspectionPhotoApi(taskId: string, photoId: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${taskId}/photos/${photoId}`, {
    method: 'DELETE',
    headers,
  })
}

export async function submitRouteCheckApi(taskId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${taskId}/route-check`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function uploadTaskPhotoApi(taskId: string, formData: FormData, headers: Record<string, string>): Promise<unknown> {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${taskId}/photos`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as Record<string, unknown>).message || '上传失败')
  }
  const json = await res.json()
  return unwrapResponse(json)
}

export async function analyzeInspectionPhotoApi(
  taskId: string,
  equipmentId: string,
  imageBase64: string,
  imageMimeType: string,
  headers?: Record<string, string>
) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${taskId}/equipments/${equipmentId}/ai-analyze`, {
    method: 'POST',
    body: JSON.stringify({ image_base64: imageBase64, image_mime_type: imageMimeType }),
    headers,
  })
}

export async function createScheduleApi(routeId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${routeId}/schedules`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateScheduleApi(routeId: string, scheduleId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${routeId}/schedules/${scheduleId}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteScheduleApi(routeId: string, scheduleId: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${routeId}/schedules/${scheduleId}`, {
    method: 'DELETE',
    headers,
  })
}

export async function stockInboundOldApi(sparePartId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/stock-inbound`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function consumeMaterialsOldApi(workOrderId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/material-consume`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function uploadWorkOrderImagesOldApi(workOrderId: string, formData: FormData, headers: Record<string, string>) {
  return uploadWorkOrderImagesApi(workOrderId, formData, headers)
}

export async function claimWorkOrderDataApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/${id}/claim`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateClaimTimeoutConfigOldApi(config: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/claim-timeout-config`, {
    method: 'PUT',
    body: JSON.stringify(config),
    headers,
  })
}

export async function completeInspectionOldApi(workOrderId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/inspection-complete`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function createSparePartOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateSparePartOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteSparePartOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createMaintenancePlanOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateMaintenancePlanOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteMaintenancePlanOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createInspectionTemplateOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/templates`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateInspectionTemplateOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/templates/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionTemplateOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/templates/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createInspectionTemplateItemOldApi(templateId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/template-items`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateInspectionTemplateItemOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/template-items/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionTemplateItemOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/template-items/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createInspectionRouteOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateInspectionRouteOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteInspectionRouteOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function setRouteLocationsOldApi(routeId: string, items: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/routes/${routeId}/locations`, {
    method: 'PUT',
    body: JSON.stringify({ items }),
    headers,
  })
}

export async function createScheduleOldApi(routeId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/schedules`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateScheduleOldApi(routeId: string, id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/schedules/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteScheduleOldApi(routeId: string, id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/schedules/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function createInspectionTaskOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function startInspectionTaskOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${id}/start`, {
    method: 'PUT',
    headers,
  })
}

export async function closeInspectionTaskOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${id}/close`, {
    method: 'PUT',
    headers,
  })
}

export async function submitEquipmentCheckOldApi(taskId: string, equipmentId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/checks`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function uploadInspectionPhotoOldApi(taskId: string, equipmentId: string, formData: FormData, headers: Record<string, string>) {
  return uploadInspectionPhotoApi(taskId, equipmentId, formData, headers)
}

export async function completeInspectionTaskOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/tasks/${id}/complete`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function analyzeInspectionPhotoOldApi(taskId: string, equipmentId: string, base64: string, mimeType: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/photos/${taskId}/analyze`, {
    method: 'POST',
    headers,
  })
}

export async function addPersonnelOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deletePersonnelOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function assignRolesOldApi(personnelId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/${personnelId}/roles`, {
    method: 'PUT',
    body: JSON.stringify({ data }),
    headers,
  })
}

export async function assignCategoriesOldApi(personnelId: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/${personnelId}/categories`, {
    method: 'PUT',
    body: JSON.stringify({ data }),
    headers,
  })
}

export async function createRoleOldApi(data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/roles`, {
    method: 'POST',
    body: JSON.stringify(data),
    headers,
  })
}

export async function updateRoleOldApi(id: string, data: unknown, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/roles/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
    headers,
  })
}

export async function deleteRoleOldApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/roles/${id}`, {
    method: 'DELETE',
    headers,
  })
}

export async function refreshFeishuOldApi(headers?: Record<string, string>) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/personnel/refresh-feishu`, {
    method: 'POST',
    headers,
  })
}

export async function downloadImportTemplateOldApi() {
  const res = await apiFetchRaw('/api/v1/equipment/equipments/import-template')
  const blob = await res.blob()
  return blob
}

export async function importEquipmentsOldApi(formData: FormData, headers: Record<string, string>) {
  const res = await fetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/import`, {
    method: 'POST',
    body: formData,
    headers,
  })
  if (!res.ok) throw new Error('导入设备失败')
  return res.json()
}

// ── Read functions (Server Component GET calls) ──

export async function fetchCategories() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/categories`)
}

export async function fetchCategoryTree() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/categories?tree=true`)
}

export async function fetchLocations() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/locations`)
}

export async function fetchLocationTree() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/locations?tree=true`)
}

export async function fetchEquipments(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.category_id) params.append('category_id', filters.category_id)
  if (filters.location_id) params.append('location_id', filters.location_id)
  if (filters.department_id) params.append('department_id', filters.department_id)
  if (filters.status) params.append('status', filters.status)
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments${qs ? `?${qs}` : ''}`)
}

export async function fetchEquipmentStatistics() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/equipments/statistics`)
}

export async function fetchDepartments() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/departments`)
}

export async function fetchInspectionTemplates(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/inspection/templates${qs ? `?${qs}` : ''}`)
}

export async function fetchWorkOrders(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.status) params.append('status', filters.status)
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.priority) params.append('priority', filters.priority)
  if (filters.order_type) params.append('order_type', filters.order_type)
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders${qs ? `?${qs}` : ''}`)
}

export async function fetchWorkOrderStatistics(exclude_status?: string) {
  const params = new URLSearchParams()
  if (exclude_status) params.append('exclude_status', exclude_status)
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/work-orders/statistics${qs ? `?${qs}` : ''}`)
}

export async function fetchFailureCodes(type: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/failure-codes/${type}`)
}

export async function fetchCalibrationPlans(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.status) params.append('status', filters.status)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/calibration/plans${qs ? `?${qs}` : ''}`)
}

export async function fetchCalibrationRecords(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.plan_id) params.append('plan_id', filters.plan_id)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/calibration/records${qs ? `?${qs}` : ''}`)
}

export async function fetchMaintenancePlans(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.equipment_id) params.append('equipment_id', filters.equipment_id)
  if (filters.status) params.append('status', filters.status)
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans${qs ? `?${qs}` : ''}`)
}

export async function fetchOverdueMaintenancePlans(days?: number) {
  const params = new URLSearchParams()
  if (days !== undefined) params.append('days', days.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/maintenance/plans/overdue${qs ? `?${qs}` : ''}`)
}

export async function fetchSpareParts(filters: Record<string, unknown> = {}) {
  const params = new URLSearchParams()
  if (filters.category) params.append('category', filters.category)
  if (filters.keyword) params.append('keyword', filters.keyword)
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active.toString())
  if (filters.page) params.append('page', filters.page.toString())
  if (filters.page_size) params.append('page_size', filters.page_size.toString())
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts${qs ? `?${qs}` : ''}`)
}

export async function fetchStockWarnings() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/equipment/spare-parts/stock/warnings`)
}