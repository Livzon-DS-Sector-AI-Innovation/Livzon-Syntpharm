'use client'

import { Tooltip } from 'antd'
import type { NodePrediction, NodeStatus } from '@/types/registration'

interface NodeProgressBarProps {
  nodes: NodePrediction[]
  size?: 'sm' | 'md'
}

const STATUS_STYLES: Record<NodeStatus, { dot: string; label: string }> = {
  completed: { dot: 'bg-[#1aae39]', label: '已完成' },
  in_progress: { dot: 'bg-[#5645d4] animate-pulse', label: '进行中' },
  pending: { dot: 'bg-[#c8c4be]', label: '未开始' },
  skipped: { dot: 'bg-transparent border border-[#a4a097] text-[#a4a097]', label: '已跳过' },
}

/** 审评节点迷你进度圆点条：●完成 ◐进行中 ○未开始 ⊘跳过 */
export function NodeProgressBar({ nodes, size = 'sm' }: NodeProgressBarProps) {
  const dotSize = size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3'
  return (
    <div className="inline-flex items-center gap-1">
      {nodes.map((node) => (
        <Tooltip
          key={node.node_index}
          title={
            <div className="text-xs">
              <div className="font-medium">
                {node.node_index}. {node.node_name}
              </div>
              <div>{STATUS_STYLES[node.status].label}</div>
              {node.actual_date && <div>实际：{node.actual_date}</div>}
              {!node.actual_date && node.estimated_date && <div>预计：{node.estimated_date}</div>}
              {node.estimated_range && (
                <div>
                  区间：{node.estimated_range[0]} ~ {node.estimated_range[1]}
                </div>
              )}
              {node.delta_days !== null && node.delta_days !== undefined && node.delta_days !== 0 && (
                <div>{node.delta_days > 0 ? `延迟 ${node.delta_days} 天` : `提前 ${-node.delta_days} 天`}</div>
              )}
            </div>
          }
        >
          <span
            className={`inline-block rounded-full ${dotSize} ${STATUS_STYLES[node.status].dot} flex items-center justify-center`}
          >
            {node.status === 'skipped' && <span className="text-[8px] leading-none">⊘</span>}
          </span>
        </Tooltip>
      ))}
    </div>
  )
}
