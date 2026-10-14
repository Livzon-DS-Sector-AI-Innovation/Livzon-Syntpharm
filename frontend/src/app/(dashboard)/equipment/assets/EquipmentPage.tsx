'use client'

import '../../../../styles/industrial-theme.css';
import { useEffect, useCallback, useMemo, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { App, ConfigProvider, Tabs, Button, Pagination } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { MenuFoldOutlined, MenuUnfoldOutlined, ReloadOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { EquipmentCategory, Location, Equipment, EquipmentStatistics } from '@/types/equipment/generated-bridge'
import { useEquipmentStore } from '@/stores/equipment'
import { antdTheme } from '@/lib/antd-theme'
import type { GetStatisticsQuery } from '@/lib/api/client/equipment'
import {
  EQUIPMENT_LIST_KEY,
  EQUIPMENT_STATISTICS_KEY,
  EQUIPMENT_TAXONOMY_KEY,
  useEquipmentListQuery,
  useEquipmentStatisticsQuery,
  useEquipmentTaxonomyQuery,
} from '@/hooks/useEquipmentLedger'
import {
  DEFAULT_EQUIPMENT_SORT_BY,
  DEFAULT_EQUIPMENT_SORT_ORDER,
  parseEquipmentUrlParams,
  writeEquipmentUrlQuery,
  type EquipmentListQuery,
  type EquipmentUrlState,
} from '@/lib/api/equipment-query'
import { CategoryTree, ColumnConfigModal, EquipmentDrawer, EquipmentFilterBar, EquipmentImportModal, EquipmentTable, LocationDrawer, LocationTree, RepairDrawer, StatsCards } from '@/components/equipment'

interface EquipmentPageProps {
  initialCategories: EquipmentCategory[]
  initialLocations: Location[]
  initialEquipments: Equipment[]
  initialTotal: number
  initialStatistics: EquipmentStatistics
  initialDepartments: import('@/lib/api/client/equipment').DepartmentOption[]
}

const SIDEBAR_WIDTH = 280
const DEFAULT_VISIBLE_COLUMNS = [
  'asset_no', 'name', 'location_text', 'department',
  'responsible', 'status', 'commissioning_date',
]

export function EquipmentPage({
  initialCategories,
  initialLocations,
  initialEquipments,
  initialTotal,
  initialStatistics,
  initialDepartments,
}: EquipmentPageProps) {
  const {
    failureCodes,
    selectedCategory,
    selectedLocation,
    statusFilter,
    departmentFilter,
    keyword,
    openEquipmentDrawer,
    setSelectedCategory,
    setSelectedLocation,
  } = useEquipmentStore()

  const queryClient = useQueryClient()

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [columnConfigOpen, setColumnConfigOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [visibleColumns, setVisibleColumns] = useState<string[]>(DEFAULT_VISIBLE_COLUMNS)

  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  // 排序与分页以 URL 为唯一来源（可分享、刷新保持）；筛选条件仍由 store 单一持有
  const { state: urlState, rejectedSort } = useMemo(() => parseEquipmentUrlParams(searchParams), [searchParams])

  const patchQuery = useCallback((patch: Partial<EquipmentUrlState>) => {
    const nextQs = writeEquipmentUrlQuery(new URLSearchParams(searchParams.toString()), { ...urlState, ...patch })
    router.replace(nextQs ? `${pathname}?${nextQs}` : pathname, { scroll: false })
  }, [pathname, router, searchParams, urlState])

  // 列配置：从 localStorage 加载首次挂载时的可见列。EquipmentTable 受控展示。
  useEffect(() => {
    try {
      const stored = localStorage.getItem('equipment_visible_columns')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
          // eslint-disable-next-line react-hooks/set-state-in-effect -- localStorage is client-only; reading it in the useState initializer would diverge from the SSR column set (hydration mismatch)
          setVisibleColumns(parsed)
          return
        }
      }
    } catch (e) {
      console.warn('Failed to load column config:', e)
    }
  }, [])

  // 持久化列配置变更到 localStorage
  useEffect(() => {
    if (visibleColumns.length > 0) {
      try {
        localStorage.setItem('equipment_visible_columns', JSON.stringify(visibleColumns))
      } catch (e) {
        console.warn('Failed to save column config:', e)
      }
    }
  }, [visibleColumns])

  // 列表取数参数：排序与分页来自 URL，筛选来自 store，二者在此合成唯一一份
  const listParams = useMemo<EquipmentListQuery>(() => ({
    category_id: selectedCategory,
    location_id: selectedLocation,
    department_id: departmentFilter,
    status: statusFilter || undefined,
    keyword: keyword || undefined,
    ...urlState,
  }), [selectedCategory, selectedLocation, departmentFilter, statusFilter, keyword, urlState])

  const statsParams = useMemo<GetStatisticsQuery>(() => ({
    category_id: selectedCategory || undefined,
    location_id: selectedLocation || undefined,
    department_id: departmentFilter || undefined,
    status: statusFilter || undefined,
  }), [selectedCategory, selectedLocation, departmentFilter, statusFilter])

  // SSR 只在「无筛选 + URL 排序分页」这一份参数上取过数；参数一致才喂 initialData，
  // 否则会把首屏数据错当成新 key 的结果（换页/换筛选后不再请求）。
  // SSR 侧某个 API 失败时喂 undefined，让 React Query 正常发起首屏补偿请求。
  const [ssrSignature] = useState(() => JSON.stringify({ ...listParams }))
  const isSsrQuery = JSON.stringify(listParams) === ssrSignature
  const equipmentsQuery = useEquipmentListQuery(listParams, isSsrQuery
    && (initialEquipments.length > 0 || initialTotal > 0)
    ? { items: initialEquipments, total: initialTotal, page: urlState.page, page_size: urlState.page_size }
    : undefined)
  const statisticsQuery = useEquipmentStatisticsQuery(
    statsParams,
    isSsrQuery && initialStatistics.total > 0 ? initialStatistics : undefined,
  )
  const taxonomyQuery = useEquipmentTaxonomyQuery(
    initialCategories.length > 0 || initialLocations.length > 0 || initialDepartments.length > 0
      ? { categories: initialCategories, locations: initialLocations, departments: initialDepartments }
      : undefined,
  )

  const categories = taxonomyQuery.data?.categories ?? initialCategories
  const locations = taxonomyQuery.data?.locations ?? initialLocations
  const departments = taxonomyQuery.data?.departments ?? initialDepartments
  const equipments = equipmentsQuery.data?.items ?? initialEquipments
  const total = equipmentsQuery.data?.total ?? initialTotal

  // 数据变更后重取（新增/编辑/删除/导入完成）
  const refreshList = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: EQUIPMENT_LIST_KEY })
  }, [queryClient])

  const refreshStatistics = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: EQUIPMENT_STATISTICS_KEY })
  }, [queryClient])

  const refreshTaxonomy = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: EQUIPMENT_TAXONOMY_KEY })
  }, [queryClient])

  // 筛选变化 → 回到第 1 页并写回 URL；取数由 queryKey 变化自动触发
  const filterSignature = `${selectedCategory ?? ''}|${selectedLocation ?? ''}|${departmentFilter ?? ''}|${statusFilter}|${keyword ?? ''}`
  const previousFilters = useRef(filterSignature)

  useEffect(() => {
    if (previousFilters.current === filterSignature) return
    previousFilters.current = filterSignature
    if (urlState.page !== 1) patchQuery({ page: 1 })
  }, [filterSignature, urlState.page, patchQuery])

  const tabItems = [
    {
      key: 'category',
      label: '分类',
      children: <CategoryTree categories={categories} onRefresh={refreshTaxonomy} />,
    },
    {
      key: 'location',
      label: '位置',
      children: <LocationTree locations={locations} onRefresh={refreshTaxonomy} />,
    },
  ]

  const tabBarExtra = (selectedCategory || selectedLocation) ? (
    <Button
      type="text"
      size="small"
      icon={<ReloadOutlined />}
      onClick={() => {
        setSelectedCategory(null)
        setSelectedLocation(null)
      }}
      style={{ color: '#787671', marginRight: 4 }}
    >
      重置
    </Button>
  ) : null

  const currentStats = statisticsQuery.data ?? initialStatistics

  return (
    <ConfigProvider theme={antdTheme} locale={zhCN}>
      <App>
        {/* 页面根容器：固定高度，无页面级滚动 */}
        <div style={{ 
          height: '100vh', 
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}>
          {/* 第一段：标题 + 统计 + 筛选栏（固定高度） */}
          <div style={{ flexShrink: 0 }}>
            {/* 标题行 */}
            <div style={{ 
              marginBottom: 8,
              paddingBottom: 6,
              borderBottom: '1px solid #E7E5E4',
            }}>
              <h2 className="equipment-page-title"
                style={{
                  fontSize: 24, 
                  fontWeight: 700,
                  margin: 0, 
                  marginBottom: 6, 
                  lineHeight: 1.2,
                  color: '#1C1917',
                  letterSpacing: '-0.02em',
                }}
              >
                设备台账
              </h2>
              <p className="equipment-page-subtitle"
                style={{ 
                  fontSize: 14, 
                  margin: 0, 
                  lineHeight: 1.5,
                  color: '#78716C',
                  fontWeight: 400,
                }}>
                分类管理 · 位置管理 · 设备档案 · 状态追踪
              </p>
            </div>

        {/* 工具栏：compact 统计 + 筛选条 + inline 摘要标签，三件套合成一条 sticky 块 */}
        <div
          className="equipment-toolbar"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 10,
            background: '#ffffff',
            padding: '8px 0 6px 0',
            borderBottom: '1px solid #E7E5E4',
          }}
        >
          {/* 统计卡片区域 - 横向铺满 */}
          <div style={{ 
            marginBottom: 8,
          }}>
            <StatsCards statistics={currentStats} compact={false} />
          </div>
          <EquipmentFilterBar
            sortBy={urlState.sort_by}
            sortOrder={urlState.sort_order}
            onResetSort={() => patchQuery({
              sort_by: DEFAULT_EQUIPMENT_SORT_BY,
              sort_order: DEFAULT_EQUIPMENT_SORT_ORDER,
              page: 1,
            })}
            invalidSort={rejectedSort}
            locations={locations}
            categories={categories}
            departments={departments}
            onOpenColumnConfig={() => setColumnConfigOpen(true)}
            onOpenImport={() => setImportOpen(true)}
            onAddNew={() => openEquipmentDrawer()}
          />
          </div>
          </div>

          {/* 第二段：左右分栏（无滚动，内部子元素控制滚动） */}
          <div 
            className="flex gap-4"
            style={{ 
              flex: 1, 
              overflow: 'hidden',
              alignItems: 'stretch',
            }}
          >
          {/* 左侧：可折叠分类/位置树（随第二段滚动） */}
          {!sidebarCollapsed && (
            <div
              className="shrink-0"
              style={{
                width: SIDEBAR_WIDTH,
                background: '#ffffff',
                padding: 20,
                borderRadius: 12,
                border: '1px solid #E7E5E4',
                alignSelf: 'flex-start',
              }}
            >
              <Tabs items={tabItems} tabBarExtraContent={tabBarExtra} />
            </div>
          )}

          {/* 右侧：设备列表（flex column 布局） */}
          <div
            className="flex-1 min-w-0"
            style={{
              background: '#ffffff',
              padding: '12px 16px',
              borderRadius: 12,
              border: '1px solid #E7E5E4',
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden',
            }}
          >
            <div className="mb-3 flex items-center gap-3">
              <Button
                type="text"
                icon={sidebarCollapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
                style={{ color: '#5d5b54' }}
              />
            </div>

            {/* 表格区域（flex: 1，内部滚动） */}
            <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
              <EquipmentTable
                equipments={equipments}
                loading={equipmentsQuery.isFetching}
                page={urlState.page}
                pageSize={urlState.page_size}
                sortBy={urlState.sort_by}
                sortOrder={urlState.sort_order}
                onQueryChange={patchQuery}
                onRefresh={refreshList}
                onRefreshStatistics={refreshStatistics}
                visibleColumns={visibleColumns}
                onVisibleColumnsChange={setVisibleColumns}
              />
            </div>

            {/* 第三段：独立分页控件（固定） */}
            <div style={{ 
              flexShrink: 0, 
              paddingTop: 12,
              borderTop: '1px solid #E7E5E4',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}>
              <span style={{ color: '#78716C', fontSize: 14 }}>
                共 <strong style={{ color: '#1C1917' }}>{total}</strong> 条
              </span>
              <Pagination
                current={urlState.page}
                pageSize={urlState.page_size}
                total={total}
                showSizeChanger
                showQuickJumper
                onChange={(page, pageSize) => patchQuery({ page, page_size: pageSize })}
                size="small"
              />
            </div>
          </div>
        </div>
        </div>

        {/* 抽屉组件（在页面根容器外） */}
        <EquipmentDrawer onRefresh={() => { refreshList(); refreshStatistics(); }} />
        <LocationDrawer onRefresh={() => { refreshTaxonomy(); refreshStatistics(); }} />
        <RepairDrawer
          equipments={equipments.map(e => ({
            id: e.id, asset_no: e.asset_no, name: e.name,
          }))}
          symptoms={failureCodes.symptoms}
          onRefresh={refreshList}
        />
        <ColumnConfigModal
          open={columnConfigOpen}
          onClose={() => setColumnConfigOpen(false)}
          onSave={(cols: string[]) => setVisibleColumns(cols)}
        />
        <EquipmentImportModal
          open={importOpen}
          onClose={() => setImportOpen(false)}
          onSuccess={refreshList}
        />
      </App>
    </ConfigProvider>
  )
}
