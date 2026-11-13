'use client'


import { useState } from 'react'
import { UploadFile,  Form, Input, Upload, App, Card, Radio, Typography } from 'antd'
import {
  InboxOutlined, ArrowLeftOutlined, CheckCircleFilled,
  FileTextOutlined, AuditOutlined, SyncOutlined,
} from '@ant-design/icons'
import { useRouter } from 'next/navigation'
import type { AuditMode } from '@/types/validation-audit'
import {
  createValidationAuditTask,
  uploadValidationAuditFiles,
} from '@/actions/validation-audit'
import { RegistrationPageHeader } from '../RegistrationPageHeader'
import ui from '../registration-ui.module.css'
import { IconCheckSquare } from '../registration-icons'

const { Dragger } = Upload
const { Text } = Typography

const AUDIT_MODE_CARDS: { value: AuditMode; icon: React.ReactNode; title: string; desc: string; tint: string }[] = [
  {
    value: 'protocol',
    icon: <FileTextOutlined style={{ fontSize: 28 }} />,
    title: '验证方案审核',
    desc: '审核方案完整性、科学性、可执行性',
    tint: '#F3F4FE',
  },
  {
    value: 'report',
    icon: <AuditOutlined style={{ fontSize: 28 }} />,
    title: '验证报告审核',
    desc: '审核报告合规性、数据完整性、结论合理性',
    tint: '#EAF4FB',
  },
  {
    value: 'protocol_report',
    icon: <SyncOutlined style={{ fontSize: 28 }} />,
    title: '方案 + 报告联合审核',
    desc: '审核方案与报告一致性、执行闭环性',
    tint: '#E9F6F1',
  },
]

export default function ValidationAuditNewClient() {
  const { message } = App.useApp()
  const router = useRouter()
  const [form] = Form.useForm()
  const [submitting, setSubmitting] = useState(false)
  const [fileList, setFileList] = useState<UploadFile[]>([])
  const [auditMode, setAuditMode] = useState<AuditMode>('protocol')

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()

      if (fileList.length === 0) {
        message.error('请上传至少一个审核文件')
        return
      }

      setSubmitting(true)

      const createResult = await createValidationAuditTask({
        task_name: values.task_name,
        product_name: values.product_name,
        method_name: values.method_name,
        source_company: values.source_company,
        audit_mode: values.audit_mode,
      })

      if (!createResult.success || !createResult.data) {
        message.error(createResult.message)
        setSubmitting(false)
        return
      }

      const taskId = createResult.data.id as string as string as string

      const formData = new FormData()
      for (const file of fileList) {
        const originFile = file.originFileObj || file
        formData.append('files', originFile as File)
      }
      const fileType = values.audit_mode === 'protocol_report' ? 'protocol' : (values.audit_mode as string)
      formData.append('file_type', fileType)

      const uploadResult = await uploadValidationAuditFiles(taskId, formData)
      if (!uploadResult.success) {
        message.error(`文件上传失败: ${uploadResult.message as string}`)
        setSubmitting(false)
        return
      }

      message.success('任务创建成功，正在进入审核...')
      router.push(`/registration/validation-audit/${taskId}`)
    } catch (error) {
      if (error instanceof Error) {
        message.error((error instanceof Error ? error.message : null))
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className={ui.regUi}>
      {/* Header */}
      <RegistrationPageHeader
        icon={IconCheckSquare}
        title="新建验证审核任务"
        sub="填写基本信息、选择审核模式、上传待审核文件"
        actions={
          <button
            type="button"
            className={ui.btn}
            onClick={() => router.push('/registration/validation-audit')}
          >
            <ArrowLeftOutlined />
            返回列表
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Task Info */}
        <div className="space-y-6">
          {/* Audit Mode */}
          <Card
            style={{ borderRadius: 12, border: '1px solid var(--line)' }}
            styles={{ body: { padding: '24px' } }}
          >
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[var(--brand-600)] text-white text-[11px] font-semibold">1</span>
                <span className="text-[15px] font-medium text-[var(--ink-1)]">选择审核模式</span>
              </div>
              <Text type="secondary" className="text-[12px] ml-7">
                根据审核范围选择对应模式
              </Text>
            </div>

            <Form form={form} layout="vertical" initialValues={{ audit_mode: 'protocol' }}>
              <Form.Item name="audit_mode" noStyle>
                <Radio.Group
                  value={auditMode}
                  onChange={(e) => {
                    setAuditMode(e.target.value)
                    form.setFieldValue('audit_mode', e.target.value)
                  }}
                  className="w-full"
                >
                  <div className="grid grid-cols-3 gap-3">
                    {AUDIT_MODE_CARDS.map((card) => (
                      <Radio.Button
                        key={card.value}
                        value={card.value}
                        className="!h-auto !rounded-lg !border-[var(--line)] !py-4 !px-3 !text-left"
                        style={{
                          backgroundColor: auditMode === card.value ? card.tint : 'var(--bg)',
                          borderColor: auditMode === card.value ? 'var(--brand-600)' : undefined,
                        }}
                      >
                        <div className="flex flex-col items-center text-center gap-2">
                          <div style={{ color: auditMode === card.value ? 'var(--brand-600)' : 'var(--ink-2)' }}>
                            {card.icon}
                          </div>
                          <div className="text-[13px] font-medium text-[var(--ink-1)]">
                            {card.title}
                          </div>
                          <div className="text-[11px] text-[var(--ink-2)] leading-snug">
                            {card.desc}
                          </div>
                        </div>
                      </Radio.Button>
                    ))}
                  </div>
                </Radio.Group>
              </Form.Item>
            </Form>
          </Card>

          {/* Task Info Form */}
          <Card
            style={{ borderRadius: 12, border: '1px solid var(--line)' }}
            styles={{ body: { padding: '24px' } }}
          >
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[var(--brand-600)] text-white text-[11px] font-semibold">2</span>
                <span className="text-[15px] font-medium text-[var(--ink-1)]">填写任务信息</span>
              </div>
            </div>

            <Form form={form} layout="vertical">
              <Form.Item
                name="task_name"
                label={<span className="text-[13px] font-medium">任务名称</span>}
                rules={[{ required: true, message: '请输入任务名称' }]}
              >
                <Input placeholder="如：XX品种HPLC含量测定验证方案审核" maxLength={300} style={{ borderRadius: 8 }} />
              </Form.Item>

              <div className="grid grid-cols-2 gap-4">
                <Form.Item
                  name="product_name"
                  label={<span className="text-[13px] font-medium">品种名称</span>}
                  rules={[{ required: true, message: '请输入品种名称' }]}
                >
                  <Input placeholder="如：盐酸万古霉素" maxLength={200} style={{ borderRadius: 8 }} />
                </Form.Item>

                <Form.Item
                  name="method_name"
                  label={<span className="text-[13px] font-medium">方法名称</span>}
                  rules={[{ required: true, message: '请输入方法名称' }]}
                >
                  <Input placeholder="如：HPLC含量测定" maxLength={300} style={{ borderRadius: 8 }} />
                </Form.Item>
              </div>

              <Form.Item
                name="source_company"
                label={<span className="text-[13px] font-medium">来源公司</span>}
                rules={[{ required: true, message: '请输入来源公司' }]}
                className="mb-0"
              >
                <Input placeholder="文件提供方公司名称" maxLength={300} style={{ borderRadius: 8 }} />
              </Form.Item>
            </Form>
          </Card>
        </div>

        {/* Right Column: File Upload */}
        <div className="space-y-6">
          <Card
            style={{ borderRadius: 12, border: '1px solid var(--line)' }}
            styles={{ body: { padding: '24px' } }}
            className="h-full"
          >
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-[var(--brand-600)] text-white text-[11px] font-semibold">3</span>
                <span className="text-[15px] font-medium text-[var(--ink-1)]">上传审核文件</span>
              </div>
              <Text type="secondary" className="text-[12px] ml-7">
                {auditMode === 'protocol_report'
                  ? '请同时上传验证方案和验证报告'
                  : auditMode === 'protocol' ? '请上传验证方案文件' : '请上传验证报告文件'}
              </Text>
            </div>

            <Dragger
              multiple
              accept=".docx,.pdf"
              fileList={fileList}
              beforeUpload={() => false}
              onChange={({ fileList: newList }) => setFileList(newList)}
              style={{
                borderRadius: 10,
                padding: '40px 0',
                backgroundColor: 'var(--bg)',
                borderColor: 'var(--line)',
              }}
            >
              <p className="text-[48px] text-[var(--brand-600)] mb-3">
                <InboxOutlined />
              </p>
              <p className="text-[15px] text-[var(--ink-1)] mb-1 font-medium">
                点击或拖拽文件到此区域
              </p>
              <p className="text-[12px] text-[var(--ink-3)]">
                支持 DOCX、PDF 格式，单文件不超过 50MB
              </p>
            </Dragger>

            {fileList.length > 0 && (
              <div className="mt-4 space-y-2">
                <Text type="secondary" className="text-[12px] font-medium">已选择文件：</Text>
                {fileList.map((f, idx) => (
                  <div key={idx} className="flex items-center justify-between px-3 py-2 bg-[var(--brand-50)] rounded-lg text-[13px]">
                    <span className="text-[var(--ink-1)] truncate mr-2">
                      <FileTextOutlined className="mr-2 text-[var(--brand-600)]" />
                      {f.name}
                    </span>
                    <span className="text-[var(--ink-3)] shrink-0">
                      {((f.size || 0) / 1024 / 1024).toFixed(2)} MB
                    </span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-3 mt-6 pb-8">
        <button
          type="button"
          className={ui.btn}
          onClick={() => router.push('/registration/validation-audit')}
        >
          取消
        </button>
        <button
          type="button"
          className={ui.btnPrimary}
          onClick={handleSubmit}
          disabled={fileList.length === 0 || submitting}
          style={{ minWidth: 160 }}
        >
          {!submitting && <CheckCircleFilled />}
          {submitting ? '创建中...' : '创建并开始审核'}
        </button>
      </div>
    </div>
  )
}
