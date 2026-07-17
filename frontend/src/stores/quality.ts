import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import {
  DeviationListItem,
  DeviationDetail,
  DeviationStatus,
  DeviationLevel,
  CapaListItem,
  CapaDetail,
  CapaWorkflowStatus,
  CapaSource,
  CapaCategory,
  DepartmentContact,
} from '@/types/quality'

// ============ Deviation Store ============
interface DeviationStore {
  // 数据
  deviations: DeviationListItem[]
  total: number
  loading: boolean

  // 筛选状态
  statusFilter: DeviationStatus | ''
  levelFilter: DeviationLevel | ''
  departmentFilter: string | ''
  keyword: string
  page: number
  pageSize: number

  // 操作
  setDeviations: (deviations: DeviationListItem[]) => void
  setTotal: (total: number) => void
  setLoading: (loading: boolean) => void
  setStatusFilter: (status: DeviationStatus | '') => void
  setLevelFilter: (level: DeviationLevel | '') => void
  setDepartmentFilter: (department: string | '') => void
  setKeyword: (keyword: string) => void
  setPage: (page: number) => void
  setPageSize: (pageSize: number) => void
  resetFilters: () => void
}

export const useDeviationStore = create<DeviationStore>()(
  devtools(
    (set) => ({
      deviations: [],
      total: 0,
      loading: false,

      statusFilter: '',
      levelFilter: '',
      departmentFilter: '',
      keyword: '',
      page: 1,
      pageSize: 20,

      setDeviations: (deviations) => set({ deviations }),
      setTotal: (total) => set({ total }),
      setLoading: (loading) => set({ loading }),
      setStatusFilter: (statusFilter) => set({ statusFilter, page: 1 }),
      setLevelFilter: (levelFilter) => set({ levelFilter, page: 1 }),
      setDepartmentFilter: (departmentFilter) => set({ departmentFilter, page: 1 }),
      setKeyword: (keyword) => set({ keyword, page: 1 }),
      setPage: (page) => set({ page }),
      setPageSize: (pageSize) => set({ pageSize, page: 1 }),
      resetFilters: () =>
        set({
          statusFilter: '',
          levelFilter: '',
          departmentFilter: '',
          keyword: '',
          page: 1,
          pageSize: 20,
        }),
    }),
    { name: 'deviation-store' }
  )
)

// ============ CAPA Store ============
interface CapaStore {
  // 数据
  capas: CapaListItem[]
  total: number
  loading: boolean

  // 筛选状态
  statusFilter: CapaWorkflowStatus | ''
  sourceFilter: CapaSource | ''
  categoryFilter: CapaCategory | ''
  keyword: string
  page: number
  pageSize: number

  // 操作
  setCapas: (capas: CapaListItem[]) => void
  setTotal: (total: number) => void
  setLoading: (loading: boolean) => void
  setStatusFilter: (status: CapaWorkflowStatus | '') => void
  setSourceFilter: (source: CapaSource | '') => void
  setCategoryFilter: (category: CapaCategory | '') => void
  setKeyword: (keyword: string) => void
  setPage: (page: number) => void
  setPageSize: (pageSize: number) => void
  resetFilters: () => void
}

export const useCapaStore = create<CapaStore>()(
  devtools(
    (set) => ({
      capas: [],
      total: 0,
      loading: false,

      statusFilter: '',
      sourceFilter: '',
      categoryFilter: '',
      keyword: '',
      page: 1,
      pageSize: 20,

      setCapas: (capas) => set({ capas }),
      setTotal: (total) => set({ total }),
      setLoading: (loading) => set({ loading }),
      setStatusFilter: (statusFilter) => set({ statusFilter, page: 1 }),
      setSourceFilter: (sourceFilter) => set({ sourceFilter, page: 1 }),
      setCategoryFilter: (categoryFilter) => set({ categoryFilter, page: 1 }),
      setKeyword: (keyword) => set({ keyword, page: 1 }),
      setPage: (page) => set({ page }),
      setPageSize: (pageSize) => set({ pageSize, page: 1 }),
      resetFilters: () =>
        set({
          statusFilter: '',
          sourceFilter: '',
          categoryFilter: '',
          keyword: '',
          page: 1,
          pageSize: 20,
        }),
    }),
    { name: 'capa-store' }
  )
)

// ============ Department Contact Store ============
interface DepartmentContactStore {
  // 数据
  contacts: DepartmentContact[]
  total: number
  loading: boolean

  // 分页
  page: number
  pageSize: number

  // 操作
  setContacts: (contacts: DepartmentContact[]) => void
  setTotal: (total: number) => void
  setLoading: (loading: boolean) => void
  setPage: (page: number) => void
  setPageSize: (pageSize: number) => void
}

export const useDepartmentContactStore = create<DepartmentContactStore>()(
  devtools(
    (set) => ({
      contacts: [],
      total: 0,
      loading: false,

      page: 1,
      pageSize: 20,

      setContacts: (contacts) => set({ contacts }),
      setTotal: (total) => set({ total }),
      setLoading: (loading) => set({ loading }),
      setPage: (page) => set({ page }),
      setPageSize: (pageSize) => set({ pageSize, page: 1 }),
    }),
    { name: 'department-contact-store' }
  )
)
