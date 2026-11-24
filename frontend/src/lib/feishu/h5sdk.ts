/**
 * 飞书 H5 JSSDK 封装：动态加载 SDK 并获取网页应用免登的登录预授权码。
 *
 * 只在飞书客户端 WebView 内可用；普通浏览器没有 window.h5sdk，会直接 reject，
 * 调用方负责降级到 OAuth 授权跳转。
 */

/** 官方 H5 JSSDK。版本号固定在已知可用版本，升级时改这一处。 */
const SDK_URL = 'https://lf-scm-cn.feishucdn.com/lark/op/h5-js-sdk-1.5.30.js'
const SDK_LOAD_TIMEOUT_MS = 6000
const SDK_READY_TIMEOUT_MS = 4000

interface FeishuH5Sdk {
  ready: (callback: () => void) => void
}

interface FeishuJsApi {
  requestAccess: (options: {
    appID: string
    scopeList?: string[]
    success?: (res: { code?: string }) => void
    fail?: (err: unknown) => void
  }) => void
}

declare global {
  interface Window {
    h5sdk?: FeishuH5Sdk
    tt?: FeishuJsApi
  }
}

/** 动态注入 JSSDK（不打包进 bundle，且加载失败能降级）。 */
function loadH5Sdk(): Promise<FeishuH5Sdk> {
  if (window.h5sdk) return Promise.resolve(window.h5sdk)

  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[data-feishu-h5sdk]')
    const script = existing ?? document.createElement('script')
    const timer = window.setTimeout(() => reject(new Error('飞书 JSSDK 加载超时')), SDK_LOAD_TIMEOUT_MS)

    script.addEventListener('load', () => {
      window.clearTimeout(timer)
      if (window.h5sdk) resolve(window.h5sdk)
      else reject(new Error('飞书 JSSDK 不可用'))
    })
    script.addEventListener('error', () => {
      window.clearTimeout(timer)
      reject(new Error('飞书 JSSDK 加载失败'))
    })

    if (!existing) {
      script.src = SDK_URL
      script.async = true
      script.dataset.feishuH5sdk = '1'
      document.head.appendChild(script)
    }
  })
}

/**
 * 把飞书 JSAPI 的错误对象压成一行。
 *
 * 飞书 WebView 里拿不到 DevTools，只能靠 console.warn 进 dev server 日志
 * （`docker compose logs frontend | grep '[browser]'`），所以失败必须带错误码。
 */
function describeFeishuError(err: unknown): string {
  if (!err) return ''
  if (typeof err === 'string') return err
  if (typeof err !== 'object') return String(err)
  const record = err as Record<string, unknown>
  const keys = ['errCode', 'errno', 'code', 'errMsg', 'errString', 'message']
  return keys
    .filter((key) => record[key] !== undefined)
    .map((key) => `${key}=${String(record[key])}`)
    .join(' ')
}

/** 取登录预授权码：必须等 h5sdk.ready 后调用，否则可能拿不到 code。 */
function requestPreauthCode(appId: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const sdk = window.h5sdk
    const jsapi = window.tt
    if (!sdk || !jsapi) {
      reject(new Error('飞书 JSSDK 不可用'))
      return
    }

    const timer = window.setTimeout(() => reject(new Error('飞书授权超时')), SDK_READY_TIMEOUT_MS)

    sdk.ready(() => {
      jsapi.requestAccess({
        appID: appId,
        scopeList: [],
        success: (res) => {
          window.clearTimeout(timer)
          if (res?.code) resolve(res.code)
          else reject(new Error('飞书未返回授权码'))
        },
        fail: (err) => {
          window.clearTimeout(timer)
          const detail = describeFeishuError(err)
          console.warn('[feishu-h5] requestAccess failed', detail)
          reject(new Error(`飞书授权未通过${detail ? `（${detail}）` : ''}`))
        },
      })
    })
  })
}

/** 加载 JSSDK 并取登录预授权码（5 分钟有效、一次性）。 */
export async function requestFeishuPreauthCode(appId: string): Promise<string> {
  await loadH5Sdk()
  return requestPreauthCode(appId)
}