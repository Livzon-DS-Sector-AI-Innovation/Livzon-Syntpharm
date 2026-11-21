'use client'

import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchDirectoryDepartments, type DirectoryDepartmentNode } from '@/lib/api/client/hr'

/**
 * 部门下拉选项：与 DepartmentTreeSelect 共用同一份组织树缓存。
 *
 * 组织树接口一次性返回全量可见部门，不存在分页截断；筛选下拉需要扁平列表，
 * 这里把树拍平。`extra` 用于补充「库里已有、但组织树已撤销」的历史值，
 * 否则老数据按该部门筛选时选项里找不到。
 */
export const DIRECTORY_DEPARTMENTS_QUERY_KEY = ['hr-directory-departments'] as const

export interface DepartmentOption {
  value: string
  label: string
}

function collectNames(nodes: DirectoryDepartmentNode[], out: string[], seen: Set<string>): void {
  for (const node of nodes) {
    const name = node.name?.trim()
    if (name && !seen.has(name)) {
      seen.add(name)
      out.push(name)
    }
    if (node.children?.length) collectNames(node.children, out, seen)
  }
}

export function useDepartmentOptions(extra: Array<string | null | undefined> = []): {
  options: DepartmentOption[]
  isLoading: boolean
} {
  const { data: nodes = [], isLoading } = useQuery<DirectoryDepartmentNode[]>({
    queryKey: DIRECTORY_DEPARTMENTS_QUERY_KEY,
    queryFn: fetchDirectoryDepartments,
    staleTime: 5 * 60 * 1000,
  })

  // extra 是调用方每次渲染新建的数组，直接进依赖会让 memo 失效；
  // 先归一化成字符串键（去空、去重交给下游 seen），memo 里只依赖这个键。
  const extraKey = Array.from(
    new Set(
      extra
        .map((raw) => raw?.trim() ?? '')
        .filter(Boolean),
    ),
  ).join('\u0000')

  const options = useMemo(() => {
    const names: string[] = []
    const seen = new Set<string>()
    collectNames(nodes, names, seen)
    for (const name of extraKey ? extraKey.split('\u0000') : []) {
      if (seen.has(name)) continue
      seen.add(name)
      names.push(name)
    }
    return names.map((name) => ({ value: name, label: name }))
  }, [nodes, extraKey])

  return { options, isLoading }
}