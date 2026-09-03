'use server'

import { z } from 'zod'
import {parse, NonEmptyStringSchema} from '@/lib/validation/schemas'
import { revalidatePath } from 'next/cache'
import {
  createDomesticApproval as createDomesticApprovalApi,
  importDomesticApprovals as importDomesticApprovalsApi,
  createOverseasApproval as createOverseasApprovalApi,
  importOverseasApprovals as importOverseasApprovalsApi,
  createInternationalReview as createInternationalReviewApi,
  importInternationalReviews as importInternationalReviewsApi,
  createCoppCertificate as createCoppCertificateApi,
  importCoppCertificates as importCoppCertificatesApi,
  createWcCertificate as createWcCertificateApi,
  importWcCertificates as importWcCertificatesApi,
} from '@/lib/api/server/registration-ledger'

const DomesticApprovalSchema = z.object({
  product_name: NonEmptyStringSchema,
  certificate_name: z.string().optional(),
  batch_no: z.string().optional(),
  issuing_authority: z.string().optional(),
  issue_date: z.string().optional(),
  valid_until: z.string().optional(),
  product_scope: z.string().optional(),
  quality_standard: z.string().optional(),
  registration_no: z.string().optional(),
})

const OverseasApprovalSchema = DomesticApprovalSchema
const InternationalReviewSchema = z.object({
  product_name: NonEmptyStringSchema,
  approved_countries: z.string().optional(),
  reviewing_countries: z.string().optional(),
})
const CoppCertificateSchema = DomesticApprovalSchema
const WcCertificateSchema = DomesticApprovalSchema

export async function createDomesticApproval(data: unknown): Promise<Record<string, unknown>> {
  const validated = parse(DomesticApprovalSchema, data)
  const result = await createDomesticApprovalApi(validated)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function importDomesticApprovals(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await importDomesticApprovalsApi(formData)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function createOverseasApproval(data: unknown): Promise<Record<string, unknown>> {
  const validated = parse(OverseasApprovalSchema, data)
  const result = await createOverseasApprovalApi(validated)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function importOverseasApprovals(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await importOverseasApprovalsApi(formData)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function createInternationalReview(data: unknown): Promise<Record<string, unknown>> {
  const validated = parse(InternationalReviewSchema, data)
  const result = await createInternationalReviewApi(validated)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function importInternationalReviews(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await importInternationalReviewsApi(formData)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function createCoppCertificate(data: unknown): Promise<Record<string, unknown>> {
  const validated = parse(CoppCertificateSchema, data)
  const result = await createCoppCertificateApi(validated)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function importCoppCertificates(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await importCoppCertificatesApi(formData)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function createWcCertificate(data: unknown): Promise<Record<string, unknown>> {
  const validated = parse(WcCertificateSchema, data)
  const result = await createWcCertificateApi(validated)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}

export async function importWcCertificates(file: File): Promise<Record<string, unknown>> {
  const formData = new FormData()
  formData.append('file', file)
  const result = await importWcCertificatesApi(formData)
  revalidatePath('/registration')
  return result as Record<string, unknown>
}