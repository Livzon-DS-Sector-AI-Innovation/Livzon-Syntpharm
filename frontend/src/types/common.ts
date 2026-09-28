export interface ModuleInfo {
  code: string
  name: string
  description: string
}

// Generic API response wrapper matching backend's ApiResponse structure
export interface ApiResponse<T> {
  code: number
  message: string
  data: T
  meta?: {
    total?: number
    page?: number
    page_size?: number
  }
}

// Generic paginated response wrapper
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}