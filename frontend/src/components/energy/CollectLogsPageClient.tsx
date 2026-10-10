'use client'

import { useState, useCallback } from 'react'
import { Select, Button } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { useEnergyStore } from '@/stores/energy'
import { CollectLogTable } from './CollectLogTable'
import { CollectLogDetailDrawer } from './CollectLogDetailDrawer'
import { getCollectLogs, triggerCollect } from '@/actions/energy'
import { CollectLog, PaginatedResponse } from '@/types/energy'

export function CollectLogsPageClient() {
  const {
    logFilters,
    setLogFilters,
    resetLogFilters,
    collectLogDrawerOpen,
    collectLogDrawerId,
    closeCollectLogDrawer,
  } = useEnergyStore()

  const [loading, setLoading] = useState(false)
  const [triggerLoading, setTriggerLoading] = useState(false)
  const [data, setData] = useState<PaginatedResponse<CollectLog>>({
    items: [],
    total: 0,
    page: 1,
    page_size: 10,
  })

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const result = await getCollectLogs(logFilters)
      setData(result)
    } catch (error) {
      console.error('获取采集日志失败:', error)
    } finally {
      setLoading(false)
    }
  }, [logFilters])

  const handleTriggerCollect = async () => {
    setTriggerLoading(true)
    try {
      await triggerCollect()
      fetchData()
    } catch (error) {
      console.error('触发采集失败:', error)
    } finally {
      setTriggerLoading(false)
    }
  }

  const handleRetry = async (platformCode: string) => {
    try {
      await triggerCollect(platformCode)
      fetchData()
    } catch (error) {
      console.error('触发重试失败:', error)
    }
  }

  const filledInputStyle = { background: '#f6f5f4', border: 'none', borderRadius: 8, height: 36 }

  return (
    <div style={{ padding: '28px 32px', maxWidth: 1280, minHeight: '100%', background: '#fafaf9' }}>
      <h1 style={{ fontSize: 28, fontWeight: 500, color: '#1a1a1a', margin: 0, letterSpacing: '-0.3px', lineHeight: 1.3 }}>
        采集日志
      </h1>
      <p style={{ fontSize: 13, color: '#a4a097', margin: '4px 0 0', lineHeight: 1.5 }}>
        查看数据采集任务的执行记录与结果详情
      </p>

      <div style={{ height: 1, marginTop: 18, marginBottom: 20, background: 'linear-gradient(to right, #5645d4 0%, #e6e0f5 40%, transparent 100%)' }} />

      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', background: '#ffffff', borderRadius: 12, padding: '12px 18px', boxShadow: '0 1px 3px rgba(10, 10, 10, 0.04)', border: '1px solid #ede9e4', marginBottom: 20 }}>
        <Select
          placeholder="采集状态"
          allowClear
          variant="filled"
          style={{ width: 120, ...filledInputStyle }}
          value={logFilters.status}
          onChange={(value) => setLogFilters({ status: value, page: 1 })}
          options={[
            { label: '成功', value: 'success' },
            { label: '失败', value: 'failed' },
            { label: '部分成功', value: 'partial' },
          ]}
        />
        <Button
          onClick={resetLogFilters}
          style={{ color: '#787671', borderRadius: 8, height: 36, fontSize: 13, fontWeight: 500 }}
        >
          重置
        </Button>
        <div style={{ flex: 1 }} />
        <Button
          icon={<ThunderboltOutlined />}
          onClick={handleTriggerCollect}
          loading={triggerLoading}
          style={{ color: '#5645d4', borderColor: '#5645d4', borderRadius: 8, fontWeight: 500, fontSize: 14, height: 36, padding: '0 16px' }}
        >
          手动采集
        </Button>
      </div>

      <CollectLogTable data={data.items} loading={loading} total={data.total} onRefresh={fetchData} onRetry={handleRetry} />

      {collectLogDrawerOpen && collectLogDrawerId && (
        <CollectLogDetailDrawer logId={collectLogDrawerId} open={collectLogDrawerOpen} onClose={closeCollectLogDrawer} />
      )}
    </div>
  )
}
