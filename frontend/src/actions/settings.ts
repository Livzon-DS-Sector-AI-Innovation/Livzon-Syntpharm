'use server'

import { cookies } from 'next/headers'
import type { LLMConfig, LLMConfigFormData, LLMConfigUpdate, FeishuConfig, FeishuConfigUpsert, FeishuDiagnosticResult } from '@/types/settings'
import {
  getLLMConfigs as getLLMConfigsServer,
  getLLMConfig as getLLMConfigServer,
  createLLMConfig as createLLMConfigServer,
  updateLLMConfig as updateLLMConfigServer,
  deleteLLMConfig as deleteLLMConfigServer,
  testLLMConnection as testLLMConnectionServer,
  getLivzonFeishuConfig as getLivzonFeishuConfigServer,
  saveLivzonFeishuConfig as saveLivzonFeishuConfigServer,
  testLivzonFeishuConfig as testLivzonFeishuConfigServer,
  syncLivzonFeishuContacts as syncLivzonFeishuContactsServer,
} from '@/lib/api/server/settings'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

interface ApiResponse<T> {
  code: number
  data: T
  message?: string
}

function wrap<T>(data: unknown): ApiResponse<T> {
  return { code: 0, data: data as T }
}

export async function getLLMConfigs(configType?: string) {
  const token = await getAuthToken()
  return wrap<LLMConfig[]>(await getLLMConfigsServer(configType, token))
}

export async function getLLMConfig(id: string) {
  const token = await getAuthToken()
  return wrap<LLMConfig>(await getLLMConfigServer(id, token))
}

export async function createLLMConfig(data: LLMConfigFormData) {
  const token = await getAuthToken()
  return wrap<LLMConfig>(await createLLMConfigServer(data, token))
}

export async function updateLLMConfig(id: string, data: LLMConfigUpdate) {
  const token = await getAuthToken()
  return wrap<LLMConfig>(await updateLLMConfigServer(id, data, token))
}

export async function deleteLLMConfig(id: string) {
  const token = await getAuthToken()
  return wrap<null>(await deleteLLMConfigServer(id, token))
}

export async function testLLMConnection() {
  const token = await getAuthToken()
  return wrap<{ status: string; detail: string }>(await testLLMConnectionServer(token))
}

export async function getLivzonFeishuConfig() {
  const token = await getAuthToken()
  return await getLivzonFeishuConfigServer(token) as FeishuConfig
}

export async function saveLivzonFeishuConfig(data: FeishuConfigUpsert) {
  const token = await getAuthToken()
  return await saveLivzonFeishuConfigServer(data, token) as FeishuConfig
}

export async function testLivzonFeishuConfig(data?: FeishuConfigUpsert) {
  const token = await getAuthToken()
  return await testLivzonFeishuConfigServer(data, token) as FeishuDiagnosticResult
}

export async function syncLivzonFeishuContacts() {
  const token = await getAuthToken()
  return await syncLivzonFeishuContactsServer(token) as { message?: string; status?: string; departments?: Record<string, unknown>; members?: Record<string, unknown> }
}