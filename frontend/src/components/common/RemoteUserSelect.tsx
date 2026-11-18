'use client'

/**
 * @deprecated 统一人员选择器已迁移到 `components/common/PersonSelect`（#219）。
 *
 * 本文件只保留旧导出名以兼容尚未迁移的调用点，内部实现与 `PersonSelect`
 * 完全相同，数据源已经是 HR 主数据（`/api/v1/hr/directory/people`）。
 * 新代码请直接 `import PersonSelect from '@/components/common/PersonSelect'`；
 * 全部调用点迁移完成后本文件会删除。
 */
export { default as RemoteUserSelect, PersonMultiSelect as RemoteUserMultiSelect } from './PersonSelect'
export type {
  PersonMultiSelectProps as RemoteUserMultiSelectProps,
  PersonSelectProps as RemoteUserSelectProps,
} from './PersonSelect'