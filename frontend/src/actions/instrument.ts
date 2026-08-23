'use server'

import { revalidatePath } from 'next/cache'
import type {
  InstrumentCreate,
  InstrumentUpdate,
  InstrumentFilter,
  CalibrationRuleCreate,
  CalibrationRuleUpdate,
  CalibrationRecordCreate,
  CalibrationRecordUpdate,
  CalibrationRecordFilter,
  ApprovalCreate,
  ReminderConfigCreate,
  ReminderConfigUpdate,
} from '@/types/instrument'
import {
  getInstruments as fetchInstruments,
  getInstrument as fetchInstrument,
  createInstrument as apiCreateInstrument,
  updateInstrument as apiUpdateInstrument,
  deleteInstrument as apiDeleteInstrument,
  deactivateInstrument as apiDeactivateInstrument,
  getOverdueInstruments as apiGetOverdueInstruments,
  getUpcomingCalibrations as apiGetUpcomingCalibrations,
  getCalibrationRules as apiGetCalibrationRules,
  getCalibrationRule as apiGetCalibrationRule,
  createCalibrationRule as apiCreateCalibrationRule,
  updateCalibrationRule as apiUpdateCalibrationRule,
  deleteCalibrationRule as apiDeleteCalibrationRule,
  getCalibrationRecords as apiGetCalibrationRecords,
  getCalibrationRecord as apiGetCalibrationRecord,
  createCalibrationRecord as apiCreateCalibrationRecord,
  updateCalibrationRecord as apiUpdateCalibrationRecord,
  deleteCalibrationRecord as apiDeleteCalibrationRecord,
  submitCalibrationRecord as apiSubmitCalibrationRecord,
  approveCalibrationRecordByAdmin as apiApproveCalibrationRecordByAdmin,
  approveCalibrationRecordByQA as apiApproveCalibrationRecordByQA,
  rejectCalibrationRecord as apiRejectCalibrationRecord,
  getInstrumentApprovals as apiGetInstrumentApprovals,
  getCalibrationRecordApprovals as apiGetCalibrationRecordApprovals,
  approveInstrument as apiApproveInstrument,
  approveCalibrationRecord as apiApproveCalibrationRecord,
  recognizeInstrumentLabel as apiRecognizeInstrumentLabel,
  getUpcomingCalibrationRecords as apiGetUpcomingCalibrationRecords,
  getRecordsForReminder as apiGetRecordsForReminder,
  sendCalibrationReminder as apiSendCalibrationReminder,
  getReminderConfigs as apiGetReminderConfigs,
  createReminderConfig as apiCreateReminderConfig,
  updateReminderConfig as apiUpdateReminderConfig,
  deleteReminderConfig as apiDeleteReminderConfig,
  autoTriggerReminders as apiAutoTriggerReminders,
  resolveFeishuUser as apiResolveFeishuUser,
  getFeishuContactUsers as apiGetFeishuContactUsers,
  getFeishuContactDepartments as apiGetFeishuContactDepartments,
} from '@/lib/api/server/instrument'

export async function getInstruments(params: InstrumentFilter = {}) {
  return fetchInstruments(params) as any
}

export async function getInstrument(id: string) {
  return fetchInstrument(id) as any
}

export async function createInstrument(data: InstrumentCreate) {
  const response = await apiCreateInstrument(data)
  revalidatePath('/quality/instrument')
  return response
}

export async function updateInstrument(id: string, data: InstrumentUpdate) {
  const response = await apiUpdateInstrument(id, data)
  revalidatePath('/quality/instrument')
  return response
}

export async function deleteInstrument(id: string) {
  const response = await apiDeleteInstrument(id)
  revalidatePath('/quality/instrument')
  return response
}

export async function deactivateInstrument(id: string, reason: string) {
  const response = await apiDeactivateInstrument(id, reason)
  revalidatePath('/quality/instrument')
  return response
}

export async function getOverdueInstruments() {
  return apiGetOverdueInstruments()
}

export async function getUpcomingCalibrations(days: number = 30) {
  return apiGetUpcomingCalibrations(days)
}

export async function getCalibrationRules(instrumentId?: string) {
  return apiGetCalibrationRules(instrumentId)
}

export async function getCalibrationRule(id: string) {
  return apiGetCalibrationRule(id)
}

export async function createCalibrationRule(data: CalibrationRuleCreate) {
  const response = await apiCreateCalibrationRule(data)
  revalidatePath('/quality/instrument')
  return response
}

export async function updateCalibrationRule(id: string, data: CalibrationRuleUpdate) {
  const response = await apiUpdateCalibrationRule(id, data)
  revalidatePath('/quality/instrument')
  return response
}

export async function deleteCalibrationRule(id: string) {
  const response = await apiDeleteCalibrationRule(id)
  revalidatePath('/quality/instrument')
  return response
}

export async function getCalibrationRecords(params: CalibrationRecordFilter = {}) {
  return apiGetCalibrationRecords(params)
}

export async function getCalibrationRecord(id: string) {
  return apiGetCalibrationRecord(id)
}

export async function createCalibrationRecord(data: CalibrationRecordCreate) {
  const response = await apiCreateCalibrationRecord(data)
  revalidatePath('/quality/instrument')
  return response
}

export async function updateCalibrationRecord(id: string, data: CalibrationRecordUpdate) {
  const response = await apiUpdateCalibrationRecord(id, data)
  revalidatePath('/quality/instrument')
  return response
}

export async function deleteCalibrationRecord(id: string) {
  const response = await apiDeleteCalibrationRecord(id)
  revalidatePath('/quality/instrument')
  return response
}

export async function submitCalibrationRecord(id: string) {
  const response = await apiSubmitCalibrationRecord(id)
  revalidatePath('/quality/instrument')
  return response
}

export async function approveCalibrationRecordByAdmin(id: string) {
  const response = await apiApproveCalibrationRecordByAdmin(id)
  revalidatePath('/quality/instrument')
  return response
}

export async function approveCalibrationRecordByQA(id: string) {
  const response = await apiApproveCalibrationRecordByQA(id)
  revalidatePath('/quality/instrument')
  return response
}

export async function rejectCalibrationRecord(id: string, comments: string) {
  const response = await apiRejectCalibrationRecord(id, comments)
  revalidatePath('/quality/instrument')
  return response
}

export async function getInstrumentApprovals(instrumentId: string) {
  return apiGetInstrumentApprovals(instrumentId)
}

export async function getCalibrationRecordApprovals(recordId: string) {
  return apiGetCalibrationRecordApprovals(recordId)
}

export async function approveInstrument(id: string, data: ApprovalCreate) {
  const response = await apiApproveInstrument(id, data)
  revalidatePath('/quality/instrument')
  return response
}

export async function approveCalibrationRecord(id: string, data: ApprovalCreate) {
  const response = await apiApproveCalibrationRecord(id, data)
  revalidatePath('/quality/instrument')
  return response
}

export async function recognizeInstrumentLabel(file: File) {
  return apiRecognizeInstrumentLabel(file)
}

export async function getUpcomingCalibrationRecords(days: number = 30) {
  return apiGetUpcomingCalibrationRecords(days)
}

export async function getRecordsForReminder(days: number = 30) {
  return apiGetRecordsForReminder(days)
}

export async function sendCalibrationReminder(
  chatId: string,
  receiveIdType: 'chat_id' | 'open_id' = 'chat_id',
  days: number = 30,
  feishuAppId?: string,
  feishuAppSecret?: string
) {
  return apiSendCalibrationReminder(chatId, receiveIdType, days, feishuAppId, feishuAppSecret)
}

export async function getReminderConfigs() {
  return apiGetReminderConfigs()
}

export async function createReminderConfig(data: ReminderConfigCreate) {
  return apiCreateReminderConfig(data)
}

export async function updateReminderConfig(id: string, data: ReminderConfigUpdate) {
  return apiUpdateReminderConfig(id, data)
}

export async function deleteReminderConfig(id: string) {
  return apiDeleteReminderConfig(id)
}

export async function autoTriggerReminders() {
  return apiAutoTriggerReminders()
}

export async function resolveFeishuUser(mobile?: string, email?: string) {
  return apiResolveFeishuUser(mobile, email)
}

export async function getFeishuContactUsers(departmentId: string = '0') {
  return apiGetFeishuContactUsers(departmentId)
}

export async function getFeishuContactDepartments(parentDepartmentId: string = '0') {
  return apiGetFeishuContactDepartments(parentDepartmentId)
}