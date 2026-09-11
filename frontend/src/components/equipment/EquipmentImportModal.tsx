'use client'

import { useState } from 'react'
import { Checkbox } from 'antd'
import { Modal, Upload, Button, Table, Tag, App, Steps } from 'antd'
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
  department_name?: string
  department_id?: string
  location_text?: string
  status: string
  scrap_status?: string
  scrap_time?: string
  // v3 契约：错误数组（后端 v4 不再返回该字段，故改为可选）
  validation_errors?: string[]
  // v4 契约：校验三态 pass / error / duplicate
  validation_status?: string
  // v4 契约：错误描述，字符串而非数组
  error_message?: string | null
  is_duplicate?: boolean
}

interface ImportResult {
  created_count: number
  skipped_count: number
  // v4 /batch 实际返回：batch_id / created_count / updated_count / skipped_count /
  // error_count / unmapped_departments —— 注意并不返回 errors 明细数组
  batch_id?: string
  updated_count?: number
  error_count?: number
  unmapped_departments?: Record<string, number[]>
  errors?: Array<{ row: number; error: string }>
}

interface EquipmentImportModalProps {
  open: boolean
  onClose: () => void
  onSuccess: () => void
}

// Excel 单元格值归一化：cellDates=true 后日期会变成 Date 对象，
// 需统一格式化为 YYYY-MM-DD，否则会像序列号 46196 那样直接进入数据库。
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
  }

  const handleClose = () => {
    resetState()
    onClose()
  }

  // 解析 Excel 文件
  const handleFileUpload = (file: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target?.result as ArrayBuffer)
        // cellDates: true —— 让日期单元格解析为 Date 对象而非序列号（如 46196）
        const workbook = XLSX.read(data, { type: 'array', cellDates: true })
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]]
        
        // 将 sheet 转换为数组（包含所有行）
        const sheetData = XLSX.utils.sheet_to_json(firstSheet, { header: 1 }) as any[][]
        

        
        // 从表头行开始解析
        // Smart Header Detection: Look for "资产编号" in the first 10 rows
        let headerRowIndex = 0
        for (let i = 0; i < Math.min(sheetData.length, 10); i++) {
            const row = sheetData[i] as any[]
            if (row && row.some((cell: any) => String(cell).trim() === '资产编号' || String(cell).trim() === 'Asset No')) {
                headerRowIndex = i
                break
            }
        }
        
        const headers = sheetData[headerRowIndex] as string[]
        const dataRows = sheetData.slice(headerRowIndex + 1).filter(row => 
          row.some(cell => cell !== '' && cell !== null && cell !== undefined)
        )
        

        // 转换为对象数组
        const result = dataRows.map(row => {
          const obj: any = {}
          headers.forEach((header, idx) => {
            if (header && idx < row.length) {
              obj[header] = normalizeCellValue(row[idx])
            }
          })
          return obj
        }).filter(obj => Object.keys(obj).length > 0)
        
        if (result.length === 0) {
          message.warning('Excel 文件无有效数据')
          return
        }
        
        message.success(`成功解析 ${result.length} 条数据（表头在第 ${headerRowIndex + 1} 行）`)
        setRawData(result)
        setCurrentStep(1)
        // 自动调用预览接口
        fetchPreview(result)
      } catch (err) {
        message.error('解析 Excel 文件失败')
        console.error(err)
      }
    }
    reader.readAsArrayBuffer(file)
    return false // 阻止自动上传
  }

  // 调用预览接口
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
      console.error(err)
      setCurrentStep(0)
    } finally {
      setLoading(false)
    }
  }

  // 执行批量导入
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
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const previewColumns = [
    { title: '行号', dataIndex: 'row_index', width: 60, fixed: 'left' as const, render: (v: number) => v + 1 },
    { title: '资产编号', dataIndex: 'asset_no', width: 110, fixed: 'left' as const },
    { title: '标签号', dataIndex: 'label_no', width: 100, render: (v: string) => v || '-' },
    { title: '设备名称', dataIndex: 'name', width: 160, ellipsis: true },
    { title: '资产类别说明', dataIndex: 'category_description', width: 140, ellipsis: true, render: (v: string) => v || '-' },
    { title: '设备分类', dataIndex: 'equipment_class', width: 80, render: (v: string) => v ? `${v}类` : '-' },
    { title: '制造商', dataIndex: 'manufacturer', width: 120, ellipsis: true, render: (v: string) => v || '-' },
    { title: '型号', dataIndex: 'model', width: 120, ellipsis: true, render: (v: string) => v || '-' },
    { title: '当前成本', dataIndex: 'current_cost', width: 100, render: (v: number) => v != null ? `¥${v.toLocaleString()}` : '-' },
    { 
      title: '数量', 
      dataIndex: 'technical_params', 
      width: 80, 
      render: (params: any) => params?.['数量'] ?? '-' 
    },
    { title: '部门', dataIndex: 'department_name', width: 120, ellipsis: true, render: (v: string) => v || '-' },
    { title: '位置', dataIndex: 'location_text', width: 120, ellipsis: true, render: (v: string) => v || '-' },
    { title: '状态', dataIndex: 'status', width: 80, render: (v: string) => <Tag color={v === '在用' ? 'green' : 'default'}>{v}</Tag> },
    { title: '报废状态', dataIndex: 'scrap_status', width: 90, render: (v: string) => v || '-' },
    { 
      title: '验证', 
      dataIndex: 'validation_errors', 
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: ImportPreviewItem) => {
        // v4 契约优先：validation_status + error_message
        if (record.validation_status) {
          if (record.validation_status === 'pass') return <Tag color="success">通过</Tag>
          if (record.validation_status === 'duplicate') return <Tag color="warning">重复</Tag>
          return (
            <span style={{ color: '#e03131', fontSize: 12 }}>
              {record.error_message || '校验未通过'}
            </span>
          )
        }
        // v3 契约兜底：validation_errors 数组（可能缺失，必须防御）
        const errors = record.validation_errors
        if (Array.isArray(errors) && errors.length > 0) {
          return <span style={{ color: '#e03131', fontSize: 12 }}>{errors.join(', ')}</span>
        }
        return <Tag color="success">通过</Tag>
      }
    },
  ]

  const isValidRow = (item: ImportPreviewItem) =>
    item.validation_status
      ? item.validation_status === 'pass'
      : (item.validation_errors?.length ?? 0) === 0

  const validCount = previewData.filter(isValidRow).length
  const invalidCount = previewData.length - validCount

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
          <p className="ant-upload-text">点击或拖拽 Excel 文件到此区域</p>
          <p className="ant-upload-hint">
            支持 .xlsx、.xls 格式，请确保表头包含：资产编号、资产说明、实物所在部门 等字段
          </p>
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
            <div style={{ display: 'flex', gap: 16 }}>
              <span>总计: <strong>{previewData.length}</strong> 条</span>
              <div className="ml-auto">
                <ForceOverrideToggle enabled={forceOverride} onToggle={setForceOverride} />
              </div>
              <span style={{ color: '#1aae39' }}>可导入: <strong>{validCount}</strong> 条</span>
              {invalidCount > 0 && (
                <span style={{ color: '#e03131' }}>异常: <strong>{invalidCount}</strong> 条</span>
              )}
            </div>
          </div>
          <ImportCockpit 
            data={previewData} 
            headers={previewHeaders} 
          />
        </div>
      )}

      {currentStep === 3 && importResult && (
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <CheckCircleOutlined style={{ fontSize: 64, color: '#1aae39', marginBottom: 24 }} />
          <div style={{ 
            background: '#f5f5f5', 
            borderRadius: 8, 
            padding: 24, 
            marginBottom: 24,
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 16,
            textAlign: 'center'
          }}>
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#1aae39' }}>{importResult.created_count}</div>
              <div style={{ fontSize: 12, color: '#666' }}>创建</div>
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#1890ff' }}>{importResult.updated_count}</div>
              <div style={{ fontSize: 12, color: '#666' }}>更新</div>
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#faad14' }}>{importResult.skipped_count}</div>
              <div style={{ fontSize: 12, color: '#666' }}>跳过</div>
            </div>
            <div>
              <div style={{ fontSize: 24, fontWeight: 700, color: '#e03131' }}>{importResult.error_count}</div>
              <div style={{ fontSize: 12, color: '#666' }}>错误</div>
            </div>
          </div>
          <div style={{ marginBottom: 16, fontSize: 12, color: '#999' }}>
            批次 ID: {importResult.batch_id}
          </div>
          <h3>导入完成</h3>
          {importResult.errors && importResult.errors.length > 0 && (
            <div style={{ marginTop: 16, textAlign: 'left', maxHeight: 200, overflow: 'auto' }}>
              <p style={{ color: '#e03131' }}>错误详情：</p>
              {importResult.errors.map((err, idx) => (
                <p key={idx} style={{ color: '#666', fontSize: 12 }}>
                  第 {err.row + 1} 行: {err.error}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}
