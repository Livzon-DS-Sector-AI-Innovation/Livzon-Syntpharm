import { InspectionPage } from '@/components/equipment/inspection'
import { fetchInspectionTemplates } from '@/lib/api/server/equipment'
import { fetchEquipments, fetchCategories, fetchLocationTree } from '@/lib/api/server/equipment'
import type { InspectionTemplate, EquipmentCategory } from '@/types/equipment'

export const dynamic = 'force-dynamic'

export default async function InspectionPageWrapper() {
  let templates: InspectionTemplate[] = []
  let equipments: { id: string; name: string; asset_no: string; location_id: string }[] = []
  let categories: EquipmentCategory[] = []
  let locations: { id: string; name: string; code: string }[] = []

  try {
    const [templatesResult, equipmentsResult, categoriesResult, locationsResult] = await Promise.all([
      fetchInspectionTemplates({ is_active: true, page: 1, page_size: 200 }),
      fetchEquipments({ page: 1, page_size: 200 }),
      fetchCategories(),
      fetchLocationTree(),
    ])
    templates = templatesResult.items || []
    equipments = (equipmentsResult.items || []).map((e: any) => ({
      id: e.id,
      name: e.name,
      asset_no: e.asset_no,
      location_id: e.location_id,
    }))
    categories = categoriesResult || []
    locations = (locationsResult || []).map((l: any) => ({
      id: l.id,
      name: l.name,
      code: l.code || l.location_code || '',
    }))
  } catch (error) {
    console.warn('巡检页面数据加载失败，使用空数据:', error)
  }

  return (
    <InspectionPage
      initialTemplates={templates}
      initialEquipments={equipments}
      initialCategories={categories}
      initialLocations={locations}
    />
  )
}
