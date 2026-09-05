
'use client'

import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { Spin, Result, Button } from 'antd'
import SopContentEditor from '@/components/safety/SopContentEditor'
import { getRegulation } from '@/actions/safety'
import type { OperationRegulation } from '@/types/safety'

export default function SopDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string




  const { data: regData, isLoading: loading, error: queryError, refetch } = useQuery({
    queryKey: ['safety-regulation', id],
    queryFn: async () => {
      const response = await getRegulation(id)
      if (response.code === 200 && response.data) {
        const data = response.data as OperationRegulation
        return {
          regulationId: data.id,
          regulationName: data.regulation_name || '标准化操规',
          content: data.content || '',
        }
      }
      return null
    },
  })

  const error = queryError?.message || (!loading && !regData ? '未找到该操规记录' : null)

  const handleBack = useCallback(() => {
    router.push('/safety/regulation/generator')
  }, [router])

  const handleSaved = useCallback(() => {
    // Content saved; no additional action needed
  }, [])

  /* ── loading ── */
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <Spin size="large" description="加载操规内容..." />
      </div>
    )
  }

  /* ── error ── */
  if (error || !regData) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '80vh' }}>
        <Result
          status="error"
          title="加载失败"
          subTitle={error || '未找到该操规记录'}
          extra={[
            <Button key="back" onClick={handleBack}>返回列表</Button>,
            <Button key="retry" type="primary" onClick={() => refetch()}>重新加载</Button>,
          ]}
        />
      </div>
    )
  }

  /* ── editor ── */
  return (
    <div style={{
      position: 'absolute',
      top: 0, left: 0, right: 0, bottom: 0,
    }}>
      <SopContentEditor
        regulationId={regData.regulationId}
        regulationName={regData.regulationName}
        content={regData.content}
        onBack={handleBack}
        onSaved={handleSaved}
      />
    </div>
  )
}
