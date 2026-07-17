'use server'

import { revalidatePath } from 'next/cache'
import type { OptimizationCreate, OptimizationUpdate } from '@/types/research'
import {
  createOptimization as createOptimizationApi,
  updateOptimization as updateOptimizationApi,
  deleteOptimization as deleteOptimizationApi,
} from '@/lib/api/server/research'

export async function createOptimizationAction(data: OptimizationCreate) {
  try {
    const optimization = await createOptimizationApi(data)
    revalidatePath('/research/process-optimization')
    return { success: true, data: optimization }
  } catch (error) {
    return { success: false, error: (error as Error).message }
  }
}

export async function updateOptimizationAction(id: string, data: OptimizationUpdate) {
  try {
    const optimization = await updateOptimizationApi(id, data)
    revalidatePath('/research/process-optimization')
    return { success: true, data: optimization }
  } catch (error) {
    return { success: false, error: (error as Error).message }
  }
}

export async function deleteOptimizationAction(id: string) {
  try {
    await deleteOptimizationApi(id)
    revalidatePath('/research/process-optimization')
    return { success: true }
  } catch (error) {
    return { success: false, error: (error as Error).message }
  }
}