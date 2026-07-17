'use server'

import { revalidatePath } from 'next/cache'
import { getServerToken } from '@/lib/auth'
import type {
  ContractGenerateRequest,
  InvoiceRecognitionRecordDeleteResponse,
  InvoiceRecognitionResponse,
  PurchaseApprovalRequest,
  PurchaseRequestApiResponse,
  PurchaseRequestCreate,
  PurchaseRequestUpdate,
} from '@/types/procurement'
import {
  recognizeInvoicePdf as recognizeInvoicePdfServer,
  deleteInvoiceRecognitionRecord as deleteInvoiceRecognitionRecordServer,
  deleteInvoiceRecognitionRecords as deleteInvoiceRecognitionRecordsServer,
  createPurchaseRequest as createPurchaseRequestServer,
  updatePurchaseRequest as updatePurchaseRequestServer,
  submitPurchaseRequest as submitPurchaseRequestServer,
  approvePurchaseRequest as approvePurchaseRequestServer,
  rejectPurchaseRequest as rejectPurchaseRequestServer,
  generateProcurementContract as generateProcurementContractServer,
  importSupplierTable as importSupplierTableServer,
} from '@/lib/api/server/procurement'

async function getAuthHeaders(): Promise<HeadersInit> {
  const token = await getServerToken()
  const headers: HeadersInit = {}
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

export type ContractGenerateActionResult =
  | { ok: true; filename: string; contentType: string; base64: string }
  | { ok: false; message: string }

export async function recognizeInvoicePdf(
  formData: FormData
): Promise<InvoiceRecognitionResponse> {
  const headers = await getAuthHeaders()
  return recognizeInvoicePdfServer(headers, formData)
}

export async function deleteInvoiceRecognitionRecord(
  recordId: string
): Promise<InvoiceRecognitionRecordDeleteResponse> {
  const headers = await getAuthHeaders()
  return deleteInvoiceRecognitionRecordServer(headers, recordId)
}

export async function deleteInvoiceRecognitionRecords(
  recordIds: string[]
): Promise<InvoiceRecognitionRecordDeleteResponse> {
  const headers = await getAuthHeaders()
  return deleteInvoiceRecognitionRecordsServer(headers, recordIds)
}

export async function createPurchaseRequest(
  payload: PurchaseRequestCreate
): Promise<PurchaseRequestApiResponse> {
  const headers = await getAuthHeaders()
  const response = await createPurchaseRequestServer(headers, payload)
  revalidatePath('/procurement')
  return response
}

export async function updatePurchaseRequest(
  requestId: string,
  payload: PurchaseRequestUpdate
): Promise<PurchaseRequestApiResponse> {
  const headers = await getAuthHeaders()
  const response = await updatePurchaseRequestServer(headers, requestId, payload)
  revalidatePath('/procurement')
  return response
}

export async function submitPurchaseRequest(
  requestId: string
): Promise<PurchaseRequestApiResponse> {
  const headers = await getAuthHeaders()
  const response = await submitPurchaseRequestServer(headers, requestId)
  revalidatePath('/procurement')
  return response
}

export async function approvePurchaseRequest(
  requestId: string,
  payload: PurchaseApprovalRequest
): Promise<PurchaseRequestApiResponse> {
  const headers = await getAuthHeaders()
  const response = await approvePurchaseRequestServer(headers, requestId, payload)
  revalidatePath('/procurement')
  return response
}

export async function rejectPurchaseRequest(
  requestId: string,
  payload: PurchaseApprovalRequest
): Promise<PurchaseRequestApiResponse> {
  const headers = await getAuthHeaders()
  const response = await rejectPurchaseRequestServer(headers, requestId, payload)
  revalidatePath('/procurement')
  return response
}

export async function generateProcurementContract(
  payload: ContractGenerateRequest
): Promise<ContractGenerateActionResult> {
  const headers = await getAuthHeaders()
  return generateProcurementContractServer(headers, payload)
}

export async function importSupplierTable(
  formData: FormData
): Promise<any> {
  const headers = await getAuthHeaders()
  const result = await importSupplierTableServer(headers, formData)
  revalidatePath('/procurement/supplier')
  return result
}