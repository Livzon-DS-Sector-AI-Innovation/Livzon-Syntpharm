import ui from './registration-ui.module.css'

/**
 * antd 语义色名 → 注册模块共享标签类。
 * 用于把存量 STATUS_LABELS 等配置里的 color 字段映射到设计令牌标签。
 */
export function tagClassOf(color?: string): string {
  switch (color) {
    case 'success':
      return ui.tagOk
    case 'error':
      return ui.tagRisk
    case 'warning':
      return ui.tagWarn
    case 'blue':
    case 'processing':
      return ui.tagInfo
    default:
      return ui.tagPlain
  }
}
