import { notFound } from 'next/navigation'

/**
 * 兜底路由（catch-all）：把「(dashboard) 段内任何未匹配的路径」主动转成 404。
 *
 * 为什么需要它：Next 对**完全未匹配**的路径会用**根** `app/not-found.tsx`，
 * 那个页面没有侧边导航 —— 用户从菜单点到死链后只能点「返回首页」才能继续。
 * 由本路由主动 `notFound()`，Spring 的 not-found boundary 就落在
 * `(dashboard)/not-found.tsx`（**带侧边导航**），用户可以顺手点别的菜单。
 *
 * 已存在的路由不受影响：Next 优先匹配更具体的路由，本路由只接住剩下的路径。
 */
export default function CatchAllNotFound(): never {
  notFound()
}
