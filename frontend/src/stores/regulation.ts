import { create } from 'zustand'
import {
  fetchRegulations,
  type Regulation,
} from '@/lib/api/client/administration/regulation'
import {
  createRegulation,
  updateRegulation,
  deleteRegulation,
} from '@/actions/administration'

interface RegulationState {
  regulations: Regulation[]
  loading: boolean
  error: string | null
  total: number
  keyword: string
  page: number
  pageSize: number

  loadRegulations: () => Promise<void>
  setKeyword: (keyword: string) => void
  setPage: (page: number) => void
  addRegulation: (data: { title: string; category?: string; version?: string; content: string; file_name?: string; file_type?: string; file_data?: string }) => Promise<void>
  removeRegulation: (id: string) => Promise<void>
  updateRegulationItem: (id: string, data: { title?: string; category?: string; version?: string; content?: string }) => Promise<void>
  searchRegulations: (keyword: string) => Regulation[]
}

export const useRegulationStore = create<RegulationState>((set, get) => ({
  regulations: [],
  loading: false,
  error: null,
  total: 0,
  keyword: '',
  page: 1,
  pageSize: 20,

  loadRegulations: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetchRegulations({
        keyword: get().keyword || undefined,
        page: get().page,
        page_size: get().pageSize,
      })
      set({ regulations: res.data, total: res.meta?.total || 0 })
    } catch (err: any) {
      set({ error: err.message || '加载失败' })
    } finally {
      set({ loading: false })
    }
  },

  setKeyword: (keyword) => {
    set({ keyword, page: 1 })
    get().loadRegulations()
  },

  setPage: (page) => {
    set({ page })
    get().loadRegulations()
  },

  addRegulation: async (data) => {
    await createRegulation(data)
    await get().loadRegulations()
  },

  removeRegulation: async (id) => {
    await deleteRegulation(id)
    await get().loadRegulations()
  },

  updateRegulationItem: async (id, data) => {
    await updateRegulation(id, data)
    await get().loadRegulations()
  },

  searchRegulations: (keyword) => {
    const lower = keyword.trim().toLowerCase()
    if (!lower) return get().regulations
    return get().regulations.filter(
      (r) =>
        r.title.toLowerCase().includes(lower) ||
        r.content.toLowerCase().includes(lower) ||
        (r.file_name && r.file_name.toLowerCase().includes(lower))
    )
  },
}))
