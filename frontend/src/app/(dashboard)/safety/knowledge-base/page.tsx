
'use client'

import { useState, useCallback } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { App, Button, Input, Select, Modal, Tooltip } from 'antd'
import {
  SearchOutlined,
  RobotOutlined,
  SyncOutlined,
  ApartmentOutlined,
} from '@ant-design/icons'
import {
  getKnowledgeArticles,
  createNewArticleVersion,
  semanticSearchArticles,
  generateKnowledgeCard,
  batchGenerateKnowledgeCards,
  generatePpt,
  generateSummary,
  syncKnowledgeArticles,
} from '@/actions/safety'
import DocumentCardGrid from '@/components/safety/DocumentCardGrid'
import KnowledgeSidebar from '@/components/safety/KnowledgeSidebar'
import KnowledgeDetailDrawer from '@/components/safety/KnowledgeDetailDrawer'
import KnowledgeFormModal from '@/components/safety/KnowledgeFormModal'
import { useKnowledgeStore } from '@/stores/safety'
import type { SafetyKnowledgeArticle } from '@/types/safety'
import { filterByMenuKey, computeMenuCounts } from '@/components/safety'

export default function KnowledgeBasePage() {
  // ── Antd App hook ──────────────────────────────────
  const { message } = App.useApp()
  const router = useRouter()

  // ── Store ──────────────────────────────────────────
  const {
    queryParams,
    selectedRowKeys,
    setQueryParams,
    setSelectedRowKeys,
  } = useKnowledgeStore()

  // ── Local state ────────────────────────────────────
  const [searchText, setSearchText] = useState('')
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [categoryFilter] = useState<string | undefined>()
  const [cardStatusFilter, setCardStatusFilter] = useState<string | undefined>()
  const [smartSearch, setSmartSearch] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedMenuKey, setSelectedMenuKey] = useState<string | null>(null)
  const [menuCounts, setMenuCounts] = useState<Map<string, number>>(new Map())
  const [syncing, setSyncing] = useState(false)

  // Modal/Drawer visibility
  const [formOpen, setFormOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState<SafetyKnowledgeArticle | null>(null)
  const [detailId, setDetailId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)



  const handleSearch = () => {
    setQueryParams({ page: 1 })
    refetch()
  }

  const queryClient = useQueryClient()

  const { data: knowledgeData, isLoading, refetch } = useQuery({
    queryKey: ['safety-knowledge', { queryParams, statusFilter, categoryFilter, smartSearch, searchText }],
    queryFn: async () => {
      const pageSize = queryParams.page_size || 200
      let response
      if (smartSearch && searchText) {
        response = await semanticSearchArticles(searchText, queryParams.page || 1, pageSize)
      } else {
        response = await getKnowledgeArticles({
          page: queryParams.page || 1,
          page_size: pageSize,
          status: statusFilter,
          category: categoryFilter,
          keyword: searchText || undefined,
        })
      }
      if (response.code === 200) {
        return { data: response.data as SafetyKnowledgeArticle[], total: response.meta?.total || 0 }
      }
      return { data: [], total: 0 }
    },
  })

  // Client-side filtering
  const items = (() => {
    const data = knowledgeData?.data || []
    let filtered = data
    if (selectedMenuKey) {
      filtered = filterByMenuKey(filtered, selectedMenuKey)
    }
    if (cardStatusFilter === 'has_card') {
      filtered = filtered.filter((a) => a.knowledge_card != null)
    } else if (cardStatusFilter === 'no_card') {
      filtered = filtered.filter((a) => !a.knowledge_card)
    }
    return filtered
  })()

  const total = (() => {
    const totalCount = knowledgeData?.total || 0
    return cardStatusFilter || selectedMenuKey ? items.length : totalCount
  })()

  const loading = isLoading

  // ── Card selection ─────────────────────────────────
  const handleSelectCard = (id: string) => {
    setSelectedRowKeys(
      selectedRowKeys.includes(id)
        ? selectedRowKeys.filter((k) => k !== id)
        : [...selectedRowKeys, id]
    )
  }

  // ── Menu selection ────────────────────────────────
  const handleMenuSelect = useCallback((key: string) => {
    setSelectedMenuKey(key)
    setQueryParams({ page: 1 })
  }, [setQueryParams])

  // ── Sync ──────────────────────────────────────────
  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await syncKnowledgeArticles()
      if (res.code === 200 && res.data) {
        message.success(
          `同步完成：创建 ${res.data.created}，更新 ${res.data.updated}，删除 ${res.data.deleted}`
        )
        refetch()
      } else {
        message.error(res.message || '同步失败')
      }
    } catch {
      message.error('同步请求失败')
    } finally {
      setSyncing(false)
    }
  }

  // ── CRUD actions ───────────────────────────────────
  const handleEdit = (record: SafetyKnowledgeArticle) => {
    setEditingRecord(record)
    setFormOpen(true)
  }

  const handleViewDetail = (record: SafetyKnowledgeArticle) => {
    setDetailId(record.id)
    setDetailOpen(true)
  }


  const handleNewVersion = async (article: SafetyKnowledgeArticle) => {
    const response = await createNewArticleVersion(article.id)
    if (response.code === 200 && response.data) {
      message.success(`已创建新版本 v${response.data.new_article.version}`)
      setDetailId(response.data.new_article.id)
      refetch()
    } else {
      message.error(response.message || '创建新版本失败')
    }
  }

  const handleFormSuccess = () => {
    setFormOpen(false)
    setEditingRecord(null)
    refetch()
  }

  const handleGenerateCard = async (articleId: string) => {
    const res = await generateKnowledgeCard(articleId)
    if (res.code === 200 && res.data) {
      message.success(res.data.message || '知识卡片生成成功')
      refetch()
    } else {
      message.error(res.message || '生成失败')
    }
  }

  const handleBatchGenerateCards = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择文档')
      return
    }
    Modal.confirm({
      title: '批量生成知识卡片',
      content: `确认为选中的 ${selectedRowKeys.length} 份文档生成知识卡片吗？`,
      onOk: async () => {
        const res = await batchGenerateKnowledgeCards(selectedRowKeys)
        if (res.code === 200 && res.data) {
          const d = res.data
          message.success(`成功 ${d.success_count} 份，失败 ${d.failed_count} 份`)
          setSelectedRowKeys([])
          refetch()
        } else {
          message.error(res.message || '批量生成失败')
        }
      },
    })
  }

  const handleGeneratePpt = async (articleId: string) => {
    const res = await generatePpt(articleId, { template: 'training', style: 'professional' })
    if (res.code === 200 && res.data) {
      message.success(res.data.message || 'PPT 生成成功')
      if (res.data.download_url) {
        window.open(`/api/v1/safety/files/${encodeURIComponent(res.data.download_url)}`, '_blank')
      }
    } else {
      message.error(res.message || 'PPT 生成失败')
    }
  }

  const handleGenerateSummary = async (articleId: string) => {
    const res = await generateSummary(articleId)
    if (res.code === 200 && res.data) {
      message.success(res.data.message || '摘要生成成功')
      refetch()
    } else {
      message.error(res.message || '摘要生成失败')
    }
  }

  // ── Render ─────────────────────────────────────────
  return (
    <div style={{ display: 'flex', margin: -24, height: 'calc(100vh - 64px)' }}>
      {/* ── Left Sidebar ── */}
      <KnowledgeSidebar
        selectedKey={selectedMenuKey}
        onSelect={handleMenuSelect}
        counts={menuCounts}
        loading={loading}
      />

      {/* ── Right Content ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 24, minWidth: 0 }}>
        {/* ── Header ── */}
        <div style={{ marginBottom: 24 }}>
        <h2
          style={{
            fontSize: 22,
            fontWeight: 600,
            color: '#1a1a1a',
            margin: 0,
            marginBottom: 4,
            lineHeight: 1.3,
          }}
        >
          文档处理中枢
        </h2>
        <p
          style={{
            fontSize: 14,
            color: '#787671',
            margin: 0,
            lineHeight: 1.5,
          }}
        >
          法规标准 · 知识卡片 · Agent 注入 · 智能检索
        </p>
      </div>

      {/* ── 持久化错误诊断 ── */}
      {loadError && (
        <div
          style={{
            marginBottom: 20,
            padding: '12px 16px',
            background: '#fff2f0',
            border: '1px solid #ffccc7',
            borderRadius: 8,
            fontSize: 13,
            color: '#a8071a',
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all',
          }}
        >
          <strong style={{ fontSize: 14 }}>⚠️ API 请求失败</strong>
          <br />
          {loadError}
          <br />
          <button
            type="button"
            onClick={() => { setLoadError(null); refetch(); }}
            style={{
              marginTop: 8,
              cursor: 'pointer',
              background: '#a8071a',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              padding: '4px 12px',
              fontSize: 12,
            }}
          >
            重试
          </button>
        </div>
      )}

      {/* ── White Card Container ── */}
      <div
        style={{
          background: '#ffffff',
          borderRadius: 12,
          border: '1px solid #e5e3df',
          padding: '16px 20px',
        }}
      >
        {/* ── Filter Bar ── */}
        <div
          style={{
            marginBottom: 16,
            display: 'flex',
            gap: 10,
            alignItems: 'center',
            flexShrink: 0,
          }}
        >
          <Select
            placeholder="状态"
            allowClear
            value={statusFilter}
            onChange={(v) => {
              setStatusFilter(v)
              setQueryParams({ page: 1 })
            }}
            style={{ width: 100 }}
            options={[
              { value: 'draft', label: '草稿' },
              { value: 'published', label: '已发布' },
              { value: 'archived', label: '已归档' },
            ]}
          />
          <Select
            placeholder="卡片状态"
            allowClear
            value={cardStatusFilter}
            onChange={(v) => {
              setCardStatusFilter(v)
              setQueryParams({ page: 1 })
            }}
            style={{ width: 120 }}
            options={[
              { value: 'has_card', label: '有知识卡片' },
              { value: 'no_card', label: '无知识卡片' },
            ]}
          />
          <Input
            placeholder={smartSearch ? '如"防爆区域电气安全相关标准"' : '搜索标题/内容/标签'}
            prefix={<SearchOutlined style={{ color: '#a4a097' }} />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={handleSearch}
            allowClear
            style={{ width: 240 }}
          />

          {/* Smart search toggle */}
          <Tooltip title={smartSearch ? '智能搜索（AI 解析查询意图）' : '关键词搜索'}>
            <button
              type="button"
              onClick={() => setSmartSearch(!smartSearch)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                cursor: 'pointer',
                background: smartSearch ? '#e6e0f5' : 'transparent',
                border: smartSearch ? '1px solid #d6b6f6' : '1px solid transparent',
                borderRadius: 20,
                padding: '2px 10px',
                fontSize: 12,
                fontWeight: smartSearch ? 600 : 400,
                color: smartSearch ? '#7b3ff2' : '#a4a097',
                transition: 'all 0.15s ease',
                lineHeight: '20px',
              }}
            >
              AI
            </button>
          </Tooltip>

          <div style={{ flex: 1 }} />

          <Button
            icon={<ApartmentOutlined />}
            onClick={() => router.push('/safety/knowledge-base/graph')}
          >
            知识图谱
          </Button>

          <Button
            icon={<SyncOutlined spin={syncing} />}
            onClick={handleSync}
            loading={syncing}
          >
            同步
          </Button>

          <Button type="primary" icon={<SearchOutlined />} onClick={handleSearch}>
            查询
          </Button>
        </div>

        {/* ── Batch Operations Bar ── */}
        {selectedRowKeys.length > 0 && (
          <div
            style={{
              marginBottom: 16,
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 12px',
              background: '#f6f5f4',
              borderRadius: 8,
            }}
          >
            <span style={{ fontSize: 13, fontWeight: 500, color: '#5d5b54' }}>
              已选 {selectedRowKeys.length} 项
            </span>
            <Button
              size="small"
              icon={<RobotOutlined />}
              onClick={handleBatchGenerateCards}
            >
              批量生成卡片
            </Button>
            <Button size="small" onClick={() => setSelectedRowKeys([])}>
              取消选择
            </Button>
          </div>
        )}

        {/* ── Card Grid ── */}
        <DocumentCardGrid
          articles={items}
          loading={loading}
          selectedCardIds={selectedRowKeys}
          onSelectCard={handleSelectCard}
          onArticleClick={handleViewDetail}
          onEdit={handleEdit}
          onGenerateCard={handleGenerateCard}
          onGeneratePpt={handleGeneratePpt}
          onGenerateSummary={handleGenerateSummary}
        />
      </div>

      {/* ── Modals & Drawer ── */}
      <KnowledgeFormModal
        open={formOpen}
        editingRecord={editingRecord}
        onClose={() => {
          setFormOpen(false)
          setEditingRecord(null)
        }}
        onSuccess={handleFormSuccess}
      />

      <KnowledgeDetailDrawer
        articleId={detailId}
        open={detailOpen}
        onClose={() => {
          setDetailOpen(false)
          setDetailId(null)
        }}
        onNewVersion={handleNewVersion}
      />
      </div>
    </div>
  )
}
