'use client'

import { create } from 'zustand'
import type { EhsChange, EhsChangeQueryParams } from '@/types/safety'

interface EhsChangeState {
  // UI state only - data is managed by React Query
  currentItem: EhsChange | null
  queryParams: EhsChangeQueryParams
  setCurrentItem: (item: EhsChange | null) => void
  setQueryParams: (params: Partial<EhsChangeQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as EhsChange | null,
  queryParams: { page: 1, page_size: 20 } as EhsChangeQueryParams,
}

export const useEhsChangeStore = create<EhsChangeState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
