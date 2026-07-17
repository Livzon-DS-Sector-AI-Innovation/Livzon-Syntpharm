import { apiFetch } from '@/lib/api/server/base'
import type {
  LabelVerificationCreateInput,
  LabelVerificationUpdateInput,
  AutoCompareRequest,
  AutoCompareResult,
} from '@/types/label-verification'

export async function createLabelVerification(data: LabelVerificationCreateInput) {
  return apiFetch('/api/v1/quality/label-verifications', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLabelVerification(id: string, data: LabelVerificationUpdateInput) {
  return apiFetch(`/api/v1/quality/label-verifications/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteLabelVerification(id: string) {
  return apiFetch(`/api/v1/quality/label-verifications/${id}`, {
    method: 'DELETE',
  })
}

export async function autoCompareVideo(
  data: AutoCompareRequest
): Promise<{ code: number; message: string; data: AutoCompareResult }> {
  return apiFetch('/api/v1/quality/label-verifications/auto-compare', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}