/**
 * 人员选择器（`components/common/RemoteUserSelect`）回写值是 `{ id, name }` 对象，
 * 而表单与提交载荷只认 UUID。这里统一做折回，供 `Form.Item normalize` 使用，
 * 同时兼容直接回填字符串（`setFieldsValue` / `initialValues`）的场景。
 */

/** 人员选择器回写的人选结构（与 common/RemoteUserSelect 的 Person 一致） */
export interface PickedPerson {
  id: string
  name: string
}

/** 单选：对象折回 UUID，字符串原样透传，空值归一为 null */
export function toPersonId(value: unknown): string | null {
  if (typeof value === 'string') return value || null
  if (value && typeof value === 'object' && typeof (value as PickedPerson).id === 'string') {
    return (value as PickedPerson).id || null
  }
  return null
}

/** 多选：对象数组折回 UUID 数组，字符串数组原样透传 */
export function toPersonIds(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => toPersonId(item))
    .filter((id): id is string => Boolean(id))
}