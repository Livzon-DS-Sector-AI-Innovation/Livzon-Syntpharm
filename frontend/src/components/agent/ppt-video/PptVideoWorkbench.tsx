'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { App, Button, Space, Tag, Typography } from 'antd'
import { ArrowLeftOutlined, RobotOutlined, SwapOutlined } from '@ant-design/icons'

import AiConfigDrawer from './AiConfigDrawer'
import RenderProgress from './RenderProgress'
import ScriptDraftBanner from './ScriptDraftBanner'
import SlideEditor from './SlideEditor'
import SlideTimeline from './SlideTimeline'
import SourceReplaceModal from './SourceReplaceModal'
import VersionPanel from './VersionPanel'
import VoiceSettings from './VoiceSettings'
import { reloadPptVideoProject } from '@/actions/agent/ppt-video'
import { PermissionGate } from '@/components/auth/PermissionGate'
import { PERM } from '@/lib/permissions/codes'
import type { ProjectDetail, VoiceOption } from '@/types/agent/ppt-video'

interface Props {
  initialDetail: ProjectDetail
  voices: VoiceOption[]
}

/**
 * 三栏工作台：左时间轴（选页）、中编辑区（讲稿/试听）、右属性与版本。
 *
 * 详情状态收敛在这一层：子组件只上报「新的 detail」，避免各栏各自拉一份
 * 出现左侧已配音、右侧还是旧版本的错位。
 */
export default function PptVideoWorkbench({ initialDetail, voices }: Props) {
  const { message } = App.useApp()
  const [detail, setDetail] = useState<ProjectDetail>(initialDetail)
  const [aiOpen, setAiOpen] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(false)
  // 选中态跟 slide_uid 走：换源后 slide_no 会整体重排，用序号会选错页
  const [activeSlideUid, setActiveSlideUid] = useState<string>(initialDetail.slides?.[0]?.slide_uid ?? '')

  const slides = useMemo(() => detail.slides ?? [], [detail.slides])

  const activeSlide = useMemo(
    () => slides.find((slide) => slide.slide_uid === activeSlideUid) ?? slides[0],
    [slides, activeSlideUid],
  )

  /** 换源后页序与 uid 都可能变，整份详情重取，选中态回到第一页 */
  const handleSourceApplied = async () => {
    const result = await reloadPptVideoProject(detail.id)
    if (!result.success || !result.data) {
      message.error(result.message)
      return
    }
    setDetail(result.data)
    setActiveSlideUid(result.data.slides?.[0]?.slide_uid ?? '')
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Space size={8} wrap>
          <Link
            href="/agent/ppt-videos"
            className="flex items-center gap-1 text-[13px] text-[#5D5B54] hover:text-[#5645D4]"
          >
            <ArrowLeftOutlined />
            返回列表
          </Link>
          <Typography.Text type="secondary" className="text-[12px]">
            {detail.source_filename}
          </Typography.Text>
          <Tag className="!m-0 !text-[11px]">源文件第 {detail.source_version} 版</Tag>
        </Space>

        <PermissionGate code={PERM.pptVideoManage}>
          <Space size={8} wrap>
            <Button size="small" icon={<RobotOutlined />} onClick={() => setAiOpen(true)}>
              项目 AI 设置
            </Button>
            <Button size="small" icon={<SwapOutlined />} onClick={() => setSourceOpen(true)}>
              更换 PPT
            </Button>
          </Space>
        </PermissionGate>
      </div>

      <RenderProgress detail={detail} onDetailChange={setDetail} />

      <ScriptDraftBanner detail={detail} onDetailChange={setDetail} />

      <div className="grid grid-cols-1 gap-3 xl:grid-cols-[224px_minmax(0,1fr)_320px]">
        <section className="rounded-xl border border-[#E5E3DF] bg-white p-3">
          <div className="mb-2 flex items-center justify-between">
            <Typography.Text strong className="text-[13px]">
              页面
            </Typography.Text>
            <Typography.Text type="secondary" className="text-[11px]">
              第 {activeSlide?.slide_no ?? 1} / {detail.slide_count} 页
            </Typography.Text>
          </div>
          <div className="max-h-[calc(100vh-320px)] min-h-[320px] overflow-y-auto">
            <SlideTimeline
              slides={slides}
              activeSlideUid={activeSlide?.slide_uid ?? ''}
              onSelect={setActiveSlideUid}
            />
          </div>
        </section>

        <section className="min-w-0">
          {activeSlide ? (
            // key 切页重挂载：讲稿草稿随页切换重置，不用在子组件里 setState 同步 props
            <SlideEditor
              key={activeSlide.slide_uid}
              detail={detail}
              slide={activeSlide}
              voices={voices}
              onDetailChange={setDetail}
            />
          ) : (
            <div className="rounded-xl border border-[#E5E3DF] bg-white p-8 text-center">
              <Typography.Text type="secondary">该项目没有可编辑的页面，请重新上传 PPT。</Typography.Text>
            </div>
          )}
        </section>

        <aside className="flex flex-col gap-3">
          <VoiceSettings key={detail.id} detail={detail} voices={voices} onDetailChange={setDetail} />
          <VersionPanel detail={detail} />
        </aside>
      </div>

      <AiConfigDrawer
        open={aiOpen}
        onClose={() => setAiOpen(false)}
        mode="project"
        configs={null}
        detail={detail}
        onDetailChange={setDetail}
      />

      {sourceOpen && (
        <SourceReplaceModal
          open={sourceOpen}
          projectId={detail.id}
          onClose={() => setSourceOpen(false)}
          onApplied={handleSourceApplied}
        />
      )}
    </div>
  )
}