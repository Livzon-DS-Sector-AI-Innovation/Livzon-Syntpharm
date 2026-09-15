'use client'

import '../../../../styles/industrial-theme.css';
import { useEffect, useCallback, useMemo, useRef, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { App, ConfigProvider, Tabs, Button, Pagination } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { MenuFoldOutlined, MenuUnfoldOutlined, ReloadOutlined } from '@ant-design/icons'
import { EquipmentCategory, Location, Equipment, EquipmentStatistics } from '@/types/equipment/generated-bridge'
import { useEquipmentStore } from '@/stores/equipment'
import { antdTheme } from '@/lib/antd-theme'
import { fetchEquipmentsClient, fetchEquipmentStatisticsClient, fetchCategoriesClient, fetchLocationsClient, fetchDepartmentsClient } from '@/lib/api/client/equipment'
import {
  DEFAULT_EQUIPMENT_SORT_BY,
  DEFAULT_EQUIPMENT_SORT_ORDER,
  parseEquipmentUrlParams,
  writeEquipmentUrlQuery,
  type EquipmentUrlState,
} from '@/lib/api/equipment-query'
import { message, Upload } from 'antd'
import type { UploadProps } from 'antd'
import { CategoryTree, ColumnConfigModal, EquipmentDrawer, EquipmentFilterBar, EquipmentImportModal, EquipmentTable, ExcelSyncButton, LocationDrawer, LocationTree, RepairDrawer, StatsCards } from '@/components/equipment'

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
    categories,
    locations,
    statistics,
    equipments,
    failureCodes,
    selectedCategory,
    selectedLocation,
    statusFilter,
    departmentFilter,
    departments,
    keyword,
    total,
    loading,
    openEquipmentDrawer,
    setSelectedCategory,
    setSelectedLocation,
    setCategories,
    setLocations,
    setEquipments,
    setStatistics,
    setTotal,
    setLoading,
    setDepartments,
  } = useEquipmentStore()

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [initialized, setInitialized] = useState(false)
  const [columnConfigOpen, setColumnConfigOpen] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  const [visibleColumns, setVisibleColumns] = useState<string[]>(DEFAULT_VISIBLE_COLUMNS)
  const toolbarRef = useRef<HTMLDivElement>(null)
  // sticky 表头的 top 偏移 = 工具栏实测高度；ResizeObserver 挂载即回调，初值仅为首帧兜底
  const [toolbarH, setToolbarH] = useState(96)

  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  // 排序与分页以 URL 为唯一来源（可分享、刷新保持）；筛选条件仍由 store 单一持有
  const { state: urlState, rejectedSort } = useMemo(() => parseEquipmentUrlParams(searchParams), [searchParams])

  const patchQuery = useCallback((patch: Partial<EquipmentUrlState>) => {
    const nextQs = writeEquipmentUrlQuery(new URLSearchParams(searchParams.toString()), { ...urlState, ...patch })
    router.replace(nextQs ? `${pathname}?${nextQs}` : pathname, { scroll: false })
  }, [pathname, router, searchParams, urlState])

  // 测量 sticky 工具栏高度：数值经 state 传给 Table 的 sticky.offsetHeader，
  // 同步写 CSS 变量 `--equipment-toolbar-h` 供侧边栏 sticky top 使用，三层粘性叠放整齐。
  // 仅在挂载时挂一次 observer；卸载时移除 CSS 变量与监听器。
  useEffect(() => {
    const el = toolbarRef.current
    if (!el) return
    const apply = () => {
      const h = el.getBoundingClientRect().height
      setToolbarH(h)
      document.documentElement.style.setProperty('--equipment-toolbar-h', `${h}px`)
    }
    apply()
    const observer = new ResizeObserver(apply)
    observer.observe(el)
    return () => {
      observer.disconnect()
      document.documentElement.style.removeProperty('--equipment-toolbar-h')
    }
  }, [])

  // 列配置：从 localStorage 加载首次挂载时的可见列。EquipmentTable 受控展示。
  useEffect(() => {
    try {
      const stored = localStorage.getItem('equipment_visible_columns')
      if (stored) {
        const parsed = JSON.parse(stored)
        if (Array.isArray(parsed) && parsed.length > 0) {
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

  // 初始化 store 数据（包含 SSR 数据）- 只在首次加载时执行
  useEffect(() => {
    if (!initialized) {
      setCategories(initialCategories)
      setLocations(initialLocations)
      setEquipments(initialEquipments)
      setTotal(initialTotal)
      setStatistics(initialStatistics)
      setInitialized(true)
    }
  }, [initialized, initialCategories, initialLocations, initialEquipments, initialTotal, initialStatistics, setCategories, setLocations, setEquipments, setTotal, setStatistics])

  // 初始化部门列表（服务端数据）
  useEffect(() => {
    setDepartments(initialDepartments)
  }, [initialDepartments, setDepartments])

  // 客户端补偿加载：如果服务端初始数据为空（某个 API 失败导致），从客户端重新获取
  useEffect(() => {
    const loadMissing = async () => {
      const tasks: Promise<void>[] = []
      if (!categories.length) {
        tasks.push(
          fetchCategoriesClient().then((cats: any[]) => { setCategories(cats) }).catch((e: any) => { console.warn('客户端加载分类失败:', e) })
        )
      }
      if (!locations.length) {
        tasks.push(
          fetchLocationsClient().then((locs: any[]) => { setLocations(locs) }).catch((e: any) => { console.warn('客户端加载位置失败:', e) })
        )
      }
      if (!departments.length) {
        tasks.push(
          fetchDepartmentsClient().then((depts: any[]) => { setDepartments(depts) }).catch((e: any) => { console.warn('客户端加载部门失败:', e) })
        )
      }
      if (tasks.length) {
        await Promise.allSettled(tasks)
      }
    }
    loadMissing()
  }, [categories.length, locations.length, departments.length, setCategories, setLocations, setDepartments])

  // 列表取数：排序与分页来自 URL，筛选来自 store，二者在此合成唯一一份请求参数
  const fetchData = useCallback(async (state: EquipmentUrlState) => {
    setLoading(true)
    try {
      const equipmentsResponse = await fetchEquipmentsClient({
        category_id: selectedCategory,
        location_id: selectedLocation,
        department_id: departmentFilter,
        status: statusFilter || undefined,
        keyword: keyword || undefined,
        sort_by: state.sort_by,
        sort_order: state.sort_order,
        page: state.page,
        page_size: state.page_size,
      })
      setEquipments(equipmentsResponse.items)
      setTotal(equipmentsResponse.total)
    } catch (error) {
      console.error('获取设备数据失败:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedCategory, selectedLocation, departmentFilter, statusFilter, keyword, setEquipments, setTotal, setLoading])

  // 数据变更后重取当前页（新增/编辑/删除/导入完成）
  const refreshList = useCallback(() => fetchData(urlState), [fetchData, urlState])

  // 单独刷新统计（根据当前筛选条件）
  const refreshStatistics = useCallback(async () => {
    try {
      const stats = await fetchEquipmentStatisticsClient({
        category_id: selectedCategory || undefined,
        location_id: selectedLocation || undefined,
        department_id: departmentFilter || undefined,
        status: statusFilter || undefined,
      })
      setStatistics(stats)
    } catch { /* 静默 */ }
  }, [selectedCategory, selectedLocation, departmentFilter, statusFilter, setStatistics])

  // 筛选条件变化时自动刷新统计
  useEffect(() => {
    refreshStatistics()
  }, [selectedCategory, selectedLocation, departmentFilter, statusFilter, refreshStatistics])

  // 刷新分类和位置树
  const refreshCategoriesAndLocations = useCallback(async () => {
    try {
      const [cats, locs] = await Promise.all([fetchCategoriesClient(), fetchLocationsClient()])
      setCategories(cats)
      setLocations(locs)
    } catch (error) {
      console.error('刷新分类/位置失败:', error)
    }
  }, [setCategories, setLocations])

  // 筛选变化 → 回到第 1 页；URL 与 store 共同决定取数，fetchData 必须在依赖内
  const filterSignature = `${selectedCategory ?? ''}|${selectedLocation ?? ''}|${departmentFilter ?? ''}|${statusFilter}|${keyword ?? ''}`
  const previousFilters = useRef(filterSignature)
  const lastFetchKey = useRef('')

  useEffect(() => {
    const filtersChanged = previousFilters.current !== filterSignature
    previousFilters.current = filterSignature
    const state: EquipmentUrlState = filtersChanged ? { ...urlState, page: 1 } : urlState
    const fetchKey = `${filterSignature}|${state.page}|${state.page_size}|${state.sort_by}|${state.sort_order}`
    if (fetchKey === lastFetchKey.current) return
    lastFetchKey.current = fetchKey
    // 已按第 1 页取数，但 URL 仍停在旧页码时补一次写回，使地址栏与实际视图一致
    if (filtersChanged && urlState.page !== 1) patchQuery({ page: 1 })
    fetchData(state)
  }, [filterSignature, urlState, patchQuery, fetchData])

  const tabItems = [
    {
      key: 'category',
      label: '分类',
      children: <CategoryTree categories={categories} onRefresh={refreshCategoriesAndLocations} />,
    },
    {
      key: 'location',
      label: '位置',
      children: <LocationTree locations={locations} onRefresh={refreshCategoriesAndLocations} />,
    },
  ]

  const syncButton = <ExcelSyncButton />
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

  const currentStats = statistics ?? initialStatistics

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
          ref={toolbarRef}
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
                loading={loading}
                page={urlState.page}
                pageSize={urlState.page_size}
                sortBy={urlState.sort_by}
                sortOrder={urlState.sort_order}
                onQueryChange={patchQuery}
                onRefresh={refreshList}
                onRefreshStatistics={refreshStatistics}
                visibleColumns={visibleColumns}
                onVisibleColumnsChange={setVisibleColumns}
                stickyTop={0}
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
        <LocationDrawer onRefresh={() => { refreshCategoriesAndLocations(); refreshStatistics(); }} />
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
