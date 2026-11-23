/**
 * 工作台传输层类型（跨文件共享）。
 *
 * 全部由 OpenAPI 生成契约派生，禁止手写字段：待办已读的入参与出参都由后端
 * `WorkbenchTodoRead` 相关 schema 定义，前端只做别名。
 */
import type { components } from '@/types/generated/schema'

/** 已读标记：source + item_id + 内容指纹（指纹来自 /workbench/overview） */
export type TodoReadMark = components['schemas']['TodoReadMark']

/** 已读写入结果（业务数据来自生成契约 TodoReadResultData） */
export type TodoReadResult = components['schemas']['TodoReadResultData']