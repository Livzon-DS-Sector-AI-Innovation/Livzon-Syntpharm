import { FeishuConfigClient } from '@/components/warehouse'
import {
  fetchWarehouseFeishuConfig,
  fetchWarehouseFeishuTables,
} from '@/lib/api/server/warehouse'
import type { WarehouseFeishuConfig, WarehouseFeishuTable } from '@/types/warehouse'

export const dynamic = 'force-dynamic'

const emptyConfig: WarehouseFeishuConfig = {
  id: null,
  config_name: '仓储飞书配置',
  app_id: '',
  bitable_app_token: null,
  finished_product_app_token: null,
  materials_packaging_app_token: null,
  hardware_app_token: null,
  is_active: true,
  remark: null,
  app_secret_configured: false,
  app_secret_masked: '',
  created_at: null,
  updated_at: null,
}

export default async function WarehouseFeishuConfigPage() {
  let initialConfig = emptyConfig
  let initialTables: WarehouseFeishuTable[] = []

  try {
    initialConfig = await fetchWarehouseFeishuConfig()
  } catch (error) {
    console.warn('仓储飞书配置初始数据加载失败，使用空配置降级:', error)
  }

  try {
    initialTables = await fetchWarehouseFeishuTables()
  } catch (error) {
    console.warn('仓储飞书表目录初始数据加载失败，使用空列表降级:', error)
  }

  return (
    <FeishuConfigClient
      initialConfig={initialConfig}
      initialTables={initialTables}
    />
  )
}
