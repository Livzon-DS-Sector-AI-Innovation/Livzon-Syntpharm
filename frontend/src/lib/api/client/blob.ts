/**
 * 浏览器端取二进制流（预览 / 下载附件）。
 *
 * 为什么不用 apiGet：附件接口返回的是文件流而不是 JSON 信封，
 * 且下载响应带 Content-Disposition，需要保留原始 Blob 交给预览组件或 <a download>。
 */

/** 从 cookie 里取登录态，拼成 Bearer 头；SSR 阶段返回空对象 */
export function authHeaders(): Record<string, string> {
  if (typeof document === 'undefined') return {}
  const token = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith('auth_token='))
  return token ? { Authorization: `Bearer ${token.slice('auth_token='.length)}` } : {}
}

/**
 * 取同源文件流；404 给出可读提示，其余状态带状态码，便于调用方直接弹 message。
 * @param path 以 / 开头的站内路径
 * @param notFoundMessage 404 时的提示文案
 */
export async function fetchBlob(path: string, notFoundMessage = '文件还未生成'): Promise<Blob> {
  const response = await fetch(path, {
    method: 'GET',
    headers: authHeaders(),
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error(response.status === 404 ? notFoundMessage : `加载失败（${response.status}）`)
  }
  return response.blob()
}