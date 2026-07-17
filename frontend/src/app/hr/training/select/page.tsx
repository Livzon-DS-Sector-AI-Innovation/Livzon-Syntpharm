export const dynamic = 'force-dynamic'

import { fetchTrainingSelectTask } from '@/lib/api/server/hr'
import TrainingSelectClient from '@/components/hr/TrainingSelectClient'

export default async function TrainingSelectPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>
}) {
  const { token } = await searchParams

  if (!token) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-500">缺少任务令牌，请从飞书消息中点击链接进入。</p>
      </div>
    )
  }

  let taskData: any = null
  try {
    const res = await fetchTrainingSelectTask(token)
    taskData = res.data
  } catch {
    // Ignore errors, taskData will remain null
  }

  if (!taskData) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-500">任务已过期或不存在，请重新发送选择任务。</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        <TrainingSelectClient token={token} initialData={taskData} />
      </div>
    </div>
  )
}
