'use client'

import { useState, useEffect, use, useRef } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  Card,
  Form,
  Input,
  Select,
  DatePicker,
  Button,
  message,
  Table,
  Space,
  Descriptions,
  Tag,
  Spin,
  Modal,
  Row,
  Col,
  Upload,
  Image,
  Popconfirm,
  Divider,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { UploadProps } from 'antd'
import {
  SaveOutlined,
  ArrowLeftOutlined,
  FileWordOutlined,
  EditOutlined,
  PlusOutlined,
  DeleteOutlined,
  UploadOutlined,
  ScanOutlined,
  EyeOutlined,
  CameraOutlined,
} from '@ant-design/icons'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  getReportById,
  updateReport,
  saveReportItems,
  generateReport,
  getTemplates,
  uploadReportImage,
  getReportImages,
} from '@/actions/material-report'
import {
  ReportDetailResponse,
  TemplateListItem,
  TemplateColumnConfig,
  reportStatusLabels,
  reportStatusColors,
} from '@/types/material-report'

interface TableRow {
  key: number
  [key: string]: any
}

export default function ReportDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params)
  const router = useRouter()
  const searchParams = useSearchParams()
  const isEditMode = searchParams.get('edit') === 'true'
  const isGenerateMode = searchParams.get('generate') === 'true'

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [report, setReport] = useState<ReportDetailResponse | null>(null)
  const [templates, setTemplates] = useState<TemplateListItem[]>([])
  const [form] = Form.useForm()
  const [tableColumns, setTableColumns] = useState<TemplateColumnConfig[]>([])
  const [tableData, setTableData] = useState<TableRow[]>([])
  const [hasChanges, setHasChanges] = useState(false)
  const [reportImages, setReportImages] = useState<any[]>([])
  const [previewVisible, setPreviewVisible] = useState(false)
  const [previewImage, setPreviewImage] = useState('')
  const [previewAIResult, setPreviewAIResult] = useState<any>(null)
  const uploadRef = useRef<any>(null)

  // 获取报告单图片
  const fetchReportImages = async () => {
    try {
      const result = await getReportImages(resolvedParams.id)
      setReportImages(result.data || [])
    } catch (error) {
      console.error('获取图片失败', error)
    }
  }

  // 上传图片并AI识别
  const handleImageUpload = async (file: File, rowKey: number, fieldKey: string) => {
    try {
      setUploading(true)
      const result = await uploadReportImage(resolvedParams.id, file, fieldKey, rowKey)

      if (result.code === 200) {
        message.success('图片上传成功，AI识别完成')

        // 如果有识别结果，自动填入表格
        const aiResult = result.data?.ai_result
        if (aiResult?.items?.length > 0) {
          const firstItem = aiResult.items[0]
          const fieldValue = firstItem.value || firstItem.name || ''
          if (fieldValue) {
            handleCellChange(rowKey, fieldKey, fieldValue)
            message.info(`已自动填入识别结果: ${fieldValue}`)
          }
        }

        // 刷新图片列表
        fetchReportImages()
      } else {
        message.error(result.message || '上传失败')
      }
    } catch (error: any) {
      message.error(error.message || '上传失败')
    } finally {
      setUploading(false)
    }
    return false // 阻止默认上传
  }

  // 图片预览
  const handlePreview = (image: any) => {
    setPreviewImage(`/uploads/${image.image_url}`)
    setPreviewAIResult(image.ai_result)
    setPreviewVisible(true)
  }

  const fetchData = async () => {
    setLoading(true)
    try {
      const [result, templateResult] = await Promise.all([
        getReportById(resolvedParams.id),
        getTemplates({ is_active: true, page: 1, page_size: 100 }),
      ])
      const data = result.data as ReportDetailResponse
      setReport(data)
      setTemplates(templateResult.data?.items || [])

      // 设置表单值
      form.setFieldsValue({
        template_id: data.template_id,
        report_title: data.report_title,
        report_date: dayjs(data.report_date),
        static_data: data.static_data || {},
      })

      // 解析表格数据
      if (data.items && data.items.length > 0 && data.template?.table_fields?.columns) {
        const columns = data.template.table_fields.columns
        setTableColumns(columns)

        // 转换items为行数据
        const rowsMap: Record<number, TableRow> = {}
        data.items.forEach((item: Record<string, any>) => {
          const rowIdx = item.row_index
          if (!rowsMap[rowIdx]) {
            rowsMap[rowIdx] = { key: rowIdx }
          }
          rowsMap[rowIdx][item.field_key] = item.field_value
        })
        setTableData(Object.values(rowsMap))
      } else if (data.template?.table_fields?.columns) {
        setTableColumns(data.template.table_fields.columns)
        setTableData([
          {
            key: 1,
            ...Object.fromEntries(
              data.template.table_fields.columns.map((c) => [c.key, ''])
            ),
          },
        ])
      }
    } catch (error) {
      message.error('获取报告单详情失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    fetchReportImages()
  }, [resolvedParams.id])

  // 添加行
  const handleAddRow = () => {
    const newRow: TableRow = {
      key: tableData.length + 1,
      ...Object.fromEntries(tableColumns.map((c) => [c.key, ''])),
    }
    setTableData([...tableData, newRow])
    setHasChanges(true)
  }

  // 删除行
  const handleDeleteRow = (key: number) => {
    setTableData(tableData.filter((row) => row.key !== key))
    setHasChanges(true)
  }

  // 单元格值变化
  const handleCellChange = (key: number, fieldKey: string, value: any) => {
    setTableData(
      tableData.map((row) => (row.key === key ? { ...row, [fieldKey]: value } : row))
    )
    setHasChanges(true)
  }

  // 保存
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      await updateReport(resolvedParams.id, {
        template_id: values.template_id,
        report_title: values.report_title,
        report_date: values.report_date.format('YYYY-MM-DD'),
        static_data: values.static_data,
      })

      // 保存明细数据
      if (tableData.length > 0) {
        const items = tableData.flatMap((row, rowIndex) =>
          tableColumns.map((col) => ({
            row_index: rowIndex + 1,
            field_key: col.key,
            field_value: row[col.key] || '',
          }))
        )
        await saveReportItems(resolvedParams.id, { items })
      }

      message.success('保存成功')
      setHasChanges(false)
      fetchData()
    } catch (error: any) {
      message.error(error.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // 生成报告单
  const handleGenerate = async () => {
    try {
      setSaving(true)
      const blob = await generateReport(resolvedParams.id)

      // 下载文件
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${report?.report_no}.docx`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      message.success('报告单已生成并下载')
    } catch (error) {
      message.error('生成报告单失败')
    } finally {
      setSaving(false)
    }
  }

  // 渲染表格列
  const renderTableColumns = (): ColumnsType<TableRow> => [
    {
      title: '序号',
      key: 'index',
      width: 60,
      render: (_, __, index) => index + 1,
    },
    ...tableColumns.map((col) => ({
      title: (
        <Space>
          {col.label}
          {isEditMode && (
            <Upload
              showUploadList={false}
              accept="image/*"
              beforeUpload={(file) => {
                handleImageUpload(file, 0, col.key)
                return false
              }}
            >
              <Button size="small" icon={<CameraOutlined />} title="AI识别图片" />
            </Upload>
          )}
        </Space>
      ),
      dataIndex: col.key,
      key: col.key,
      width: col.width || 120,
      render: (value: any, record: TableRow) => (
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={value}
            onChange={(e) => handleCellChange(record.key, col.key, e.target.value)}
            disabled={!isEditMode}
            style={{ flex: 1 }}
          />
          {isEditMode && (
            <Upload
              showUploadList={false}
              accept="image/*"
              beforeUpload={(file) => {
                handleImageUpload(file, record.key, col.key)
                return false
              }}
            >
              <Button icon={<CameraOutlined />} />
            </Upload>
          )}
        </Space.Compact>
      ),
    })),
    ...(isEditMode
      ? [
          {
            title: '操作',
            key: 'action',
            width: 80,
            render: (_: any, record: TableRow) =>
              tableData.length > 1 && (
                <Button
                  type="link"
                  danger
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={() => handleDeleteRow(record.key)}
                >
                  删除
                </Button>
              ),
          } as const,
        ]
      : []),
  ]

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 100 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!report) {
    return <div style={{ padding: 24 }}>报告单不存在</div>
  }

  return (
    <div style={{ padding: 24 }}>
      <Card
        title={`报告单详情 - ${report.report_no}`}
        extra={
          <Space>
            <Link href="/quality/material-report">
              <Button icon={<ArrowLeftOutlined />}>返回</Button>
            </Link>
            {isEditMode ? (
              <>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  loading={saving}
                  onClick={handleSave}
                >
                  保存
                </Button>
              </>
            ) : (
              <>
                <Button
                  type="primary"
                  icon={<EditOutlined />}
                  onClick={() => router.push(`/quality/material-report/${resolvedParams.id}?edit=true`)}
                >
                  编辑
                </Button>
                {report.status === 'draft' && (
                  <Button
                    type="primary"
                    icon={<FileWordOutlined />}
                    onClick={handleGenerate}
                  >
                    生成报告单
                  </Button>
                )}
              </>
            )}
          </Space>
        }
      >
        {/* 基本信息 */}
        <Descriptions bordered column={2} style={{ marginBottom: 24 }}>
          <Descriptions.Item label="报告单编号">{report.report_no}</Descriptions.Item>
          <Descriptions.Item label="状态">
            <Tag color={reportStatusColors[report.status]}>
              {reportStatusLabels[report.status] || report.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="模板名称">
            {report.template?.template_name || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="报告日期">
            {dayjs(report.report_date).format('YYYY-MM-DD')}
          </Descriptions.Item>
        </Descriptions>

        {/* 编辑表单 */}
        <Form form={form} layout="vertical">
          <Card title="报告单信息" style={{ marginBottom: 16 }}>
            <Row gutter={24}>
              <Col span={12}>
                <Form.Item name="template_id" label="选择模板">
                  <Select
                    disabled={!isEditMode}
                    options={templates.map((t) => ({
                      label: t.template_name,
                      value: t.id,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="report_title"
                  label="报告标题"
                  rules={[{ required: true, message: '请输入报告标题' }]}
                >
                  <Input disabled={!isEditMode} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 静态字段 */}
          {report.template && Object.keys(report.template.field_mapping || {}).length > 0 && (
            <Card title="静态字段" style={{ marginBottom: 16 }}>
              <Row gutter={24}>
                {Object.entries(report.template.field_mapping || {}).map(([key, config]: [string, any]) => (
                  <Col span={8} key={key}>
                    <Form.Item name={['static_data', key]} label={config.label || key}>
                      <Input disabled={!isEditMode} />
                    </Form.Item>
                  </Col>
                ))}
              </Row>
            </Card>
          )}
        </Form>

        {/* 动态表格 */}
        {tableColumns.length > 0 && (
          <Card
            title="检测项目明细"
            extra={
              isEditMode && (
                <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRow}>
                  添加行
                </Button>
              )
            }
          >
            <Table
              columns={renderTableColumns()}
              dataSource={tableData}
              rowKey="key"
              pagination={false}
              scroll={{ x: true }}
            />
          </Card>
        )}

        {/* 已上传图片列表 */}
        {reportImages.length > 0 && (
          <Card title="已上传图片" size="small" style={{ marginTop: 16 }}>
            <Space wrap size="small">
              {reportImages.map((img) => (
                <div key={img.id} style={{ position: 'relative' }}>
                  <Image
                    src={`/uploads/${img.image_url}`}
                    width={80}
                    height={80}
                    style={{ objectFit: 'cover' }}
                    preview={{
                      src: `/uploads/${img.image_url}`,
                    }}
                  />
                  <Button
                    type="text"
                    size="small"
                    icon={<EyeOutlined />}
                    onClick={() => handlePreview(img)}
                    style={{ position: 'absolute', top: 0, right: 0 }}
                  />
                </div>
              ))}
            </Space>
          </Card>
        )}
      </Card>

      {/* 图片预览和AI识别结果弹窗 */}
      <Modal
        title="图片预览"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={800}
      >
        <Image src={previewImage} style={{ width: '100%' }} />
        {previewAIResult && (
          <>
            <Divider>AI识别结果</Divider>
            <pre style={{ background: '#f5f5f5', padding: 16, borderRadius: 4 }}>
              {JSON.stringify(previewAIResult, null, 2)}
            </pre>
          </>
        )}
      </Modal>
    </div>
  )
}