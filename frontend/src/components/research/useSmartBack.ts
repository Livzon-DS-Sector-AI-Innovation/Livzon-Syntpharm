'use client'

import { useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import {
  RETURN_TO_PARAM, describeReturnTarget, sanitizeReturnTo,
} from '@/lib/navigation/returnTo'

interface Options {
  /** 既没有来源签名、也没有浏览器历史时的最终落点（本级列表页） */
  fallbackHref: string
  /** 兜底落点的页面名，用于「返回报告列表」文案 */
  fallbackLabel: string
}

interface SmartBack {
  /** 执行返回：来源签名 → 浏览器上一页 → 上级列表页 */
  back: () => void
  /** 按钮文案，随来源变化 */
  label: string
  /** 悬停提示：明确会回到哪一页，避免「返回到哪」的预期落差 */
  hint: string
}

/**
 * 返回上一操作界面：来源签名 → 浏览器历史 → 上级列表页，三级回退。
 *
 * 为什么不能只用 router.back()：用户从收藏、消息或新标签页直接打开详情页时，
 * 历史里没有上一页，back() 会把人送出系统；所以优先用跳转时带上的 returnTo，
 * 最后才落到本级列表页。
 */
export function useSmartBack({ fallbackHref, fallbackLabel }: Options): SmartBack {
  const router = useRouter()
  const searchParams = useSearchParams()
  const from = sanitizeReturnTo(searchParams.get(RETURN_TO_PARAM))
  const fromLabel = describeReturnTarget(from)

  const back = useCallback(() => {
    if (from) {
      router.push(from)
      return
    }
    // history.state.idx 由 Next 维护：>0 说明有本站上一页可以退
    const idx = (window.history.state as { idx?: number } | null)?.idx ?? 0
    if (idx > 0) {
      router.back()
      return
    }
    router.push(fallbackHref)
  }, [fallbackHref, from, router])

  return {
    back,
    label: from ? `返回${fromLabel ?? '上一页'}` : `返回${fallbackLabel}`,
    hint: from ? `回到${fromLabel ?? '上一页'}` : `回到${fallbackLabel}`,
  }
}