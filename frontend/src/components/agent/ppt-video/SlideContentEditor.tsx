'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Drawer, Empty, Input, Spin, Typography, Upload } from 'antd'
import { PictureOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons'

import { editSlideImage, editSlideText, loadEditableShapes } from '@/actions/agent/ppt-video'
import type { EditableShapeItem, ProjectDetail } from '@/types/agent/ppt-video'

const { TextArea } = Input
const MAX_IMAGE_BYTES = 10 * 1024 * 1024
const ACCEPT_IMAGE = '.png,.jpg,.jpeg,.webp'
const ACCEPT_MIME = new Set(['image/png', 'image/jpeg', 'image/webp'])
/** 后端只回传前 200 字，达到这个长度就无法确定是否被截断，这类元素改为只读 */
const TEXT_ROUND_TRIP_LIMIT = 200

/** 提交成功后把对应的草稿摘掉，重试时不会重复提交（每次提交都会让源文件版本 +1） */
function omitDrafts<T>(drafts: Record<number, T>, applied: Set<number>): Record<number, T> {
  if (applied.size === 0) return drafts
  const next: Record<number, T> = {}
  for (const [key, value] of Object.entries(drafts)) {
    if (!applied.has(Number(key))) next[Number(key)] = value
  }
  return next
}

interface Props {
  open: boolean
  projectId: string
  slideUid: string
  slideNo: number
  onClose: () => void
  /** 部分成功也要刷新详情（页图被清空、版本号变化） */
  onDetailChange: (detail: ProjectDetail) => void
  /** 全部保存成功回调：父组件据此询问是否重写本页讲稿 */
  onSaved: (detail: ProjectDetail) => void
}

interface ImageDraft {
  file: File
  previewUrl: string
}

/**
 * 页内轻量编辑抽屉：只改文本框文字与替换图片，不动版式。
 *
 * 保存时逐项提交（每项各自一次换源），任一项失败即停下并保留剩余草稿，
 * 避免「一次全失败、不知道哪项挂了」。文字改动的段落会被合并为一段。
 */
export default function SlideContentEditor({
  open,
  projectId,
  slideUid,
  slideNo,
  onClose,
  onDetailChange,
  onSaved,
}: Props) {
  const { message } = App.useApp()
  const [textDrafts, setTextDrafts] = useState<Record<number, string>>({})
  const [imageDrafts, setImageDrafts] = useState<Record<number, ImageDraft>>({})
  const [saving, setSaving] = useState(false)

  // 客户端读取走 React Query，抽屉打开时才请求；每次打开都重新拉，避免拿到编辑前的缓存
  const shapesQuery = useQuery({
    queryKey: ['ppt-video-shapes', projectId, slideUid],
    queryFn: async () => {
      const result = await loadEditableShapes(projectId, slideUid)
      if (!result.success || !result.data) throw new Error(result.message)
      return result.data.items ?? []
    },
    enabled: open,
    staleTime: 0,
    retry: false,
  })
  const shapes = open ? (shapesQuery.data ?? null) : null
  const loading = open && shapesQuery.isLoading
  const loadError = shapesQuery.error instanceof Error ? shapesQuery.error.message : null

  // 预览地址是本地 objectURL，统一登记后释放：换图/清空草稿时释放对应那张，卸载时兜底全清
  const draftsRef = useRef<Record<number, ImageDraft>>({})
  const previewUrlsRef = useRef<Set<string>>(new Set())
  useEffect(() => {
    draftsRef.current = imageDrafts
  }, [imageDrafts])
  useEffect(() => {
    const urls = previewUrlsRef.current
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url))
      urls.clear()
    }
  }, [])

  const makePreviewUrl = useCallback((file: File) => {
    const url = URL.createObjectURL(file)
    previewUrlsRef.current.add(url)
    return url
  }, [])

  const dropPreviewUrl = useCallback((url: string) => {
    URL.revokeObjectURL(url)
    previewUrlsRef.current.delete(url)
  }, [])

  const textItems = useMemo(
    () => (shapes ?? []).filter((shape) => shape.editable_text && shape.text.length < TEXT_ROUND_TRIP_LIMIT),
    [shapes],
  )
  const lockedTextItems = useMemo(
    () => (shapes ?? []).filter((shape) => shape.editable_text && shape.text.length >= TEXT_ROUND_TRIP_LIMIT),
    [shapes],
  )
  const imageItems = useMemo(() => (shapes ?? []).filter((shape) => shape.has_picture), [shapes])

  const textChanged = textItems.some((shape) => (textDrafts[shape.index] ?? shape.text) !== shape.text)
  const imageChanged = Object.keys(imageDrafts).length > 0
  const dirty = textChanged || imageChanged

  const pickImage = useCallback(
    (shape: EditableShapeItem, file: File) => {
      if (!ACCEPT_MIME.has(file.type)) {
        message.error('只支持 png / jpg / webp 图片')
        return
      }
      if (file.size > MAX_IMAGE_BYTES) {
        message.error('图片超过 10MB，请先压缩')
        return
      }
      const previousUrl = draftsRef.current[shape.index]?.previewUrl
      const previewUrl = makePreviewUrl(file)
      setImageDrafts((previous) => ({ ...previous, [shape.index]: { file, previewUrl } }))
      if (previousUrl) dropPreviewUrl(previousUrl)
    },
    [dropPreviewUrl, makePreviewUrl, message],
  )

  const handleSave = async () => {
    if (saving) return
    setSaving(true)
    let latest: ProjectDetail | null = null
    let failedName: string | null = null
    const appliedText = new Set<number>()
    const appliedImage = new Set<number>()

    for (const shape of textItems) {
      const draft = textDrafts[shape.index]
      if (draft === undefined || draft === shape.text) continue
      if (!draft.trim()) {
        failedName = `${shape.name}：文字不能为空（要删除该元素请用 PowerPoint 重新上传）`
        break
      }
      const result = await editSlideText(projectId, slideUid, shape.index, draft)
      if (!result.success || !result.data) {
        failedName = `${shape.name}：${result.message}`
        break
      }
      appliedText.add(shape.index)
      latest = result.data
    }

    if (!failedName) {
      for (const shape of imageItems) {
        const draft = imageDrafts[shape.index]
        if (!draft) continue
        const result = await editSlideImage(projectId, slideUid, shape.index, draft.file)
        if (!result.success || !result.data) {
          failedName = `${shape.name}：${result.message}`
          break
        }
        appliedImage.add(shape.index)
        latest = result.data
      }
    }

    appliedImage.forEach((index) => {
      const url = draftsRef.current[index]?.previewUrl
      if (url) dropPreviewUrl(url)
    })
    setTextDrafts((previous) => omitDrafts(previous, appliedText))
    setImageDrafts((previous) => omitDrafts(previous, appliedImage))
    setSaving(false)

    // 部分成功也要刷新：页图已被清空、版本号已变
    if (latest) {
      onDetailChange(latest)
      void shapesQuery.refetch()
    }
    if (failedName) {
      message.error(failedName)
      return
    }
    if (!latest) return
    message.success(`第 ${slideNo} 页已更新为源文件第 ${latest.source_version} 版`)
    onSaved(latest)
    handleClose()
  }

  /** 关闭即丢弃草稿：重新打开时从源文件现状重新拉一遍元素 */
  const handleClose = () => {
    if (saving) return
    Object.values(imageDrafts).forEach((draft) => dropPreviewUrl(draft.previewUrl))
    setTextDrafts({})
    setImageDrafts({})
    onClose()
  }

  const footer = (
    <div className="flex items-center justify-between">
      <Typography.Text type="secondary" className="text-[12px]">
        {dirty ? '有未保存的修改' : '暂无修改'}
      </Typography.Text>
      <div className="flex gap-2">
        <Button onClick={handleClose} disabled={saving}>
          取消
        </Button>
        <Button type="primary" loading={saving} disabled={!dirty} onClick={handleSave}>
          保存修改
        </Button>
      </div>
    </div>
  )

  return (
    <Drawer
      title={`编辑本页内容 · 第 ${slideNo} 页`}
      width="min(560px, 100vw)"
      open={open}
      onClose={handleClose}
      destroyOnHidden
      footer={shapes ? footer : null}
    >
      <Alert
        type="info"
        showIcon
        className="!mb-3"
        message="只改文字与图片，不保证版式"
        description="文字沿用原文本框首个文字的字体字号，多段落会合并为一段；改动需要重新生成视频后才能看到新画面。"
      />

      {loading && (
        <div className="flex h-40 items-center justify-center gap-2">
          <Spin />
          <Typography.Text type="secondary">读取页面元素…</Typography.Text>
        </div>
      )}

      {loadError && !loading && (
        <Alert
          type="error"
          showIcon
          message="读取页面元素失败"
          description={loadError}
          action={
            <Button size="small" icon={<ReloadOutlined />} onClick={() => void shapesQuery.refetch()}>
              重试
            </Button>
          }
        />
      )}

      {shapes && !loading && !loadError && (
        <div className="flex flex-col gap-3">
          {textItems.length + imageItems.length + lockedTextItems.length === 0 && (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="本页没有可编辑的文本框或图片，可用顶部「更换 PPT」整份替换"
            />
          )}

          {textItems.length > 0 && (
            <section className="rounded-xl border border-[#E5E3DF] bg-white p-3">
              <Typography.Text strong className="text-[13px]">
                文本元素（{textItems.length}）
              </Typography.Text>
              <div className="mt-2 flex flex-col gap-3">
                {textItems.map((shape) => (
                  <div key={shape.index} className="mb-1">
                    <Typography.Text className="text-[13px] font-medium">{shape.name}</Typography.Text>
                    <TextArea
                      value={textDrafts[shape.index] ?? shape.text}
                      onChange={(event) =>
                        setTextDrafts((previous) => ({ ...previous, [shape.index]: event.target.value }))
                      }
                      autoSize={{ minRows: 2, maxRows: 8 }}
                      showCount
                    />
                  </div>
                ))}
              </div>
            </section>
          )}

          {imageItems.length > 0 && (
            <section className="rounded-xl border border-[#E5E3DF] bg-white p-3">
              <Typography.Text strong className="text-[13px]">
                图片元素（{imageItems.length}）
              </Typography.Text>
              <div className="mt-2 flex flex-col gap-3">
                {imageItems.map((shape) => {
                  const draft = imageDrafts[shape.index]
                  return (
                    <div key={shape.index} className="flex items-center gap-3">
                      <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-md border border-dashed border-[#E5E3DF] bg-[#FAFAF9]">
                        {draft ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={draft.previewUrl} alt="待替换图片预览" className="h-full w-full object-cover" />
                        ) : (
                          <PictureOutlined className="text-[#A4A097]" />
                        )}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-[13px] font-medium">{shape.name}</div>
                        <Typography.Text type="secondary" className="text-[11px]">
                          {draft ? `待替换：${draft.file.name}` : '支持 png / jpg / webp，≤ 10MB'}
                        </Typography.Text>
                      </div>
                      <Upload
                        accept={ACCEPT_IMAGE}
                        showUploadList={false}
                        beforeUpload={(file) => {
                          pickImage(shape, file)
                          return false
                        }}
                      >
                        <Button size="small" icon={<UploadOutlined />}>
                          替换图片
                        </Button>
                      </Upload>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {lockedTextItems.length > 0 && (
            <Alert
              type="warning"
              showIcon
              message="有元素文字过长，已改为只读"
              description={`${lockedTextItems
                .map((shape) => shape.name)
                .join('、')} 的文本达到 ${TEXT_ROUND_TRIP_LIMIT} 字，页面只回传前 ${TEXT_ROUND_TRIP_LIMIT} 字，直接保存可能截断内容。请在 PowerPoint 中修改后用「更换 PPT」上传。`}
            />
          )}
        </div>
      )}
    </Drawer>
  )
}