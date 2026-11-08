'use client'

/**
 * 全部项目的知识库总览。
 *
 * 未选项目时替代 KnowledgeBaseManager：一屏看清各项目知识库的就绪状态与文档解析进度，
 * 点「查看」或直接点整行即切到该项目的管理界面。
 */
import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Card, Empty, Table, Tag } from 'antd'
import dayjs from 'dayjs'
import { fetchKnowledgeBaseList } from '@/lib/api/client/research/knowledge-base'
import {
  KB_STATUS_COLORS,
  KB_STATUS_LABELS,
  type KnowledgeBaseItem,
} from '@/types/research/knowledge-base'

interface Props {
  /** 切到某个项目的知识库管理界面 */
  onSelectProject: (projectId: string) => void
}

export function KnowledgeBaseOverview({ onSelectProject }: Props) {
  const { data: items = [], isLoading } = useQuery({
    queryKey: ['knowledge-bases', 'all'],
    queryFn: fetchKnowledgeBaseList,
    // 有文档还在解析时轮询，让总览里的进度自己往前走
    refetchInterval: (query) =>
      (query.state.data ?? []).some((kb) => (kb.parsing_count ?? 0) > 0) ? 5000 : false,
  })

  const summary = useMemo(() => {
    const projectIds = new Set(items.map((kb) => kb.project_id))
    const parsing = items.reduce((sum, kb) => sum + (kb.parsing_count ?? 0), 0)
    return { projectCount: projectIds.size, parsing }
  }, [items])

  const columns = [
    {
      title: '项目',
      dataIndex: 'project_name',
      key: 'project_name',
      width: 220,
      ellipsis: true,
      render: (v: string, record: KnowledgeBaseItem) => v || record.project_id,
    },
    {
      title: '知识库',
      dataIndex: 'name',
      key: 'name',
      width: 240,
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (v: string) => (
        <Tag color={KB_STATUS_COLORS[v] ?? 'default'}>{KB_STATUS_LABELS[v] ?? v}</Tag>
      ),
    },
    { title: '文档数', dataIndex: 'document_count', key: 'document_count', width: 90 },
    {
      title: '已解析',
      dataIndex: 'parsed_count',
      key: 'parsed_count',
      width: 90,
      render: (v: number) => <span style={{ color: v > 0 ? '#389e0d' : '#bfbfbf' }}>{v}</span>,
    },
    {
      title: '解析中',
      dataIndex: 'parsing_count',
      key: 'parsing_count',
      width: 90,
      render: (v: number) => (v > 0 ? <Tag color="processing">{v}</Tag> : <span style={{ color: '#bfbfbf' }}>0</span>),
    },
    {
      title: '失败',
      dataIndex: 'failed_count',
      key: 'failed_count',
      width: 80,
      render: (v: number) => (v > 0 ? <span style={{ color: '#cf1322' }}>{v}</span> : <span style={{ color: '#bfbfbf' }}>0</span>),
    },
    {
      title: '更新时间',
      dataIndex: 'last_synced_at',
      key: 'last_synced_at',
      width: 160,
      render: (v: string | null, record: KnowledgeBaseItem) =>
        dayjs(v ?? record.created_at ?? undefined).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: unknown, record: KnowledgeBaseItem) => (
        <Button type="link" size="small" onClick={() => onSelectProject(record.project_id)}>
          查看
        </Button>
      ),
    },
  ]

  return (
    <Card
      title={
        <span>
          知识库总览
          <span style={{ fontSize: 13, color: '#8c8c8c', fontWeight: 400, marginLeft: 8 }}>
            共 {items.length} 个 · 覆盖 {summary.projectCount} 个项目
            {summary.parsing > 0 ? ` · ${summary.parsing} 份解析中` : ''}
          </span>
        </span>
      }
    >
      <Table
        dataSource={items}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20, hideOnSinglePage: true }}
        scroll={{ x: 1200 }}
        locale={{
          emptyText: (
            <Empty
              description="还没有任何项目知识库：在上方选择一个项目，即可为它创建知识库并上传资料"
            />
          ),
        }}
        onRow={(record) => ({
          onClick: () => onSelectProject(record.project_id),
          style: { cursor: 'pointer' },
        })}
      />
    </Card>
  )
}