'use client'

import { useMemo, useState } from 'react'
import { Alert, App, Button, Input, Select, Slider, Space, Tag, Typography } from 'antd'
import { RobotOutlined, SaveOutlined, SoundOutlined } from '@ant-design/icons'

import { previewSlide, rewriteScripts, saveSlideScript } from '@/actions/agent/ppt-video'
import { fetchPptVideoDetail } from '@/lib/api/client/agent'
import {
  formatDuration,
  type LanguageCode,
  type ProjectDetail,
  type SlideItem,
  type VoiceOption,
} from '@/types/agent/ppt-video'

const { TextArea } = Input

/** 讲稿来源标签：避免用户误以为 AI 初稿是自己写的 */
const SOURCE_LABEL: Record<string, { text: string; color?: string }> = {
  ai: { text: 'AI 初稿', color: 'purple' },
  upload: { text: '上传讲稿', color: 'blue' },
  manual: { text: '手工编辑', color: 'green' },
}

interface Props {
  detail: ProjectDetail
  slide: SlideItem
  voices: VoiceOption[]
  onDetailChange: (detail: ProjectDetail) => void
}

/**
 * 中栏编辑区：剧场底大图 + 讲稿 + 单页覆盖（语言/音色/语速）+ 试听。
 *
 * 页级覆盖留空即跟随项目默认；清空用「跟随默认」按钮，避免把空串写进库。
 */
export default function SlideEditor({ detail, slide, voices, onDetailChange }: Props) {
  const { message } = App.useApp()
  const [scriptText, setScriptText] = useState(slide.script_text ?? '')
  const [language, setLanguage] = useState<LanguageCode | undefined>(slide.language ?? undefined)
  const [voiceId, setVoiceId] = useState<string | undefined>(slide.voice_id ?? undefined)
  const [speed, setSpeed] = useState<number | undefined>(slide.speed ?? undefined)
  const [saving, setSaving] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [rewriting, setRewriting] = useState(false)
  // 库里的配音地址优先；试听后就地覆盖，不必等整页重新拉取
  const [audioOverride, setAudioOverride] = useState<string | null | undefined>(undefined)
  const audioUrl = audioOverride !== undefined ? audioOverride : (slide.audio_url ?? null)

  // 切页由父组件用 key 重新挂载本组件完成重置，不在这里 setState（避免级联渲染）

  const effectiveLanguage: LanguageCode = language ?? detail.default_language
  const source = SOURCE_LABEL[slide.script_source] ?? null
  // 无页内文字 → AI 不会生成；生成中 → 空稿只是「还没轮到」
  const noSourceText = !slide.has_page_text && !scriptText.trim()
  const drafting =
    !scriptText.trim() && ['queued', 'running'].includes(detail.script_ai?.status ?? '')
  const languageVoices = useMemo(
    () => voices.filter((voice) => voice.language === effectiveLanguage),
    [voices, effectiveLanguage],
  )

  const handleSave = async () => {
    setSaving(true)
    const result = await saveSlideScript(
      detail.id,
      slide.slide_uid,
      {
        script_text: scriptText,
        language: language ?? null,
        voice_id: voiceId ?? null,
        speed: speed ?? null,
        clear_language: !language,
        clear_voice: !voiceId,
        clear_speed: speed === undefined,
      },
      slide.slide_no,
    )
    setSaving(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    if (result.data) onDetailChange(result.data)
    message.success(result.message)
  }

  /** 单页改写走同步（background=false），拿到结果后直接回填编辑框 */
  const handleRewriteOne = async () => {
    setRewriting(true)
    const result = await rewriteScripts(detail.id, {
      mode: 'rewrite_one',
      slide_uids: [slide.slide_uid],
      instruction: null,
      background: false,
    })
    setRewriting(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    if (result.data?.status === 'failed') {
      message.error(result.data.errors?.[0] || '本页改写失败，请检查模型配置')
      return
    }
    try {
      const fresh = await fetchPptVideoDetail(detail.id)
      onDetailChange(fresh)
      const next = (fresh.slides ?? []).find((item) => item.slide_uid === slide.slide_uid)
      if (next) setScriptText(next.script_text ?? '')
      message.success('已按当前画面重写本页，记得试听确认')
    } catch (error) {
      console.warn('改写后刷新详情失败:', error)
      message.warning('改写已完成，但刷新内容失败，请手动刷新页面')
    }
  }

  const handlePreview = async () => {
    setPreviewing(true)
    const result = await previewSlide(detail.id, slide.slide_uid)
    setPreviewing(false)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setAudioOverride(result.data.audio_url ?? null)
    message.success(`旁白已就绪，时长 ${formatDuration(result.data.duration_ms)}，可试听确认`)
  }

  return (
    <div className="flex h-full flex-col gap-3 overflow-y-auto">
      <div className="rounded-xl border border-[#E5E3DF] bg-[#141414] p-3">
        <div className="flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-black">
          {slide.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={slide.image_url}
              alt={`第 ${slide.slide_no} 页预览`}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <Typography.Text className="!text-[#A4A097]">
              页面图尚未生成（渲染任务完成后可见）
            </Typography.Text>
          )}
        </div>
        <div className="mt-2 flex items-center justify-between text-[12px] text-[#A4A097]">
          <span>1920×1080 · 等比留边不裁切</span>
          <span>
            第 {slide.slide_no} 页 / 共 {detail.slide_count} 页
          </span>
        </div>
      </div>

      <div className="rounded-xl border border-[#E5E3DF] bg-white p-4">
        <div className="mb-2 flex items-center justify-between">
          <Typography.Text strong>本页讲稿</Typography.Text>
          <Space size={6}>
            {source && (
              <Tag color={source.color} className="!m-0">
                {source.text}
              </Tag>
            )}
            <Tag className="!m-0">{slide.script_text.length} 字</Tag>
            {slide.audio_sha256 && (
              <Tag color="green" className="!m-0">
                配音 sha {slide.audio_sha256.slice(0, 8)}
              </Tag>
            )}
          </Space>
        </div>
        {slide.script_stale && (
          <Alert
            type="warning"
            showIcon
            className="!mb-2"
            message="画面已更新，当前讲稿还是按旧画面写的"
            description="换源或改页后，讲稿与画面可能对不上，建议按当前画面重写这一页。"
            action={
              <Button size="small" loading={rewriting} onClick={handleRewriteOne}>
                按当前画面重写
              </Button>
            }
          />
        )}
        <TextArea
          value={scriptText}
          onChange={(event) => setScriptText(event.target.value)}
          autoSize={{ minRows: 5, maxRows: 12 }}
          placeholder={
            noSourceText
              ? '本页 PPT 没有可识别的文字，AI 不会生成初稿，请手工填写旁白。'
              : drafting
                ? 'AI 正在生成初稿，完成后会自动填入；也可以直接手写。'
                : `按页填写旁白，例如：本页介绍 ${detail.name} 的工艺流程与关键控制点。`
          }
          showCount
          maxLength={2000}
        />
        {noSourceText && (
          <Typography.Paragraph type="secondary" className="!mb-0 !mt-2 !text-[12px]">
            本页无文字：AI 初稿只依据页内文字与备注生成，本页需要手工填写讲稿。
          </Typography.Paragraph>
        )}
        {drafting && (
          <Typography.Paragraph type="secondary" className="!mb-0 !mt-2 !text-[12px]">
            初稿生成中，已有讲稿的页面不会被覆盖。
          </Typography.Paragraph>
        )}
        {slide.page_notes && (
          <Typography.Paragraph type="secondary" className="!mb-0 !mt-2 !text-[12px]">
            备注参考：{slide.page_notes.slice(0, 120)}
          </Typography.Paragraph>
        )}

        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
          <div>
            <Typography.Text type="secondary" className="text-[12px]">
              语言（留空跟随项目：{detail.default_language === 'zh' ? '中文' : '英文'}）
            </Typography.Text>
            <Select<LanguageCode>
              allowClear
              className="mt-1 w-full"
              placeholder="跟随项目默认"
              value={language}
              onChange={(value) => {
                setLanguage(value)
                setVoiceId(undefined)
              }}
              options={[
                { value: 'zh', label: '中文' },
                { value: 'en', label: '英文' },
              ]}
            />
          </div>
          <div>
            <Typography.Text type="secondary" className="text-[12px]">
              音色（留空跟随项目）
            </Typography.Text>
            <Select
              allowClear
              className="mt-1 w-full"
              placeholder={`跟随项目默认 ${detail.default_voice_id}`}
              value={voiceId}
              onChange={setVoiceId}
              options={languageVoices.map((voice) => ({
                value: voice.voice_id,
                label: `${voice.display_name}（${voice.gender === 'female' ? '女' : '男'}）`,
              }))}
            />
          </div>
          <div>
            <Typography.Text type="secondary" className="text-[12px]">
              语速 {speed ? speed.toFixed(2) : detail.speed.toFixed(2)}x
            </Typography.Text>
            <Slider
              className="!mt-2"
              min={0.5}
              max={2}
              step={0.05}
              value={speed ?? detail.speed}
              onChange={(value) => setSpeed(value)}
              tooltip={{ formatter: (value) => `${value?.toFixed(2)}x` }}
            />
          </div>
        </div>

        <Space className="mt-3">
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
            保存本页
          </Button>
          <Button icon={<RobotOutlined />} loading={rewriting} onClick={handleRewriteOne}>
            AI 改写本页
          </Button>
          <Button icon={<SoundOutlined />} loading={previewing} onClick={handlePreview}>
            试听 / 重新生成旁白
          </Button>
          {(language || voiceId || speed !== undefined) && (
            <Button
              type="text"
              onClick={() => {
                setLanguage(undefined)
                setVoiceId(undefined)
                setSpeed(undefined)
              }}
            >
              跟随项目默认
            </Button>
          )}
        </Space>

        {audioUrl && (
          <div className="mt-3 rounded-lg bg-[#FAFAF9] p-2">
            <audio controls src={audioUrl} className="w-full" preload="none">
              您的浏览器不支持音频播放
            </audio>
          </div>
        )}
      </div>
    </div>
  )
}