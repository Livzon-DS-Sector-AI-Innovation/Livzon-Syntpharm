

/** 登录表单（useActionState）状态。定义在类型文件而不是 `actions/auth.ts`：
 *  `'use server'` 文件只允许导出异步函数。 */
export interface LoginActionState {
  error?: string
}

/**
 * 飞书免登 Server Action 返回值。
 *
 * 刻意不在这里 `redirect()`：Server Action 内 redirect 会让客户端 `await` 处抛出
 * `NEXT_REDIRECT`，被调用方 catch 后误判为登录失败（表现：闪一下报错页再进主页）。
 * 改为返回目标地址，由客户端做整页导航，同时确保 Set-Cookie 已落盘。
 */
export interface FeishuLoginActionResult {
  error?: string
  redirectTo?: string
}
