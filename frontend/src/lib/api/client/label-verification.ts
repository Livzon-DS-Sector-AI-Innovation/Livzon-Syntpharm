import {
  LabelVerificationListResponse,
  LabelVerificationResponse,
  LabelVerificationStatisticsResponse,
  LabelVerificationListParams,
} from '@/types/label-verification'

export async function fetchLabelVerifications(
  params?: LabelVerificationListParams
): Promise<LabelVerificationListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.batch_number) searchParams.set('batch_number', params.batch_number)
  if (params?.product_name) searchParams.set('product_name', params.product_name)
  if (params?.result_status) searchParams.set('result_status', params.result_status)
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  searchParams.set('page', String(params?.page || 1))
  searchParams.set('page_size', String(params?.page_size || 20))

  const res = await fetch(`/api/v1/quality/label-verifications?${searchParams.toString()}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取标签复核列表失败')
  return res.json()
}

export async function fetchLabelVerificationById(id: string): Promise<LabelVerificationResponse> {
  const res = await fetch(`/api/v1/quality/label-verifications/${id}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取标签复核详情失败')
  return res.json()
}

export async function fetchLabelVerificationStatistics(): Promise<LabelVerificationStatisticsResponse> {
  const res = await fetch(`/api/v1/quality/label-verifications/statistics`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取标签复核统计数据失败')
  return res.json()
}

export async function fetchLabelVerificationsByBatch(batchNumber: string): Promise<LabelVerificationListResponse> {
  const res = await fetch(`/api/v1/quality/label-verifications/batch/${batchNumber}`, {
    cache: 'no-store',
  })
  if (!res.ok) throw new Error('获取批号历史记录失败')
  return res.json()
}



