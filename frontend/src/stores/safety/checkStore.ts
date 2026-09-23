'use client'

import { create } from 'zustand'
import type { SafetyCheck, SafetyCheckQueryParams } from '@/types/safety'

interface CheckState {
  // UI state only - data is managed by React Query
  currentItem: SafetyCheck | null
  queryParams: SafetyCheckQueryParams
  setCurrentItem: (item: SafetyCheck | null) => void
  setQueryParams: (params: Partial<SafetyCheckQueryParams>) => void
  reset: () => void
}

const initialState = {
  currentItem: null as SafetyCheck | null,
  queryParams: { page: 1, page_size: 20 } as SafetyCheckQueryParams,
}

export const useCheckStore = create<CheckState>((set) => ({
  ...initialState,

  setCurrentItem: (currentItem) => set({ currentItem }),
  setQueryParams: (params) =>
    set((state) => ({ queryParams: { ...state.queryParams, ...params } })),

  reset: () => set(initialState),
}))
