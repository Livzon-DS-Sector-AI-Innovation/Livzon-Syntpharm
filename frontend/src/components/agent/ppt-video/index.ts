'use client'

/**
 * PPT 配音视频组件出口。
 *
 * `'use client'` 必须留在 barrel 上：里面有使用 antd `App.useApp()` / hooks 的组件，
 * 服务端评估会直接报错（与各模块约定一致）。
 */
export { default as AiConfigDrawer } from './AiConfigDrawer'
export { default as AiGuidePanel } from './AiGuidePanel'
export { default as AiKeyPanel } from './AiKeyPanel'
export { default as AiModelPicker } from './AiModelPicker'
export { default as HighlightPreview } from './HighlightPreview'
export { default as ManifestDrawer } from './ManifestDrawer'
export { default as PageImagesProgress } from './PageImagesProgress'
export { default as PptUploadModal } from './PptUploadModal'
export { default as PptVideoTable } from './PptVideoTable'
export { default as PptVideoWorkbench } from './PptVideoWorkbench'
export { default as ProjectSettingsCard } from './ProjectSettingsCard'
export { default as RenderProgress } from './RenderProgress'
export { default as RevisionDrawer } from './RevisionDrawer'
export { default as ScriptDraftBanner } from './ScriptDraftBanner'
export { default as SlideContentEditor } from './SlideContentEditor'
export { default as SlideEditor } from './SlideEditor'
export { default as SlideTimeline } from './SlideTimeline'
export { default as SourceReplaceModal } from './SourceReplaceModal'
export { default as VersionPanel } from './VersionPanel'
export { default as VideoPreviewModal } from './VideoPreviewModal'