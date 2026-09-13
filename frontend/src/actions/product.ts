'use server'

import { revalidatePath } from 'next/cache'
import type { WorkshopProductCreate } from '@/types/workshop-product'
import { ProductCreateInput, ProductUpdateInput } from '@/types/product'
import {
  createProduct as createProductApi,
  updateProduct as updateProductApi,
  deleteProduct as deleteProductApi,
  getProducts as getProductsApi,
  getProductsByWorkshop as getProductsByWorkshopApi,
  getProduct as getProductApi,
  createWorkshopProduct as createWorkshopProductApi,
  syncProductsFromFeishu as syncProductsFromFeishuApi,
  syncProductToFeishu as syncProductToFeishuApi,
} from '@/lib/api/server/product'

export async function createProduct(data: ProductCreateInput): Promise<Record<string, unknown>> {
  const result = await createProductApi(data)
  revalidatePath('/production/products')
  return result as Record<string, unknown>
}

export async function updateProduct(id: string, data: ProductUpdateInput): Promise<Record<string, unknown>> {
  const result = await updateProductApi(id, data)
  revalidatePath('/production/products')
  return result as Record<string, unknown>
}

export async function deleteProduct(id: string): Promise<Record<string, unknown>> {
  const result = await deleteProductApi(id)
  revalidatePath('/production/products')
  return result as Record<string, unknown>
}

export async function getProducts(): Promise<Record<string, unknown>> {
  return getProductsApi() as Promise<Record<string, unknown>>
}

export async function getProductsByWorkshop(workshop: string): Promise<Record<string, unknown>> {
  return getProductsByWorkshopApi(workshop) as Promise<Record<string, unknown>>
}

export async function getProduct(productId: string): Promise<Record<string, unknown>> {
  return getProductApi(productId) as Promise<Record<string, unknown>>
}

export async function createWorkshopProduct(data: WorkshopProductCreate): Promise<Record<string, unknown>> {
  return createWorkshopProductApi(data) as Promise<Record<string, unknown>>
}

export async function syncProductsFromFeishu(): Promise<{
  code: number
  message: string
  data: { created: number; updated: number; failed: number; total: number }
}> {
  const result = await syncProductsFromFeishuApi()
  revalidatePath('/product')
  return result as {
    code: number
    message: string
    data: { created: number; updated: number; failed: number; total: number }
  }
}

export async function syncProductToFeishu(id: string): Promise<{
  code: number
  message: string
  data: { feishu_record_id: string }
}> {
  const result = await syncProductToFeishuApi(id)
  revalidatePath('/product')
  return result as {
    code: number
    message: string
    data: { feishu_record_id: string }
  }
}
