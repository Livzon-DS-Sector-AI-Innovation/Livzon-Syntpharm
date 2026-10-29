'use client'

import { useState } from 'react'
import { useQuery, keepPreviousData } from '@tanstack/react-query'
import { DataUnavailable } from '@/components/common/DataUnavailable'
import { UploadFile, Table, Input, Button, Space, App, Card, Modal, Form, Upload } from 'antd'
import { UploadOutlined, DownloadOutlined, DeleteOutlined } from '@ant-design/icons'
import { SupplementaryReplyListItem } from '@/types/registration'
import { fetchSupplementaryReplies, fetchSupplementaryReplyDownloadUrl } from '@/lib/api/client/registration'
import { generateSupplementaryReply, deleteSupplementaryReplyAction } from '@/actions/registration'
import dayjs from 'dayjs'

interface SupplementaryReplyClientProps {
  initialReplies: SupplementaryReplyListItem[]
  initialTotal: number
}

export default function SupplementaryReplyClient({
  initialReplies,
  initialTotal,
}: SupplementaryReplyClientProps) {
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
  const [form] = Form.useForm()
  const [noticeFileList, setNoticeFileList] = useState<UploadFile[]>([])
  const [templateFileList, setTemplateFileList] = useState<UploadFile[]>([])

  const isInitialQuery = query.page === 1 && query.pageSize === 20 && !query.drugName

  const repliesQuery = useQuery({
    queryKey: ['supplementary-replies', query],
    queryFn: async () => {
      const res = await fetchSupplementaryReplies({
        drug_name: query.drugName || undefined,
        page: query.page,
        page_size: query.pageSize,
      })
      return { items: res.data, total: res.meta?.total || 0 }
    },
    placeholderData: keepPreviousData,
    // 首屏首页直接用服务端已取好的数据，避免闪一次 loading；其余页码必须真取
    initialData: isInitialQuery ? { items: initialReplies, total: initialTotal } : undefined,
  })

  const replies = repliesQuery.data?.items ?? []
  const total = repliesQuery.data?.total ?? 0

  // 搜索：条件与当前一致时强制重取，否则提交新条件（页码回到 1）
  const handleSearch = () => {
    const nextDrugName = drugName.trim()
    if (nextDrugName === query.drugName && query.page === 1) {
      void repliesQuery.refetch()
      return
    }
    setQuery({ page: 1, pageSize: query.pageSize, drugName: nextDrugName })
  }

  const handlePageChange = (newPage: number, newPageSize: number) => {
    setQuery(prev => ({ ...prev, page: newPage, pageSize: newPageSize }))
  }

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()
      
      if (noticeFileList.length === 0) {
        message.error('请上传CDE通知函PDF')
        return
      }

      setGenerating(true)
      
      const formData = new FormData()
      formData.append('notice', noticeFileList[0].originFileObj as File)
      
      if (templateFileList.length > 0) {
        formData.append('template', templateFileList[0].originFileObj as File)
      }
      
      const result = await generateSupplementaryReply(formData, {
        drug_name: values.drug_name,
        registration_number: values.registration_number,
        acceptance_number: values.acceptance_number,
        company_name: values.company_name,
        remarks: values.remarks,
      })

      if (result.success) {
        message.success(result.message)
        setGenerateModalOpen(false)
        form.resetFields()
        setNoticeFileList([])
        setTemplateFileList([])
        void repliesQuery.refetch()
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
      await deleteSupplementaryReplyAction(id)
      message.success('删除成功')
      void repliesQuery.refetch()
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
      title: '登记号',
      dataIndex: 'registration_number',
      key: 'registration_number',
      width: 150,
    },
    {
      title: '受理号',
      dataIndex: 'acceptance_number',
      key: 'acceptance_number',
      width: 150,
    },
    {
      title: '问题数量',
      dataIndex: 'question_count',
      key: 'question_count',
      width: 100,
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
      render: (_: unknown, record: SupplementaryReplyListItem) => (
        <Space>
          <Button
            type="link"
            icon={<DownloadOutlined />}
            onClick={async () => { const url = await fetchSupplementaryReplyDownloadUrl(record.id); window.open(url, "_blank"); }}
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
        发补回复管理
      </h1>
      <p className="text-[14px] text-[var(--color-steel)] mb-4">
        根据CDE补充资料通知函自动生成发补回复Word文档
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
            生成发补回复
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={replies}
          rowKey="id"
          loading={repliesQuery.isPending}
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
          scroll={{ x: 1200 }}
          locale={{
            // 取数失败时在表格内嵌降级区块，与「确实没有记录」的空态区分开
            emptyText: repliesQuery.isError ? (
              <DataUnavailable compact onRetry={() => void repliesQuery.refetch()} />
            ) : undefined,
          }}
        />
      </Card>

      <Modal
        title="生成发补回复文档"
        open={generateModalOpen}
        onOk={handleGenerate}
        onCancel={() => {
          setGenerateModalOpen(false)
          form.resetFields()
          setNoticeFileList([])
          setTemplateFileList([])
        }}
        confirmLoading={generating}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="notice"
            label="CDE通知函（PDF）"
            rules={[{ required: true, message: '请上传CDE通知函PDF' }]}
          >
            <Upload
              beforeUpload={() => false}
              fileList={noticeFileList}
              onChange={({ fileList }) => setNoticeFileList(fileList)}
              maxCount={1}
              accept=".pdf"
            >
              <Button icon={<UploadOutlined />}>选择 PDF 文件</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            name="template"
            label="公司模板（Word，可选）"
          >
            <Upload
              beforeUpload={() => false}
              fileList={templateFileList}
              onChange={({ fileList }) => setTemplateFileList(fileList)}
              maxCount={1}
              accept=".docx,.doc"
            >
              <Button icon={<UploadOutlined />}>选择 Word 文件（可选）</Button>
            </Upload>
          </Form.Item>

          <Form.Item
            name="drug_name"
            label="药品名称（可选，默认从PDF提取）"
          >
            <Input placeholder="如不填则自动从PDF提取" />
          </Form.Item>

          <Form.Item
            name="registration_number"
            label="登记号（可选）"
          >
            <Input placeholder="如不填则自动从PDF提取" />
          </Form.Item>

          <Form.Item
            name="acceptance_number"
            label="受理号（可选）"
          >
            <Input placeholder="如不填则自动从PDF提取" />
          </Form.Item>

          <Form.Item
            name="company_name"
            label="申请人/公司名称（可选）"
          >
            <Input placeholder="如不填则自动从PDF提取" />
          </Form.Item>

          <Form.Item name="remarks" label="备注">
            <Input.TextArea rows={3} placeholder="可选" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
