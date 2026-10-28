'use client'

import { useQuery } from '@tanstack/react-query'
import type { EquipmentListQuery, EquipmentStatsQuery } from '@/lib/api/equipment-query'
import {
  fetchCategoryTree,
  fetchDepartments,
  fetchEquipmentsClient,
  fetchEquipmentStatisticsClient,
  fetchLocationTree,
} from '@/lib/api/client/equipment'
import type {
  DepartmentOption,
  EquipmentCategory,
  EquipmentListResponse,
  EquipmentStatistics,
  Location,
} from '@/types/equipment/generated-bridge'

export const EQUIPMENT_LIST_KEY = ['equipment', 'equipments'] as const
export const EQUIPMENT_STATISTICS_KEY = ['equipment', 'statistics'] as const
export const EQUIPMENT_TAXONOMY_KEY = ['equipment', 'taxonomy'] as const

export interface EquipmentTaxonomy {
  categories: EquipmentCategory[]
  locations: Location[]
  departments: DepartmentOption[]
}

/**
 * 台账列表：筛选条件与排序/分页在此合成唯一一份参数，同时作为 queryKey。
 * staleTime 显式归零：全局默认 5 分钟会把 SSR 喂进来的首屏数据判成「新鲜」，
 * 切回已有 key（如取消排序回到默认 asset_no）就不再发请求，界面与地址栏脱节。
 */
export function useEquipmentListQuery(query: EquipmentListQuery, initialData?: EquipmentListResponse) {
  return useQuery({
    queryKey: [...EQUIPMENT_LIST_KEY, query],
    queryFn: () => fetchEquipmentsClient(query),
    staleTime: 0,
    initialData,
  })
}

/** 状态统计：与列表共用筛选口径，但不含排序/分页 */
export function useEquipmentStatisticsQuery(filters: EquipmentStatsQuery, initialData?: EquipmentStatistics) {
  return useQuery({
    queryKey: [...EQUIPMENT_STATISTICS_KEY, filters],
    queryFn: () => fetchEquipmentStatisticsClient(filters),
    staleTime: 0,
    initialData,
  })
}

/**
 * 分类树 / 位置树 / 部门：低频变更的引用数据，一次取全并让页面与各抽屉共享缓存。
 * 服务端首屏同样取 tree=true，否则补偿加载会把层级树降级成平铺列表。
 */
export function useEquipmentTaxonomyQuery(initialData?: EquipmentTaxonomy) {
  return useQuery({
    queryKey: EQUIPMENT_TAXONOMY_KEY,
    queryFn: async (): Promise<EquipmentTaxonomy> => {
      const [categories, locations, departments] = await Promise.all([
        fetchCategoryTree(),
        fetchLocationTree(),
        fetchDepartments(),
      ])
      return { categories, locations, departments }
    },
    initialData,
  })
}
