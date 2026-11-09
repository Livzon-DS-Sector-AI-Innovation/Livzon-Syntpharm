/**
 * 智能体 - PPT 配音视频：新建时的浏览器端上传通道。
 *
 * 为什么不用 Server Action：新建需要（1）真实上传百分比（2）可中断的请求。
 * AGENTS.md 明确允许「需要上传进度追踪」时在 `lib/api/client/` 直接请求，
 * 因此这里用 XHR（`upload.onprogress` + `abort()`），其余写操作仍在 `actions/`。
 *
 * 相对路径由 `src/proxy.ts` 转发到后端，禁止硬编码后端地址。
 * 取消语义由后端兜底：请求断开后服务端不落库（见 `modules/agent/api.py` 的断连检测）。
 */
import { getAuthToken, redirectToLogin } from '@/lib/api/client'
import type { ProjectDetail } from '@/types/agent/ppt-video'

const API = '/api/v1/agent/ppt-videos'

/** 服务端要跑 LibreOffice 转换 + 逐页解析，给足 15 分钟；网更快时也会先被网关断 */
const DEFAULT_TIMEOUT_MS = 15 * 60 * 1000

/** 用户主动停止上传：不是故障，调用方应静默回退而不是弹错误 */
export class UploadCanceledError extends Error {
  constructor() {
    super('已取消本次上传')
    this.name = 'UploadCanceledError'
  }
}

export class UploadFailedError extends Error {
  constructor(
    message: string,
    public status?: number,
  ) {
    super(message)
    this.name = 'UploadFailedError'
  }
}

export interface UploadPptVideoOptions {
  formData: FormData
  /** 字节发送进度，0-99；转成服务端解析阶段后不再回调，避免伪造进度 */
  onProgress?: (percent: number) => void
  /** 请求体已发完，进入服务端转换/解析阶段 */
  onUploaded?: () => void
  /** 外部中断（用户点「停止上传」、关页、组件卸载） */
  signal?: AbortSignal
  timeoutMs?: number
}

const STATUS_MESSAGE: Record<number, string> = {
  400: '上传内容不符合要求，请检查文件格式与页数',
  401: '登录已过期，请重新登录',
  403: '当前账号没有新建权限',
  413: '文件超过网关大小限制，请压缩后再上传',
  422: '上传参数校验失败，请检查填写内容',
  499: '上传已取消',
  500: '服务端处理失败，请稍后重试',
  502: '网关错误，请稍后重试',
  503: '服务暂时不可用，请稍后重试',
  504: '服务端处理超时，请稍后重试',
}

function extractMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null
  const envelope = body as { message?: unknown; detail?: unknown }
  if (typeof envelope.message === 'string' && envelope.message.trim()) return envelope.message
  if (typeof envelope.detail === 'string' && envelope.detail.trim()) return envelope.detail
  return null
}

/**
 * 上传 PPT（含可选讲稿）并创建项目。
 *
 * 成功返回项目详情；用户中止抛 `UploadCanceledError`；其它失败抛 `UploadFailedError`。
 */
export function uploadPptVideoProject({
  formData,
  onProgress,
  onUploaded,
  signal,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}: UploadPptVideoOptions): Promise<ProjectDetail> {
  return new Promise<ProjectDetail>((resolve, reject) => {
    if (signal?.aborted) {
      reject(new UploadCanceledError())
      return
    }

    const xhr = new XMLHttpRequest()
    let settled = false

    const finish = (step: () => void) => {
      if (settled) return
      settled = true
      signal?.removeEventListener('abort', handleAbort)
      step()
    }

    function handleAbort() {
      xhr.abort()
    }

    xhr.open('POST', API, true)
    // 不设 Content-Type：multipart 的 boundary 必须由浏览器生成
    const token = getAuthToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.responseType = 'text'
    xhr.timeout = timeoutMs

    xhr.upload.onprogress = (event) => {
      if (settled || !event.lengthComputable || !onProgress) return
      // 服务端解析阶段没有可信百分比，发送阶段最多报到 99
      onProgress(Math.min(99, Math.round((event.loaded / event.total) * 100)))
    }
    // 请求体发完 ≠ 创建成功：后面还有转换、解析、落库
    xhr.upload.onload = () => {
      if (!settled) onUploaded?.()
    }

    xhr.onload = () => {
      finish(() => {
        let body: unknown = null
        try {
          body = xhr.responseText ? JSON.parse(xhr.responseText) : null
        } catch {
          body = null
        }

        if (xhr.status >= 200 && xhr.status < 300) {
          const data = (body as { data?: ProjectDetail } | null)?.data
          if (data?.id) {
            resolve(data)
            return
          }
          reject(new UploadFailedError('服务端返回数据不完整，请到项目列表确认是否已创建'))
          return
        }

        if (xhr.status === 401) redirectToLogin()
        reject(
          new UploadFailedError(
            extractMessage(body) || STATUS_MESSAGE[xhr.status] || `上传失败（HTTP ${xhr.status}）`,
            xhr.status,
          ),
        )
      })
    }

    xhr.onerror = () => finish(() => reject(new UploadFailedError('网络连接中断，请检查网络后重试')))
    xhr.ontimeout = () => finish(() => reject(new UploadFailedError('上传超时，请稍后重试')))
    xhr.onabort = () => finish(() => reject(new UploadCanceledError()))

    signal?.addEventListener('abort', handleAbort, { once: true })
    xhr.send(formData)
  })
}