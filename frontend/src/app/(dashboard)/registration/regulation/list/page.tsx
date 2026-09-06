'use client'

import { useEffect, useState, useCallback, Suspense } from 'react'
import { Segmented, Input, Select, DatePicker, Spin } from 'antd'
import {
  LoadingOutlined, SearchOutlined, FilterOutlined, ReloadOutlined,
  InboxOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { useSearchParams, useRouter } from 'next/navigation'
import {
  RegulatoryDocument, DocumentListParams,
  fetchDocuments,
} from '@/lib/api/client/regulatory-tracker'

const { RangePicker } = DatePicker

// ====== 配置常量 ======

type CategoryKey = 'all' | 'attention' | 'general' | 'archive' | 'failed'

const CATEGORY_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '重点关注', value: 'attention' },
  { label: '一般法规', value: 'general' },
  { label: '法规档案', value: 'archive' },
  { label: '分析失败', value: 'failed' },
]

const CATEGORY_API_MAP: Record<string, string | undefined> = {
  all: undefined,
  attention: 'attention',
  general: 'general',
  archive: 'archive',
  failed: 'failed',
}

// 低饱和度影响等级配色
const IMPACT_TAG_CONFIG: Record<string, { color: string; bg: string; label: string }> = {
  high:   { color: '#dc2626', bg: '#fef2f2', label: '高影响' },
  medium: { color: '#d97706', bg: '#fffbeb', label: '中影响' },
  low:    { color: '#475569', bg: '#f8fafc', label: '低影响' },
  none:   { color: '#94a3b8', bg: '#f8fafc', label: '无影响' },
}

const REGULATION_TYPE_OPTIONS = [
  '指导原则', '法规', '公告', '征求意见稿', '通知', '药典增补', '问答函', '检查通知',
]

// ====== 辅助函数 ======

function getImpactLevel(doc: RegulatoryDocument): string {
  if (doc.aiAnalysisStatus !== 'completed' || !doc.aiKeyPoints) return 'unanalyzed'
  const kp = doc.aiKeyPoints as Record<string, unknown>
  return (kp.impact_level as string) || 'low'
}

function getRegulationType(doc: RegulatoryDocument): string {
  if (!doc.aiKeyPoints) return ''
  const kp = doc.aiKeyPoints as Record<string, unknown>
  return (kp.regulation_type as string) || ''
}

// ====== 组件 ======

function WorkspaceContent() {
  const router = useRouter()
  const searchParams = useSearchParams()

  // 状态
  const [documents, setDocuments] = useState<RegulatoryDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 50

  // 筛选状态
  const [category, setCategory] = useState<CategoryKey>('all')
  const [keyword, setKeyword] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [regulationType, setRegulationType] = useState<string | undefined>()
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs | null, dayjs.Dayjs | null] | null>(null)
  const [filtersOpen, setFiltersOpen] = useState(false)

  // 从 URL 参数初始化（Dashboard 跳转）
  // Sync from searchParams (adjusting state during render)
  const [prevSearchParams, setPrevSearchParams] = useState<string>('')
  const currentSearchParams = searchParams.toString()
  if (currentSearchParams !== prevSearchParams) {
    setPrevSearchParams(currentSearchParams)
    const dateParam = searchParams.get('date')
    const categoryParam = searchParams.get('category')

    if (categoryParam) {
      const mapped = Object.entries(CATEGORY_API_MAP).find(([, v]) => v === categoryParam)
      if (mapped) setCategory(mapped[0] as CategoryKey)
    }

    if (dateParam === 'today') {
      const today = dayjs()
      setDateRange([today, today])
    } else if (dateParam === '7days') {
      setDateRange([dayjs().subtract(6, 'day'), dayjs()])
    }
  }

  // 构建请求参数
  const buildParams = useCallback((): DocumentListParams => {
    const params: DocumentListParams = { page, pageSize }

    const apiCategory = CATEGORY_API_MAP[category]
    if (apiCategory) params.documentCategory = apiCategory

    if (keyword) params.keyword = keyword

    if (dateRange && dateRange[0] && dateRange[1]) {
      params.firstFoundFrom = dateRange[0].format('YYYY-MM-DD')
      params.firstFoundTo = dateRange[1].format('YYYY-MM-DD')
    }

    if (regulationType) params.regulationType = regulationType

    // 按发布日期降序（最新优先）
    params.sortBy = 'publish_date'
    params.sortOrder = 'desc'

    return params
  }, [category, keyword, dateRange, regulationType, page])

  // 加载数据
  const loadDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const params = buildParams()
      const data = await fetchDocuments(params)
      if (data) {
        setDocuments(data.items)
        setTotal(data.total)
      }
    } catch (error) {
      console.error('加载法规列表失败:', error)
    } finally {
      setLoading(false)
    }
  }, [buildParams])

  // 搜索处理
  const handleSearch = (value: string) => {
    setKeyword(value)
    setPage(1)
  }

  // 分类切换
  const handleCategoryChange = (value: string | number) => {
    setCategory(value as CategoryKey)
    setPage(1)
  }

  // 刷新
  const handleRefresh = () => {
    loadDocuments()
  }

  // ====== 渲染函数 ======

  const renderImpactTag = (doc: RegulatoryDocument) => {
    if (doc.aiAnalysisStatus === 'failed') {
      return (
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
          style={{ color: '#dc2626', backgroundColor: '#fef2f2' }}
        >
          分析失败
        </span>
      )
    }
    if (doc.aiAnalysisStatus === 'pending' || doc.aiAnalysisStatus === 'analyzing') {
      return (
        <span className="text-xs text-gray-400 flex items-center gap-1">
          <LoadingOutlined spin style={{ fontSize: 10 }} />
          分析中
        </span>
      )
    }
    if (!doc.aiAnalysisStatus) {
      return <span className="text-xs text-gray-400">待回填</span>
    }

    const level = getImpactLevel(doc)
    const config = IMPACT_TAG_CONFIG[level]
    if (!config) return null

    return (
      <span
        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
        style={{ color: config.color, backgroundColor: config.bg }}
      >
        {config.label}
      </span>
    )
  }


  const renderDocRow = (doc: RegulatoryDocument) => {
    const level = getImpactLevel(doc)
    const isHigh = level === 'high'
    const regType = getRegulationType(doc)
    const dateStr = doc.publishDate
      ? dayjs(doc.publishDate).format('YYYY-MM-DD')
      : doc.firstFoundAt
        ? dayjs(doc.firstFoundAt).format('YYYY-MM-DD')
        : ''

    // AI 提示层：三种状态
    let aiHint: React.ReactNode = null
    if (doc.aiAnalysisStatus === 'completed' && doc.aiSummary) {
      aiHint = (
        <div className="text-[13px] text-gray-600 mt-1.5 truncate leading-relaxed">
          <span className="text-gray-400">AI判断：</span>{doc.aiSummary}
        </div>
      )
    } else if (doc.aiAnalysisStatus === 'failed') {
      aiHint = (
        <div className="text-[13px] text-gray-400 mt-1.5">
          AI 评估失败
        </div>
      )
    } else {
      aiHint = (
        <div className="text-[13px] text-gray-300 mt-1.5">
          待 AI 回填
        </div>
      )
    }

    // 左侧边框：高影响法规显示红色细线
    const borderClass = isHigh ? 'border-l-[3px] border-l-red-500' : 'border-l-[3px] border-l-transparent'

    return (
      <div
        key={doc.id}
        onClick={() => router.push(`/registration/regulation/${doc.id}`)}
        className={`block px-6 py-4 hover:bg-gray-50/60 transition-colors duration-150 cursor-pointer ${borderClass}`}
      >
        <div className="flex items-start gap-4">
          {/* 主内容区 */}
          <div className="flex-1 min-w-0">
            {/* 标题 */}
            <div className={`text-[15px] leading-snug text-gray-900 truncate ${isHigh ? 'font-semibold' : 'font-normal'}`}>
              {doc.title}
            </div>
            
            {/* AI 提示层 */}
            {aiHint}
            
            {/* 元信息：来源 · 日期 · 类型 */}
            <div className="text-[11px] text-gray-400 mt-1.5 flex items-center gap-1.5">
              <span>CDE</span>
              <span className="text-gray-200">·</span>
              <span>{dateStr}</span>
              {regType && (
                <>
                  <span className="text-gray-200">·</span>
                  <span>{regType}</span>
                </>
              )}
            </div>
          </div>

          {/* 影响等级 */}
          <div className="w-20 flex-shrink-0 flex items-center pt-0.5">
            {renderImpactTag(doc)}
          </div>

          {/* 查看详情入口 */}
          <div className="w-20 flex-shrink-0 flex items-center pt-0.5 justify-end">
            <span className="text-xs text-gray-400">
              查看详情
            </span>
          </div>
        </div>
      </div>
    )
  }

  const renderEmptyState = () => {
    const emptyMessages: Record<CategoryKey, string> = {
      all: '暂无法规数据',
      attention: '暂无重点关注法规',
      general: '暂无一般法规',
      archive: '暂无归档法规',
      failed: '暂无分析失败的法规',
    }
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-300">
        <InboxOutlined style={{ fontSize: 36 }} />
        <p className="mt-3 text-sm text-gray-400">{emptyMessages[category]}</p>
      </div>
    )
  }

  // ====== 主渲染 ======

  return (
    <div className="min-h-screen bg-white">
      {/* 页头 */}
      <div className="border-b border-gray-100">
        <div className="max-w-[1400px] mx-auto px-8 pt-7 pb-5">
          <div className="flex items-center justify-between mb-5">
            <h1 className="text-xl font-semibold text-gray-900 tracking-tight">法规工作台</h1>
            <button
              onClick={handleRefresh}
              className="text-gray-400 hover:text-gray-600 transition-colors p-1.5 rounded-md hover:bg-gray-50"
              title="刷新"
            >
              <ReloadOutlined />
            </button>
          </div>

          {/* Segmented Control + 搜索 + 筛选 */}
          <div className="flex items-center justify-between gap-4">
            <Segmented
              options={CATEGORY_OPTIONS}
              value={category}
              onChange={handleCategoryChange}
              size="middle"
            />
            <div className="flex items-center gap-2">
              <Input
                placeholder="搜索法规标题"
                prefix={<SearchOutlined className="text-gray-300" />}
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onPressEnter={() => handleSearch(searchInput)}
                allowClear
                onClear={() => handleSearch('')}
                style={{ width: 240 }}
                className="rounded-md"
              />
              <button
                onClick={() => setFiltersOpen(!filtersOpen)}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-md border transition-colors ${
                  filtersOpen
                    ? 'border-blue-200 text-blue-600 bg-blue-50/50'
                    : 'border-gray-200 text-gray-500 hover:border-gray-300 hover:text-gray-600'
                }`}
              >
                <FilterOutlined style={{ fontSize: 12 }} />
                筛选
              </button>
            </div>
          </div>

          {/* 二级筛选（默认折叠） */}
          {filtersOpen && (
            <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-50">
              <Select
                placeholder="法规类型"
                allowClear
                style={{ width: 140 }}
                value={regulationType}
                onChange={(v) => { setRegulationType(v); setPage(1) }}
                options={REGULATION_TYPE_OPTIONS.map(t => ({ label: t, value: t }))}
              />
              <RangePicker
                value={dateRange as [dayjs.Dayjs | null, dayjs.Dayjs | null]}
                onChange={(dates) => {
                  setDateRange(dates as [dayjs.Dayjs | null, dayjs.Dayjs | null])
                  setPage(1)
                }}
                placeholder={['发现日期起', '发现日期止']}
                className="rounded-md"
              />
              {(regulationType || dateRange || keyword) && (
                <button
                  onClick={() => {
                    setRegulationType(undefined)
                    setDateRange(null)
                    setKeyword('')
                    setSearchInput('')
                    setPage(1)
                  }}
                  className="text-xs text-gray-400 hover:text-gray-600"
                >
                  清除筛选
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 列表内容 */}
      <div className="max-w-[1400px] mx-auto">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Spin size="large" />
          </div>
        ) : documents.length === 0 ? (
          renderEmptyState()
        ) : (
          <div className="divide-y divide-gray-50">
            {documents.map(doc => renderDocRow(doc))}
          </div>
        )}

        {/* 分页 */}
        {total > pageSize && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-50">
            <span className="text-sm text-gray-400">
              共 {total} 条法规
            </span>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                className="px-3 py-1 text-sm border border-gray-200 rounded-md disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-50 text-gray-600 transition-colors"
              >
                上一页
              </button>
              <span className="text-sm text-gray-500 tabular-nums">
                {page} / {Math.ceil(total / pageSize)}
              </span>
              <button
                disabled={page >= Math.ceil(total / pageSize)}
                onClick={() => setPage(p => p + 1)}
                className="px-3 py-1 text-sm border border-gray-200 rounded-md disabled:opacity-30 disabled:cursor-not-allowed hover:bg-gray-50 text-gray-600 transition-colors"
              >
                下一页
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )

}

// 默认导出，包裹在 Suspense 中以满足 Next.js 要求
export default function RegulatoryWorkspacePage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-screen"><div className="text-gray-400">加载中...</div></div>}>
      <WorkspaceContent />
    </Suspense>
  )
}
