import type { components } from '@/types/generated/schema'

export interface ModuleInfo {
  code: string
  name: string
  description: string
}

/**
 * The backend's response envelope, taken from the OpenAPI contract rather than
 * restated here. `Omit`/`&` re-add the type parameter so call sites keep
 * `ApiResponse<Foo>` while every field shape stays owned by the generated schema.
 */
export type ApiResponse<T> = Omit<components['schemas']['ApiResponse'], 'data'> & {
  data: T
}

/**
 * A page of results, projected from the contract rather than declared here:
 * the list lives in `data`, the pagination numbers in `meta`. Both shapes come
 * from the generated schema, so this cannot drift from the backend.
 */
export type PaginatedResponse<T> = {
  items: T[]
} & components['schemas']['PaginationMeta']