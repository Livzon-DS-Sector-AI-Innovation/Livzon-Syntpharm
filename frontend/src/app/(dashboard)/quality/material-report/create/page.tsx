'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
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
  Popconfirm,
  Row,
  Col,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { PlusOutlined, SaveOutlined, DeleteOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import Link from 'next/link'
import dayjs from 'dayjs'
import {
  createReport,
  saveReportItems,
  getTemplates,
  getTemplateById,
} from '@/actions/material-report'
import {
  TemplateListItem,
  TemplateResponse,
  TemplateColumnConfig,
} from '@/types/material-report'

interface TableRow {
  key: number
  [key: string]: any
}

export default function CreateReportPage() {
  const router = useRouter()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState<TemplateListItem[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateResponse | null>(null)
  const [tableColumns, setTableColumns] = useState<TemplateColumnConfig[]>([])
  const [tableData, setTableData] = useState<TableRow[]>([])
  const [reportId, setReportId] = useState<string | null>(null)

  // 加载模板列表
  useEffect(() => {
    const fetchTemplates = async () => {
      try {
        const result = await getTemplates({ is_active: true, page: 1, page_size: 100 })
        setTemplates(result.data?.items || [])
      } catch (error) {
        message.error('获取模板列表失败')
      }
    }
    fetchTemplates()
  }, [])

  // 选择模板后加载字段配置
  const handleTemplateChange = async (templateId: string) => {
    try {
      const result = await getTemplateById(templateId)
      const template = result.data
      setSelectedTemplate(template)

      // 设置静态字段
      const staticData: Record<string, any> = {}
      const fieldMapping = template?.field_mapping || {}
      Object.keys(fieldMapping).forEach((key) => {
        staticData[key] = ''
      })
      form.setFieldsValue({ static_data: staticData })

      // 设置动态表格列
      const columns = (template?.table_fields?.columns || []) as TemplateColumnConfig[]
      setTableColumns(columns)

      // 添加初始行
      if (columns.length > 0) {
        setTableData([{ key: 1, ...Object.fromEntries(columns.map((c) => [c.key, ''])) }])
      }
    } catch (error) {
      message.error('获取模板详情失败')
    }
  }

  // 添加行
  const handleAddRow = () => {
    const newRow: TableRow = {
      key: tableData.length + 1,
      ...Object.fromEntries(tableColumns.map((c) => [c.key, ''])),
    }
    setTableData([...tableData, newRow])
  }

  // 删除行
  const handleDeleteRow = (key: number) => {
    setTableData(tableData.filter((row) => row.key !== key))
  }

  // 单元格值变化
  const handleCellChange = (key: number, fieldKey: string, value: any) => {
    setTableData(
      tableData.map((row) => (row.key === key ? { ...row, [fieldKey]: value } : row))
    )
  }

  // 保存报告单
  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setLoading(true)

      // 创建报告单
      const result = await createReport({
        template_id: values.template_id,
        report_title: values.report_title,
        report_date: values.report_date.format('YYYY-MM-DD'),
        static_data: values.static_data,
      })

      const newReportId = result.data?.id
      setReportId(newReportId)

      // 保存明细数据
      if (tableData.length > 0) {
        const items = tableData.flatMap((row, rowIndex) =>
          tableColumns.map((col) => ({
            row_index: rowIndex + 1,
            field_key: col.key,
            field_value: row[col.key] || '',
          }))
        )

        await saveReportItems(newReportId, { items })
      }

      message.success('保存成功')
      router.push(`/quality/material-report/${newReportId}`)
    } catch (error: any) {
      if (error.errorFields) {
        message.error('请填写必填字段')
      } else {
        message.error(error.message || '保存失败')
      }
    } finally {
      setLoading(false)
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
      title: col.label,
      dataIndex: col.key,
      key: col.key,
      width: col.width || 120,
      render: (value: any, record: TableRow) => (
        <Input
          value={value}
          onChange={(e) => handleCellChange(record.key, col.key, e.target.value)}
          placeholder={`请输入${col.label}`}
        />
      ),
    })),
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record) =>
        tableData.length > 1 && (
          <Popconfirm
            title="确认删除此行？"
            onConfirm={() => handleDeleteRow(record.key)}
          >
            <Button type="link" danger size="small" icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <Card
        title="新建报告单"
        extra={
          <Space>
            <Link href="/quality/material-report">
              <Button icon={<ArrowLeftOutlined />}>返回</Button>
            </Link>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={loading}
              onClick={handleSave}
            >
              保存
            </Button>
          </Space>
        }
      >
        {/* 基本信息 */}
        <Form form={form} layout="vertical">
          <Row gutter={24}>
            <Col span={12}>
              <Form.Item
                name="template_id"
                label="选择模板"
                rules={[{ required: true, message: '请选择模板' }]}
              >
                <Select
                  placeholder="请选择模板"
                  onChange={handleTemplateChange}
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
                <Input placeholder="请输入报告标题" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="report_date"
                label="报告日期"
                rules={[{ required: true, message: '请选择报告日期' }]}
                initialValue={dayjs()}
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>

        {/* 静态字段 */}
        {selectedTemplate && Object.keys(selectedTemplate.field_mapping || {}).length > 0 && (
          <Card title="静态字段" style={{ marginTop: 16 }}>
            <Row gutter={24}>
              {Object.entries(selectedTemplate.field_mapping || {}).map(([key, config]: [string, any]) => (
                <Col span={8} key={key}>
                  <Form.Item name={['static_data', key]} label={config.label || key}>
                    <Input placeholder={`请输入${config.label || key}`} />
                  </Form.Item>
                </Col>
              ))}
            </Row>
          </Card>
        )}

        {/* 动态表格 */}
        {tableColumns.length > 0 && (
          <Card
            title="检测项目明细"
            style={{ marginTop: 16 }}
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRow}>
                添加行
              </Button>
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
      </Card>
    </div>
  )
}