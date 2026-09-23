'use client'

import { create } from 'zustand'
import type { OhHazardMonitor, OhHazardMonitorQueryParams } from '@/types/safety'

interface OhHazardMonitorState {
  // UI state only - data is managed by React Query
  currentItem: OhHazardMonitor | null
  queryParams: OhHazardMonitorQueryParams
  setCurrentItem: (item: OhHazardMonitor | null) => void
  setQueryParams: (params: Partial<OhHazardMonitorQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as OhHazardMonitor | null,
  queryParams: { page: 1, page_size: 20 } as OhHazardMonitorQueryParams,
}

export const useOhHazardMonitorStore = create<OhHazardMonitorState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
