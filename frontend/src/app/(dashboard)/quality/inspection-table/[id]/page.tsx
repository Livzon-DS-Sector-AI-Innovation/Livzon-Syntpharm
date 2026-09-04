'use client'

import { useState, useEffect, use, useRef } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  DatePicker,
  Select,
  Tag,
  message,
  Spin,
  Modal,
  Upload,
  Image,
  Popconfirm,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import {
  ArrowLeftOutlined,
  PlusOutlined,
  SaveOutlined,
  DeleteOutlined,
  ScanOutlined,
  UploadOutlined,
  DownloadOutlined,
  FileWordOutlined,
} from '@ant-design/icons'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  getInspectionTable,
  batchSaveTableRows,
  recognizeImage,
  recognizeMultipleImagesV3,
  uploadInspectionTemplate,
  deleteInspectionTemplate,
} from '@/actions/inspection-table'
import type { InspectionTableDetail, InspectionTableRow, ColumnConfig, RecognizeResult } from '@/types/inspection-table'

const API_BASE = '/api/v1'

interface TableRow {
  key: string
  id?: number
  [key: string]: unknown
}

export default function InspectionTableDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const resolvedParams = use(params)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [tableData, setTableData] = useState<InspectionTableDetail | null>(null)
  const [rows, setRows] = useState<TableRow[]>([])
  const [hasChanges, setHasChanges] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]) // 批量选择

  // 识别相关状态
  const [recognizeModalVisible, setRecognizeModalVisible] = useState(false)
  const [recognizing, setRecognizing] = useState(false)
  const [recognizeResult, setRecognizeResult] = useState<RecognizeResult | null>(null)
  const [recognizedRows, setRecognizedRows] = useState<Record<string, any>[]>([])
  const recognizingRef = useRef(false) // 防止重复识别

  // 模板上传状态
  const [uploadingTemplate, setUploadingTemplate] = useState(false)
  const [exporting, setExporting] = useState(false)

  // 上传 Word 模板
  const handleUploadTemplate = async (file: File) => {
    if (!tableData) return

    setUploadingTemplate(true)
    try {
      await uploadInspectionTemplate(tableData.id, file)
      message.success('模板上传成功')
      fetchData()
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "模板上传失败") || '模板上传失败')
    } finally {
      setUploadingTemplate(false)
    }

    return false
  }

  const handleDeleteTemplate = async () => {
    if (!tableData) return

    try {
      await deleteInspectionTemplate(tableData.id)
      message.success('模板删除成功')
      fetchData()
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '模板删除失败')
    }
  }

  // 导出单条数据
  const handleExportRow = async (rowId: number) => {
    if (!tableData) return

    setExporting(true)
    try {
      const link = document.createElement('a')
      link.href = `${API_BASE}/quality/inspection-table/${tableData.id}/rows/${rowId}/export`
      link.download = ''
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      message.success('导出开始')
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  // 批量导出选中的数据
  const handleBatchExport = async () => {
    if (!tableData || selectedRowKeys.length === 0) return

    setExporting(true)
    try {
      const rowIds = selectedRowKeys.join(',')
      const link = document.createElement('a')
      link.href = `${API_BASE}/quality/inspection-table/${tableData.id}/export?row_ids=${rowIds}`
      link.download = ''
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      message.success(`开始导出 ${selectedRowKeys.length} 条数据`)
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  // 导出全部数据
  const handleExportAll = async () => {
    if (!tableData) return

    setExporting(true)
    try {
      const link = document.createElement('a')
      link.href = `${API_BASE}/quality/inspection-table/${tableData.id}/export`
      link.download = ''
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      message.success('开始导出全部数据')
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '导出失败')
    } finally {
      setExporting(false)
    }
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const result = await getInspectionTable(resolvedParams.id)
      const data = result as InspectionTableDetail
      setTableData(data)

      // 转换数据行
      const rowData: TableRow[] = data.rows.map((row: InspectionTableRow) => ({
        key: String(row.id),
        id: row.id,
        ...row.row_data,
      }))
      setRows(rowData)
    } catch (_error) {
      message.error('获取数据失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [resolvedParams.id])

  // 处理多文件上传并识别
  const handleFileUpload = async (fileList: File[]) => {
    // 防止重复调用
    if (recognizingRef.current) return
    if (!tableData || !fileList || fileList.length === 0) return

    const files = Array.from(fileList)

    try {
      recognizingRef.current = true
      setRecognizing(true)
      let result: RecognizeResult

      if (files.length === 1) {
        result = await recognizeImage(resolvedParams.id, files[0])
      } else {
        result = await recognizeMultipleImagesV3(resolvedParams.id, files)
      }

      setRecognizeResult(result)

      // 初始化可编辑的行数据
      if (result.recognized_rows && result.recognized_rows.length > 0) {
        const editableRows = result.recognized_rows.map((row, index) => ({
          ...row,
          _key: `recognized_${Date.now()}_${index}`,
        }))
        setRecognizedRows(editableRows)
      } else {
        // 如果没有识别到数据，创建空行
        const emptyRow: Record<string, any> = { _key: `recognized_${Date.now()}` }
        tableData.columns_config.forEach((col) => {
          emptyRow[col.key] = ''
        })
        setRecognizedRows([emptyRow])
      }

      // 显示预览 Modal
      setRecognizeModalVisible(true)
    } catch (error: unknown) {
      console.error('识别失败:', error)
      message.error((error instanceof Error ? error.message : "操作失败") || '识别失败，请查看控制台获取详情')
    } finally {
      setRecognizing(false)
      recognizingRef.current = false
    }

    // 返回 false 阻止默认上传行为
    return false
  }

  // 处理上传变化（支持多文件）
  const handleUploadChange = (info: { fileList: Array<{ originFileObj?: File }> }) => {
    if (info.fileList) {
      handleFileUpload(info.fileList.map((f: { originFileObj?: File }) => f.originFileObj).filter((f): f is File => f !== undefined))
    }
  }

  // 更新识别结果行的值
  const handleRecognizedRowChange = (index: number, field: string, value: unknown) => {
    const newRows = [...recognizedRows]
    newRows[index] = { ...newRows[index], [field]: value }
    setRecognizedRows(newRows)
  }

  // 添加新的识别行
  const handleAddRecognizedRow = () => {
    if (!tableData) return
    const emptyRow: Record<string, any> = { _key: `recognized_${Date.now()}` }
    tableData.columns_config.forEach((col) => {
      emptyRow[col.key] = ''
    })
    setRecognizedRows([...recognizedRows, emptyRow])
  }

  // 删除识别行
  const handleDeleteRecognizedRow = (index: number) => {
    setRecognizedRows(recognizedRows.filter((_, i) => i !== index))
  }

  // 确认添加识别结果
  const handleConfirmRecognize = () => {
    // 将识别结果转换为表格行并添加到rows
    const newRows: TableRow[] = recognizedRows.map((row) => {
      const newRow: TableRow = {
        key: `new_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        id: undefined,
      }
      // 只复制列配置中定义的字段
      tableData?.columns_config.forEach((col) => {
        newRow[col.key] = row[col.key] || ''
      })
      return newRow
    })

    setRows([...rows, ...newRows])
    setHasChanges(true)
    setRecognizeModalVisible(false)
    setRecognizeResult(null)
    setRecognizedRows([])
    message.success(`已添加 ${newRows.length} 行数据，请检查并保存`)
  }

  // 取消识别
  const handleCancelRecognize = () => {
    setRecognizeModalVisible(false)
    setRecognizeResult(null)
    setRecognizedRows([])
  }

  // 添加行
  const handleAddRow = () => {
    const newRow: TableRow = {
      key: `new_${Date.now()}`,
      id: undefined,
    }
    // 初始化空值
    tableData?.columns_config.forEach((col) => {
      newRow[col.key] = ''
    })
    setRows([...rows, newRow])
    setHasChanges(true)
  }

  // 删除行
  const handleDeleteRow = (key: string) => {
    setRows(rows.filter((row) => row.key !== key))
    setHasChanges(true)
  }

  // 单元格值变化
  const handleCellChange = (key: string, fieldKey: string, value: unknown) => {
    setRows(
      rows.map((row) => (row.key === key ? { ...row, [fieldKey]: value } : row))
    )
    setHasChanges(true)
  }

  // 保存所有数据
  const handleSave = async () => {
    if (!tableData) return

    try {
      setSaving(true)

      // 构建行数据
      const rowsData = rows.map((row) => {
        const rowData: Record<string, any> = {}
        tableData.columns_config.forEach((col) => {
          rowData[col.key] = row[col.key] || ''
        })
        return rowData
      })

      await batchSaveTableRows(tableData.id, rowsData)

      message.success('保存成功')
      setHasChanges(false)
      fetchData()
    } catch (error: unknown) {
      message.error((error instanceof Error ? error.message : "操作失败") || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // 渲染表格列
  const renderTableColumns = (): ColumnsType<TableRow> => {
    if (!tableData) return []

    return [
      {
        title: '序号',
        key: 'index',
        width: 60,
        render: (_, __, index) => index + 1,
      },
      ...tableData.columns_config.map((col: ColumnConfig) => ({
        title: (
          <span>
            {col.label}
            {col.required && <Tag color="red" style={{ marginLeft: 4 }}>*</Tag>}
          </span>
        ),
        dataIndex: col.key,
        key: col.key,
        width: col.width || 200,
        ellipsis: false,
        render: (value: unknown, record: TableRow) => {
          if (col.type === 'date') {
            return (
              <DatePicker
                value={value ? dayjs(value as string) : null}
                onChange={(_, dateString) => handleCellChange(record.key, col.key, dateString)}
                style={{ width: '100%' }}
              />
            )
          }
          if (col.type === 'select' && col.options) {
            return (
              <Select
                value={value}
                onChange={(v) => handleCellChange(record.key, col.key, v)}
                style={{ width: '100%' }}
                options={col.options}
                placeholder={`请选择${col.label}`}
              />
            )
          }
          return (
            <Input
              value={value as string}
              onChange={(e) => handleCellChange(record.key, col.key, e.target.value)}
              placeholder={`请输入${col.label}`}
              style={{ minWidth: 150 }}
            />
          )
        },
      })),
      {
        title: '操作',
        key: 'action',
        width: 160,
        fixed: 'right' as const,
        render: (_, record) => (
          <Space size="small">
            {tableData?.template_path && record.id && (
              <Button
                type="link"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => record.id && handleExportRow(record.id)}
                disabled={exporting}
              >
                导出
              </Button>
            )}
            <Button
              type="link"
              danger
              size="small"
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteRow(record.key)}
            >
              删除
            </Button>
          </Space>
        ),
      },
    ]
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!tableData) {
    return <div style={{ padding: 24 }}>数据表不存在</div>
  }

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={`数据表详情 - ${tableData.table_name}`}
        extra={
          <Space>
            <Link href="/quality/inspection-table">
              <Button icon={<ArrowLeftOutlined />}>返回</Button>
            </Link>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={saving}
              onClick={handleSave}
              disabled={!hasChanges}
            >
              保存
            </Button>
          </Space>
        }
      >
        {/* 表格信息 */}
        {tableData.table_description && (
          <div style={{ marginBottom: 16, color: '#666' }}>
            {tableData.table_description}
          </div>
        )}

        {/* 数据表格 */}
        <Card
          title={
            <Space>
              <span>数据</span>
              {selectedRowKeys.length > 0 && (
                <Tag color="blue">{selectedRowKeys.length} 条已选择</Tag>
              )}
            </Space>
          }
          extra={
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRow}>
                添加行
              </Button>
              <Upload
                accept="image/*"
                multiple
                showUploadList={false}
                onChange={handleUploadChange}
                disabled={recognizing}
              >
                <Button icon={<ScanOutlined />} loading={recognizing}>
                  识别添加（支持多张）
                </Button>
              </Upload>
              {/* 导出按钮组 */}
              {tableData?.template_path ? (
                <>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={handleExportAll}
                    disabled={rows.length === 0 || exporting}
                    loading={exporting}
                  >
                    导出全部
                  </Button>
                  <Button
                    icon={<DownloadOutlined />}
                    onClick={handleBatchExport}
                    disabled={selectedRowKeys.length === 0 || exporting}
                    loading={exporting}
                  >
                    导出选中 ({selectedRowKeys.length})
                  </Button>
                  <Popconfirm
                    title="确定要删除模板吗？"
                    onConfirm={handleDeleteTemplate}
                    okText="确定"
                    cancelText="取消"
                  >
                    <Button danger icon={<FileWordOutlined />}>
                      删除模板
                    </Button>
                  </Popconfirm>
                </>
              ) : (
                <Upload
                  accept=".docx,.doc"
                  showUploadList={false}
                  beforeUpload={handleUploadTemplate}
                  disabled={uploadingTemplate}
                >
                  <Button icon={<UploadOutlined />} loading={uploadingTemplate}>
                    上传Word模板
                  </Button>
                </Upload>
              )}
            </Space>
          }
        >
          {tableData?.template_path && (
            <div style={{ marginBottom: 12, padding: '8px 12px', background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f' }}>
              <Space>
                <FileWordOutlined style={{ color: '#52c41a' }} />
                <span style={{ color: '#52c41a' }}>已上传模板：{tableData.template_name}</span>
              </Space>
            </div>
          )}
          {tableData.columns_config.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              暂无列配置，请在列表页编辑数据表添加表头
            </div>
          ) : (
            <Table
              columns={renderTableColumns()}
              dataSource={rows}
              rowKey="key"
              rowSelection={{
                selectedRowKeys,
                onChange: (keys) => setSelectedRowKeys(keys),
              }}
              pagination={false}
              scroll={{ x: true }}
              size="small"
            />
          )}
        </Card>

        {/* 提示 */}
        {hasChanges && (
          <div style={{ marginTop: 16, color: '#faad14' }}>
            * 您有未保存的更改，请点击保存按钮保存数据
          </div>
        )}
      </Card>

      {/* AI 识别结果预览 Modal */}
      <Modal
        title="AI 识别结果预览"
        open={recognizeModalVisible || recognizeResult !== null}
        onCancel={handleCancelRecognize}
        onOk={handleConfirmRecognize}
        width={900}
        okText="添加数据"
        cancelText="取消"
        maskClosable={false}
      >
        {recognizeResult && (
          <div>
            {/* 图片预览（支持单图和多图） */}
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontWeight: 500, marginBottom: 8 }}>
                识别图片（{recognizeResult.images?.length || (recognizeResult.image_url ? 1 : 0)} 张）：
              </p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {recognizeResult.images?.map((img, index) => (
                  <Image
                    key={index}
                    src={`${img.saved_path}`}
                    alt={img.original_name || `图片${index + 1}`}
                    style={{ maxWidth: 150, maxHeight: 100, border: '1px solid #d9d9d9', borderRadius: 4 }}
                  />
                ))}
                {recognizeResult.image_url && !recognizeResult.images && (
                  <Image
                    src={`${recognizeResult.image_url}`}
                    alt="识别图片"
                    style={{ maxWidth: '100%', maxHeight: 200, border: '1px solid #d9d9d9', borderRadius: 4 }}
                  />
                )}
              </div>
            </div>

            {/* 数据预览表格 */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <p style={{ fontWeight: 500, margin: 0 }}>
                  识别数据（请人工复核）- 共 {recognizedRows.length} 行：
                </p>
                <Button size="small" onClick={handleAddRecognizedRow} icon={<PlusOutlined />}>
                  添加行
                </Button>
              </div>
              <Table
                dataSource={recognizedRows.map((row, index) => ({ ...row, _index: index }))}
                rowKey="_key"
                size="small"
                pagination={false}
                scroll={{ x: true }}
                columns={[
                  {
                    title: '序号',
                    key: 'index',
                    width: 60,
                    render: (_, __, index) => index + 1,
                  },
                  ...(tableData?.columns_config.map((col) => ({
                    title: col.label,
                    dataIndex: col.key,
                    key: col.key,
                    width: 150,
                    render: (value: unknown, record: Record<string, unknown>) => (
                      <Input
                        value={(value as string) || ''}
                        onChange={(e) => handleRecognizedRowChange(record._index as number, col.key, e.target.value)}
                        placeholder={`识别值: ${value || '(空)'}`}
                      />
                    ),
                  })) || []),
                  {
                    title: '操作',
                    key: 'action',
                    width: 80,
                    render: (_, record: Record<string, unknown>) => (
                      <Button
                        type="link"
                        danger
                        size="small"
                        onClick={() => handleDeleteRecognizedRow(record._index as number)}
                      >
                        删除
                      </Button>
                    ),
                  },
                ]}
              />
            </div>

            {recognizedRows.length === 0 && (
              <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                未识别到数据，请检查图片或手动添加
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
