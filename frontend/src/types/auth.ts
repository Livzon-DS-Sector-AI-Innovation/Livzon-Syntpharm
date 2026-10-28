export interface LoginResponse {
  data?: {
    access_token?: string
  }
  message?: string
  detail?: string
}

/** 登录表单（useActionState）状态。定义在类型文件而不是 `actions/auth.ts`：
 *  `'use server'` 文件只允许导出异步函数。 */
export interface LoginActionState {
  error?: string
}
