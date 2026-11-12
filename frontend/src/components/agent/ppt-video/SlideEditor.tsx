'use client'

import { useMemo, useState } from 'react'
import { Alert, App, Button, Checkbox, ColorPicker, Input, Modal, Select, Slider, Space, Tag, Typography } from 'antd'
import {
  DownloadOutlined,
  EditOutlined,
  HighlightOutlined,
  RobotOutlined,
  SaveOutlined,
  SoundOutlined,
} from '@ant-design/icons'

import HighlightRegionsDrawer from './HighlightRegionsDrawer'
import SlideContentEditor from './SlideContentEditor'
import { previewSlide, rewriteScripts, saveSlideScript } from '@/actions/agent/ppt-video'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { fetchPptVideoDetail } from '@/lib/api/client/agent'
import { PERM } from '@/lib/permissions/codes'
import {
  HIGHLIGHT_STYLE_OPTIONS,
  formatDuration,
  genderLabel,
  voiceLabel,
  type HighlightRegionsPayload,
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
  const [contentOpen, setContentOpen] = useState(false)
  const [rewritePromptOpen, setRewritePromptOpen] = useState(false)
  const [scriptText, setScriptText] = useState(slide.script_text ?? '')
  const [language, setLanguage] = useState<LanguageCode | undefined>(slide.language ?? undefined)
  const [voiceId, setVoiceId] = useState<string | undefined>(slide.voice_id ?? undefined)
  const [speed, setSpeed] = useState<number | undefined>(slide.speed ?? undefined)
  // 页级高亮覆盖：勾选后才生效，留空则逐项跟随项目设置（项目再空则跟随模块默认）
  const [highlightEnabled, setHighlightEnabled] = useState(slide.highlight_override_enabled)
  const [highlightStyle, setHighlightStyle] = useState<string | undefined>(slide.highlight_style ?? undefined)
  const [highlightColor, setHighlightColor] = useState<string | undefined>(slide.highlight_color ?? undefined)
  // 区域级配置：同样只在本页草案里改，随「保存本页」整份提交（后端是整份替换语义）
  const [highlightRegions, setHighlightRegions] = useState<HighlightRegionsPayload | null>(
    slide.highlight_regions ?? null,
  )
  const [regionsOpen, setRegionsOpen] = useState(false)
  const regionCount = highlightRegions?.regions?.length ?? 0
  const sentenceRuleCount = highlightRegions?.sentences?.length ?? 0
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
  const projectVoice = voices.find((voice) => voice.voice_id === detail.default_voice_id)
  // 本页未启用高亮时，控件上要显示「实际会用的那一档」，避免误以为改不了就没配置
  const inheritedHighlightColor =
    detail.highlight_override_enabled && detail.highlight_color
      ? detail.highlight_color
      : detail.module_highlight_color

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
        highlight_override_enabled: highlightEnabled,
        highlight_style: highlightStyle ?? null,
        highlight_color: highlightColor ?? null,
        // 总是整份回写：空配置写成空数组对象，后端据此清空；不传会让库里旧配置留着
        highlight_regions:
          highlightRegions && (highlightRegions.regions?.length || highlightRegions.sentences?.length)
            ? highlightRegions
            : { regions: [], sentences: [] },
        clear_language: !language,
        clear_voice: !voiceId,
        clear_speed: speed === undefined,
        clear_highlight_style: !highlightStyle,
        clear_highlight_color: !highlightColor,
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

  /**
   * 页内编辑保存成功：画面变了但讲稿没变，默认不覆盖人工精修稿。
   * 「暂不重写」放在主按钮位置，是 Enter 与视觉上的默认项。
   */
  const handleContentSaved = (next: ProjectDetail) => {
    onDetailChange(next)
    setRewritePromptOpen(true)
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
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="text-[12px] text-[#A4A097]">页面预览</span>
          <Space size={6}>
            <PermissionGate code={PERM.pptVideoManage}>
              <Button size="small" type="primary" icon={<EditOutlined />} onClick={() => setContentOpen(true)}>
                编辑本页内容
              </Button>
            </PermissionGate>
            <PermissionGate code={PERM.pptVideoRead}>
              <Button size="small" icon={<DownloadOutlined />} href={detail.source_download_url} download>
                下载 PPT
              </Button>
            </PermissionGate>
          </Space>
        </div>
        <div className="flex aspect-video items-center justify-center overflow-hidden rounded-lg bg-black">
          {slide.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={slide.image_url}
              alt={`第 ${slide.slide_no} 页预览`}
              decoding="async"
              className="max-h-full max-w-full object-contain"
            />
          ) : slide.script_stale ? (
            <div className="flex flex-col items-center gap-2">
              <Typography.Text className="!text-[#A4A097]">
                本页画面已修改，旧页图已失效，重新生成视频后才能看到新画面
              </Typography.Text>
              <Button size="small" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
                去生成视频
              </Button>
            </div>
          ) : (
            <Typography.Text className="!text-[#A4A097]">
              页面图还没生成，生成进度完成后就能看到
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

      <SlideContentEditor
        open={contentOpen}
        projectId={detail.id}
        slideUid={slide.slide_uid}
        slideNo={slide.slide_no}
        onClose={() => setContentOpen(false)}
        onDetailChange={onDetailChange}
        onSaved={handleContentSaved}
      />

      <HighlightRegionsDrawer
        open={regionsOpen}
        projectId={detail.id}
        slide={slide}
        value={highlightRegions}
        onClose={() => setRegionsOpen(false)}
        onChange={setHighlightRegions}
      />

      <Modal
        open={rewritePromptOpen}
        title="画面已更新"
        closable={false}
        maskClosable={false}
        footer={[
          <Button key="skip" type="primary" onClick={() => setRewritePromptOpen(false)}>
            暂不重写
          </Button>,
          <Button
            key="rewrite"
            loading={rewriting}
            onClick={() => {
              setRewritePromptOpen(false)
              void handleRewriteOne()
            }}
          >
            按新画面重写本页
          </Button>,
        ]}
      >
        本页画面已更新，讲稿还是按旧画面写的。要现在按新画面重写这一页吗？重写会覆盖本页现有讲稿。
      </Modal>

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
                已配音
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
              placeholder={`跟随项目默认：${voiceLabel(projectVoice?.display_name)}`}
              value={voiceId}
              onChange={setVoiceId}
              options={languageVoices.map((voice) => ({
                value: voice.voice_id,
                label: `${voice.display_name}（${genderLabel(voice.gender)}）`,
              }))}
            />
          </div>
          <div>
            <Typography.Text type="secondary" className="text-[12px]">
              语速 {(speed ?? detail.speed).toFixed(2)} 倍
            </Typography.Text>
            <Slider
              className="!mt-2"
              min={0.5}
              max={2}
              step={0.05}
              value={speed ?? detail.speed}
              onChange={(value) => setSpeed(value)}
              tooltip={{ formatter: (value) => `${value?.toFixed(2)} 倍` }}
            />
          </div>
        </div>

        <div className="mt-3 rounded-lg bg-[#FAFAF9] px-3 py-2">
          <Checkbox checked={highlightEnabled} onChange={(event) => setHighlightEnabled(event.target.checked)}>
            <span className="text-[12px] text-[#37352F]">高亮效果</span>
          </Checkbox>
          <Typography.Text type="secondary" className="!ml-1 !text-[11px]">
            {highlightEnabled
              ? '本页按下面的样式与颜色高亮。'
              : '未勾选时本页跟随项目设置（项目未开启高亮则本页也不亮）；已选的样式与颜色会保留，勾选后立即恢复。'}
          </Typography.Text>
        </div>

        <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
          <div>
            <Typography.Text type="secondary" className="text-[12px]">
              本页高亮样式（留空跟随项目设置）
            </Typography.Text>
            <Select<string>
              allowClear
              className="mt-1 w-full"
              placeholder="跟随项目设置"
              value={highlightStyle}
              disabled={!highlightEnabled}
              onChange={(value) => setHighlightStyle(value)}
              options={HIGHLIGHT_STYLE_OPTIONS}
            />
          </div>
          <div>
            <Typography.Text type="secondary" className="text-[12px]">
              本页高亮颜色（留空跟随项目设置）
            </Typography.Text>
            <div className="mt-1 flex items-center gap-2">
              <ColorPicker
                value={highlightColor ?? inheritedHighlightColor}
                disabled={!highlightEnabled}
                onChange={(color) => setHighlightColor(color.toHexString().toUpperCase())}
              />
              <Typography.Text type="secondary" className="text-[12px]">
                {highlightEnabled
                  ? (highlightColor ?? '未单独设置，使用项目的高亮颜色')
                  : '未勾选，本页跟随项目设置（项目未开启则本页不亮）'}
              </Typography.Text>
              {highlightColor && (
                <Button
                  type="link"
                  size="small"
                  disabled={!highlightEnabled}
                  onClick={() => setHighlightColor(undefined)}
                >
                  清除
                </Button>
              )}
            </div>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Button size="small" icon={<HighlightOutlined />} onClick={() => setRegionsOpen(true)}>
            高亮区域设置
          </Button>
          <Typography.Text type="secondary" className="!text-[12px]">
            {regionCount
              ? `已配 ${regionCount} 个区域${sentenceRuleCount ? `、${sentenceRuleCount} 句单独设定` : ''}`
              : '默认按讲稿自动定位；可逐区域指定效果，或手绘一块区域兜底'}
          </Typography.Text>
          {regionCount + sentenceRuleCount > 0 && (
            <Button type="link" size="small" onClick={() => setHighlightRegions(null)}>
              清空区域设置
            </Button>
          )}
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
          {(language ||
            voiceId ||
            speed !== undefined ||
            highlightEnabled ||
            highlightStyle ||
            highlightColor ||
            regionCount + sentenceRuleCount > 0) && (
            <Button
              type="text"
              onClick={() => {
                setLanguage(undefined)
                setVoiceId(undefined)
                setSpeed(undefined)
                // 高亮只关开关、样式与颜色原样保留：清空交给各控件自己的「清除」
                setHighlightEnabled(false)
                setHighlightRegions(null)
              }}
            >
              全部跟随项目设置
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