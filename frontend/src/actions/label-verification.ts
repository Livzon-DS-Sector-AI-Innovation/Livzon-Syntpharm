'use server'

import { revalidatePath } from 'next/cache'
import type {
  LabelVerificationCreateInput,
  LabelVerificationUpdateInput,
  AutoCompareRequest,
  AutoCompareResult,
} from '@/types/label-verification'
import {
  createLabelVerification as apiCreateLabelVerification,
  updateLabelVerification as apiUpdateLabelVerification,
  deleteLabelVerification as apiDeleteLabelVerification,
  autoCompareVideo as apiAutoCompareVideo,
} from '@/lib/api/server/label-verification'

export async function createLabelVerification(
  data: LabelVerificationCreateInput
) {
  const json = await apiCreateLabelVerification(data)
  revalidatePath('/quality/label-verification')
  return json
}

export async function updateLabelVerification(
  id: string,
  data: LabelVerificationUpdateInput
) {
  const json = await apiUpdateLabelVerification(id, data)
  revalidatePath('/quality/label-verification')
  return json
}

export async function deleteLabelVerification(id: string) {
  await apiDeleteLabelVerification(id)
  revalidatePath('/quality/label-verification')
}

export async function autoCompareVideo(
  data: AutoCompareRequest
): Promise<{ code: number; message: string; data: AutoCompareResult }> {
  return apiAutoCompareVideo(data)
}