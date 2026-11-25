'use server'

import { revalidatePath } from 'next/cache'
import {
  AuthorizationLetterCreateInput,
  AuthorizationLetterFilterOptions,
  AuthorizationLetterListItem,
  ParseCOAResponse,
  ProductInfo,
  ProjectKpi,
  ProjectProgressLog,
  ReferenceStandardListItem,
  RegistrationProject,
} from '@/types/registration'
import type { components } from '@/types/generated/schema'
import type { ApiResponse, MessageResponse } from '@/types/common'
import type { PageResult } from '@/lib/api/page'

import {
  generateAuthorizationLetter as generateAuthorizationLetterApi,
  deleteAuthorizationLetter as deleteAuthorizationLetterApi,
  generateReferenceStandard as generateReferenceStandardApi,
  deleteReferenceStandard as deleteReferenceStandardApi,
  fetchAuthorizationLetters as fetchAuthorizationLettersApi,
  fetchAuthorizationLetterFilterOptions as fetchAuthorizationLetterFilterOptionsApi,
  fetchRegistrationProducts as fetchRegistrationProductsApi,
  fetchRegistrationProjects as fetchRegistrationProjectsApi,
  fetchReferenceStandards as fetchReferenceStandardsApi,
  createDrug as createDrugApi,
  updateDrug as updateDrugApi,
  deleteDrug as deleteDrugApi,
  parseCOA as parseCOAApi,
  createRegistrationProject as createRegistrationProjectApi,
  updateRegistrationProject as updateRegistrationProjectApi,
  deleteRegistrationProject as deleteRegistrationProjectApi,
  fetchProjectKpi as fetchProjectKpiApi,
  fetchProjectLogs as fetchProjectLogsApi,
  advanceProjectStage as advanceProjectStageApi,
  addProjectLog as addProjectLogApi,
} from '@/lib/api/server/registration'

type DrugCreate = components['schemas']['DrugCreate']
type DrugUpdate = components['schemas']['DrugUpdate']
type AuthorizationLetterData = components['schemas']['AuthorizationLetterResponse']
type ReferenceStandardData = components['schemas']['ReferenceStandardResponse']
type DrugData = components['schemas']['DrugWithNodesResponse']
type ProjectData = components['schemas']['ProjectResponse']

export async function generateAuthorizationLetter(
  formData: FormData,
  data: AuthorizationLetterCreateInput
): Promise<{ success: boolean; message: string; data?: AuthorizationLetterData }> {
  try {
    const submitData = new FormData()
    const template = formData.get('template')
    if (template instanceof File) {
      submitData.append('template', template)
    }
    const variant = formData.get('template_variant')
    if (typeof variant === 'string' && variant) {
      submitData.append('template_variant', variant)
    }
    submitData.append('product_name', data.product_name)
    submitData.append('registration_number', data.registration_number)
    submitData.append('preparation_unit', data.preparation_unit)
    submitData.append('preparation_name', data.preparation_name)
    submitData.append('administration_route', data.administration_route)
    if (data.remarks) {
      submitData.append('remarks', data.remarks)
    }
    const replacements = formData.get('replacements')
    if (replacements) {
      submitData.append('replacements', replacements as string)
    }

    const dataPayload = (await generateAuthorizationLetterApi(submitData)) as AuthorizationLetterData
    revalidatePath('/registration')
    return {
      success: true,
      message: '授权书生成成功',
      data: dataPayload,
    }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '生成授权书失败',
    }
  }
}

export async function deleteAuthorizationLetter(id: string): Promise<MessageResponse> {
  const result = (await deleteAuthorizationLetterApi(id)) as MessageResponse
  revalidatePath('/registration')
  return result
}

export async function generateReferenceStandard(
  formData: FormData,
  data: {
    drug_name: string
    reference_substance_name?: string
    batch_number?: string
    manufacturer?: string
    english_name?: string
    molecular_formula?: string
    molecular_weight?: string
    cas_number?: string
    content?: string
    moisture?: string
    rsd?: string
    expiration_date?: string
    storage_condition?: string
    remarks?: string
  }
): Promise<{ success: boolean; message: string; data?: ReferenceStandardData }> {
  try {
    const submitData = new FormData()
    submitData.append('coa', formData.get('coa') as File)
    submitData.append('drug_name', data.drug_name)
    
    if (data.reference_substance_name) submitData.append('reference_substance_name', data.reference_substance_name)
    if (data.batch_number) submitData.append('batch_number', data.batch_number)
    if (data.manufacturer) submitData.append('manufacturer', data.manufacturer)
    if (data.english_name) submitData.append('english_name', data.english_name)
    if (data.molecular_formula) submitData.append('molecular_formula', data.molecular_formula)
    if (data.molecular_weight) submitData.append('molecular_weight', data.molecular_weight)
    if (data.cas_number) submitData.append('cas_number', data.cas_number)
    if (data.content) submitData.append('content', data.content)
    if (data.moisture) submitData.append('moisture', data.moisture)
    if (data.rsd) submitData.append('rsd', data.rsd)
    if (data.expiration_date) submitData.append('expiration_date', data.expiration_date)
    if (data.storage_condition) submitData.append('storage_condition', data.storage_condition)
    if (data.remarks) submitData.append('remarks', data.remarks)

    const dataPayload = (await generateReferenceStandardApi(submitData)) as ReferenceStandardData
    revalidatePath('/registration')
    return {
      success: true,
      message: '对照物质说明表生成成功',
      data: dataPayload,
    }
  } catch (error) {
    return {
      success: false,
      message: error instanceof Error ? error.message : '生成对照物质说明表失败',
    }
  }
}

export async function deleteReferenceStandardAction(id: string): Promise<MessageResponse> {
  const result = (await deleteReferenceStandardApi(id)) as MessageResponse
  revalidatePath('/registration')
  return result
}

export async function fetchAuthorizationLettersServer(
  params: { page: number; page_size: number; keyword?: string; product_name?: string; year?: number }
): Promise<PageResult<AuthorizationLetterListItem>> {
  return fetchAuthorizationLettersApi(params)
}

export async function fetchAuthorizationLetterFilterOptionsServer(): Promise<AuthorizationLetterFilterOptions> {
  return fetchAuthorizationLetterFilterOptionsApi()
}

export async function fetchProductsServer(): Promise<ProductInfo[]> {
  return fetchRegistrationProductsApi()
}

export async function fetchRegistrationProjectsServer(params?: {
  search?: string
  registration_type?: string
  status?: string
}): Promise<RegistrationProject[]> {
  return fetchRegistrationProjectsApi(params)
}

export async function fetchProjectKpiServer(): Promise<ProjectKpi> {
  return fetchProjectKpiApi()
}

export async function fetchProjectLogsServer(projectId: string): Promise<ProjectProgressLog[]> {
  return fetchProjectLogsApi(projectId)
}

export async function fetchReferenceStandardsServer(
  params: { page: number; page_size: number }
): Promise<PageResult<ReferenceStandardListItem>> {
  return fetchReferenceStandardsApi(params)
}

export async function createDrug(data: DrugCreate): Promise<ApiResponse<DrugData>> {
  const result = (await createDrugApi(data)) as ApiResponse<DrugData>
  revalidatePath('/registration/review')
  return result
}

export async function updateDrug(id: string, data: DrugUpdate): Promise<ApiResponse<DrugData>> {
  const result = (await updateDrugApi(id, data)) as ApiResponse<DrugData>
  revalidatePath('/registration/review')
  return result
}

export async function deleteDrug(id: string): Promise<MessageResponse> {
  const result = (await deleteDrugApi(id)) as MessageResponse
  revalidatePath('/registration/review')
  return result
}

export async function parseCOA(file: File): Promise<ParseCOAResponse> {
  return parseCOAApi(file)
}

export async function createRegistrationProject(
  data: components['schemas']['ProjectCreate']
): Promise<ApiResponse<ProjectData>> {
  const result = (await createRegistrationProjectApi(data)) as ApiResponse<ProjectData>
  revalidatePath('/registration')
  return result
}

export async function updateRegistrationProject(
  id: string,
  data: components['schemas']['ProjectUpdate']
): Promise<ApiResponse<ProjectData>> {
  const result = (await updateRegistrationProjectApi(id, data)) as ApiResponse<ProjectData>
  revalidatePath('/registration')
  return result
}

export async function deleteRegistrationProject(id: string): Promise<MessageResponse> {
  const result = (await deleteRegistrationProjectApi(id)) as MessageResponse
  revalidatePath('/registration')
  return result
}

/** 推进申报前阶段（受理为界；触发状态流转并由后端自动写 system 进展记录） */
export async function advanceProjectStage(
  id: string,
  stage: string
): Promise<{ success: boolean; message: string; data?: ProjectData }> {
  try {
    const dataPayload = (await advanceProjectStageApi(id, stage)) as ProjectData
    revalidatePath('/registration/projects')
    return { success: true, message: '阶段已更新', data: dataPayload }
  } catch (error) {
    return { success: false, message: error instanceof Error ? error.message : '阶段推进失败' }
  }
}

/** 添加手动进展记录（自动带时间与当前登录人；记录只增不删） */
export async function addProjectProgressLog(
  id: string,
  content: string
): Promise<{ success: boolean; message: string; data?: components['schemas']['ProgressLogResponse'] }> {
  try {
    const dataPayload = (await addProjectLogApi(id, content)) as components['schemas']['ProgressLogResponse']
    revalidatePath('/registration/projects')
    return { success: true, message: '记录已添加', data: dataPayload }
  } catch (error) {
    return { success: false, message: error instanceof Error ? error.message : '添加记录失败' }
  }
}
