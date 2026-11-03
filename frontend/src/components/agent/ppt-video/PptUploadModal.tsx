'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, App, Button, Form, Input, Modal, Select, Slider, Space, Typography, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { InboxOutlined } from '@ant-design/icons'

import { createPptVideoProject } from '@/actions/agent/ppt-video'
import type { LanguageCode, VoiceOption } from '@/types/agent/ppt-video'

interface Props {
  open: boolean
  voices: VoiceOption[]
  onClose: () => void
}

interface FormValues {
  name?: string
  default_language: LanguageCode
  default_voice_id?: string
  speed: number
}

/**
 * 新建项目：PPT 必填，逐页讲稿可选。
 *
 * 文件不直传后端：Upload 只做本地选取（beforeUpload 返回 false），提交时
 * 由 Server Action 组装 FormData，避免客户端直接 fetch 写接口。
 */
export default function PptUploadModal({ open, voices, onClose }: Props) {
  const { message } = App.useApp()
  const router = useRouter()
  const [form] = Form.useForm<FormValues>()
  const [pptFiles, setPptFiles] = useState<UploadFile[]>([])
  const [scriptFiles, setScriptFiles] = useState<UploadFile[]>([])
  const [submitting, setSubmitting] = useState(false)

  const language = Form.useWatch('default_language', form) ?? 'zh'
  const languageVoices = useMemo(() => voices.filter((voice) => voice.language === language), [voices, language])

  // 弹窗由列表条件挂载（关闭即卸载），表单与文件列表天然是空的，不在这里 resetFields
  const handleLanguage = (next: LanguageCode) => {
    const fallback = voices.find((voice) => voice.language === next)
    form.setFieldsValue({ default_voice_id: fallback?.voice_id })
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const ppt = pptFiles[0]?.originFileObj as File | undefined
    if (!ppt) {
      message.error('请选择要上传的 PPT 文件')
      return
    }
    const script = scriptFiles[0]?.originFileObj as File | undefined

    const payload = new FormData()
    payload.append('file', ppt)
    payload.append('name', values.name?.trim() || ppt.name.replace(/\.[^.]+$/, ''))
    payload.append('default_language', values.default_language)
    if (values.default_voice_id) payload.append('default_voice_id', values.default_voice_id)
    payload.append('speed', String(values.speed ?? 1))
    if (script) payload.append('script_file', script)

    setSubmitting(true)
    const result = await createPptVideoProject(payload)
    setSubmitting(false)

    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    message.success(result.message)
    onClose()
    router.push(`/agent/ppt-videos/${result.data.id}`)
    router.refresh()
  }

  return (
    <Modal
      title="新建 PPT 配音视频"
      open={open}
      onCancel={onClose}
      onOk={handleSubmit}
      okText="上传并打开工作台"
      cancelText="取消"
      confirmLoading={submitting}
      width={620}
      destroyOnHidden
    >
      <Form<FormValues>
        form={form}
        layout="vertical"
        className="mt-3"
        initialValues={{ default_language: 'zh', speed: 1 }}
      >
        <Form.Item label="PPT 文件（.ppt / .pptx，单文件 ≤100MB）" required>
          <Upload.Dragger
            accept=".ppt,.pptx"
            maxCount={1}
            multiple={false}
            beforeUpload={() => false}
            fileList={pptFiles}
            onChange={({ fileList }) => setPptFiles(fileList.slice(-1))}
            onRemove={() => {
              setPptFiles([])
              return true
            }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">点击或拖拽 PPT 到此处</p>
            <p className="ant-upload-hint">第 1 页自动作为片头，正文从第 2 页开始；页面按 1920×1080 等比留边渲染</p>
          </Upload.Dragger>
        </Form.Item>

        <Form.Item
          label="逐页讲稿（可选，.txt / .md / .docx）"
          extra="每页一段，用空行或「---」分隔；不上传也没关系，系统会读取每页文字自动生成初稿，已有讲稿的页面不会被覆盖"
        >
          <Upload
            accept=".txt,.md,.docx"
            maxCount={1}
            multiple={false}
            beforeUpload={() => false}
            fileList={scriptFiles}
            onChange={({ fileList }) => setScriptFiles(fileList.slice(-1))}
            onRemove={() => {
              setScriptFiles([])
              return true
            }}
          >
            <Button>选择讲稿文件</Button>
          </Upload>
        </Form.Item>

        <Form.Item label="项目名" name="name" extra="留空则用文件名">
          <Input placeholder="例如：2026 年 Q1 研发进展汇报" maxLength={255} />
        </Form.Item>

        <Space size={12} className="w-full" align="start">
          <Form.Item label="默认语言" name="default_language" className="!mb-0">
            <Select<LanguageCode>
              style={{ width: 140 }}
              onChange={handleLanguage}
              options={[
                { value: 'zh', label: '中文' },
                { value: 'en', label: '英文' },
              ]}
            />
          </Form.Item>
          <Form.Item label="默认音色" name="default_voice_id" className="!mb-0">
            <Select
              style={{ width: 260 }}
              allowClear
              placeholder="跟随系统默认"
              options={languageVoices.map((voice) => ({
                value: voice.voice_id,
                label: `${voice.display_name}（${voice.gender === 'female' ? '女' : '男'}）`,
              }))}
            />
          </Form.Item>
        </Space>

        <Form.Item label="默认语速" name="speed" className="!mt-4 !mb-0">
          <Slider min={0.5} max={2} step={0.05} tooltip={{ formatter: (value) => `${value?.toFixed(2)}x` }} />
        </Form.Item>

        <Alert
          className="!mt-3"
          type="info"
          showIcon
          message="上传后先出页面图，AI 自动生成逐页讲稿初稿"
          description={
            <Typography.Text className="text-[12px]">
              创建只需几秒；初稿在后台按页生成，进工作台可直接改，改完逐页试听，不用等整片渲染。
              纯图片页没有可识别的文字，需要手工填写。
            </Typography.Text>
          }
        />
      </Form>
    </Modal>
  )
}