'use server'

import { cookies } from 'next/headers'
import {
  createGlossaryTermApi,
  deleteGlossaryTermApi,
  deleteTranslationFileApi,
  retranslateTaskApi,
  updateGlossaryTermApi,
} from '@/lib/api/server/docx-translator'

async function getAuthToken() {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

export async function createGlossaryTerm(payload: { term_en: string; term_zh: string; is_enabled: boolean }) {
  return createGlossaryTermApi(await getAuthToken(), payload)
}

export async function updateGlossaryTerm(
  termId: string,
  payload: { term_en?: string; term_zh?: string; is_enabled?: boolean }
) {
  return updateGlossaryTermApi(await getAuthToken(), termId, payload)
}

export async function deleteGlossaryTerm(termId: string) {
  return deleteGlossaryTermApi(await getAuthToken(), termId)
}

export async function deleteTranslationFile(fileId: string) {
  return deleteTranslationFileApi(await getAuthToken(), fileId)
}


export async function retranslateTranslationTask(taskId: string) {
  return retranslateTaskApi(await getAuthToken(), taskId)
}
