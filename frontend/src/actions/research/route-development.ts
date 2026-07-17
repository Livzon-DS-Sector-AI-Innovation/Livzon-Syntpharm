'use server'

import { revalidatePath } from 'next/cache'
import type { RouteCreate, RouteUpdate } from '@/types/research'
import {
  createRoute as createRouteApi,
  updateRoute as updateRouteApi,
  deleteRoute as deleteRouteApi,
} from '@/lib/api/server/research'

export async function createRouteAction(data: RouteCreate) {
  try {
    const route = await createRouteApi(data)
    revalidatePath('/research/route-development')
    return { success: true, data: route }
  } catch (error) {
    return { success: false, error: (error as Error).message }
  }
}

export async function updateRouteAction(routeId: string, data: RouteUpdate) {
  try {
    const route = await updateRouteApi(routeId, data)
    revalidatePath('/research/route-development')
    revalidatePath(`/research/route-development/${routeId}`)
    return { success: true, data: route }
  } catch (error) {
    return { success: false, error: (error as Error).message }
  }
}

export async function deleteRouteAction(routeId: string) {
  try {
    await deleteRouteApi(routeId)
    revalidatePath('/research/route-development')
    return { success: true }
  } catch (error) {
    return { success: false, error: (error as Error).message }
  }
}