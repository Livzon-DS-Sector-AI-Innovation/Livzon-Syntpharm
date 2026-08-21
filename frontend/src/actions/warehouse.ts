'use server'

import { revalidatePath } from 'next/cache'
import { cookies } from 'next/headers'

import type {
  WarehouseFeishuConfigUpsert,
} from '@/types/warehouse'
import {
  saveWarehouseFeishuConfig as saveWarehouseFeishuConfigServer,
  testWarehouseFeishuConfig as testWarehouseFeishuConfigServer,
  refreshWarehouseFeishuTables as refreshWarehouseFeishuTablesServer,
  setWarehouseFeishuTableEnabled as setWarehouseFeishuTableEnabledServer,
  setWarehouseFeishuTablesEnabled as setWarehouseFeishuTablesEnabledServer,
  syncWarehouseFeishuTable as syncWarehouseFeishuTableServer,
  restartWarehouseFeishuWs as restartWarehouseFeishuWsServer,
} from '@/lib/api/server/warehouse'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

export async function saveWarehouseFeishuConfig(
  data: WarehouseFeishuConfigUpsert,
) {
  const token = await getAuthToken()
  const response = await saveWarehouseFeishuConfigServer(token, data)
  revalidatePath('/warehouse/feishu-config')
  return response
}

export async function testWarehouseFeishuConfig(
  data: WarehouseFeishuConfigUpsert,
) {
  const token = await getAuthToken()
  return testWarehouseFeishuConfigServer(token, data)
}

export async function refreshWarehouseFeishuTables() {
  const token = await getAuthToken()
  const response = await refreshWarehouseFeishuTablesServer(token)
  revalidatePath('/warehouse/feishu-config')
  revalidatePath('/warehouse/raw-material')
  revalidatePath('/warehouse/packaging')
  revalidatePath('/warehouse/product')
  return response
}

export async function setWarehouseFeishuTableEnabled(
  tableId: string,
  isEnabled: boolean,
) {
  const token = await getAuthToken()
  const response = await setWarehouseFeishuTableEnabledServer(token, tableId, isEnabled)
  revalidatePath('/warehouse/feishu-config')
  revalidatePath('/warehouse/raw-material')
  revalidatePath('/warehouse/packaging')
  revalidatePath('/warehouse/product')
  return response
}

export async function setWarehouseFeishuTablesEnabled(
  tableIds: string[],
  isEnabled: boolean,
) {
  const token = await getAuthToken()
  const response = await setWarehouseFeishuTablesEnabledServer(token, tableIds, isEnabled)
  revalidatePath('/warehouse/feishu-config')
  revalidatePath('/warehouse/raw-material')
  revalidatePath('/warehouse/packaging')
  revalidatePath('/warehouse/product')
  return response
}

export async function syncWarehouseFeishuTable(tableId: string) {
  const token = await getAuthToken()
  const response = await syncWarehouseFeishuTableServer(token, tableId)
  revalidatePath('/warehouse/feishu-config')
  revalidatePath('/warehouse/raw-material')
  revalidatePath('/warehouse/packaging')
  revalidatePath('/warehouse/product')
  return response
}

export async function restartWarehouseFeishuWs() {
  const token = await getAuthToken()
  return restartWarehouseFeishuWsServer(token)
}