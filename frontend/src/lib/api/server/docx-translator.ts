/** 文档翻译 —— 服务端请求（Server Action 用） */

import type { components } from '@/types/generated/schema'
import { apiFetch, getApiBaseUrl, unwrapResponse } from './base'

type Schemas = components['schemas']

const A = (path: string) => `${getApiBaseUrl()}/api/v1/registration/docx-translator${path}`

type Envelope<T> = { code: number; data?: T | null; message?: string; meta?: unknown }

const auth = (token?: string) => (token ? { headers: { Authorization: `Bearer ${token}` } } : {})

export async function createGlossaryTermApi(
  token: string | undefined,
  payload: Schemas['DocxGlossaryTermCreate']
) {
  return unwrapResponse(
    await apiFetch<Envelope<Schemas['DocxGlossaryTermResponse']>>(A('/glossary'), {
      method: 'POST',
      body: JSON.stringify(payload),
      ...auth(token),
    })
  )
}

export async function updateGlossaryTermApi(
  token: string | undefined,
  termId: string,
  payload: Schemas['DocxGlossaryTermUpdate']
) {
  return unwrapResponse(
    await apiFetch<Envelope<Schemas['DocxGlossaryTermResponse']>>(A(`/glossary/${termId}`), {
      method: 'PUT',
      body: JSON.stringify(payload),
      ...auth(token),
    })
  )
}

export async function deleteGlossaryTermApi(token: string | undefined, termId: string) {
  return unwrapResponse(
    await apiFetch<Envelope<null>>(A(`/glossary/${termId}`), {
      method: 'DELETE',
      ...auth(token),
    })
  )
}

export async function deleteTranslationFileApi(token: string | undefined, fileId: string) {
  return unwrapResponse(
    await apiFetch<Envelope<null>>(A(`/files/${fileId}`), {
      method: 'DELETE',
      ...auth(token),
    })
  )
}


export async function retranslateTaskApi(token: string | undefined, taskId: string) {
  return unwrapResponse(
    await apiFetch<Envelope<Schemas['DocxTranslationJobAccepted']>>(A(`/tasks/${taskId}/retranslate`), {
      method: 'POST',
      ...auth(token),
    })
  )
}
