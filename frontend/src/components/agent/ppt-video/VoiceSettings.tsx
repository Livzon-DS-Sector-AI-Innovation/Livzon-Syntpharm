'use client'

import { useMemo, useState } from 'react'
import { App, Button, Input, Select, Slider, Space, Tag, Typography } from 'antd'
import { SaveOutlined } from '@ant-design/icons'

import { updateProjectSettings } from '@/actions/agent/ppt-video'
import type { LanguageCode, ProjectDetail, VoiceOption } from '@/types/agent/ppt-video'

interface Props {
  detail: ProjectDetail
  voices: VoiceOption[]
  onDetailChange: (detail: ProjectDetail) => void
}

const LANGUAGE_LABEL: Record<LanguageCode, string> = { zh: '中文', en: '英文' }

/**
 * 右栏属性区：项目默认语言 / 音色 / 语速。
 *
 * 这些是「未被单页覆盖的页」的取值来源，改动会让正文 key 变化（body_stale），
 * 因此保存后提示用户按需重新生成，而不是悄悄复用旧成片。
 */
export default function VoiceSettings({ detail, voices, onDetailChange }: Props) {
  const { message } = App.useApp()
  const [name, setName] = useState(detail.name)
  const [language, setLanguage] = useState<LanguageCode>(detail.default_language)
  const [voiceId, setVoiceId] = useState(detail.default_voice_id)
  const [speed, setSpeed] = useState(detail.speed)
  const [saving, setSaving] = useState(false)

  // 草稿随项目切换重置（父组件用 key=project.id 重挂载），轮询刷新不会打断正在编辑的值
  const languageVoices = useMemo(() => voices.filter((voice) => voice.language === language), [voices, language])

  const handleLanguage = (next: LanguageCode) => {
    setLanguage(next)
    // 语言变了音色必须跟着换，否则后端会按「音色与语言不匹配」拒绝
    const fallback = voices.find((voice) => voice.language === next)
    setVoiceId(fallback?.voice_id ?? '')
  }

  const handleSave = async () => {
    setSaving(true)
    const result = await updateProjectSettings(detail.id, {
      name: name.trim() || detail.name,
      default_language: language,
      default_voice_id: voiceId,
      speed,
    })
    setSaving(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    if (result.data) onDetailChange(result.data)
    message.success('默认设置已保存，按上方提示决定是否重新生成')
  }

  const currentVoice = voices.find((voice) => voice.voice_id === detail.default_voice_id)

  return (
    <div className="rounded-xl border border-[#E5E3DF] bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <Typography.Text strong>项目默认</Typography.Text>
        <Tag color={detail.status === 'ready' ? 'green' : detail.status === 'failed' ? 'red' : 'default'}>
          {detail.status === 'ready' ? '已出片' : detail.status === 'failed' ? '失败' : '草稿'}
        </Tag>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <Typography.Text type="secondary" className="text-[12px]">
            项目名
          </Typography.Text>
          <Input className="mt-1" value={name} onChange={(event) => setName(event.target.value)} maxLength={255} />
        </div>

        <div>
          <Typography.Text type="secondary" className="text-[12px]">
            默认语言
          </Typography.Text>
          <Select<LanguageCode>
            className="mt-1 w-full"
            value={language}
            onChange={handleLanguage}
            options={[
              { value: 'zh', label: '中文' },
              { value: 'en', label: '英文' },
            ]}
          />
        </div>

        <div>
          <Typography.Text type="secondary" className="text-[12px]">
            默认音色
          </Typography.Text>
          <Select
            className="mt-1 w-full"
            value={voiceId || undefined}
            placeholder="选择音色"
            onChange={setVoiceId}
            options={languageVoices.map((voice) => ({
              value: voice.voice_id,
              label: `${voice.display_name}（${LANGUAGE_LABEL[voice.language]}·${voice.gender === 'female' ? '女' : '男'}）`,
            }))}
          />
          {currentVoice && (
            <Typography.Text type="secondary" className="mt-1 block text-[11px]">
              {currentVoice.source} · {currentVoice.version} · {currentVoice.license}
            </Typography.Text>
          )}
        </div>

        <div>
          <Typography.Text type="secondary" className="text-[12px]">
            默认语速 {speed.toFixed(2)}x
          </Typography.Text>
          <Slider
            className="!mt-2"
            min={0.5}
            max={2}
            step={0.05}
            value={speed}
            onChange={setSpeed}
            tooltip={{ formatter: (value) => `${value?.toFixed(2)}x` }}
          />
        </div>
      </div>

      <Space className="mt-3 w-full" direction="vertical" size={4}>
        <Button type="primary" block icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
          保存默认设置
        </Button>
        <Typography.Text type="secondary" className="block text-[11px] leading-4">
          只影响「未单独设置语言/音色/语速」的页；改动后需重新生成正文。
        </Typography.Text>
      </Space>
    </div>
  )
}