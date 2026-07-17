'use client'

import { useEffect, useState, useCallback, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Select, Card, Table, Button, Space, Upload, Modal, Form, Input, DatePicker, InputNumber, App } from 'antd'
import { UploadOutlined, DownloadOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  fetchDomesticApprovals, exportDomesticApprovals,
  fetchOverseasApprovals, exportOverseasApprovals,
  fetchInternationalReviews, exportInternationalReviews,
  fetchCoppCertificates, exportCoppCertificates,
  fetchWcCertificates, exportWcCertificates,
  fetchReviewingDrugs,
  type DomesticApproval, type OverseasApproval, type InternationalReview,
  type CoppCertificate, type WcCertificate, type ReviewingDrug,
} from '@/lib/api/client/registration-ledger'
import {
  createDomesticApproval, importDomesticApprovals,
  createOverseasApproval, importOverseasApprovals,
  createInternationalReview, importInternationalReviews,
  createCoppCertificate, importCoppCertificates,
  createWcCertificate, importWcCertificates,
} from '@/actions/registration-ledger'
import dayjs from 'dayjs'

type LedgerType = 'domestic' | 'overseas' | 'international' | 'copp' | 'wc' | 'reviewing'

const LEDGER_TYPES = [
  { value: 'domestic', label: '国内已获批' },
  { value: 'overseas', label: '国外已获批' },
  { value: 'international', label: '国际（关联审评）' },
  { value: 'copp', label: 'COPP证书' },
  { value: 'wc', label: 'WC证书' },
  { value: 'reviewing', label: '审评中' },
]

const NODE_NAMES = [
  '受理', '药学审评', '临床审评', '生产现场检查', '抽样检验',
  '标准复核', '审评报告', '审批', '制证', '送达'
]

function LedgerContent() {
  const { message } = App.useApp()
  const router = useRouter()
  const searchParams = useSearchParams()
  const urlType = searchParams.get('type') as LedgerType | null

  const [type, setType] = useState<LedgerType>(urlType || 'domestic')
  const [data, setData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    if (urlType && LEDGER_TYPES.some(t => t.value === urlType)) {
      setType(urlType)
    }
  }, [urlType])

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      let result: any[] = []
      switch (type) {
        case 'domestic': result = await fetchDomesticApprovals(); break
        case 'overseas': result = await fetchOverseasApprovals(); break
        case 'international': result = await fetchInternationalReviews(); break
        case 'copp': result = await fetchCoppCertificates(); break
        case 'wc': result = await fetchWcCertificates(); break
        case 'reviewing': result = await fetchReviewingDrugs(); break
      }
      setData(result)
    } catch {
      message.error('加载数据失败')
    } finally {
      setLoading(false)
    }
  }, [type])

  useEffect(() => { loadData() }, [loadData])

  const handleImport = async (file: File) => {
    console.log('🚀 Starting import, file:', file.name, 'type:', type)
    try {
      let result: any
      switch (type) {
        case 'domestic': result = await importDomesticApprovals(file); break
        case 'overseas': result = await importOverseasApprovals(file); break
        case 'international': result = await importInternationalReviews(file); break
        case 'copp': result = await importCoppCertificates(file); break
        case 'wc': result = await importWcCertificates(file); break
      }
      console.log('✅ Import result:', result)
      
      const data = result?.data
      if (data?.success_count === 0) {
        // 解析成功但没有有效数据
        message.warning(data?.message || '文件已解析但未导入有效数据，请检查表头或数据行')
      } else if (data?.success_count > 0) {
        // 成功导入
        message.success(data?.message || `成功导入 ${data.success_count} 条记录`)
        loadData()  // 只在有数据时刷新
      } else {
        // 其他情况
        message.success(data?.message || '导入成功')
        loadData()
      }
      
      // 如果有错误，显示错误详情
      if (data?.errors && data.errors.length > 0) {
        console.warn('⚠️ Import errors:', data.errors)
        message.error(`导入有 ${data.errors.length} 条错误，请查看控制台`)
      }
    } catch (err: any) {
      console.error('❌ Import error:', err)
      message.error(err?.message || '导入失败')
    }
    return false
  }

  const handleExport = () => {
    switch (type) {
      case 'domestic': exportDomesticApprovals(); break
      case 'overseas': exportOverseasApprovals(); break
      case 'international': exportInternationalReviews(); break
      case 'copp': exportCoppCertificates(); break
      case 'wc': exportWcCertificates(); break
    }
  }

  const handleAdd = async (values: any) => {
    try {
      const formatted = {
        ...values,
        issue_date: values.issue_date ? dayjs(values.issue_date).format('YYYY-MM-DD') : null,
        valid_until: values.valid_until ? dayjs(values.valid_until).format('YYYY-MM-DD') : null,
      }
      switch (type) {
        case 'domestic': await createDomesticApproval(formatted); break
        case 'overseas': await createOverseasApproval(formatted); break
        case 'international': await createInternationalReview(formatted); break
        case 'copp': await createCoppCertificate(formatted); break
        case 'wc': await createWcCertificate(formatted); break
      }
      message.success('添加成功')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch {
      message.error('添加失败')
    }
  }

  const handleTypeChange = (val: LedgerType) => {
    setType(val)
    router.push(`/registration/ledger?type=${val}`)
  }

  const getColumns = (): ColumnsType<any> => {
    if (type === 'reviewing') {
      return [
        { title: '药品名称', dataIndex: 'product_name', key: 'product_name', width: 150 },
        { title: '药品类型', dataIndex: 'drug_type', key: 'drug_type', width: 100 },
        { title: '受理日期', dataIndex: 'acceptance_date', key: 'acceptance_date', width: 110 },
        { title: '当前节点', dataIndex: 'current_node', key: 'current_node', width: 90,
          render: (v: number) => v ? `第${v}节点` : '-' },
        ...NODE_NAMES.map((name, idx) => ({
          title: name,
          dataIndex: `node_${idx + 1}`,
          key: `node_${idx + 1}`,
          width: 100,
          render: (v: string | null) => v || '-',
        })),
      ]
    }
    
    switch (type) {
      case 'domestic':
        return [
          { title: '品名', dataIndex: 'product_name', key: 'product_name', width: 150 },
          { title: '证书名称', dataIndex: 'certificate_name', key: 'certificate_name', width: 120 },
          { title: '批件号', dataIndex: 'batch_no', key: 'batch_no', width: 150 },
          { title: '国家/发证机关', dataIndex: 'issuing_authority', key: 'issuing_authority', width: 120 },
          { title: '发证日期', dataIndex: 'issue_date', key: 'issue_date', width: 110 },
          { title: '证书有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 120 },
          { title: '产品范围', dataIndex: 'product_scope', key: 'product_scope', ellipsis: true },
          { title: '质量标准', dataIndex: 'quality_standard', key: 'quality_standard', ellipsis: true },
          { title: '登记号', dataIndex: 'registration_no', key: 'registration_no', width: 120 },
          { title: '证书是否过期', dataIndex: 'is_expired', key: 'is_expired', width: 110 },
          { title: '生产车间', dataIndex: 'production_workshop', key: 'production_workshop', width: 120 },
          { title: '产品有效期', dataIndex: 'product_validity', key: 'product_validity', width: 110 },
          { title: '贮存条件', dataIndex: 'storage_condition', key: 'storage_condition', ellipsis: true },
        ]
      case 'overseas':
        return [
          { title: '品名', dataIndex: 'product_name', key: 'product_name', width: 150 },
          { title: '证书名称', dataIndex: 'certificate_name', key: 'certificate_name', width: 120 },
          { title: '批件号', dataIndex: 'batch_no', key: 'batch_no', width: 150 },
          { title: '国家/发证机关', dataIndex: 'issuing_authority', key: 'issuing_authority', width: 120 },
          { title: '发证日期', dataIndex: 'issue_date', key: 'issue_date', width: 110 },
          { title: '证书有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 120 },
          { title: '产品范围', dataIndex: 'product_scope', key: 'product_scope', ellipsis: true },
          { title: '质量标准', dataIndex: 'quality_standard', key: 'quality_standard', ellipsis: true },
          { title: '证书是否过期', dataIndex: 'is_expired', key: 'is_expired', width: 110 },
          { title: '生产车间', dataIndex: 'production_workshop', key: 'production_workshop', width: 120 },
          { title: '产品有效期', dataIndex: 'product_validity', key: 'product_validity', width: 110 },
          { title: '贮存条件', dataIndex: 'storage_condition', key: 'storage_condition', ellipsis: true },
        ]
      case 'international':
        return [
          { title: '品名', dataIndex: 'product_name', key: 'product_name', width: 150 },
          { title: '获批国家', dataIndex: 'approved_countries', key: 'approved_countries', ellipsis: true },
          { title: '获批国家数量', dataIndex: 'approved_country_count', key: 'approved_country_count', width: 120 },
          { title: '获批客户', dataIndex: 'approved_clients', key: 'approved_clients', ellipsis: true },
          { title: '获批客户数量', dataIndex: 'approved_client_count', key: 'approved_client_count', width: 120 },
          { title: '审评中 - 国家', dataIndex: 'reviewing_countries', key: 'reviewing_countries', ellipsis: true },
          { title: '审评中 - 国家数量', dataIndex: 'reviewing_country_count', key: 'reviewing_country_count', width: 130 },
          { title: '审评中 - 客户', dataIndex: 'reviewing_clients', key: 'reviewing_clients', ellipsis: true },
          { title: '审评中 - 客户数量', dataIndex: 'reviewing_client_count', key: 'reviewing_client_count', width: 130 },
        ]
      case 'copp':
        return [
          { title: '品名', dataIndex: 'product_name', key: 'product_name', width: 150 },
          { title: '证书名称', dataIndex: 'certificate_name', key: 'certificate_name', width: 120 },
          { title: '批件号', dataIndex: 'batch_no', key: 'batch_no', width: 150 },
          { title: '国家/发证机关', dataIndex: 'issuing_authority', key: 'issuing_authority', width: 120 },
          { title: '发证日期', dataIndex: 'issue_date', key: 'issue_date', width: 110 },
          { title: '证书有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 120 },
          { title: '产品范围', dataIndex: 'product_scope', key: 'product_scope', ellipsis: true },
          { title: '适用国家', dataIndex: 'applicable_countries', key: 'applicable_countries', ellipsis: true },
          { title: '证书是否过期', dataIndex: 'is_expired', key: 'is_expired', width: 110 },
        ]
      case 'wc':
        return [
          { title: '品名', dataIndex: 'product_name', key: 'product_name', width: 150 },
          { title: '证书名称', dataIndex: 'certificate_name', key: 'certificate_name', width: 120 },
          { title: '批件号', dataIndex: 'batch_no', key: 'batch_no', width: 150 },
          { title: '国家/发证机关', dataIndex: 'issuing_authority', key: 'issuing_authority', width: 120 },
          { title: '发证日期', dataIndex: 'issue_date', key: 'issue_date', width: 110 },
          { title: '证书有效期至', dataIndex: 'valid_until', key: 'valid_until', width: 120 },
          { title: '产品范围', dataIndex: 'product_scope', key: 'product_scope', ellipsis: true },
          { title: '证书是否过期', dataIndex: 'is_expired', key: 'is_expired', width: 110 },
        ]
    }
  }

  const getTitle = () => {
    const found = LEDGER_TYPES.find(t => t.value === type)
    return found ? found.label : '注册台账'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-2">注册台账</h1>
        <p className="text-[14px] text-[var(--color-steel)]">管理公司注册证书和审评信息</p>
      </div>

      <Card>
        <div className="flex items-center justify-between mb-4">
          <Select
            value={type}
            onChange={handleTypeChange}
            options={LEDGER_TYPES}
            style={{ width: 200 }}
            size="large"
          />
          <Space>
            {type !== 'reviewing' && (
              <>
                <Upload beforeUpload={handleImport} accept=".xlsx,.xls" showUploadList={false}>
                  <Button icon={<UploadOutlined />}>导入 Excel</Button>
                </Upload>
                <Button icon={<DownloadOutlined />} onClick={handleExport}>导出 Excel</Button>
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                  手动添加
                </Button>
              </>
            )}
          </Space>
        </div>

        <Table
          columns={getColumns()}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 'max-content' }}
          size="small"
        />
      </Card>

      {type !== 'reviewing' && (
        <Modal
          title={`添加${getTitle()}记录`}
          open={modalOpen}
          onCancel={() => { setModalOpen(false); form.resetFields() }}
          onOk={() => form.submit()}
          width={600}
        >
          <Form form={form} layout="vertical" onFinish={handleAdd}>
            <Form.Item name="product_name" label="品名" rules={[{ required: true, message: '请输入品名' }]}>
              <Input />
            </Form.Item>
            {type !== 'international' && (
              <>
                <Form.Item name="certificate_name" label="证书名称">
                  <Input />
                </Form.Item>
                <Form.Item name="batch_no" label="批件号">
                  <Input />
                </Form.Item>
                <Form.Item name="issuing_authority" label="国家/发证机关">
                  <Input />
                </Form.Item>
                <Form.Item name="issue_date" label="发证日期">
                  <DatePicker className="w-full" />
                </Form.Item>
                <Form.Item name="valid_until" label="证书有效期至">
                  <DatePicker className="w-full" />
                </Form.Item>
              </>
            )}
            {type === 'domestic' && (
              <>
                <Form.Item name="registration_no" label="登记号">
                  <Input />
                </Form.Item>
                <Form.Item name="production_workshop" label="生产车间">
                  <Input />
                </Form.Item>
              </>
            )}
            {type === 'copp' && (
              <Form.Item name="applicable_countries" label="适用国家">
                <Input />
              </Form.Item>
            )}
            {type === 'international' && (
              <>
                <Form.Item name="approved_countries" label="获批国家">
                  <Input.TextArea />
                </Form.Item>
                <Form.Item name="approved_country_count" label="获批国家数量">
                  <InputNumber className="w-full" />
                </Form.Item>
                <Form.Item name="approved_clients" label="获批客户">
                  <Input.TextArea />
                </Form.Item>
                <Form.Item name="approved_client_count" label="获批客户数量">
                  <InputNumber className="w-full" />
                </Form.Item>
                <Form.Item name="reviewing_countries" label="审评中 - 国家">
                  <Input.TextArea />
                </Form.Item>
                <Form.Item name="reviewing_country_count" label="审评中 - 国家数量">
                  <InputNumber className="w-full" />
                </Form.Item>
                <Form.Item name="reviewing_clients" label="审评中 - 客户">
                  <Input.TextArea />
                </Form.Item>
                <Form.Item name="reviewing_client_count" label="审评中 - 客户数量">
                  <InputNumber className="w-full" />
                </Form.Item>
              </>
            )}
          </Form>
        </Modal>
      )}
    </div>
  )
}

export default function LedgerPage() {
  return (
    <Suspense>
      <LedgerContent />
    </Suspense>
  )
}
