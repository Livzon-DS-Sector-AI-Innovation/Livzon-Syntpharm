
'use client'

import { useState, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, useRouter } from 'next/navigation'
import { Spin, Result, Button, App } from 'antd'
import SopContentEditor from '@/components/safety/SopContentEditor'
import { getRegulation, reviseRegulation } from '@/actions/safety'
import type { OperationRegulation } from '@/types/safety'

export default function RegulationRevisePage() {
  const params = useParams()
  const router = useRouter()
  const id = params.id as string
  const { message } = App.useApp()




  const { data: regData, isLoading: loading, error: queryError, refetch } = useQuery({
    queryKey: ['safety-regulation-revise', id],
    queryFn: async () => {
      const response = await getRegulation(id)
      if (response.code === 200 && response.data) {
        const data = response.data as OperationRegulation
        if (!data.content) {
          throw new Error('该操规尚未生成标准化内容，无法在线修订。请先上传旧版操规进行标准化生成。')
        }
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
    router.push('/safety/regulation')
  }, [router])

  const handleReviseSave = useCallback(
    async (content: string, revisionOpinion: string) => {
      const response = await reviseRegulation(id, content, revisionOpinion || undefined)
      if (response.code === 200) {
        message.success(`修订保存成功，已生成修订记录 ${response.data?.revision_no || ''}`)
      } else {
        throw new Error(response.message || '修订保存失败')
      }
    },
    [id, message],
  )

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
          title="无法修订"
          subTitle={error || '未找到该操规记录'}
          extra={[
            <Button key="back" onClick={handleBack}>返回列表</Button>,
            <Button key="retry" type="primary" onClick={() => refetch()}>重新加载</Button>,
          ]}
        />
      </div>
    )
  }

  /* ── editor in revision mode ── */
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
        onSaved={() => {
          // Navigate back after save
          router.push('/safety/regulation')
        }}
        revisionMode
        onReviseSave={handleReviseSave}
      />
    </div>
  )
}
