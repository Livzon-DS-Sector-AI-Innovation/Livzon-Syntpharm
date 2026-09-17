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

export async function createProduct(data: ProductCreateInput) {
  const result = await createProductApi(data)
  revalidatePath('/production/products')
  return result
}

export async function updateProduct(id: string, data: ProductUpdateInput) {
  const result = await updateProductApi(id, data)
  revalidatePath('/production/products')
  return result
}

export async function deleteProduct(id: string) {
  const result = await deleteProductApi(id)
  revalidatePath('/production/products')
  return result
}

export async function getProducts(): Promise<any> {
  return getProductsApi()
}

export async function getProductsByWorkshop(workshop: string): Promise<any> {
  return getProductsByWorkshopApi(workshop)
}

export async function getProduct(productId: string): Promise<any> {
  return getProductApi(productId)
}

export async function createWorkshopProduct(data: WorkshopProductCreate): Promise<any> {
  return createWorkshopProductApi(data)
}

export async function syncProductsFromFeishu(): Promise<{
  code: number
  message: string
  data: { created: number; updated: number; failed: number; total: number }
}> {
  const result = await syncProductsFromFeishuApi()
  revalidatePath('/product')
  return result
}

export async function syncProductToFeishu(id: string): Promise<{
  code: number
  message: string
  data: { feishu_record_id: string }
}> {
  const result = await syncProductToFeishuApi(id)
  revalidatePath('/product')
  return result
}