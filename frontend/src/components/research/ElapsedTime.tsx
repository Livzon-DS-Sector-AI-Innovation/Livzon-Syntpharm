'use client'

import { useEffect, useState } from 'react'
import { formatDuration, jobElapsedMs, type ReportGenJob } from '@/types/research/report-gen'

interface Props {
  job: ReportGenJob
}

/**
 * 生成耗时：每秒自更新。
 *
 * 为什么要单独抽一个组件：详情页要显示「已用 X 分 Y 秒」，但把每秒 tick 放在页面顶层
 * 会让整棵子树（docx 预览 DOM、数百条位置清单）跟着重渲染一次，滚动时明显掉帧。
 * tick 收在这里后，每秒只重渲染这一段文本。
 */
export function ElapsedTime({ job }: Props) {
  const running = !job.finished_at
  const [, setTick] = useState(0)

  useEffect(() => {
    if (!running) return
    const timer = setInterval(() => setTick((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [running])

  return <span>{formatDuration(jobElapsedMs(job))}</span>
}