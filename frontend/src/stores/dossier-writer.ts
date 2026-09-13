import { create } from 'zustand'
import type {
  ProductDossier,
  Chapter,
  ChapterDetail,
} from '@/types/dossier-writer'
import {
  fetchProductDossiers,
  fetchProductDossier,
  fetchChapterTree,
  fetchChapterDetail,
} from '@/lib/api/client/dossier-writer'

interface DossierWriterState {
  // 品种资料列表
  dossiers: ProductDossier[]
  dossiersTotal: number
  dossiersLoading: boolean

  // 当前品种资料
  currentDossier: ProductDossier | null
  currentDossierLoading: boolean

  // 章节树
  chapterTree: Chapter[]
  chapterTreeLoading: boolean

  // 当前章节
  currentChapter: ChapterDetail | null
  currentChapterLoading: boolean

  // 预览刷新键
  previewRefreshKey: number

  // Actions
  loadDossiers: (skip?: number, limit?: number) => Promise<void>
  loadDossier: (id: string) => Promise<void>
  loadChapterTree: (dossierId: string) => Promise<void>
  loadChapterDetail: (chapterId: string) => Promise<void>
  loadAvailableAssets: (chapterId: string) => Promise<void>
  setCurrentDossier: (dossier: ProductDossier | null) => void
  setCurrentChapter: (chapter: ChapterDetail | null) => void
  invalidateChapterContext: (dossierId: string, chapterId?: string) => Promise<void>
}

export const useDossierWriterStore = create<DossierWriterState>((set, get) => ({
  // 初始状态
  dossiers: [],
  dossiersTotal: 0,
  dossiersLoading: false,

  currentDossier: null,
  currentDossierLoading: false,

  chapterTree: [],
  chapterTreeLoading: false,

  currentChapter: null,
  currentChapterLoading: false,

  previewRefreshKey: 0,

  // Actions
  loadDossiers: async (skip = 0, limit = 100) => {
    set({ dossiersLoading: true })
    try {
      const data = await fetchProductDossiers(skip, limit)
      set({
        dossiers: data.items,
        dossiersTotal: data.total,
        dossiersLoading: false,
      })
    } catch {
      set({ dossiersLoading: false })
    }
  },

  loadDossier: async (id: string) => {
    set({ currentDossierLoading: true })
    try {
      const dossier = await fetchProductDossier(id)
      set({ currentDossier: dossier, currentDossierLoading: false })
    } catch {
      set({ currentDossierLoading: false })
    }
  },

  loadChapterTree: async (dossierId: string) => {
    set({ chapterTreeLoading: true })
    try {
      const tree = await fetchChapterTree(dossierId)
      set({ chapterTree: tree, chapterTreeLoading: false })
    } catch {
      set({ chapterTreeLoading: false })
    }
  },

  loadChapterDetail: async (chapterId: string) => {
    set({ currentChapterLoading: true })
    try {
      const detail = await fetchChapterDetail(chapterId)
      set({ currentChapter: detail, currentChapterLoading: false })
    } catch {
      set({ currentChapterLoading: false })
    }
  },

  loadAvailableAssets: async (chapterId: string) => {
    // This function will be implemented in the API client when needed
    // For now, it's a placeholder to satisfy the interface
    console.log(`Loading available assets for chapter ${chapterId}`)
  },

  setCurrentDossier: (dossier) => set({ currentDossier: dossier }),
  setCurrentChapter: (chapter) => set({ currentChapter: chapter }),

  invalidateChapterContext: async (dossierId: string, chapterId?: string) => {
    await get().loadChapterTree(dossierId)
    if (chapterId) {
      await get().loadAvailableAssets(chapterId)
    }
    set(s => ({ previewRefreshKey: s.previewRefreshKey + 1 }))
  },
}))
