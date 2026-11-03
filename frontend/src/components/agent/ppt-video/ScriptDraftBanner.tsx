'use client'

import { useEffect, useRef, useState } from 'react'
import { Alert, App, Button, Input, Progress, Segmented, Select, Space, Tag, Typography } from 'antd'
import { HistoryOutlined, ReloadOutlined, ThunderboltOutlined } from '@ant-design/icons'

import RevisionDrawer from './RevisionDrawer'
import { loadScriptRevisions, regenerateScriptDraft, rewriteScripts } from '@/actions/agent/ppt-video'
import { fetchPptVideoDetail } from '@/lib/api/client/agent'
import {
  REWRITE_MODE_HINT,
  REWRITE_MODE_LABEL,
  type ProjectDetail,
  type RewriteMode,
  type ScriptAiState,
} from '@/types/agent/ppt-video'

/** 仍在跑的状态：需要轮询详情刷新进度 */
const ACTIVE = new Set(['queued', 'running'])

/** 横幅上可选的三种批量语义；rewrite_one 只在单页编辑区出现 */
const BANNER_MODES: RewriteMode[] = ['fill_blank', 'rewrite_all', 'rewrite_selected']

/** 旧数据/旧接口没有 script_ai 时的兜底，等同「从未生成」 */
const IDLE_STATE: ScriptAiState = {
  status: 'idle',
  error: null,
  progress: 0,
  total: 0,
  done: 0,
  pending: 0,
  skipped: 0,
  failed: 0,
}

interface Props {
  detail: ProjectDetail
  onDetailChange: (detail: ProjectDetail) => void
}

/**
 * 顶部讲稿区：初稿进度 + 批量改写入口。
 *
 * 批量改写一律走后台任务（可能跑几分钟），提交后按修订记录的状态轮询，
 * 完成再拉一次详情——比按页猜进度可靠。
 */
export default function ScriptDraftBanner({ detail, onDetailChange }: Props) {
  const { message } = App.useApp()
  const state = detail.script_ai ?? IDLE_STATE
  const status = state.status
  const active = ACTIVE.has(status)
  const pending = state.pending

  const [retrying, setRetrying] = useState(false)
  const [mode, setMode] = useState<RewriteMode>('fill_blank')
  const [instruction, setInstruction] = useState('')
  const [scope, setScope] = useState<string[]>([])
  const [rewriting, setRewriting] = useState(false)
  const [revisionId, setRevisionId] = useState<string | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const [revisionsOpen, setRevisionsOpen] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!active) return
    let cancelled = false

    const tick = async () => {
      try {
        const fresh = await fetchPptVideoDetail(detail.id)
        if (!cancelled) onDetailChange(fresh)
      } catch (error) {
        console.warn('轮询讲稿初稿进度失败:', error)
      }
      if (!cancelled) timer.current = setTimeout(tick, 3000)
    }

    timer.current = setTimeout(tick, 3000)
    return () => {
      cancelled = true
      if (timer.current) clearTimeout(timer.current)
    }
  }, [active, detail.id, onDetailChange])

  // 改写任务：按 revision 状态收尾
  useEffect(() => {
    if (!rewriting) return
    let cancelled = false
    const startedAt = Date.now()
    const tick = async () => {
      setElapsed(Math.round((Date.now() - startedAt) / 1000))
      const result = await loadScriptRevisions(detail.id, 10)
      const target = revisionId ? (result.data ?? []).find((item) => item.id === revisionId) : null
      const finished = target ? target.status === 'succeeded' || target.status === 'failed' : true
      if (finished) {
        if (cancelled) return
        try {
          const fresh = await fetchPptVideoDetail(detail.id)
          if (!cancelled) onDetailChange(fresh)
        } catch (error) {
          console.warn('改写完成后刷新详情失败:', error)
        }
        if (target?.status === 'failed') {
          message.error(target.error_message || '改写失败，可在修订记录里查看')
        } else {
          message.success('讲稿改写完成')
        }
        setRewriting(false)
        setRevisionId(null)
        return
      }
      timer.current = setTimeout(tick, 3000)
    }
    timer.current = setTimeout(tick, 3000)
    return () => {
      cancelled = true
      if (timer.current) clearTimeout(timer.current)
    }
  }, [rewriting, revisionId, detail.id, onDetailChange, message])

  const handleRetry = async () => {
    setRetrying(true)
    const result = await regenerateScriptDraft(detail.id)
    setRetrying(false)
    if (!result.success) {
      message.error(result.message)
      return
    }
    if (result.data) onDetailChange(result.data)
    message.success(result.message)
  }

  const handleRun = async () => {
    if (mode === 'rewrite_selected' && !scope.length) {
      message.warning('请先勾选要改写的页面')
      return
    }
    setRewriting(true)
    setElapsed(0)
    const result = await rewriteScripts(detail.id, {
      mode,
      slide_uids: mode === 'rewrite_selected' ? scope : undefined,
      instruction: instruction.trim() || null,
      background: true,
    })
    if (!result.success || !result.data) {
      setRewriting(false)
      message.error(result.message)
      return
    }
    if (result.data.status === 'queued') {
      setRevisionId(result.data.revision_id ?? null)
      message.info(result.message)
      return
    }
    // 极短任务可能同步返回
    setRewriting(false)
    try {
      onDetailChange(await fetchPptVideoDetail(detail.id))
    } catch (error) {
      console.warn('改写后刷新详情失败:', error)
    }
    message.success(result.message)
  }

  const draftBlock = active ? (
    <div className="rounded-xl border border-[#D9D3F7] bg-[#F7F5FE] px-5 py-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Typography.Text strong className="text-[13px] text-[#3F3577]">
          正在生成讲稿初稿 {state.done}/{state.total} 页
        </Typography.Text>
        <Typography.Text className="text-[12px] text-[#5D5B54]">
          已有讲稿的页面不会被覆盖，可以先改其他页
        </Typography.Text>
      </div>
      <Progress
        percent={state.progress}
        status="active"
        strokeColor="#5645D4"
        className="!mb-0 !mt-2"
        size="small"
      />
    </div>
  ) : status === 'disabled' && pending > 0 ? (
    <Alert
      type="info"
      showIcon
      message="自动生成初稿已关闭"
      description="后台已关闭 AI 讲稿生成，请手工填写讲稿，或联系管理员打开 AGENT_PPT_VIDEO_SCRIPT_AI_ENABLED。"
    />
  ) : status === 'failed' || status === 'partial' ? (
    <Alert
      type={status === 'partial' ? 'warning' : 'error'}
      showIcon
      message={
        status === 'partial'
          ? `讲稿初稿部分完成，还有 ${state.failed || pending} 页没生成`
          : `讲稿初稿生成失败${state.failed || pending ? `，${state.failed || pending} 页仍为空` : ''}`
      }
      description={state.error || '可重试生成剩余空页；已有讲稿不受影响。'}
      action={
        <Button size="small" icon={<ReloadOutlined />} loading={retrying} onClick={handleRetry}>
          重新生成剩余页
        </Button>
      }
    />
  ) : null

  const slideOptions = (detail.slides ?? []).map((slide) => ({
    value: slide.slide_uid,
    label: `第 ${slide.slide_no} 页 · ${(slide.script_text || slide.page_text || '未填写讲稿')
      .replace(/\s+/g, ' ')
      .slice(0, 18)}`,
  }))

  return (
    <div className="flex flex-col gap-2">
      {draftBlock}

      <div className="rounded-xl border border-[#E5E3DF] bg-white px-4 py-3">
        <div className="flex flex-wrap items-center gap-2">
          <Segmented
            size="small"
            value={mode}
            onChange={(value) => setMode(value as RewriteMode)}
            options={BANNER_MODES.map((item) => ({ value: item, label: REWRITE_MODE_LABEL[item] }))}
            disabled={rewriting}
          />
          <Typography.Text type="secondary" className="text-[11px]">
            {REWRITE_MODE_HINT[mode]}
          </Typography.Text>

          <span className="ml-auto flex items-center gap-2">
            <Button size="small" icon={<HistoryOutlined />} onClick={() => setRevisionsOpen(true)}>
              修订记录
            </Button>
            <Button
              size="small"
              type="primary"
              icon={<ThunderboltOutlined />}
              loading={rewriting}
              onClick={handleRun}
            >
              开始改写
            </Button>
          </span>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Input
            allowClear
            size="small"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            disabled={rewriting}
            placeholder="可选：本次指令，例如「更口语一点，每页不超过 120 字」"
            className="min-w-[260px] flex-1"
            maxLength={500}
          />
          {mode === 'rewrite_selected' && (
            <Select
              mode="multiple"
              size="small"
              allowClear
              value={scope}
              onChange={setScope}
              disabled={rewriting}
              placeholder="选择要改写的页面"
              className="min-w-[240px]"
              maxTagCount="responsive"
              options={slideOptions}
            />
          )}
          {mode === 'rewrite_all' && (
            <Tag color="orange" className="!m-0 !text-[11px]">
              覆盖前自动存快照，可回滚
            </Tag>
          )}
        </div>

        {rewriting && (
          <div className="mt-2">
            <Progress percent={100} status="active" showInfo={false} strokeWidth={2} strokeColor="#5645D4" />
            <Space size={6} className="mt-1">
              <Typography.Text type="secondary" className="text-[11px]">
                改写任务进行中（{elapsed}s）· 完成后自动刷新，可在修订记录里回滚
              </Typography.Text>
            </Space>
          </div>
        )}
      </div>

      <RevisionDrawer
        open={revisionsOpen}
        projectId={detail.id}
        onClose={() => setRevisionsOpen(false)}
        onRolledBack={onDetailChange}
      />
    </div>
  )
}