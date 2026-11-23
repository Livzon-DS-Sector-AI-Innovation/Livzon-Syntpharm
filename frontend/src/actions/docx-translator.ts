'use server'

import { cookies } from 'next/headers'

import type { components } from '@/types/generated/schema'
import {
  createGlossaryTermApi,
  deleteGlossaryTermApi,
  deleteTranslationFileApi,
  retranslateTaskApi,
  updateGlossaryTermApi,
} from '@/lib/api/server/docx-translator'

type Schemas = components['schemas']

async function getAuthToken() {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

export async function createGlossaryTerm(payload: Schemas['DocxGlossaryTermCreate']) {
  return createGlossaryTermApi(await getAuthToken(), payload)
}

export async function updateGlossaryTerm(termId: string, payload: Schemas['DocxGlossaryTermUpdate']) {
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
