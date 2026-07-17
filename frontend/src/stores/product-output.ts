import { create } from 'zustand'
import type {
  ProductOutput,
  ProductOutputQueryParams,
  SummaryData,
} from '@/types/product-output'

interface ProductOutputState {
  records: ProductOutput[]
  total: number
  queryParams: ProductOutputQueryParams
  loading: boolean
  selectedWorkshop: string | null
  summary: SummaryData | null
  summaryLoading: boolean

  setRecords: (records: ProductOutput[]) => void
  setTotal: (total: number) => void
  setQueryParams: (params: Partial<ProductOutputQueryParams>) => void
  setLoading: (loading: boolean) => void
  setSelectedWorkshop: (workshop: string | null) => void
  setSummary: (summary: SummaryData | null) => void
  setSummaryLoading: (loading: boolean) => void
  addRecord: (record: ProductOutput) => void
  updateRecord: (id: string, updates: Partial<ProductOutput>) => void
  removeRecord: (id: string) => void
  reset: () => void
}

const initialState = {
  records: [] as ProductOutput[],
  total: 0,
  queryParams: { page: 1, page_size: 20 } as ProductOutputQueryParams,
  loading: false,
  selectedWorkshop: null as string | null,
  summary: null as SummaryData | null,
  summaryLoading: false,
}

export const useProductOutputStore = create<ProductOutputState>((set) => ({
  ...initialState,

  setRecords: (records) => set({ records }),
  setTotal: (total) => set({ total }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),
  setLoading: (loading) => set({ loading }),
  setSelectedWorkshop: (workshop) => set({ selectedWorkshop: workshop }),
  setSummary: (summary) => set({ summary }),
  setSummaryLoading: (loading) => set({ summaryLoading: loading }),

  addRecord: (record) =>
    set((state) => ({ records: [record, ...state.records] })),

  updateRecord: (id, updates) =>
    set((state) => ({
      records: state.records.map((r) => (r.id === id ? { ...r, ...updates } : r)),
    })),

  removeRecord: (id) =>
    set((state) => ({
      records: state.records.filter((r) => r.id !== id),
    })),

  reset: () => set(initialState),
}))
