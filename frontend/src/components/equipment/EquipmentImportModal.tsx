'use client'

import { useState } from 'react'
import { Modal, Upload, Button, App, Steps } from 'antd'
import { InboxOutlined, CheckCircleOutlined } from '@ant-design/icons'
import * as XLSX from 'xlsx'
import { previewEquipmentImport, batchImportEquipment } from '@/actions/equipment'
import { ForceOverrideToggle } from './ForceOverrideToggle'
import { ImportCockpit } from './ImportCockpit'

const { Dragger } = Upload

interface ImportPreviewItem {
  row_index: number
  asset_no: string
  label_no?: string
  name: string
  equipment_class: string
  category_description?: string
  manufacturer?: string
  model?: string
  current_cost?: number
  book_value?: number
  commissioning_date?: string
  status?: string
  responsible_person_name?: string
  department_name?: string
  location_text?: string
  validation_status: 'pass' | 'error' | 'duplicate'
  error_message?: string
  is_duplicate?: boolean
}

interface ImportResult {
  batch_id: string
  created_count: number
  updated_count: number
  skipped_count: number
  error_count: number
  unmapped_departments?: Record<string, number[]>
  errors?: Array<{ row: number; error: string }>
}

interface EquipmentImportModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

function normalizeCellValue(value: unknown): unknown {
  if (value instanceof Date && !Number.isNaN(value.getTime())) {
    const y = value.getFullYear()
    const m = String(value.getMonth() + 1).padStart(2, '0')
    const d = String(value.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }
  return value
}

export function EquipmentImportModal({ open, onClose, onSuccess }: EquipmentImportModalProps) {
  const { message } = App.useApp()
  const [currentStep, setCurrentStep] = useState(0)
  const [rawData, setRawData] = useState<any[]>([])
  const [previewData, setPreviewData] = useState<ImportPreviewItem[]>([])
  const [previewHeaders, setPreviewHeaders] = useState<any[]>([])
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [forceOverride, setForceOverride] = useState(false)

  const resetState = () => {
    setCurrentStep(0)
    setRawData([])
    setPreviewData([])
    setImportResult(null)
    setLoading(false)
    setForceOverride(false)
  }

  const handleClose = () => {
    resetState()
    onClose()
  }

  const handleFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer)
        const workbook = XLSX.read(data, { type: 'array', cellDates: true })
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
        const jsonData = XLSX.utils.sheet_to_json(firstSheet, { defval: null })
        
        const normalized = jsonData.map(row => {
          const normalizedRow: any = {}
          for (const [key, value] of Object.entries(row as Record<string, unknown>)) {
            normalizedRow[key] = normalizeCellValue(value)
          }
          return normalizedRow
        })
        
        setRawData(normalized)
        setCurrentStep(1)
        fetchPreview(normalized)
      } catch (err) {
        message.error('Excel 解析失败')
        setCurrentStep(0)
      }
    }
    reader.readAsArrayBuffer(file)
    return false
  }

  const fetchPreview = async (data: any[]) => {
    setLoading(true)
    try {
      const result = await previewEquipmentImport(data, forceOverride)
      if (result.code === 200) {
        setPreviewData(result.data.items);
        setPreviewHeaders(result.data.headers || []);
        setCurrentStep(2)
      } else {
        message.error(result.message || '预览失败')
        setCurrentStep(0)
      }
    } catch (err) {
      message.error('预览请求失败')
      setCurrentStep(0)
    } finally {
      setLoading(false)
    }
  }

  const handleImport = async () => {
    setLoading(true)
    try {
      const result = await batchImportEquipment(rawData, forceOverride)
      if (result.code === 200) {
        setImportResult(result.data)
        setCurrentStep(3)
        message.success(`成功导入 ${result.data.created_count} 条记录`)
        onSuccess()
      } else {
        message.error(result.message || '导入失败')
      }
    } catch (err) {
      message.error('导入请求失败')
    } finally {
      setLoading(false)
    }
  }

  const validCount = previewData.filter(item => item.validation_status === 'pass').length
  const invalidCount = previewData.filter(item => item.validation_status === 'error').length
  const duplicateCount = previewData.filter(item => item.validation_status === 'duplicate').length

  const steps = [
    { title: '上传文件' },
    { title: '解析数据' },
    { title: '预览确认' },
    { title: '导入完成' },
  ]

  return (
    <Modal
      title="批量导入设备"
      open={open}
      onCancel={handleClose}
      width={900}
      footer={
        currentStep === 2 ? (
          <div>
            <div style={{ marginBottom: 8, fontSize: 12, color: '#78716C' }}>
              数据导入按：<strong>资产编号 + 部门 + 位置</strong> 匹配已有记录。
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Button onClick={() => setCurrentStep(0)}>重新上传</Button>
              <div>
                <Button onClick={handleClose}>取消</Button>
                <Button 
                  type="primary" 
                  onClick={handleImport} 
                  loading={loading}
                  disabled={validCount === 0}
                >
                  确认导入 ({validCount} 条)
                </Button>
              </div>
            </div>
          </div>
        ) : currentStep === 3 ? (
          <Button type="primary" onClick={handleClose}>完成</Button>
        ) : null
      }
    >
      <Steps current={currentStep} items={steps} style={{ marginBottom: 24 }} />

      {currentStep === 0 && (
        <Dragger
          accept=".xlsx,.xls"
          beforeUpload={handleFileUpload}
          showUploadList={false}
          style={{ padding: '40px 0' }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">点击或拖拽 Excel 文件到此处上传</p>
          <p className="ant-upload-hint">支持 .xlsx 和 .xls 格式</p>
        </Dragger>
      )}

      {currentStep === 1 && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <p>正在解析数据...</p>
        </div>
      )}

      {currentStep === 2 && (
        <div>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <span>总计: <strong>{previewData.length}</strong> 条</span>
              <span style={{ color: '#10b981' }}>可导入: <strong>{validCount}</strong> 条</span>
              {invalidCount > 0 && (
                <span style={{ color: '#ef4444' }}>异常: <strong>{invalidCount}</strong> 条</span>
              )}
              {duplicateCount > 0 && (
                <span style={{ color: '#f59e0b' }}>重复: <strong>{duplicateCount}</strong> 条</span>
              )}
            </div>
            <ForceOverrideToggle enabled={forceOverride} onToggle={setForceOverride} />
          </div>
          <ImportCockpit 
            data={previewData} 
            headers={previewHeaders} 
          />
        </div>
      )}

      {currentStep === 3 && importResult && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <CheckCircleOutlined style={{ fontSize: 64, color: '#10b981', marginBottom: 24 }} />
          <div style={{ 
            background: '#f5f5f5', 
            borderRadius: 8, 
            padding: 24, 
            marginTop: 16,
            textAlign: 'left',
          }}>
            <div style={{ marginBottom: 12 }}>
              <strong>导入结果：</strong>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div>
                <span style={{ color: '#10b981' }}>✓ 新增：</span>
                <strong>{importResult.created_count}</strong> 条
              </div>
              <div>
                <span style={{ color: '#0075de' }}>↻ 更新：</span>
                <strong>{importResult.updated_count}</strong> 条
              </div>
              <div>
                <span style={{ color: '#78716C' }}>⊘ 跳过：</span>
                <strong>{importResult.skipped_count}</strong> 条
              </div>
              <div>
                <span style={{ color: '#ef4444' }}>✗ 失败：</span>
                <strong>{importResult.error_count}</strong> 条
              </div>
            </div>
            {importResult.errors && importResult.errors.length > 0 && (
              <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e5e3df' }}>
                <strong style={{ color: '#ef4444' }}>错误详情：</strong>
                <div style={{ marginTop: 8, maxHeight: 200, overflow: 'auto' }}>
                  {importResult.errors.map((err, idx) => (
                    <div key={idx} style={{ fontSize: 12, color: '#5d5b54', marginBottom: 4 }}>
                      行 {err.row}: {err.error}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </Modal>
  )
}
