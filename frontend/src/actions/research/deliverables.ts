'use server'

import { revalidatePath } from 'next/cache'
import {
  createDeliverable as createDeliverableApi,
  updateDeliverable as updateDeliverableApi,
  deleteDeliverable as deleteDeliverableApi,
  uploadDeliverableFile as uploadDeliverableFileApi,
} from '@/lib/api/server/research'

export async function createDeliverable(data: {
  project_id: string
  stage: string
  deliverable_type: string
  title: string
  status?: string
  version?: string
  content?: string
}) {
  const result = await createDeliverableApi(data)
  revalidatePath('/research/projects')
  return result
}

export async function updateDeliverable(id: string, data: {
  title?: string
  status?: string
  version?: string
  content?: string
}) {
  const result = await updateDeliverableApi(id, data)
  revalidatePath('/research/projects')
  return result
}

export async function deleteDeliverable(id: string) {
  await deleteDeliverableApi(id)
  revalidatePath('/research/projects')
}

export async function uploadDeliverableFile(deliverableId: string, formData: FormData) {
  const result = await uploadDeliverableFileApi(deliverableId, formData)
  revalidatePath('/research/projects')
  return result
}