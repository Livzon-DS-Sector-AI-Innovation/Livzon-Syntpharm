/**
 * 浏览器保存文件的公共实现。
 *
 * 下载必须由浏览器直接接收文件流（AGENTS.md 下载例外），各处原本各写一份
 * 「createObjectURL → a.click() → revokeObjectURL」，这里统一收口。
 */

/** 触发浏览器保存一个 Blob */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

/** 直接把 fetch 的响应体存盘（调用方需先确保 response.ok） */
export async function saveResponse(response: Response, filename: string): Promise<void> {
  saveBlob(await response.blob(), filename)
}
