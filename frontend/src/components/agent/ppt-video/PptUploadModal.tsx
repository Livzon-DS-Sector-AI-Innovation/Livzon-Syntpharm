'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Alert, App, Button, Form, Input, Modal, Select, Slider, Space, Typography, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { InboxOutlined } from '@ant-design/icons'

import UploadWaitingView, { type UploadPhase } from './UploadWaitingView'
import { UploadCanceledError, uploadPptVideoProject } from '@/lib/api/client/ppt-video-upload'
import type { LanguageCode, ProjectDetail, VoiceOption } from '@/types/agent/ppt-video'

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

/** 表单 → 上传中 → 服务端解析中；后两态统称「等待」 */
type Phase = 'form' | UploadPhase

/**
 * 新建项目：PPT 必填，逐页讲稿可选。
 *
 * 文件选取只做本地缓存（beforeUpload 返回 false）；提交由浏览器端 XHR 直传
 * （`lib/api/client/ppt-video-upload.ts`），为了拿真实上传百分比并能中断请求。
 *
 * 等待期间弹窗锁定（无关闭按钮、点遮罩/ESC 无效），唯一出口是「停止上传」；
 * 停止、出错、关页都视为取消本次新建，服务端靠断连检测回滚，不留半成品。
 */
export default function PptUploadModal({ open, voices, onClose }: Props) {
  const { message } = App.useApp()
  const router = useRouter()
  const [form] = Form.useForm<FormValues>()
  const [pptFiles, setPptFiles] = useState<UploadFile[]>([])
  const [scriptFiles, setScriptFiles] = useState<UploadFile[]>([])
  const [phase, setPhase] = useState<Phase>('form')
  const [percent, setPercent] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [stopping, setStopping] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  const waiting = phase !== 'form'
  const language = Form.useWatch('default_language', form) ?? 'zh'
  const languageVoices = useMemo(() => voices.filter((voice) => voice.language === language), [voices, language])

  // 等待期拦截刷新/关页：确认离开就中断请求；同时兜住组件被外部卸载（如路由切换）
  useEffect(() => {
    if (!waiting) return

    const beforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    const pageHide = () => abortRef.current?.abort()

    window.addEventListener('beforeunload', beforeUnload)
    window.addEventListener('pagehide', pageHide)
    return () => {
      window.removeEventListener('beforeunload', beforeUnload)
      window.removeEventListener('pagehide', pageHide)
    }
  }, [waiting])

  useEffect(() => () => abortRef.current?.abort(), [])

  // 弹窗由列表条件挂载（关闭即卸载），表单与文件列表天然是空的，不在这里 resetFields
  const handleLanguage = (next: LanguageCode) => {
    const fallback = voices.find((voice) => voice.language === next)
    form.setFieldsValue({ default_voice_id: fallback?.voice_id })
  }

  const handleStop = () => {
    if (!abortRef.current) return
    setStopping(true)
    abortRef.current.abort()
  }

  const handleSubmit = async () => {
    if (waiting) return

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

    const controller = new AbortController()
    abortRef.current = controller
    setError(null)
    setPercent(0)
    setStopping(false)
    setPhase('uploading')

    try {
      const detail: ProjectDetail = await uploadPptVideoProject({
        formData: payload,
        signal: controller.signal,
        onProgress: setPercent,
        onUploaded: () => setPhase('processing'),
      })
      setPhase('form')
      message.success('项目已创建，正在打开工作台')
      onClose()
      router.push(`/agent/ppt-videos/${detail.id}`)
      router.refresh()
    } catch (err) {
      setPhase('form')
      // 已选文件与表单值全部保留，用户改一下即可重试
      if (err instanceof UploadCanceledError) {
        message.info('已取消本次新建')
      } else {
        setError(err instanceof Error && err.message ? err.message : '上传失败，请稍后重试')
      }
    } finally {
      abortRef.current = null
      setStopping(false)
    }
  }

  return (
    <Modal
      title={waiting ? '正在创建项目' : '新建 PPT 配音视频'}
      open={open}
      onCancel={waiting ? undefined : onClose}
      onOk={handleSubmit}
      okText="上传并打开工作台"
      cancelText="取消"
      width={620}
      destroyOnHidden
      closable={!waiting}
      maskClosable={!waiting}
      keyboard={!waiting}
      footer={waiting ? null : undefined}
    >
      {waiting ? (
        <UploadWaitingView
          phase={phase}
          percent={percent}
          fileName={pptFiles[0]?.name ?? ''}
          stopping={stopping}
          onStop={handleStop}
        />
      ) : (
        <Form<FormValues>
          form={form}
          layout="vertical"
          className="mt-3"
          initialValues={{ default_language: 'zh', speed: 1 }}
        >
          {error && (
            <Alert
              type="error"
              showIcon
              closable
              message={error}
              description="本次新建已取消，不会生成项目；已选文件与填写内容都已保留，可直接重试。"
              onClose={() => setError(null)}
              className="!mb-3"
            />
          )}

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
              <p className="ant-upload-hint">
                第 1 页自动作为片头，正文从第 2 页开始；页面按 1920×1080 等比留边渲染
              </p>
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
                上传期间请勿关闭页面；解析完成后自动进入工作台。初稿在后台按页生成，进工作台可直接改，改完逐页试听，不用等整片渲染。
                纯图片页没有可识别的文字，需要手工填写。
              </Typography.Text>
            }
          />
        </Form>
      )}
    </Modal>
  )
}