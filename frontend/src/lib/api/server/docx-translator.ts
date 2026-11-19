/** 文档翻译 —— 服务端请求（Server Action 用） */

import type { DocxGlossaryTerm } from '@/types/docx-translator'
import { apiFetch, getApiBaseUrl, unwrapResponse } from './base'

const A = (path: string) => `${getApiBaseUrl()}/api/v1/registration/docx-translator${path}`

type Envelope<T> = { code: number; data?: T | null; message?: string; meta?: unknown }

const auth = (token?: string) => (token ? { headers: { Authorization: `Bearer ${token}` } } : {})

export async function createGlossaryTermApi(
  token: string | undefined,
  payload: { term_en: string; term_zh: string; is_enabled: boolean }
) {
  return unwrapResponse(
    await apiFetch<Envelope<DocxGlossaryTerm>>(A('/glossary'), {
      method: 'POST',
      body: JSON.stringify(payload),
      ...auth(token),
    })
  )
}

export async function updateGlossaryTermApi(
  token: string | undefined,
  termId: string,
  payload: { term_en?: string; term_zh?: string; is_enabled?: boolean }
) {
  return unwrapResponse(
    await apiFetch<Envelope<DocxGlossaryTerm>>(A(`/glossary/${termId}`), {
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
    await apiFetch<Envelope<{ job_id: string; status: 'running' }>>(A(`/tasks/${taskId}/retranslate`), {
      method: 'POST',
      ...auth(token),
    })
  )
}
