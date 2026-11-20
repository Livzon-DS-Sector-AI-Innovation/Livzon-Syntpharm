'use client'

import { CloudDownloadOutlined } from '@ant-design/icons'
import { Button, Modal, Space, Typography } from 'antd'

interface Props {
  open: boolean
  /** 页面内播放地址（后端 inline 媒体流，支持 Range） */
  src?: string | null
  title?: string
  fileName?: string | null
  downloadUrl?: string | null
  onClose: () => void
}

/**
 * 成片预览弹窗：原生 `<video>` + 后端媒体流，播放/拖进度/全屏/音量都由浏览器提供。
 *
 * 必须 `destroyOnHidden`：antd 的 Modal 默认只是把内容隐藏，`<video>` 仍在 DOM 里
 * 继续缓冲，关掉弹窗后网络请求不会停。销毁后重新打开会重新拉流，代价只有一次 Range 请求。
 */
export default function VideoPreviewModal({ open, src, title, fileName, downloadUrl, onClose }: Props) {
  return (
    <Modal
      open={open}
      title={
        <Space size={6} wrap>
          <span>成片预览</span>
          {title && (
            <Typography.Text type="secondary" className="text-[12px]">
              {title}
            </Typography.Text>
          )}
        </Space>
      }
      width={880}
      centered
      destroyOnHidden
      onCancel={onClose}
      styles={{ body: { padding: 0 } }}
      footer={
        <Space>
          {downloadUrl && (
            <Button icon={<CloudDownloadOutlined />} href={downloadUrl} download>
              下载
            </Button>
          )}
          <Button onClick={onClose}>关闭</Button>
        </Space>
      }
    >
      {open && src ? (
        // key 绑 src：切换版本时强制换源，避免沿用上一个视频的缓冲与进度
        <video
          key={src}
          src={src}
          controls
          playsInline
          preload="metadata"
          className="block w-full rounded-b-lg bg-black"
          style={{ maxHeight: '70vh' }}
        >
          {fileName ? `当前浏览器不支持内嵌播放，可下载后观看：${fileName}` : '当前浏览器不支持内嵌播放'}
        </video>
      ) : (
        <div className="flex h-[240px] items-center justify-center text-[13px] text-[#A4A097]">
          这个版本还没有可播放的成片
        </div>
      )}
    </Modal>
  )
}