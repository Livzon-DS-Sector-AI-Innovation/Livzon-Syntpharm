'use client'

import { Button, Progress, Spin, Typography } from 'antd'
import { CloudUploadOutlined } from '@ant-design/icons'

export type UploadPhase = 'uploading' | 'processing'

interface Props {
  phase: UploadPhase
  /** 字节发送进度 0-99；解析阶段不再有可信百分比 */
  percent: number
  fileName: string
  /** 正在处理「停止上传」的点击，防重复提交 */
  stopping?: boolean
  onStop: () => void
}

/**
 * 新建项目的等待视图：上传百分比 → 服务端解析中。
 *
 * 只负责展示与触发停止；中断请求由父组件持有的 AbortController 完成。
 * 进度语义保持诚实：发送阶段报百分比，解析阶段只给不定态，不伪造数字。
 */
export default function UploadWaitingView({ phase, percent, fileName, stopping, onStop }: Props) {
  const uploading = phase === 'uploading'

  return (
    <div className="flex flex-col items-center gap-4 px-2 py-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-[#F3F0FF] text-[24px] text-[#5645D4]">
        {uploading ? <CloudUploadOutlined /> : <Spin size="small" />}
      </div>

      <div className="w-full">
        <Typography.Title level={5} className="!mb-1 !text-[16px]">
          {uploading ? '正在上传，请勿关闭此页' : '正在解析页面，请稍候'}
        </Typography.Title>
        <Typography.Text type="secondary" className="block truncate text-[12px]" title={fileName}>
          {fileName}
        </Typography.Text>
      </div>

      <div className="w-full max-w-[420px]">
        {uploading ? (
          <>
            <Progress percent={percent} status="active" strokeColor="#5645D4" />
            <Typography.Text type="secondary" className="text-[12px]">
              已上传 {percent}%
            </Typography.Text>
          </>
        ) : (
          <Typography.Text type="secondary" className="text-[12px]">
            文件已发送，正在转换并逐页解析；解析完成后会自动进入工作台
          </Typography.Text>
        )}
      </div>

      <Typography.Text type="secondary" className="max-w-[440px] text-[12px]">
        解析耗时与页数相关，请不要刷新或关闭本页。如需中止，点下方按钮，本次新建会被取消且不会产生项目。
      </Typography.Text>

      <Button danger onClick={onStop} loading={stopping} className="!mt-1">
        停止上传
      </Button>
    </div>
  )
}