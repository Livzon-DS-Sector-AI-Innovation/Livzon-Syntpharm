'use client'

import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { DataUnavailable } from '@/components/common/DataUnavailable'
import { UploadFile, Table, Input, Button, Space, App, Card, Modal, Form, Upload, Row, Col, Spin, Alert } from 'antd'
import {DownloadOutlined, DeleteOutlined, FileSearchOutlined} from '@ant-design/icons'
import { ReferenceStandardListItem } from '@/types/registration'
import { fetchReferenceStandards, fetchReferenceStandardDownloadUrl } from '@/lib/api/client/registration'
import { parseCOA } from '@/actions/registration'
import { generateReferenceStandard, deleteReferenceStandardAction } from '@/actions/registration'
import dayjs from 'dayjs'

interface ReferenceStandardClientProps {
  initialRecords: ReferenceStandardListItem[]
  initialTotal: number
}

export default function ReferenceStandardClient({
  initialRecords,
  initialTotal,
}: ReferenceStandardClientProps) {
  const { message } = App.useApp()
  const [drugName, setDrugName] = useState('')
  // 已提交的查询条件：输入框内容不直接触发请求，点「搜索」才提交
  const [query, setQuery] = useState<{ page: number; pageSize: number; drugName: string }>({
    page: 1,
    pageSize: 20,
    drugName: '',
  })
  const [generateModalOpen, setGenerateModalOpen] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [parsedInfo, setParsedInfo] = useState<string>('')
  const [form] = Form.useForm()
  const [coaFileList, setCoaFileList] = useState<UploadFile[]>([])

  const isInitialQuery = query.page === 1 && query.pageSize === 20 && !query.drugName

  const recordsQuery = useQuery({
    queryKey: ['reference-standards', query],
    queryFn: async () => {
      const res = await fetchReferenceStandards({
        drug_name: query.drugName || undefined,
        page: query.page,
        page_size: query.pageSize,
      })
      return { items: res.data, total: res.meta?.total || 0 }
    },
    placeholderData: keepPreviousData,
    // 首屏首页直接用服务端已取好的数据，避免闪一次 loading；其余页码必须真取
    initialData: isInitialQuery ? { items: initialRecords, total: initialTotal } : undefined,
  })

  const records = recordsQuery.data?.items ?? []
  const total = recordsQuery.data?.total ?? 0

  // 搜索：条件与当前一致时强制重取，否则提交新条件（页码回到 1）
  const handleSearch = () => {
    const nextDrugName = drugName.trim()
    if (nextDrugName === query.drugName && query.page === 1) {
      void recordsQuery.refetch()
      return
    }
    setQuery({ page: 1, pageSize: query.pageSize, drugName: nextDrugName })
  }

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setQuery(prev => ({ ...prev, page: newPage, pageSize: newPageSize }))
  }

  // 上传COA后自动解析
  const handleCoaUpload = async (file: File) => {
    setParsing(true)
    setParsedInfo('')
    try {
      const result = await parseCOA(file)
      const meta = result.metadata
      
      // 自动填充表单
      const formValues: Record<string, string> = {}
      if (meta.drug_name) formValues.drug_name = meta.drug_name
      if (meta.reference_substance_name) formValues.reference_substance_name = meta.reference_substance_name
      if (meta.batch_number) formValues.batch_number = meta.batch_number
      if (meta.manufacturer) formValues.manufacturer = meta.manufacturer
      if (meta.english_name) formValues.english_name = meta.english_name
      if (meta.molecular_formula) formValues.molecular_formula = meta.molecular_formula
      if (meta.molecular_weight) formValues.molecular_weight = meta.molecular_weight
      if (meta.cas_number) formValues.cas_number = meta.cas_number
      if (meta.content) formValues.content = meta.content
      if (meta.moisture) formValues.moisture = meta.moisture
      if (meta.rsd) formValues.rsd = meta.rsd
      if (meta.expiration_date) formValues.expiration_date = meta.expiration_date
      if (meta.storage_condition) formValues.storage_condition = meta.storage_condition
      
      form.setFieldsValue(formValues)
      
      const filledCount = Object.keys(formValues).length
      if (filledCount > 0) {
        setParsedInfo(`已从COA中提取 ${filledCount} 个字段，请核对后提交`)
        message.success(`COA解析成功，已自动填充 ${filledCount} 个字段`)
      } else {
        setParsedInfo('COA解析完成，但未提取到关键信息，请手动填写')
        message.warning('COA解析完成，但未提取到关键信息，请手动填写')
      }
    } catch (err: unknown) {
      message.error((err instanceof Error ? err.message : null) || 'COA解析失败')
      setParsedInfo('COA解析失败，请手动填写')
    } finally {
      setParsing(false)
    }
    return false // 阻止自动上传
  }

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()

      if (coaFileList.length === 0) {
        message.error('请上传COA文件')
        return
      }

      setGenerating(true)

      const formData = new FormData()
      formData.append('coa', coaFileList[0].originFileObj as File)

      const result = await generateReferenceStandard(formData, {
        drug_name: values.drug_name,
        reference_substance_name: values.reference_substance_name,
        batch_number: values.batch_number,
        manufacturer: values.manufacturer,
        english_name: values.english_name,
        molecular_formula: values.molecular_formula,
        molecular_weight: values.molecular_weight,
        cas_number: values.cas_number,
        content: values.content,
        moisture: values.moisture,
        rsd: values.rsd,
        expiration_date: values.expiration_date,
        storage_condition: values.storage_condition,
        remarks: values.remarks,
      })

      if (result.success) {
        message.success(result.message)
        setGenerateModalOpen(false)
        form.resetFields()
        setCoaFileList([])
        setParsedInfo('')
        void recordsQuery.refetch()
      } else {
        message.error(result.message)
      }
    } catch (err: unknown) {
      message.error((err instanceof Error ? err.message : null) || '生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteReferenceStandardAction(id)
      message.success('删除成功')
      void recordsQuery.refetch()
    } catch (err: unknown) {
      message.error((err instanceof Error ? err.message : null) || '删除失败')
    }
  }

  const columns = [
    {
      title: '药品名称',
      dataIndex: 'drug_name',
      key: 'drug_name',
      width: 200,
    },
    {
      title: '对照物质名称',
      dataIndex: 'reference_substance_name',
      key: 'reference_substance_name',
      width: 200,
    },
    {
      title: '批号',
      dataIndex: 'batch_number',
      key: 'batch_number',
      width: 150,
    },
    {
      title: '生产厂家',
      dataIndex: 'manufacturer',
      key: 'manufacturer',
      width: 200,
    },
    {
      title: '生成文件',
      dataIndex: 'output_file_name',
      key: 'output_file_name',
      width: 250,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      fixed: 'right' as const,
      render: (_: unknown, record: ReferenceStandardListItem) => (
        <Space>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={async () => { const url = await fetchReferenceStandardDownloadUrl(record.id); window.open(url, "_blank"); }}
            target="_blank"
          >
            下载
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-2">
        对照物质说明表管理
      </h1>
      <p className="text-[14px] text-[var(--color-steel)] mb-4">
        上传COA检验报告，自动提取信息并生成对照物质说明表Word文档
      </p>

      <Card>
        <div className="flex gap-4 mb-4">
          <Input
            placeholder="药品名称搜索"
            value={drugName}
            onChange={(e) => setDrugName(e.target.value)}
            style={{ width: 200 }}
            allowClear
          />
          <Button onClick={handleSearch}>搜索</Button>
          <Button type="primary" onClick={() => setGenerateModalOpen(true)}>
            生成说明表
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={records}
          rowKey="id"
          loading={recordsQuery.isPending}
          pagination={{
            current: query.page,
            pageSize: query.pageSize,
            total: total,
            showSizeChanger: true,
            // 后端 PageParams 为 le=200，选项不得超过该上限否则 422
            pageSizeOptions: [10, 20, 50, 100],
            showTotal: (total) => `共 ${total} 条`,
            onChange: handlePageChange,
          }}
          scroll={{ x: 1400 }}
          locale={{
            // 取数失败时在表格内嵌降级区块，与「确实没有记录」的空态区分开
            emptyText: recordsQuery.isError ? (
              <DataUnavailable compact onRetry={() => void recordsQuery.refetch()} />
            ) : undefined,
          }}
        />
      </Card>

      <Modal
        title="生成对照物质说明表"
        open={generateModalOpen}
        onOk={handleGenerate}
        onCancel={() => {
          setGenerateModalOpen(false)
          form.resetFields()
          setCoaFileList([])
          setParsedInfo('')
        }}
        confirmLoading={generating}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="coa"
            label="COA文件（PDF）— 上传后自动提取信息"
            rules={[{ required: true, message: '请上传COA文件' }]}
          >
            <Upload
              beforeUpload={handleCoaUpload}
              fileList={coaFileList}
              onChange={({ fileList }) => setCoaFileList(fileList)}
              maxCount={1}
              accept=".pdf"
            >
              <Button icon={parsing ? <Spin size="small" /> : <FileSearchOutlined />}>
                {parsing ? '解析中...' : '上传并自动解析'}
              </Button>
            </Upload>
          </Form.Item>

          {parsedInfo && (
            <Alert
              title={parsedInfo}
              type={parsedInfo.includes('失败') || parsedInfo.includes('未提取') ? 'warning' : 'success'}
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="drug_name"
                label="药品名称"
                rules={[{ required: true, message: '请输入药品名称' }]}
              >
                <Input placeholder="请输入药品名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="reference_substance_name" label="对照物质名称">
                <Input placeholder="如不填则默认使用药品名称" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="batch_number" label="批号">
                <Input placeholder="请输入批号" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="manufacturer" label="生产厂家">
                <Input placeholder="请输入生产厂家" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="english_name" label="英文名">
                <Input placeholder="请输入英文名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="cas_number" label="CAS号">
                <Input placeholder="请输入CAS号" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="molecular_formula" label="分子式">
                <Input placeholder="如 C39H57FN4O4" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="molecular_weight" label="分子量">
                <Input placeholder="请输入分子量" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="content" label="含量">
                <Input placeholder="如 99.5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="moisture" label="水分/干燥失重">
                <Input placeholder="如 0.5" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="rsd" label="RSD">
                <Input placeholder="如 0.1" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="expiration_date" label="有效期">
                <Input placeholder="如 2026-12-31" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="storage_condition" label="贮存条件">
                <Input placeholder="如 冷藏、常温、阴凉" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={3} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
