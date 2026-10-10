'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import { safeApiFetch } from '@/lib/api/server/base'
import { uploadHazardPhoto } from '@/lib/api/server/safety'

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<{ code: number; message: string; data: T; meta?: { page?: number; page_size?: number; total?: number } }> {
  return safeApiFetch<T>(`/api/v1${endpoint}`, options)
}

export async function uploadPhoto(endpoint: string, file: File) {
  const authHeaders = await getAuthHeaders()
  const result = await uploadHazardPhoto(`/api/v1${endpoint}`, file, authHeaders)
  revalidatePath('/safety/hazard')
  return result as Record<string, unknown>
}
