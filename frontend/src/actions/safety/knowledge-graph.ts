'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import {
  getFullGraph as getFullGraphApi,
  getGraphNodes as getGraphNodesApi,
  getGraphEdges as getGraphEdgesApi,
  searchGraphNodes as searchGraphNodesApi,
  expandGraphNode as expandGraphNodeApi,
  triggerGraphGeneration as triggerGraphGenerationApi,
} from '@/lib/api/server/safety'
import type {
  FullGraphData,
  GraphEdge,
  GraphExpandParams,
  GraphGenerateRequest,
  GraphGenerateResult,
  GraphNode,
  GraphQueryParams,
} from '@/types/safety'

export async function getFullGraph(params?: GraphQueryParams): Promise<FullGraphData> {
  const authHeaders = await getAuthHeaders()
  const res = await getFullGraphApi((params || {}) as unknown as Record<string, unknown>, authHeaders)
  return res.data as FullGraphData
}

export async function getGraphNodes(params?: GraphQueryParams): Promise<GraphNode[]> {
  const authHeaders = await getAuthHeaders()
  const res = await getGraphNodesApi((params || {}) as unknown as Record<string, unknown>, authHeaders)
  return res.data as GraphNode[]
}

export async function getGraphEdges(params?: GraphQueryParams): Promise<GraphEdge[]> {
  const authHeaders = await getAuthHeaders()
  const res = await getGraphEdgesApi((params || {}) as Record<string, unknown>, authHeaders)
  return res.data as GraphEdge[]
}

export async function searchGraphNodes(query: string, nodeTypes?: string): Promise<GraphNode[]> {
  const authHeaders = await getAuthHeaders()
  const res = await searchGraphNodesApi(query, nodeTypes, authHeaders)
  return res.data as GraphNode[]
}

export async function expandGraphNode(params: GraphExpandParams): Promise<FullGraphData> {
  const authHeaders = await getAuthHeaders()
  const res = await expandGraphNodeApi(params as unknown as Record<string, unknown>, authHeaders)
  return res.data as FullGraphData
}

export async function triggerGraphGeneration(data?: GraphGenerateRequest): Promise<GraphGenerateResult> {
  const authHeaders = await getAuthHeaders()
  const res = await triggerGraphGenerationApi(data || {}, authHeaders)
  revalidatePath('/safety/knowledge-base/graph')
  return res.data as GraphGenerateResult
}